#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import concurrent.futures
import json
import logging
import os

# 導入相關模塊
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .database import Database
from .hourly_data import HourlyDataHandler

sys.path.append(os.path.dirname(__file__))
import threading
import xml.etree.ElementTree as ET

import requests
import typer

from .. import config
from ..utils.rich_console import console

logger = logging.getLogger(__name__)


class GSCClient:
    def __init__(self, db: Database):
        """初始化 GSC 客戶端"""
        self.scopes = config.GSC_SCOPES
        self.credentials_path = str(config.get_credentials_path())
        self.client_config_path = str(config.CLIENT_SECRET_PATH)

        # 初始化狀態
        self.credentials: Optional[Credentials] = None
        self.service: Optional[Any] = None
        self.database = db

        # API 使用計數器
        self.api_requests_today = 0
        self.api_requests_this_minute = 0
        self.last_minute_reset = datetime.now().replace(second=0, microsecond=0)
        self.today = datetime.now().date()
        self._api_lock = threading.Lock()

        # 從數據庫載入今日API使用計數
        self._load_api_usage_from_db()

        # 嘗試加載已有憑證，如果成功則初始化 service
        if self._load_credentials():
            self.service = build("searchconsole", "v1", credentials=self.credentials)

        # OAuth 配置
        self.client_config = self._load_client_config()
        current_port = os.getenv("PORT", "8000")
        if "web" in self.client_config:
            self.client_config["web"]["redirect_uris"] = [
                f"http://localhost:{current_port}/auth/callback"
            ]

        # 初始化每小時數據處理器
        self.hourly_handler = None
        if self.service:
            self.hourly_handler = HourlyDataHandler(self.service, self.database)

    def authenticate(self) -> bool:
        """
        執行完整的認證流程。

        1. 檢查現有憑證是否有效。
        2. 如果無效，啟動控制台 OAuth 流程。
        3. 獲取新的憑證並保存。

        Returns:
            如果最終認證成功則返回 True，否則返回 False。
        """
        if self.is_authenticated():
            console.print("✅ 已使用現有有效憑證進行認證。")
            return True

        console.print("🚀 [bold yellow]需要新的認證，啟動 OAuth2 流程...[/bold yellow]")
        auth_url = self.get_auth_url()

        console.print("\n1. 請將以下 URL 複製到您的瀏覽器中打開，並登入您的 Google 帳戶進行授權：")
        console.print(f"\n[link={auth_url}]{auth_url}[/link]\n")

        console.print(
            "2. 授權後，您將被重定向到一個無法打開的頁面 (這是正常的)。"
            "請從該頁面的瀏覽器地址欄中，複製 `code=` 後面的所有內容。"
        )

        auth_code = typer.prompt("3. 請在此處貼上您複製的授權碼 (code)")

        if not auth_code:
            console.print("[bold red]❌ 未提供授權碼，認證已取消。[/bold red]")
            return False

        console.print("\n⏳ [cyan]正在使用授權碼換取憑證...[/cyan]")
        if self.handle_oauth_callback(auth_code.strip()):
            console.print("[bold green]✅ 認證成功！憑證已保存。[/bold green]")
            return True
        else:
            console.print("[bold red]❌ 認證失敗。請檢查您的授權碼或配置。[/bold red]")
            return False

    def stream_site_data(self, site_url: str, start_date: str, end_date: str):
        """
        以流式方式從 GSC API 獲取數據，作為一個 generator。
        優化：遍歷 search_type，但在單個請求中包含 device 維度，以減少請求總數。
        """
        if not self.is_authenticated() or not self.service:
            raise Exception("GSC service not initialized")

        search_types = ["web", "image", "video", "news", "discover", "googleNews"]

        for search_type in search_types:
            start_row = 0
            while True:
                try:
                    request_body = {
                        "startDate": start_date,
                        "endDate": end_date,
                        "dimensions": ["page", "query", "device"],
                        "rowLimit": 25000,
                        "startRow": start_row,
                        "type": search_type,
                    }

                    response = (
                        self.service.searchanalytics()
                        .query(siteUrl=site_url, body=request_body)
                        .execute()
                    )

                    self._track_api_request()

                    rows = response.get("rows", [])
                    if not rows:
                        break

                    device_chunks: Dict[str, List[Dict[str, Any]]] = {}
                    for row in rows:
                        dimensions = request_body["dimensions"]
                        row_keys = row["keys"]
                        # 確保類型正確
                        keys = dict(zip(dimensions, row_keys)) if dimensions and row_keys else {}  # type: ignore  # type: ignore
                        device = keys.get("device", "N/A")

                        if device not in device_chunks:
                            device_chunks[device] = []

                        processed_row = {
                            "page": keys.get("page"),
                            "query": keys.get("query"),
                            "clicks": row.get("clicks"),
                            "impressions": row.get("impressions"),
                            "ctr": row.get("ctr"),
                            "position": row.get("position"),
                        }
                        device_chunks[device].append(processed_row)

                    for device, chunk in device_chunks.items():
                        yield device, search_type, chunk

                    if len(rows) < 25000:
                        break

                    start_row += 25000

                except HttpError as e:
                    if e.resp.status in [404, 403, 400]:
                        logger.warning(
                            f"No data or unsupported type for {site_url} with type "
                            f"{search_type} for date {start_date} (HTTP {e.resp.status}). Skipping."
                        )
                        break
                    logger.error(f"HTTP error for type {search_type}: {e}", exc_info=True)
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error for type {search_type}: {e}", exc_info=True)
                    raise

    def stream_hourly_data(self, site_url: str, start_date: str, end_date: str):
        """
        以流式方式從 GSC API 獲取每小時的詳細數據。
        此方法根據 2025/04/09 的官方文件進行了修正。
        """
        if not self.is_authenticated() or not self.service:
            raise Exception("GSC service not initialized")

        start_row = 0
        while True:
            try:
                # 根據官方文件修正 request_body
                request_body = {
                    "startDate": start_date,
                    "endDate": end_date,
                    # 關鍵修正 1: dimensions 必須包含 'HOUR'
                    "dimensions": ["HOUR", "query", "page", "device"],
                    # 關鍵修正 2: dataState 必須是 'HOURLY_ALL'
                    "dataState": "HOURLY_ALL",
                    "rowLimit": 25000,
                    "startRow": start_row,
                }

                response = (
                    self.service.searchanalytics()
                    .query(siteUrl=site_url, body=request_body)
                    .execute()
                )

                self._track_api_request()

                rows = response.get("rows", [])
                if not rows:
                    break

                for row in rows:
                    dimensions = request_body["dimensions"]
                    row_keys = row["keys"]
                    # 確保類型正確  # type: ignore
                    keys = dict(zip(dimensions, row_keys)) if dimensions and row_keys else {}  # type: ignore
                    # API 回傳的 'HOUR' 鍵是一個完整的 ISO 8601 時間戳
                    dt_str = keys.get("HOUR", "")
                    if not dt_str:
                        continue

                    dt_obj = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

                    yield {
                        "query": keys.get("query"),
                        "page": keys.get("page"),
                        "device": keys.get("device"),
                        "date": dt_obj.strftime("%Y-%m-%d"),
                        "hour": dt_obj.hour,
                        "hour_timestamp": dt_obj.isoformat(),
                        "clicks": row.get("clicks", 0),
                        "impressions": row.get("impressions", 0),
                        "ctr": row.get("ctr", 0),
                        "position": row.get("position", 0),
                    }

                if len(rows) < 25000:
                    break

                start_row += 25000

            except HttpError as e:
                logger.error(f"獲取每小時數據時發生 HTTP 錯誤: {e}", exc_info=True)
                break
            except Exception as e:
                logger.error(f"獲取每小時數據時發生意外錯誤: {e}", exc_info=True)
                break

    def _load_client_config(self) -> Dict[str, Any]:
        """載入 Google OAuth 客戶端配置"""
        try:
            with open(self.client_config_path, "r") as f:
                config_data = json.load(f)
                # 確保返回正確的類型
                return dict(config_data) if isinstance(config_data, dict) else {"web": {}}
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load client config from {self.client_config_path}: {e}")
            return {"web": {}}

    def get_auth_url(self) -> str:
        """獲取OAuth認證URL"""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.scopes,
            redirect_uri=self.client_config["web"]["redirect_uris"][0],
        )

        auth_url, _ = flow.authorization_url(
            access_type="offline", include_granted_scopes="false", prompt="consent"
        )

        return str(auth_url)

    def handle_oauth_callback(self, code: str) -> bool:
        """處理OAuth回調"""
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=self.client_config["web"]["redirect_uris"][0],
            )

            flow.fetch_token(code=code)
            if flow.credentials:
                self.credentials = flow.credentials  # type: ignore
                self._save_credentials()

                # 初始化服務和每小時處理器
                self.service = build("searchconsole", "v1", credentials=self.credentials)
                self.hourly_handler = HourlyDataHandler(self.service, self.database)

                logger.info("OAuth authentication successful")
                return True

        except Exception as e:
            logger.error(f"OAuth callback failed: {e}")

        return False

    def _save_credentials(self):
        """保存認證資訊到文件"""
        if self.credentials:
            creds_data = {
                "token": self.credentials.token,
                "refresh_token": self.credentials.refresh_token,
                "token_uri": self.credentials.token_uri,
                "client_id": self.credentials.client_id,
                "client_secret": self.credentials.client_secret,
                "scopes": self.credentials.scopes,
            }
            try:
                os.makedirs(os.path.dirname(self.credentials_path), exist_ok=True)
                with open(self.credentials_path, "w") as f:
                    json.dump(creds_data, f)
                logger.info(f"Credentials saved to {self.credentials_path}")
            except Exception as e:
                logger.error(f"Failed to save credentials to {self.credentials_path}: {e}")

    def _load_credentials(self) -> bool:
        """
        從文件加載憑證。如果憑證過期且有刷新令牌，則嘗試刷新。
        """
        if os.path.exists(self.credentials_path):
            try:
                with open(self.credentials_path, "r") as f:
                    creds_data = json.load(f)
                    self.credentials = Credentials.from_authorized_user_info(
                        creds_data, self.scopes
                    )

                # 檢查憑證是否過期，如果過期且有刷新令牌，則刷新
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    logger.info("Credentials expired, attempting to refresh...")
                    self.credentials.refresh(Request())
                    self._save_credentials()  # 保存刷新後的憑證
                    logger.info("Credentials refreshed successfully.")

                return self.credentials is not None and self.credentials.valid

            except Exception as e:
                logger.error(f"Failed to load or refresh credentials: {e}")
                self.credentials = None
                return False
        return False

    def is_authenticated(self) -> bool:
        """檢查是否已認證"""
        if not self.credentials:
            self._load_credentials()

        if self.credentials:
            if self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                    self._save_credentials()
                    return True
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    return False

            return not self.credentials.expired

        return False

    def get_sites(self) -> List[str]:
        """獲取GSC中的站點列表"""
        if not self.is_authenticated():
            raise Exception("Not authenticated with GSC")

        if self.service is None:
            raise Exception("GSC service not initialized")

        try:
            sites_response = self.service.sites().list().execute()
            sites = []

            for site in sites_response.get("siteEntry", []):
                if site["permissionLevel"] in ["siteFullUser", "siteOwner"]:
                    sites.append(site["siteUrl"])

            return sites

        except HttpError as e:
            logger.error(f"Failed to get sites: {e}")
            return []

    def get_sitemaps(self, site_url: str) -> List[Dict[str, Any]]:
        """獲取站點的索引頁面（sitemap）列表"""
        if not self.is_authenticated():
            raise Exception("Not authenticated with GSC")

        if self.service is None:
            raise Exception("GSC service not initialized")

        try:
            sitemaps_response = self.service.sitemaps().list(siteUrl=site_url).execute()
            sitemaps = sitemaps_response.get("sitemap", [])
            return list(sitemaps) if sitemaps else []

        except HttpError as e:
            logger.error(f"Failed to get sitemaps for {site_url}: {e}")
            return []

    def get_sitemap_details(self, site_url: str, feedpath: str) -> Dict[str, Any]:
        """獲取特定索引頁面的詳細信息"""
        if not self.is_authenticated():
            raise Exception("Not authenticated with GSC")

        if self.service is None:
            raise Exception("GSC service not initialized")

        try:
            sitemap_response = (
                self.service.sitemaps().get(siteUrl=site_url, feedpath=feedpath).execute()
            )
            return dict(sitemap_response) if sitemap_response else {}

        except HttpError as e:
            logger.error(f"Failed to get sitemap details for {site_url}/{feedpath}: {e}")
            return {}

    def get_all_sitemaps_for_sites(self, site_urls: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """批量獲取多個站點的索引頁面"""
        if not self.is_authenticated():
            raise Exception("Not authenticated with GSC")

        if self.service is None:
            raise Exception("GSC service not initialized")

        results = {}

        for site_url in site_urls:
            try:
                sitemaps = self.get_sitemaps(site_url)
                results[site_url] = sitemaps
                logger.info(f"Retrieved {len(sitemaps)} sitemaps for {site_url}")
            except Exception as e:
                logger.error(f"Failed to get sitemaps for {site_url}: {e}")
                results[site_url] = []

        return results

    def get_indexed_pages_count(self, site_url: str) -> Dict[str, Any]:
        """獲取站點的索引頁面統計信息"""
        if not self.is_authenticated():
            raise Exception("Not authenticated with GSC")

        if self.service is None:
            raise Exception("GSC service not initialized")

        try:
            # 獲取 sitemap 列表
            sitemaps = self.get_sitemaps(site_url)

            total_pages = 0
            sitemap_details = []

            for sitemap in sitemaps:
                feedpath = sitemap.get("path", "")
                if feedpath:
                    details = self.get_sitemap_details(site_url, feedpath)
                    if details:
                        contents = details.get("contents", [])
                        for content in contents:
                            if "submitted" in content:
                                submitted_count = content["submitted"]
                                if isinstance(submitted_count, (int, float)):
                                    total_pages += int(submitted_count)

                        sitemap_details.append(
                            {
                                "path": feedpath,
                                "lastSubmitted": sitemap.get("lastSubmitted"),
                                "contents": contents,
                            }
                        )

            return {
                "site_url": site_url,
                "total_sitemaps": len(sitemaps),
                "total_indexed_pages": total_pages,
                "sitemap_details": sitemap_details,
            }

        except Exception as e:
            logger.error(f"Failed to get indexed pages count for {site_url}: {e}")
            return {
                "site_url": site_url,
                "total_sitemaps": 0,
                "total_indexed_pages": 0,
                "sitemap_details": [],
            }

    def get_url_inspection(self, site_url: str, inspection_url: str) -> Dict[str, Any]:
        """使用 URL Inspection API 檢查特定 URL 的索引狀態"""
        if not self.is_authenticated():
            raise Exception("Not authenticated with GSC")

        if self.service is None:
            raise Exception("GSC service not initialized")

        try:
            request = {"inspectionUrl": inspection_url, "siteUrl": site_url}

            response = self.service.urlInspection().index().inspect(request).execute()
            return dict(response) if response else {}

        except HttpError as e:
            logger.error(f"獲取 URL 檢查結果時出錯: {e}")
            return {"error": str(e)}

    def get_sample_pages_from_analytics(
        self, site_url: str, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """
        [重構] 從搜索分析中獲取頁面樣本數據，以近似模擬索引覆蓋情況。
        原名 get_index_coverage_report，已重命名以更準確地反映其功能。
        """
        if not self.service:
            logger.error("GSC service is not initialized.")
            return {"error": "GSC service not initialized."}
        try:
            # 使用 searchanalytics API 獲取一段時間內的頁面數據
            response = (
                self.service.searchanalytics()
                .query(
                    siteUrl=site_url,
                    body={
                        "startDate": start_date,
                        "endDate": end_date,
                        "dimensions": ["page"],
                        "rowLimit": 500,  # 獲取一個樣本量
                    },
                )
                .execute()
            )
            self._track_api_request()
            return dict(response) if response else {}
        except Exception as e:
            logger.error(f"從搜索分析獲取頁面樣本時出錯: {e}")
            return {"error": str(e)}

    def get_crawl_stats(self, site_url: str) -> Dict[str, Any]:
        """
        [NEW] 獲取指定站點的抓取統計信息。
        """
        if not self.service:
            raise Exception("GSC service not initialized")

        try:
            response = self.service.urlcrawlerrorscounts().query(siteUrl=site_url).execute()
            self._track_api_request()
            return dict(response) if response else {}
        except HttpError as e:
            logger.error(f"Failed to get crawl stats for {site_url}: {e}")
            return {"error": str(e), "status": e.resp.status}
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching crawl stats: {e}")
            return {"error": str(e)}

    def get_indexed_pages_via_search_analytics(
        self, site_url: str, start_date: Optional[str], end_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        """通過搜索分析數據獲取索引頁面列表"""
        if not self.is_authenticated() or not self.service:
            raise Exception("GSC service not initialized")

        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        try:
            # 獲取頁面維度的數據
            pages_data = self.get_search_analytics_batch(
                site_url, start_date, end_date, dimensions=["page"]
            )

            indexed_pages = []
            for row in pages_data:
                page = row.get("keys", [""])[0]
                if page:
                    indexed_pages.append(
                        {
                            "page": page,
                            "clicks": row.get("clicks", 0),
                            "impressions": row.get("impressions", 0),
                            "ctr": row.get("ctr", 0),
                            "position": row.get("position", 0),
                        }
                    )

            return indexed_pages

        except HttpError as e:
            logger.error(f"Failed to get indexed pages via search analytics for {site_url}: {e}")
            return []

    def get_all_indexed_pages(
        self,
        site_url: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """獲取站點的所有索引頁面信息（綜合方法）"""

        # 確保日期不為 None
        final_start_date = start_date or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        final_end_date = end_date or datetime.now().strftime("%Y-%m-%d")

        try:
            # 1. 獲取 sitemap 信息
            sitemap_info = self.get_indexed_pages_count(site_url)

            # 2. 獲取搜索分析中的索引頁面
            search_analytics_pages = self.get_indexed_pages_via_search_analytics(
                site_url, final_start_date, final_end_date
            )

            # 3. 獲取爬蟲統計
            crawl_stats = self.get_crawl_stats(site_url)

            return {
                "site_url": site_url,
                "date_range": f"{final_start_date} to {final_end_date}",
                "sitemap_info": sitemap_info,
                "search_analytics_pages": search_analytics_pages,
                "crawl_stats": crawl_stats,
                "total_pages_from_search": len(search_analytics_pages),
                "total_pages_from_sitemap": sitemap_info.get("total_indexed_pages", 0),
            }

        except Exception as e:
            logger.error(f"Failed to get all indexed pages for {site_url}: {e}")
            return {"site_url": site_url, "error": str(e)}

    def get_sitemap_urls_for_site(self, site_url: str) -> List[str]:
        """
        獲取一個站點所有 sitemaps 中的所有 URL。
        此方法現在統一使用 get_sitemap_urls，並移除了對 parse_sitemap_xml 的依賴。
        """
        all_urls = set()
        try:
            # 首先從 robots.txt 獲取 sitemaps
            sitemap_paths = self.get_sitemaps_from_robots(site_url)

            # 如果 robots.txt 中沒有，則嘗試從 GSC API 獲取
            if not sitemap_paths:
                sitemaps = self.get_sitemaps(site_url)
                sitemap_paths = [s["path"] for s in sitemaps]

            # 遍歷所有找到的 sitemap 路徑
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_url = {
                    executor.submit(self.get_sitemap_urls, path): path for path in sitemap_paths
                }
                for future in concurrent.futures.as_completed(future_to_url):
                    try:
                        urls = future.result()
                        all_urls.update(urls)
                    except Exception as exc:
                        logger.error(f"從 sitemap {future_to_url[future]} 獲取 URL 時出錯: {exc}")

            return list(all_urls)
        except Exception as e:
            logger.error(f"為站點 {site_url} 獲取 sitemap URLs 時出錯: {e}")
            return []

    def get_sitemaps_from_robots(self, site_url: str) -> List[str]:
        """從 robots.txt 文件中獲取 sitemap URL"""

        import requests

        try:
            # 構建 robots.txt URL
            if site_url.startswith("sc-domain:"):
                domain = site_url.replace("sc-domain:", "")
                robots_url = f"https://{domain}/robots.txt"
            else:
                # 確保有協議
                if not site_url.startswith(("http://", "https://")):
                    site_url = f"https://{site_url}"
                robots_url = f"{site_url.rstrip('/')}/robots.txt"

            # 獲取 robots.txt 內容
            response = requests.get(robots_url, timeout=30)
            response.raise_for_status()

            # 解析 sitemap 行
            sitemaps = []
            for line in response.text.split("\n"):
                line = line.strip()
                if line.lower().startswith("sitemap:"):
                    sitemap_url = line[8:].strip()
                    if sitemap_url:
                        sitemaps.append(sitemap_url)

            return sitemaps

        except Exception as e:
            logger.warning(f"Failed to get sitemaps from robots.txt for {site_url}: {e}")
            return []

    def get_sitemap_urls(self, sitemap_path: str) -> List[str]:
        """
        遞迴地從 sitemap（或 sitemap 索引）中提取所有 URL。
        這是統一的、健壯的 sitemap 解析器。
        """
        all_urls: List[str] = []

        try:
            logger.info(f"正在處理: {sitemap_path}")
            response = requests.get(sitemap_path, timeout=30)
            response.raise_for_status()

            content = response.content
            root = ET.fromstring(content)

            namespace = ""
            if "}" in root.tag:
                namespace = root.tag.split("}")[0].strip("{")

            # 檢查是 sitemap index 還是 sitemap
            if root.tag.endswith("sitemapindex"):
                logger.info(f"{sitemap_path} 是一個站點地圖索引，正在解析子地圖...")
                sitemap_links = [
                    elem.text
                    for elem in root.findall(f"{{{namespace}}}sitemap/{{{namespace}}}loc")
                    if elem.text
                ]
                for link in sitemap_links:
                    all_urls.extend(self.get_sitemap_urls(link))  # 遞迴調用
            elif root.tag.endswith("urlset"):
                logger.info(f"{sitemap_path} 是一個標準站點地圖，正在解析 URL...")
                urls = [
                    elem.text
                    for elem in root.findall(f"{{{namespace}}}url/{{{namespace}}}loc")
                    if elem.text
                ]
                all_urls.extend(urls)
            else:
                logger.warning(f"未知的根標籤 '{root.tag}' 在 {sitemap_path}")

        except requests.exceptions.RequestException as e:
            logger.error(f"下載站點地圖 {sitemap_path} 失敗: {e}")
        except ET.ParseError as e:
            logger.error(f"解析站點地圖 XML {sitemap_path} 失敗: {e}")
        except Exception as e:
            logger.error(f"處理站點地圖 {sitemap_path} 時發生未知錯誤: {e}")

        # 在遞迴的最外層返回結果
        # 為了避免在遞迴中打印重複日誌，我們只在最頂層調用時打印總數
        # 這需要一個輔助函數或一個調用深度標記，暫時簡化處理
        return all_urls

    def compare_db_and_sitemap(self, site_url: str, site_id: int) -> Dict[str, Any]:
        """比較數據庫中的 URL 和 sitemap 中的 URL"""
        try:
            # 1. [REFACTORED] 從 gsc_performance_data 獲取數據庫中的 URL
            db_urls = set(self.database.get_all_pages_for_site(site_id=site_id))
            if not db_urls:
                logger.warning(f"在數據庫中找不到站點 ID {site_id} 的任何頁面數據。")

            # 2. 獲取 sitemap 中的 URL
            sitemap_urls = set(self.get_sitemap_urls_for_site(site_url))
            if not sitemap_urls:
                logger.warning(f"無法從 {site_url} 的 sitemap 中獲取任何 URL。")

            # 3. 比較差異
            only_in_db = sorted(list(db_urls - sitemap_urls))
            only_in_sitemap = sorted(list(sitemap_urls - db_urls))
            in_both = sorted(list(db_urls & sitemap_urls))

            return {
                "site_url": site_url,
                "db_url_count": len(db_urls),
                "sitemap_url_count": len(sitemap_urls),
                "common_url_count": len(in_both),
                "only_in_db": only_in_db,
                "only_in_sitemap": only_in_sitemap,
                "in_both": in_both,
            }
        except Exception as e:
            logger.error(f"比較數據庫和 sitemap 時出錯: {e}", exc_info=True)
            return {"error": str(e)}

    def get_search_analytics(
        self,
        site_url: str,
        start_date: str,
        end_date: str,
        dimensions: Optional[List[str]] = None,
        row_limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """獲取搜索分析數據"""
        if not self.is_authenticated():
            raise Exception("Not authenticated with GSC")

        if self.service is None:
            raise Exception("GSC service not initialized")

        if dimensions is None:
            dimensions = ["query"]

        try:
            request = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": dimensions,
                "rowLimit": row_limit,
                "startRow": 0,
            }

            response = (
                self.service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            )

            self._track_api_request()  # 追蹤API使用
            rows = response.get("rows", [])
            return list(rows) if rows else []

        except HttpError as e:
            logger.error(f"Failed to get search analytics for {site_url}: {e}")
            return []

    def get_search_analytics_batch(
        self,
        site_url: str,
        start_date: str,
        end_date: str,
        dimensions: Optional[List[str]] = None,
        device_filter: Optional[str] = None,
        max_total_rows: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """批次獲取搜索分析數據"""
        if not self.is_authenticated():
            raise Exception("Not authenticated with GSC")

        if self.service is None:
            raise Exception("GSC service not initialized")

        if dimensions is None:
            dimensions = ["query"]

        all_rows: List[Dict[str, Any]] = []
        max_rows_per_request = 25000
        start_row = 0

        try:
            while max_total_rows is None or len(all_rows) < max_total_rows:
                # 計算這次請求的行數限制
                if max_total_rows is None:
                    row_limit = max_rows_per_request
                else:
                    row_limit = min(max_rows_per_request, max_total_rows - len(all_rows))

                logger.info(
                    f"Requesting batch: startRow={start_row}, rowLimit={row_limit}, "
                    f"total_so_far={len(all_rows)}"
                )

                request = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": dimensions,
                    "rowLimit": row_limit,
                    "startRow": start_row,
                }

                if device_filter:
                    request["dimensionFilterGroups"] = [
                        {
                            "filters": [
                                {
                                    "dimension": "device",
                                    "operator": "equals",
                                    "expression": device_filter,
                                }
                            ]
                        }
                    ]

                response = (
                    self.service.searchanalytics().query(siteUrl=site_url, body=request).execute()
                )

                self._track_api_request()  # 追蹤API使用
                rows = response.get("rows", [])
                logger.info(f"Received {len(rows)} rows from GSC API")

                if not rows:
                    logger.info("No more rows returned, breaking")
                    break

                all_rows.extend(rows)
                start_row += len(rows)

                # 不要因為返回行數少就停止！GSC API 可能有隱藏限制
                # 只有當真的沒有數據時才停止
                if len(rows) == 0:
                    logger.info("No rows returned, stopping")
                    break

                # 如果返回行數少於請求，但大於 1000，繼續嘗試下一頁
                if len(rows) < max_rows_per_request and len(rows) < 1000:
                    logger.info(f"Received only {len(rows)} rows (< 1000), likely end of data")
                    break

        except HttpError as e:
            logger.error(f"Failed to get search analytics batch for {site_url}: {e}")

        return all_rows

    def get_keywords_for_site(self, site_url: str, limit: int = 100) -> List[str]:
        """獲取站點的熱門關鍵字"""
        try:
            data = self.get_search_analytics_batch(
                site_url,
                (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                datetime.now().strftime("%Y-%m-%d"),
                dimensions=["query"],
                max_total_rows=limit,
            )

            # 按點擊數排序
            sorted_data = sorted(data, key=lambda x: x.get("clicks", 0), reverse=True)
            return [row["keys"][0] for row in sorted_data[:limit]]

        except Exception as e:
            logger.error(f"Failed to get keywords for {site_url}: {e}")
            return []

    def _track_api_request(self):
        """追蹤API請求 (線程安全)"""
        with self._api_lock:
            now = datetime.now()
            current_minute = now.replace(second=0, microsecond=0)
            current_date = now.date()

            # 重置每日計數器
            if current_date != self.today:
                self.api_requests_today = 0
                self.today = current_date
                # 為新的一天創建數據庫記錄
                self._load_api_usage_from_db()

            # 重置每分鐘計數器
            if current_minute != self.last_minute_reset:
                self.api_requests_this_minute = 0
                self.last_minute_reset = current_minute

            self.api_requests_today += 1
            self.api_requests_this_minute += 1

            # 保存到數據庫
            self._save_api_usage_to_db()

            # 記錄到日誌
            logger.info(
                f"API請求計數: 今日 {self.api_requests_today}, "
                f"本分鐘 {self.api_requests_this_minute}"
            )

    def get_api_usage_stats(self) -> Dict[str, Any]:
        """獲取API使用統計"""
        with self._api_lock:
            return {
                "requests_today": self.api_requests_today,
                "requests_this_minute": self.api_requests_this_minute,
                "daily_limit": 100000,
                "minute_limit": 1200,
                "daily_remaining": 100000 - self.api_requests_today,
                "minute_remaining": 1200 - self.api_requests_this_minute,
                "daily_usage_percent": (self.api_requests_today / 100000) * 100,
                "minute_usage_percent": (self.api_requests_this_minute / 1200) * 100,
            }

    def _load_api_usage_from_db(self):
        """從數據庫載入今日API使用計數"""
        try:
            self.database.init_api_usage_table()
            # 載入今日的計數
            today_str = self.today.strftime("%Y-%m-%d")
            self.api_requests_today = self.database.get_api_usage(today_str)
            logger.info(f"載入今日API使用計數: {self.api_requests_today}")

        except Exception as e:
            logger.error(f"載入API使用統計失敗: {e}")

    def _save_api_usage_to_db(self):
        """保存今日API使用計數到數據庫"""
        today_str = self.today.strftime("%Y-%m-%d")
        self.database.update_api_usage(today_str, self.api_requests_today)
