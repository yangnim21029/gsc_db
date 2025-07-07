#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import concurrent.futures
import logging
import os
import ssl

# 導入相關模塊
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .database import Database
from .hourly_data import HourlyDataHandler

sys.path.append(os.path.dirname(__file__))
import threading
import time
import xml.etree.ElementTree as ET

import requests

from .. import config
from ..utils.rich_console import console

logger = logging.getLogger(__name__)


class GSCClient:
    _api_lock = threading.Lock()
    api_requests_this_minute = 0
    last_minute_reset = datetime.now().replace(second=0, microsecond=0)

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

    def authenticate(self):
        """
        執行或驗證GSC認證。如果憑證有效則直接使用，否則啟動OAuth流程。
        此方法確保 self.service 在結束時是可用的。
        """
        # 如果 service 物件已存在且有效，則直接返回，避免重複認證
        if self.service and self.credentials and self.credentials.valid:
            return

        creds: Optional[Credentials] = None

        # 1. 嘗試從 token 文件加載
        if os.path.exists(self.credentials_path):
            try:
                # 首先加載，類型尚不確定
                loaded_creds = Credentials.from_authorized_user_file(
                    self.credentials_path, self.scopes
                )
                # 顯式檢查類型，確保類型安全
                if isinstance(loaded_creds, Credentials):
                    creds = loaded_creds
                else:
                    logger.warning(
                        f"從 {self.credentials_path} 加載的憑證類型不正確，將忽略並重新認證。"
                    )
            except Exception as e:
                logger.warning(f"加載 {self.credentials_path} 失敗: {e}，將嘗試重新認證。")
                creds = None

        # 2. 如果憑證無效或需要刷新，則處理
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"刷新 token 失敗，將重新啟動認證流程: {e}")
                    creds = None  # 強制重新認證
            else:
                # 3. 如果沒有可用憑證，啟動 InstalledAppFlow 流程
                try:
                    console.print("🚀 [bold yellow]需要新的認證，啟動 OAuth2 流程...[/bold yellow]")
                    console.print("您的瀏覽器將會自動打開，請登入並授權。")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.client_config_path, self.scopes
                    )

                    # flow.run_local_server() 返回的是 Credentials
                    flow_creds = flow.run_local_server(port=0)
                    if isinstance(flow_creds, Credentials):
                        creds = flow_creds

                except FileNotFoundError:
                    console.print(
                        f"[bold red]錯誤: 找不到 OAuth 用戶端密鑰檔案: {self.client_config_path}。[/bold red]"
                    )
                    console.print(
                        "請從 Google Cloud Console 下載 '電腦版應用程式' 的憑證，並將其命名為 client_secret.json 放在 cred/ 目錄下。"
                    )
                    raise
                except Exception as e:
                    logger.error(f"OAuth 流程出錯: {e}")
                    raise

        # 4. 保存新的憑證
        if creds and isinstance(creds, Credentials):
            try:
                with open(self.credentials_path, "w") as token:
                    token.write(creds.to_json())
            except Exception as e:
                logger.error(f"保存 token 失敗: {e}")

        # 5. 最終設置 class 屬性
        if creds and isinstance(creds, Credentials):
            self.credentials = creds
            self.service = build("searchconsole", "v1", credentials=self.credentials)
            self.hourly_handler = HourlyDataHandler(self.service, self.database)
        else:
            raise ConnectionRefusedError("無法獲取有效的 Google 認證憑證。")

    def _rate_limit_check(self):
        """實施 API 速率限制檢查"""
        with self._api_lock:
            now = datetime.now()
            current_minute = now.replace(second=0, microsecond=0)

            # 重置每分鐘計數器
            if current_minute > self.last_minute_reset:
                self.api_requests_this_minute = 0
                self.last_minute_reset = current_minute

            # 檢查每分鐘限制 (保守估計 100 requests/minute)
            if self.api_requests_this_minute >= 100:
                sleep_time = 60 - now.second
                logger.info(f"達到每分鐘速率限制，等待 {sleep_time} 秒...")
                time.sleep(sleep_time)
                self.api_requests_this_minute = 0
                self.last_minute_reset = datetime.now().replace(second=0, microsecond=0)

    def stream_site_data_optimized(self, site_url: str, start_date: str, end_date: str):
        """
        優化版本：使用 API 最佳實踐的數據流式獲取
        - 減少併發請求
        - 使用 gzip 壓縮
        - 使用 fields 參數
        - 遵循每日查詢模式
        """
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        search_types = ["web", "image", "video", "news", "discover", "googleNews"]

        # 按日期分組，每天處理一次
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

        while current_date <= end_date_obj:
            date_str = current_date.strftime("%Y-%m-%d")

            # 對每個搜索類型順序處理（避免過度併發）
            for search_type in search_types:
                try:
                    self._rate_limit_check()

                    # 使用 API 推薦的查詢模式
                    request_body = {
                        "startDate": date_str,
                        "endDate": date_str,  # 每天查詢一天的數據
                        "dimensions": ["page", "query", "device"],
                        "rowLimit": 25000,
                        "startRow": 0,
                        "type": search_type,
                    }

                    all_rows = []
                    start_row = 0

                    while True:
                        request_body["startRow"] = start_row

                        response = (
                            self.service.searchanalytics()
                            .query(siteUrl=site_url, body=request_body)
                            .execute()
                        )

                        self._track_api_request()

                        rows = response.get("rows", [])
                        if not rows:
                            break

                        all_rows.extend(rows)

                        if len(rows) < 25000:
                            break

                        start_row += 25000

                    # 按設備分組數據
                    if all_rows:
                        device_chunks: Dict[str, List[Dict[str, Any]]] = {}
                        for row in all_rows:
                            dimensions = request_body["dimensions"]
                            row_keys = row["keys"]
                            keys = (
                                dict(zip(dimensions, row_keys)) if dimensions and row_keys else {}  # type: ignore
                            )
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

                except HttpError as e:
                    if e.resp.status in [404, 403, 400]:
                        logger.warning(
                            f"No data for {site_url} with type {search_type} "
                            f"on {date_str} (HTTP {e.resp.status}). Skipping."
                        )
                        continue
                    elif e.resp.status == 429:
                        logger.warning("Rate limit exceeded, waiting 60 seconds...")
                        time.sleep(60)
                        continue
                    logger.error(f"HTTP error for type {search_type}: {e}", exc_info=True)
                    raise
                except ssl.SSLError as e:
                    logger.warning(
                        f"SSL error for type {search_type}: {e}. "
                        "This will be retried by the caller."
                    )
                    raise
                except requests.exceptions.RequestException as e:
                    logger.warning(
                        f"Network error for type {search_type}: {e}. "
                        "This will be retried by the caller."
                    )
                    raise

                # 在不同搜索類型之間添加更長的延遲來減少 SSL 錯誤
                time.sleep(1.0)  # 增加到 1.0 秒，進一步減少 SSL 錯誤

            current_date += timedelta(days=1)

    def stream_site_data(self, site_url: str, start_date: str, end_date: str):
        """
        保持向後兼容性，但內部使用優化版本
        """
        return self.stream_site_data_optimized(site_url, start_date, end_date)

    def stream_hourly_data(self, site_url: str, start_date: str, end_date: str):
        """
        以流式方式從 GSC API 獲取每小時的詳細數據。
        此方法根據 2025/04/09 的官方文件進行了修正。
        """
        if not self.service:
            self.authenticate()
        if not self.service:
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

    def get_sites(self) -> List[str]:
        """獲取帳戶中的所有站點"""
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        site_list = []
        try:
            site_list = self.service.sites().list().execute()
            return [s["siteUrl"] for s in site_list.get("siteEntry", [])]
        except HttpError as e:
            logger.error(f"獲取網站列表時出錯: {e}")
            return []

    def get_sitemaps(self, site_url: str) -> List[Dict[str, Any]]:
        """獲取站點的索引頁面（sitemap）列表"""
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        try:
            sitemaps_response = self.service.sitemaps().list(siteUrl=site_url).execute()  # type: ignore
            sitemaps = sitemaps_response.get("sitemap", [])
            return list(sitemaps) if sitemaps else []

        except HttpError as e:
            logger.error(f"Failed to get sitemaps for {site_url}: {e}")
            return []

    def get_sitemap_details(self, site_url: str, feedpath: str) -> Dict[str, Any]:
        """獲取特定索引頁面的詳細信息"""
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        try:
            sitemap_response = (
                self.service.sitemaps().get(siteUrl=site_url, feedpath=feedpath).execute()  # type: ignore
            )
            return dict(sitemap_response) if sitemap_response else {}

        except HttpError as e:
            logger.error(f"Failed to get sitemap details for {site_url}/{feedpath}: {e}")
            return {}

    def get_all_sitemaps_for_sites(self, site_urls: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """批量獲取多個站點的索引頁面"""
        if not self.service:
            self.authenticate()
        if not self.service:
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
        if not self.service:
            self.authenticate()
        if not self.service:
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
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        try:
            request = {"inspectionUrl": inspection_url, "siteUrl": site_url}

            response = self.service.urlInspection().index().inspect(request).execute()  # type: ignore
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
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")
        try:
            # 使用 searchAnalytics.query API 獲取數據
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
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")
        try:
            response = self.service.urlcrawlerrorscounts().query(siteUrl=site_url).execute()  # type: ignore
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
        """通過 Search Analytics API 獲取索引頁面列表，帶有重試機制"""
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"正在從 GSC 獲取 {site_url} 從 {start_date} 到 {end_date} 的數據...")

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
        """[核心功能] 獲取指定站點的所有已索引頁面，並返回詳細資訊和統計數據。"""
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        # 確保日期不為 None
        if not start_date or not end_date:
            today = datetime.now()
            start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")

        try:
            # 使用 ThreadPoolExecutor 並行處理 Sitemap 和 Analytics 數據
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # 提交 Sitemap URL 獲取任務
                future_sitemap_urls = executor.submit(self.get_sitemap_urls_for_site, site_url)
                # 提交 Analytics Page 獲取任務
                future_analytics_pages = executor.submit(
                    self.get_sample_pages_from_analytics, site_url, start_date, end_date
                )

                # 等待結果
                sitemap_urls = set(future_sitemap_urls.result())
                analytics_result = future_analytics_pages.result()

            analytics_pages = set(analytics_result.get("pages", []))
            total_pages_in_analytics = analytics_result.get("total_pages", 0)

            # 進行比較
            common_urls = sitemap_urls.intersection(analytics_pages)
            sitemap_only_urls = sitemap_urls.difference(analytics_pages)
            analytics_only_urls = analytics_pages.difference(sitemap_urls)

            # 計算覆蓋率和冗餘率
            coverage_rate = len(common_urls) / len(sitemap_urls) if len(sitemap_urls) > 0 else 0
            redundancy_rate = (
                len(sitemap_only_urls) / len(sitemap_urls) if len(sitemap_urls) > 0 else 0
            )

            return {
                "sitemap_urls_count": len(sitemap_urls),
                "analytics_pages_count": len(analytics_pages),
                "total_pages_in_analytics": total_pages_in_analytics,
                "common_urls_count": len(common_urls),
                "sitemap_only_urls_count": len(sitemap_only_urls),
                "analytics_only_urls_count": len(analytics_only_urls),
                "coverage_rate": coverage_rate,
                "redundancy_rate": redundancy_rate,
                # "sitemap_only_urls": list(sitemap_only_urls), # 可選返回
                # "analytics_only_urls": list(analytics_only_urls), # 可選返回
            }

        except Exception as e:
            logger.error(f"在 get_all_indexed_pages 中發生錯誤: {e}", exc_info=True)
            return {"error": str(e)}

    def get_sitemap_urls_for_site(self, site_url: str) -> List[str]:
        """
        從給定的站點 URL 中提取所有 Sitemap 中包含的 URL。
        此方法現在統一使用 get_sitemap_urls，並移除了對 parse_sitemap_xml 的依賴。
        """
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        all_sitemap_urls = set()

        try:
            # 1. 從 robots.txt 獲取 Sitemaps
            sitemap_paths = self.get_sitemaps_from_robots(site_url)

            # 2. 如果 robots.txt 中沒有，則從 GSC API 獲取
            if not sitemap_paths:
                sitemap_list = self.get_sitemaps(site_url)
                sitemap_paths = [sitemap["path"] for sitemap in sitemap_list]

            # 3. 並行解析所有 Sitemap 文件
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_url = {
                    executor.submit(self.get_sitemap_urls, path): path for path in sitemap_paths
                }
                for future in concurrent.futures.as_completed(future_to_url):
                    try:
                        urls = future.result()
                        all_sitemap_urls.update(urls)
                    except Exception as exc:
                        logger.error(f"解析 sitemap 時出錯: {exc}")

            return list(all_sitemap_urls)

        except Exception as e:
            logger.error(f"無法獲取站點 {site_url} 的 sitemap URL: {e}")
            return []

    def get_sitemaps_from_robots(self, site_url: str) -> List[str]:
        """從 robots.txt 文件中解析出 sitemap 的 URL"""
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        robots_url = f"{site_url.rstrip('/')}/robots.txt"
        sitemap_urls = []
        try:
            response = requests.get(robots_url, timeout=10)
            response.raise_for_status()
            for line in response.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sitemap_urls.append(line.split(":", 1)[1].strip())
        except requests.RequestException as e:
            logger.warning(f"無法從 {robots_url} 獲取 robots.txt: {e}")
        return sitemap_urls

    def get_sitemap_urls(self, sitemap_path: str) -> List[str]:
        """
        [REFACTORED] 解析單個 Sitemap 文件（或索引文件），返回所有 URL 列表。
        此版本支持遞歸解析 Sitemap 索引文件。
        """
        urls = []
        try:
            response = requests.get(sitemap_path, timeout=30)
            response.raise_for_status()

            # 避免 XML 炸彈
            if len(response.content) > 10 * 1024 * 1024:  # 10MB
                logger.error(f"Sitemap file {sitemap_path} is too large, skipping.")
                return []

            root = ET.fromstring(response.content)
            namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # 檢查是 Sitemap 索引還是 URL Set
            if root.tag.endswith("sitemapindex"):
                # 如果是 Sitemap 索引，遞歸調用
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    child_sitemaps = [
                        loc.text for loc in root.findall("sm:sitemap/sm:loc", namespace) if loc.text
                    ]
                    future_to_url = {
                        executor.submit(self.get_sitemap_urls, child_path): child_path
                        for child_path in child_sitemaps
                    }
                    for future in concurrent.futures.as_completed(future_to_url):
                        try:
                            urls.extend(future.result())
                        except Exception as exc:
                            logger.error(f"解析子 sitemap 時出錯: {exc}")

            elif root.tag.endswith("urlset"):
                # 如果是普通的 URL Set
                urls.extend(
                    [loc.text for loc in root.findall("sm:url/sm:loc", namespace) if loc.text]
                )
        except requests.RequestException as e:
            logger.error(f"無法獲取 sitemap '{sitemap_path}': {e}")
        except ET.ParseError as e:
            logger.error(f"無法解析 sitemap XML '{sitemap_path}': {e}")
        except Exception as e:
            logger.error(f"處理 sitemap '{sitemap_path}' 時發生未知錯誤: {e}")

        return urls

    def compare_db_and_sitemap(self, site_url: str, site_id: int) -> Dict[str, Any]:
        """比較資料庫中的頁面與 Sitemap 中的 URL，找出冗餘和缺失。"""
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        # 1. 從資料庫獲取所有獨立頁面
        try:
            db_pages = set(self.database.get_distinct_pages_for_site(site_id))
            if not db_pages:
                logger.warning(f"在數據庫中找不到站點 ID {site_id} 的任何頁面數據。")

            # 2. 獲取 sitemap 中的所有 URL
            sitemap_urls = set(self.get_sitemap_urls_for_site(site_url))
            if not sitemap_urls:
                logger.warning(f"從 {site_url} 的 sitemap 中找不到任何 URL。")

            # 3. 比較差異
            only_in_db = sorted(list(db_pages - sitemap_urls))
            only_in_sitemap = sorted(list(sitemap_urls - db_pages))
            in_both = sorted(list(db_pages & sitemap_urls))

            return {
                "site_url": site_url,
                "db_url_count": len(db_pages),
                "sitemap_url_count": len(sitemap_urls),
                "common_url_count": len(in_both),
                "redundant_urls_in_db_count": len(only_in_db),
                "missing_urls_in_sitemap_count": len(only_in_sitemap),
                "redundant_urls_in_db": only_in_db[:20],  # 僅顯示前 20 條以作樣本
                "missing_urls_in_sitemap": only_in_sitemap[:20],
            }
        except Exception as e:
            logger.error(f"比較數據庫和 sitemap 時出錯: {e}")
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
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        if dimensions is None:
            dimensions = ["page", "query"]

        try:
            request = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": dimensions,
                "rowLimit": row_limit,
            }
            response = (
                self.service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            )
            self._track_api_request()
            rows: List[Dict[str, Any]] = response.get("rows", [])
            return rows
        except HttpError as e:
            logger.error(f"Search analytics API error for {site_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_search_analytics: {e}")
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
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        if dimensions is None:
            dimensions = ["page"]

        all_rows: List[Dict[str, Any]] = []
        start_row = 0
        row_limit = 25000  # API 最大值

        while True:
            try:
                request = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": dimensions,
                    "startRow": start_row,
                    "rowLimit": row_limit,
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

                self._rate_limit_check()
                response = (
                    self.service.searchanalytics().query(siteUrl=site_url, body=request).execute()
                )
                self._track_api_request()

                rows = response.get("rows", [])
                if not rows:
                    break  # 沒有更多數據

                all_rows.extend(rows)

                # 檢查是否已達到請求的總行數限制
                if max_total_rows is not None and len(all_rows) >= max_total_rows:
                    return all_rows[:max_total_rows]

                # 如果返回的行數小於請求的行數，說明已經是最後一頁
                if len(rows) < row_limit:
                    break

                start_row += row_limit

            except HttpError as e:
                logger.error(f"Search analytics API error for {site_url}: {e}")
                break  # 發生錯誤時終止循環
            except Exception as e:
                logger.error(f"Unexpected error in get_search_analytics_batch: {e}")
                break

        return all_rows

    def get_keywords_for_site(self, site_url: str, limit: int = 100) -> List[str]:
        """獲取站點的熱門關鍵字"""
        if not self.service:
            self.authenticate()
        if not self.service:
            raise Exception("GSC service not initialized")

        try:
            analytics_data = self.get_search_analytics(
                site_url=site_url,
                start_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                dimensions=["query"],
                row_limit=limit,
            )

            # 按點擊數排序
            sorted_data = sorted(analytics_data, key=lambda x: x.get("clicks", 0), reverse=True)
            return [row["keys"][0] for row in sorted_data[:limit] if "keys" in row]

        except Exception as e:
            logger.error(f"獲取關鍵字時出錯: {e}")
            return []

    def _track_api_request(self):
        """
        跟蹤 API 請求計數，用於速率限制和每日配額。
        此方法需要是線程安全的。
        """
        with self._api_lock:
            now = datetime.now()
            today = now.date()

            # 檢查是否新的一天，如果是，重置每日計數器
            if today != self.today:
                logger.info(f"新的一天 ({today})，重置每日 API 使用計數。")
                self._save_api_usage_to_db()  # 保存前一天的計數
                self.api_requests_today = 0
                self.today = today

            # 增加計數
            self.api_requests_this_minute += 1
            self.api_requests_today += 1

            # 每 10 次請求後，將當前計數異步保存到數據庫
            if self.api_requests_today % 10 == 0:
                # 使用線程以避免阻塞主流程
                save_thread = threading.Thread(target=self._save_api_usage_to_db)
                save_thread.start()

    def get_api_usage_stats(self) -> Dict[str, Any]:
        """獲取當前的 API 使用統計信息"""
        return {
            "today": self.today.strftime("%Y-%m-%d"),
            "requests_today": self.api_requests_today,
            "requests_this_minute": self.api_requests_this_minute,
        }

    def _load_api_usage_from_db(self):
        """從數據庫加載今天的 API 使用計數"""
        today_str = self.today.strftime("%Y-%m-%d")
        count = self.database.get_api_usage(today_str)
        self.api_requests_today = count
        logger.info(f"從數據庫加載了今天的 API 使用次數: {count}")

    def _save_api_usage_to_db(self):
        """將當前的 API 使用計數保存到數據庫"""
        today_str = self.today.strftime("%Y-%m-%d")
        try:
            self.database.update_api_usage(today_str, self.api_requests_today)
        except Exception as e:
            logger.error(f"無法將 API 使用情況保存到數據庫: {e}")
