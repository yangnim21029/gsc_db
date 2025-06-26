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

from .database import Database

logger = logging.getLogger(__name__)

class GSCClient:
    def __init__(self):
        """初始化 GSC 客戶端"""
        self.credentials = None
        self.service = None
        self.database = Database()
        
        # OAuth 配置 - 從 client_secret.json 讀取
        self.client_config = self._load_client_config()
        
        # 動態設定 redirect_uri 根據目前 PORT
        current_port = os.getenv('PORT', '8000')  # 預設改為 8000
        if 'web' in self.client_config:
            self.client_config['web']['redirect_uris'] = [f"http://localhost:{current_port}/auth/callback"]
        
        self.scopes = [
            'https://www.googleapis.com/auth/webmasters.readonly',
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
    
    def _load_client_config(self) -> Dict[str, Any]:
        """載入 Google OAuth 客戶端配置"""
        client_secret_path = os.getenv('CLIENT_SECRET_PATH', 'client_secret.json')
        try:
            with open(client_secret_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Client secret file not found: {client_secret_path}")
            return {"web": {}}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in client secret file: {client_secret_path}")
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
            include_granted_scopes='false',  # 不自動包含額外權限
            prompt='consent'  # 強制顯示同意畫面以獲取 refresh_token
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
            self.credentials = flow.credentials
            
            # 保存認證資訊
            self._save_credentials()
            
            # 初始化服務
            self.service = build('searchconsole', 'v1', credentials=self.credentials)
            
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
                
                self.credentials = Credentials.from_authorized_user_info(creds_data)
                
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
            # 如果 token 過期但有 refresh_token，嘗試刷新
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
                                 device_filter: str = None,
                                 max_total_rows: int = 100000) -> List[Dict[str, Any]]:
        """
        批次獲取搜索分析數據，支援超過 25,000 筆記錄
        根據官方文件建議，使用分頁方式獲取大量數據
        """
        if not self.is_authenticated():
            raise Exception("Not authenticated with GSC")
        
        all_rows = []
        max_rows_per_request = 25000
        start_row = 0
        
        try:
            while len(all_rows) < max_total_rows:
                # 構建請求
                request = {
                    'startDate': start_date,
                    'endDate': end_date,
                    'dimensions': dimensions,
                    'rowLimit': min(max_rows_per_request, max_total_rows - len(all_rows)),
                    'startRow': start_row
                }
                
                # 添加設備篩選器
                if device_filter:
                    request['dimensionFilterGroups'] = [{
                        'filters': [{
                            'dimension': 'device',
                            'expression': device_filter
                        }]
                    }]
                
                # 執行查詢
                response = self.service.searchanalytics().query(
                    siteUrl=site_url,
                    body=request
                ).execute()
                
                rows = response.get('rows', [])
                if not rows:
                    break  # 沒有更多數據
                
                all_rows.extend(rows)
                start_row += len(rows)
                
                # 如果返回的行數少於請求的行數，表示已到達最後一頁
                if len(rows) < max_rows_per_request:
                    break
                
                logger.info(f"Retrieved {len(all_rows)} rows so far for {site_url}")
                
        except HttpError as e:
            logger.error(f"Failed to get search analytics for {site_url}: {e}")
            return []
        
        logger.info(f"Total retrieved {len(all_rows)} rows for {site_url}")
        return all_rows

    def sync_site_data(self, site_url: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """同步站點數據到數據庫"""
        try:
            # 獲取或創建站點記錄
            site = self.database.get_site_by_domain(site_url)
            if not site:
                site_id = self.database.add_site(site_url, site_url.replace('sc-domain:', ''))
                site = {'id': site_id, 'domain': site_url}
            
            # 獲取查詢數據
            query_data = self.get_search_analytics(
                site_url, start_date, end_date,
                dimensions=['query', 'page', 'date']
            )
            
            # 處理數據
            rankings = []
            processed_queries = set()
            
            for row in query_data:
                query = row['keys'][0] if len(row['keys']) > 0 else ''
                page = row['keys'][1] if len(row['keys']) > 1 else ''
                date = row['keys'][2] if len(row['keys']) > 2 else start_date
                
                # 獲取或創建關鍵字記錄
                keyword_id = self.database.add_keyword(query, site['id'])
                
                if keyword_id:
                    ranking = {
                        'site_id': site['id'],
                        'keyword_id': keyword_id,
                        'date': date,
                        'query': query,
                        'position': row.get('position', 0),
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'page': page
                    }
                    rankings.append(ranking)
                    processed_queries.add(query)
            
            # 保存到數據庫
            saved_count = self.database.save_ranking_data(rankings)
            
            logger.info(f"Synced {saved_count} records for {site_url} from {start_date} to {end_date}")
            
            return {
                'site': site_url,
                'start_date': start_date,
                'end_date': end_date,
                'count': saved_count,
                'unique_queries': len(processed_queries)
            }
            
        except Exception as e:
            logger.error(f"Failed to sync data for {site_url}: {e}")
            raise
    
    def sync_multiple_sites(self, sites: List[str], start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """同步多個站點的數據"""
        results = []
        
        for site in sites:
            try:
                result = self.sync_site_data(site, start_date, end_date)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to sync {site}: {e}")
                results.append({
                    'site': site,
                    'error': str(e),
                    'count': 0
                })
        
        return results
    
    def get_keywords_for_site(self, site_url: str, limit: int = 100) -> List[str]:
        """獲取站點的關鍵字列表"""
        try:
            # 獲取最近30天的數據
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            query_data = self.get_search_analytics(
                site_url, start_date, end_date,
                dimensions=['query'],
                row_limit=limit
            )
            
            keywords = []
            for row in query_data:
                if row['keys']:
                    keywords.append(row['keys'][0])
            
            return keywords
            
        except Exception as e:
            logger.error(f"Failed to get keywords for {site_url}: {e}")
            return []

    def sync_site_data_enhanced(self, site_url: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        增強版站點數據同步，支援大量數據和多維度
        根據官方建議的策略：先獲取關鍵字數據，再獲取頁面數據
        """
        try:
            # 獲取或創建站點記錄
            site = self.database.get_site_by_domain(site_url)
            if not site:
                site_id = self.database.add_site(site_url, site_url.replace('sc-domain:', ''))
                site = {'id': site_id, 'domain': site_url}
            
            total_processed = 0
            results = {
                'site': site_url,
                'start_date': start_date,
                'end_date': end_date,
                'keyword_data': 0,
                'page_data': 0,
                'unique_queries': 0,
                'unique_pages': 0
            }
            
            # 第一步：獲取關鍵字維度數據 (query, date)
            logger.info(f"Syncing keyword data for {site_url} from {start_date} to {end_date}")
            keyword_rows = self.get_search_analytics_batch(
                site_url, start_date, end_date,
                dimensions=['query', 'date'],
                max_total_rows=100000
            )
            
            # 處理關鍵字數據
            keyword_rankings = []
            processed_queries = set()
            
            for row in keyword_rows:
                query = row['keys'][0] if len(row['keys']) > 0 else ''
                date = row['keys'][1] if len(row['keys']) > 1 else start_date
                
                if not query:
                    continue
                
                # 獲取或創建關鍵字記錄
                keyword_id = self.database.add_keyword(query, site['id'])
                
                if keyword_id:
                    ranking = {
                        'site_id': site['id'],
                        'keyword_id': keyword_id,
                        'date': date,
                        'query': query,
                        'position': row.get('position', 0),
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'page': ''  # 關鍵字維度查詢不包含頁面信息
                    }
                    keyword_rankings.append(ranking)
                    processed_queries.add(query)
            
            # 保存關鍵字數據
            if keyword_rankings:
                saved_keyword_count = self.database.save_ranking_data(keyword_rankings)
                results['keyword_data'] = saved_keyword_count
                results['unique_queries'] = len(processed_queries)
                total_processed += saved_keyword_count
            
            # 第二步：獲取頁面維度數據 (page, date)
            logger.info(f"Syncing page data for {site_url} from {start_date} to {end_date}")
            page_rows = self.get_search_analytics_batch(
                site_url, start_date, end_date,
                dimensions=['page', 'date'],
                max_total_rows=50000
            )
            
            # 處理頁面數據
            page_data_list = []
            processed_pages = set()
            
            for row in page_rows:
                page = row['keys'][0] if len(row['keys']) > 0 else ''
                date = row['keys'][1] if len(row['keys']) > 1 else start_date
                
                if not page:
                    continue
                
                page_data = {
                    'site_id': site['id'],
                    'page': page,
                    'date': date,
                    'clicks': row.get('clicks', 0),
                    'impressions': row.get('impressions', 0),
                    'ctr': row.get('ctr', 0),
                    'position': row.get('position', 0)
                }
                page_data_list.append(page_data)
                processed_pages.add(page)
            
            # 保存頁面數據
            if page_data_list:
                saved_page_count = self.database.save_page_data(page_data_list)
                results['page_data'] = saved_page_count
                results['unique_pages'] = len(processed_pages)
                total_processed += saved_page_count
            
            logger.info(f"Enhanced sync completed for {site_url}: {total_processed} total records")
            return results
            
        except Exception as e:
            logger.error(f"Failed to sync enhanced data for {site_url}: {e}")
            raise

    def sync_site_data_daily_range(self, site_url: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        按天同步數據範圍，確保每天單獨處理避免數據過大
        """
        from datetime import datetime, timedelta
        
        results = []
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current_date <= end_date_obj:
            date_str = current_date.strftime('%Y-%m-%d')
            try:
                logger.info(f"Syncing {site_url} for date: {date_str}")
                result = self.sync_site_data_enhanced(site_url, date_str, date_str)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to sync {site_url} for {date_str}: {e}")
                results.append({
                    'site': site_url,
                    'date': date_str,
                    'error': str(e),
                    'keyword_data': 0,
                    'page_data': 0
                })
            
            current_date += timedelta(days=1)
        
        return results 