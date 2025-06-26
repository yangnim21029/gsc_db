#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

# 導入相關模塊
import sys
sys.path.append(os.path.dirname(__file__))
from database import Database
from hourly_data import HourlyDataHandler

logger = logging.getLogger(__name__)

class GSCClient:
    def __init__(self):
        """初始化 GSC 客戶端"""
        self.scopes = ['https://www.googleapis.com/auth/webmasters.readonly']
        self.credentials_file = 'gsc_credentials.json'
        self.client_config_file = 'client_secret.json'
        
        # 初始化狀態
        self.credentials: Optional[Credentials] = None
        self.service: Optional[Any] = None
        self.database = Database()
        
        # 嘗試加載已有憑證
        self._load_credentials()
        
        # OAuth 配置
        self.client_config = self._load_client_config()
        current_port = os.getenv('PORT', '8000')
        if 'web' in self.client_config:
            self.client_config['web']['redirect_uris'] = [f"http://localhost:{current_port}/auth/callback"]
        
        self.scopes = [
            'https://www.googleapis.com/auth/webmasters.readonly',
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
        
        # 初始化每小時數據處理器
        self.hourly_handler = None
        if self.service:
            self.hourly_handler = HourlyDataHandler(self.service, self.database)
    
    def _load_client_config(self) -> Dict[str, Any]:
        """載入 Google OAuth 客戶端配置"""
        client_secret_path = os.getenv('CLIENT_SECRET_PATH', 'client_secret.json')
        try:
            with open(client_secret_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"web": {}}
    
    def get_auth_url(self) -> str:
        """獲取OAuth認證URL"""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.scopes,
            redirect_uri=self.client_config['web']['redirect_uris'][0]
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='false',
            prompt='consent'
        )
        
        return auth_url
    
    def handle_oauth_callback(self, code: str) -> bool:
        """處理OAuth回調"""
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=self.client_config['web']['redirect_uris'][0]
            )
            
            flow.fetch_token(code=code)
            if flow.credentials:
                self.credentials = flow.credentials  # type: ignore
                self._save_credentials()
                
                # 初始化服務和每小時處理器
                self.service = build('searchconsole', 'v1', credentials=self.credentials)
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
                'token': self.credentials.token,
                'refresh_token': self.credentials.refresh_token,
                'token_uri': self.credentials.token_uri,
                'client_id': self.credentials.client_id,
                'client_secret': self.credentials.client_secret,
                'scopes': self.credentials.scopes
            }
            
            with open('gsc_credentials.json', 'w') as f:
                json.dump(creds_data, f)
    
    def _load_credentials(self) -> bool:
        """從文件載入認證資訊"""
        try:
            if os.path.exists('gsc_credentials.json'):
                with open('gsc_credentials.json', 'r') as f:
                    creds_data = json.load(f)
                
                self.credentials = Credentials.from_authorized_user_info(creds_data)  # type: ignore
                
                # 檢查是否需要刷新token
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                    self._save_credentials()
                
                self.service = build('searchconsole', 'v1', credentials=self.credentials)
                return True
                
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
        
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
            
            for site in sites_response.get('siteEntry', []):
                if site['permissionLevel'] in ['siteFullUser', 'siteOwner']:
                    sites.append(site['siteUrl'])
            
            return sites
            
        except HttpError as e:
            logger.error(f"Failed to get sites: {e}")
            return []
    
    def get_search_analytics(self, site_url: str, start_date: str, end_date: str, 
                           dimensions: List[str] = ['query'], row_limit: int = 1000) -> List[Dict[str, Any]]:
        """獲取搜索分析數據"""
        if not self.is_authenticated():
            raise Exception("Not authenticated with GSC")
        
        if self.service is None:
            raise Exception("GSC service not initialized")
        
        try:
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'rowLimit': row_limit,
                'startRow': 0
            }
            
            response = self.service.searchanalytics().query(
                siteUrl=site_url,
                body=request
            ).execute()
            
            return response.get('rows', [])
            
        except HttpError as e:
            logger.error(f"Failed to get search analytics for {site_url}: {e}")
            return []
    
    def get_search_analytics_batch(self, site_url: str, start_date: str, end_date: str, 
                                 dimensions: List[str] = ['query'], 
                                 device_filter: Optional[str] = None,
                                 max_total_rows: Optional[int] = None) -> List[Dict[str, Any]]:
        """批次獲取搜索分析數據"""
        if not self.is_authenticated():
            raise Exception("Not authenticated with GSC")
        
        if self.service is None:
            raise Exception("GSC service not initialized")
        
        all_rows = []
        max_rows_per_request = 25000
        start_row = 0
        
        try:
            while max_total_rows is None or len(all_rows) < max_total_rows:
                # 計算這次請求的行數限制
                if max_total_rows is None:
                    row_limit = max_rows_per_request
                else:
                    row_limit = min(max_rows_per_request, max_total_rows - len(all_rows))
                
                logger.info(f"Requesting batch: startRow={start_row}, rowLimit={row_limit}, total_so_far={len(all_rows)}")
                
                request = {
                    'startDate': start_date,
                    'endDate': end_date,
                    'dimensions': dimensions,
                    'rowLimit': row_limit,
                    'startRow': start_row
                }
                
                if device_filter:
                    request['dimensionFilterGroups'] = [{
                        'filters': [{
                            'dimension': 'device',
                            'operator': 'equals',
                            'expression': device_filter
                        }]
                    }]
                
                response = self.service.searchanalytics().query(
                    siteUrl=site_url,
                    body=request
                ).execute()
                
                rows = response.get('rows', [])
                logger.info(f"Received {len(rows)} rows from GSC API")
                
                if not rows:
                    logger.info("No more rows returned, breaking")
                    break
                
                all_rows.extend(rows)
                start_row += len(rows)
                
                # 不要因為返回行數少就停止！GSC API 可能有隱藏限制
                # 只有當真的沒有數據時才停止
                if len(rows) == 0:
                    logger.info(f"No rows returned, stopping")
                    break
                    
                # 如果返回行數少於請求，但大於 1000，繼續嘗試下一頁
                if len(rows) < max_rows_per_request and len(rows) < 1000:
                    logger.info(f"Received only {len(rows)} rows (< 1000), likely end of data")
                    break
                
        except HttpError as e:
            logger.error(f"Failed to get search analytics batch for {site_url}: {e}")
        
        return all_rows
    
    def sync_site_data(self, site_url: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """同步站點數據 - 調用 enhanced 版本"""
        return self.sync_site_data_enhanced(site_url, start_date, end_date)
    
    def sync_multiple_sites(self, sites: List[str], start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """同步多個站點的數據"""
        results = []
        for site_url in sites:
            try:
                result = self.sync_site_data_enhanced(site_url, start_date, end_date)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to sync {site_url}: {e}")
                results.append({
                    'site': site_url,
                    'error': str(e),
                    'success': False
                })
        return results
    
    def get_keywords_for_site(self, site_url: str, limit: int = 100) -> List[str]:
        """獲取站點的熱門關鍵字"""
        try:
            data = self.get_search_analytics_batch(
                site_url, 
                (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                datetime.now().strftime('%Y-%m-%d'),
                dimensions=['query'],
                max_total_rows=limit
            )
            
            # 按點擊數排序
            sorted_data = sorted(data, key=lambda x: x.get('clicks', 0), reverse=True)
            return [row['keys'][0] for row in sorted_data[:limit]]
            
        except Exception as e:
            logger.error(f"Failed to get keywords for {site_url}: {e}")
            return []
    
    def sync_site_data_enhanced(self, site_url: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """增強版站點數據同步"""
        try:
            # 獲取或創建站點記錄
            site = self.database.get_site_by_domain(site_url)
            if not site:
                site_id = self.database.add_site(site_url, site_url.replace('sc-domain:', ''))
                site = {'id': site_id, 'domain': site_url}
            
            # 同步關鍵字數據
            keyword_result = self._sync_keyword_data(site, site_url, start_date, end_date)
            
            # 同步頁面數據
            page_result = self._sync_page_data(site, site_url, start_date, end_date)
            
            # 合併結果
            return {
                'site': site_url,
                'start_date': start_date,
                'end_date': end_date,
                'keyword_count': keyword_result.get('keyword_count', 0),
                'ranking_count': keyword_result.get('ranking_count', 0), 
                'page_count': page_result.get('page_count', 0),
                'type': 'enhanced'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync enhanced data for {site_url}: {e}")
            raise
    
    def _sync_keyword_data(self, site: Dict[str, Any], site_url: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """同步關鍵字數據 - 使用多維度策略突破 5000 行限制"""
        all_search_data = []
        
        # 策略 1: 分設備查詢
        devices = ['desktop', 'mobile', 'tablet']
        for device in devices:
            logger.info(f"Fetching data for device: {device}")
            device_data = self.get_search_analytics_batch(
                site_url, start_date, end_date,
                dimensions=['date', 'query', 'device'],
                device_filter=device
            )
            all_search_data.extend(device_data)
            logger.info(f"Device {device}: {len(device_data)} records")
        
        # 策略 2: 如果數據量還是不夠，嘗試添加頁面維度
        if len(all_search_data) < 15000:  # 如果少於預期，再查一次包含頁面的數據
            logger.info("Fetching additional data with page dimension")
            page_data = self.get_search_analytics_batch(
                site_url, start_date, end_date,
                dimensions=['date', 'query', 'page']
            )
            
            # 去重合併（按 date+query 組合）
            existing_keys = set()
            for row in all_search_data:
                keys = row.get('keys', [])
                if len(keys) >= 2:
                    existing_keys.add(f"{keys[0]}|{keys[1]}")
            
            for row in page_data:
                keys = row.get('keys', [])
                if len(keys) >= 2:
                    key = f"{keys[0]}|{keys[1]}"
                    if key not in existing_keys:
                        all_search_data.append(row)
                        existing_keys.add(key)
            
            logger.info(f"Total after page dimension: {len(all_search_data)} records")
        
        search_data = all_search_data
        
        # 處理關鍵字數據 - 合併多維度數據
        keywords_added = set()
        ranking_map = {}  # 用於合併同一關鍵字的多條記錄
        
        for row in search_data:
            keys = row.get('keys', [])
            if len(keys) >= 2:
                date, query = keys[0], keys[1]
                device = keys[2] if len(keys) > 2 else 'ALL'
                page = keys[3] if len(keys) > 3 else keys[2] if len(keys) == 3 and device == 'ALL' else None
                
                # 添加關鍵字
                keyword_id = self.database.add_keyword(query, site['id'])
                if keyword_id:
                    keywords_added.add(query)
                
                # 合併同一天同一關鍵字的數據
                key = f"{date}|{query}|{device}"
                if key in ranking_map:
                    # 合併數據：累加點擊和曝光，取最佳排名，重新計算 CTR
                    existing = ranking_map[key]
                    existing['clicks'] += row.get('clicks', 0)
                    existing['impressions'] += row.get('impressions', 0)
                    existing['position'] = min(existing['position'], row.get('position', 999)) if existing['position'] > 0 else row.get('position', 0)
                    if existing['impressions'] > 0:
                        existing['ctr'] = existing['clicks'] / existing['impressions']
                    if page and not existing.get('page'):
                        existing['page'] = page
                else:
                    # 新記錄
                    ranking = {
                        'site_id': site['id'],
                        'keyword_id': keyword_id,
                        'date': date,
                        'query': query,
                        'position': row.get('position', 0),
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'page': page,
                        'device': device
                    }
                    ranking_map[key] = ranking
        
        rankings = list(ranking_map.values())
        
        # 保存排名數據
        saved_count = self.database.save_ranking_data(rankings)
        
        return {
            'keyword_count': len(keywords_added),
            'ranking_count': saved_count
        }
    
    def _sync_page_data(self, site: Dict[str, Any], site_url: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """同步頁面數據"""
        # 獲取頁面數據
        page_data = self.get_search_analytics_batch(
            site_url, start_date, end_date,
            dimensions=['date', 'page']
        )
        
        # 處理頁面數據
        pages = []
        for row in page_data:
            keys = row.get('keys', [])
            if len(keys) >= 2:
                date, page = keys[0], keys[1]
                
                page_record = {
                    'site_id': site['id'],
                    'page': page,
                    'date': date,
                    'clicks': row.get('clicks', 0),
                    'impressions': row.get('impressions', 0),
                    'ctr': row.get('ctr', 0),
                    'position': row.get('position', 0)
                }
                pages.append(page_record)
        
        # 保存頁面數據
        saved_count = self.database.save_page_data(pages)
        
        return {
            'page_count': saved_count
        }
    
    # 每小時數據方法委托給 HourlyDataHandler
    def get_search_analytics_hourly(self, *args, **kwargs):
        """獲取每小時搜索分析數據"""
        if not self.hourly_handler:
            self.hourly_handler = HourlyDataHandler(self.service, self.database)
        return self.hourly_handler.get_search_analytics_hourly(*args, **kwargs)
    
    def get_hourly_data_batch(self, *args, **kwargs):
        """批次獲取每小時數據"""
        if not self.hourly_handler:
            self.hourly_handler = HourlyDataHandler(self.service, self.database)
        return self.hourly_handler.get_hourly_data_batch(*args, **kwargs)
    
    def sync_hourly_data(self, *args, **kwargs):
        """同步每小時數據到數據庫"""
        if not self.hourly_handler:
            self.hourly_handler = HourlyDataHandler(self.service, self.database)
        return self.hourly_handler.sync_hourly_data(*args, **kwargs) 