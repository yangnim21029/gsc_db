#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Any
import json

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = 'gsc_data.db'):
        """初始化數據庫連接"""
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self) -> sqlite3.Connection:
        """獲取數據庫連接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 讓查詢結果支持字典方式訪問
        return conn
    
    def check_connection(self) -> bool:
        """檢查數據庫連接"""
        try:
            with self.get_connection() as conn:
                conn.execute('SELECT 1')
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def init_db(self):
        """初始化數據庫表結構"""
        with self.get_connection() as conn:
            # 站點表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # 關鍵字表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    site_id INTEGER,
                    category TEXT,
                    priority INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (site_id) REFERENCES sites (id),
                    UNIQUE(keyword, site_id)
                )
            ''')
            
            # 每日排名數據表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_rankings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    keyword_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    query TEXT NOT NULL,
                    position REAL,
                    clicks INTEGER DEFAULT 0,
                    impressions INTEGER DEFAULT 0,
                    ctr REAL DEFAULT 0,
                    page TEXT,
                    country TEXT DEFAULT 'TWN',
                    device TEXT DEFAULT 'ALL',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (site_id) REFERENCES sites (id),
                    FOREIGN KEY (keyword_id) REFERENCES keywords (id),
                    UNIQUE(site_id, keyword_id, date, query, country, device)
                )
            ''')
            
            # 頁面數據表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS page_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    page TEXT NOT NULL,
                    date DATE NOT NULL,
                    clicks INTEGER DEFAULT 0,
                    impressions INTEGER DEFAULT 0,
                    ctr REAL DEFAULT 0,
                    position REAL DEFAULT 0,
                    country TEXT DEFAULT 'TWN',
                    device TEXT DEFAULT 'ALL',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (site_id) REFERENCES sites (id),
                    UNIQUE(site_id, page, date, country, device)
                )
            ''')
            
            # 創建索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_daily_rankings_date ON daily_rankings(date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_daily_rankings_site ON daily_rankings(site_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_daily_rankings_keyword ON daily_rankings(keyword_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_page_data_date ON page_data(date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_page_data_site ON page_data(site_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_keywords_site ON keywords(site_id)')
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    # 站點管理
    def add_site(self, domain: str, name: str, category: str = None) -> int:
        """添加站點"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'INSERT INTO sites (domain, name, category) VALUES (?, ?, ?)',
                (domain, name, category)
            )
            return cursor.lastrowid
    
    def get_sites(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """獲取站點列表"""
        with self.get_connection() as conn:
            query = 'SELECT * FROM sites'
            if active_only:
                query += ' WHERE is_active = 1'
            query += ' ORDER BY name'
            
            return [dict(row) for row in conn.execute(query).fetchall()]
    
    def get_site_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """根據域名獲取站點"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM sites WHERE domain = ?',
                (domain,)
            ).fetchone()
            return dict(row) if row else None
    
    # 關鍵字管理
    def add_keyword(self, keyword: str, site_id: int, category: str = None, priority: int = 0) -> int:
        """添加關鍵字"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'INSERT OR IGNORE INTO keywords (keyword, site_id, category, priority) VALUES (?, ?, ?, ?)',
                (keyword, site_id, category, priority)
            )
            if cursor.lastrowid:
                return cursor.lastrowid
            else:
                # 如果關鍵字已存在，獲取其ID
                row = conn.execute(
                    'SELECT id FROM keywords WHERE keyword = ? AND site_id = ?',
                    (keyword, site_id)
                ).fetchone()
                return row[0] if row else None
    
    def get_keywords(self, site_id: int = None) -> List[Dict[str, Any]]:
        """獲取關鍵字列表"""
        with self.get_connection() as conn:
            if site_id:
                query = 'SELECT * FROM keywords WHERE site_id = ? ORDER BY priority DESC, keyword'
                params = (site_id,)
            else:
                query = 'SELECT * FROM keywords ORDER BY priority DESC, keyword'
                params = ()
            
            return [dict(row) for row in conn.execute(query, params).fetchall()]
    
    # 排名數據管理
    def save_ranking_data(self, rankings: List[Dict[str, Any]]) -> int:
        """保存排名數據"""
        saved_count = 0
        with self.get_connection() as conn:
            for ranking in rankings:
                try:
                    conn.execute('''
                        INSERT OR REPLACE INTO daily_rankings 
                        (site_id, keyword_id, date, query, position, clicks, impressions, ctr, page, country, device)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ranking['site_id'],
                        ranking['keyword_id'],
                        ranking['date'],
                        ranking['query'],
                        ranking.get('position'),
                        ranking.get('clicks', 0),
                        ranking.get('impressions', 0),
                        ranking.get('ctr', 0),
                        ranking.get('page'),
                        ranking.get('country', 'TWN'),
                        ranking.get('device', 'ALL')
                    ))
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Failed to save ranking data: {e}, data: {ranking}")
            
            conn.commit()
        
        logger.info(f"Saved {saved_count} ranking records")
        return saved_count
    
    def save_page_data(self, page_data_list: List[Dict[str, Any]]) -> int:
        """保存頁面數據"""
        saved_count = 0
        with self.get_connection() as conn:
            for page_data in page_data_list:
                try:
                    conn.execute('''
                        INSERT OR REPLACE INTO page_data 
                        (site_id, page, date, clicks, impressions, ctr, position, country, device)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        page_data['site_id'],
                        page_data['page'],
                        page_data['date'],
                        page_data.get('clicks', 0),
                        page_data.get('impressions', 0),
                        page_data.get('ctr', 0),
                        page_data.get('position', 0),
                        page_data.get('country', 'TWN'),
                        page_data.get('device', 'ALL')
                    ))
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Failed to save page data: {e}, data: {page_data}")
            
            conn.commit()
        
        logger.info(f"Saved {saved_count} page data records")
        return saved_count
    
    def get_page_data(self, site_id: int = None, page: str = None, 
                     start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """獲取頁面數據"""
        with self.get_connection() as conn:
            query = '''
                SELECT pd.*, s.domain, s.name as site_name
                FROM page_data pd
                JOIN sites s ON pd.site_id = s.id
                WHERE 1=1
            '''
            params = []
            
            if site_id:
                query += ' AND pd.site_id = ?'
                params.append(site_id)
            
            if page:
                query += ' AND pd.page LIKE ?'
                params.append(f'%{page}%')
            
            if start_date:
                query += ' AND pd.date >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND pd.date <= ?'
                params.append(end_date)
            
            query += ' ORDER BY pd.date DESC, pd.clicks DESC'
            
            return [dict(row) for row in conn.execute(query, params).fetchall()]
    
    def get_rankings(self, site_id: int = None, keyword_id: int = None, 
                    start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """獲取排名數據"""
        with self.get_connection() as conn:
            query = '''
                SELECT dr.*, s.domain, s.name as site_name, k.keyword
                FROM daily_rankings dr
                JOIN sites s ON dr.site_id = s.id
                JOIN keywords k ON dr.keyword_id = k.id
                WHERE 1=1
            '''
            params = []
            
            if site_id:
                query += ' AND dr.site_id = ?'
                params.append(site_id)
            
            if keyword_id:
                query += ' AND dr.keyword_id = ?'
                params.append(keyword_id)
            
            if start_date:
                query += ' AND dr.date >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND dr.date <= ?'
                params.append(end_date)
            
            query += ' ORDER BY dr.date DESC, dr.position ASC'
            
            return [dict(row) for row in conn.execute(query, params).fetchall()]
    
    # 語義搜索相關
    def search_keywords_by_semantic(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """語義搜索關鍵字"""
        with self.get_connection() as conn:
            # 簡單的模糊搜索，後續可以擴展為向量搜索
            query = '''
                SELECT DISTINCT k.*, s.domain, s.name as site_name
                FROM keywords k
                JOIN sites s ON k.site_id = s.id
                WHERE k.keyword LIKE ? OR k.category LIKE ?
                ORDER BY k.priority DESC, k.keyword
                LIMIT ?
            '''
            search_pattern = f'%{search_term}%'
            return [dict(row) for row in conn.execute(
                query, (search_pattern, search_pattern, limit)
            ).fetchall()]
    
    def get_monthly_keyword_summary(self, keyword_pattern: str, month: str, limit: int = 30) -> List[Dict[str, Any]]:
        """獲取月度關鍵字匯總"""
        with self.get_connection() as conn:
            query = '''
                SELECT 
                    k.keyword,
                    s.domain,
                    s.name as site_name,
                    AVG(dr.position) as avg_position,
                    SUM(dr.clicks) as total_clicks,
                    SUM(dr.impressions) as total_impressions,
                    AVG(dr.ctr) as avg_ctr,
                    COUNT(dr.date) as data_points
                FROM keywords k
                JOIN sites s ON k.site_id = s.id
                LEFT JOIN daily_rankings dr ON k.id = dr.keyword_id
                WHERE k.keyword LIKE ?
                    AND dr.date LIKE ?
                GROUP BY k.id, s.id
                ORDER BY total_clicks DESC, avg_position ASC
                LIMIT ?
            '''
            keyword_search = f'%{keyword_pattern}%'
            month_pattern = f'{month}%'  # 例如 '2024-01%'
            
            return [dict(row) for row in conn.execute(
                query, (keyword_search, month_pattern, limit)
            ).fetchall()] 