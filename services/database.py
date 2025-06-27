#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = 'gsc_data.db'):
        """初始化數據庫連接"""
        self.db_path = db_path
        self.init_db()

        # 初始化每小時數據處理器
        try:
            from .hourly_database import HourlyDatabase
            self.hourly_db = HourlyDatabase(self.get_connection)
        except ImportError:
            # 如果無法導入，創建一個空的佔位符
            self.hourly_db = None

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

            # 每小時排名數據表 (新增)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS hourly_rankings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    keyword_id INTEGER,
                    date DATE NOT NULL,
                    hour INTEGER NOT NULL,
                    hour_timestamp TEXT NOT NULL,
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
                    UNIQUE(site_id, keyword_id, hour_timestamp, query, country, device)
                )
            ''')

            # 創建索引
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_daily_rankings_date ON daily_rankings(date)')
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_daily_rankings_site ON daily_rankings(site_id)')
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_daily_rankings_keyword ON daily_rankings(keyword_id)')
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_page_data_date ON page_data(date)')
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_page_data_site ON page_data(site_id)')
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_keywords_site ON keywords(site_id)')

            # 每小時數據索引 (新增)
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_hourly_rankings_date ON hourly_rankings(date)')
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_hourly_rankings_site ON hourly_rankings(site_id)')
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_hourly_rankings_hour ON hourly_rankings(hour)')
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_hourly_rankings_timestamp ON hourly_rankings(hour_timestamp)')

            conn.commit()
            logger.info("Database initialized successfully")

            # 初始化任務追蹤表
            self.init_task_table()

    # 站點管理
    def add_site(
            self,
            domain: str,
            name: str,
            category: Optional[str] = None) -> int:
        """添加站點"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'INSERT INTO sites (domain, name, category) VALUES (?, ?, ?)',
                (domain, name, category)
            )
            site_id = cursor.lastrowid
            if site_id is None:
                raise Exception("Failed to add site")
            return site_id

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
    def add_keyword(
            self,
            keyword: str,
            site_id: int,
            category: Optional[str] = None,
            priority: int = 0) -> Optional[int]:
        """添加關鍵字，返回關鍵字 ID，如果失敗返回 None"""
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

    def get_keywords(
            self, site_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """獲取關鍵字列表"""
        with self.get_connection() as conn:
            if site_id:
                query = 'SELECT * FROM keywords WHERE site_id = ? ORDER BY priority DESC, keyword'
                params = (site_id,)
            else:
                query = 'SELECT * FROM keywords ORDER BY priority DESC, keyword'
                params = ()

            return [dict(row)
                    for row in conn.execute(query, params).fetchall()]

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
                    logger.error(
                        f"Failed to save ranking data: {e}, data: {ranking}")

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
                    logger.error(
                        f"Failed to save page data: {e}, data: {page_data}")

            conn.commit()

        logger.info(f"Saved {saved_count} page data records")
        return saved_count

    def get_page_data(self,
                      site_id: Optional[int] = None,
                      page: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> List[Dict[str,
                                                                   Any]]:
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

            return [dict(row)
                    for row in conn.execute(query, params).fetchall()]

    def get_rankings(self,
                     site_id: Optional[int] = None,
                     keyword_id: Optional[int] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> List[Dict[str,
                                                                  Any]]:
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

            return [dict(row)
                    for row in conn.execute(query, params).fetchall()]

    # 語義搜索相關
    def search_keywords_by_semantic(
            self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
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

    def get_monthly_keyword_summary(
            self, keyword_pattern: str, month: str, limit: int = 30) -> List[Dict[str, Any]]:
        """獲取月度關鍵字總結"""
        with self.get_connection() as conn:
            query = '''
                SELECT
                    k.keyword,
                    COUNT(dr.id) as data_points,
                    AVG(dr.position) as avg_position,
                    MAX(dr.position) as max_position,
                    MIN(dr.position) as min_position,
                    SUM(dr.clicks) as total_clicks,
                    SUM(dr.impressions) as total_impressions,
                    AVG(dr.ctr) as avg_ctr
                FROM keywords k
                JOIN daily_rankings dr ON k.id = dr.keyword_id
                WHERE k.keyword LIKE ?
                AND strftime('%Y-%m', dr.date) = ?
                GROUP BY k.keyword
                ORDER BY total_clicks DESC, avg_position ASC
                LIMIT ?
            '''
            return [
                dict(row) for row in conn.execute(
                    query, (f'%{keyword_pattern}%', month, limit)).fetchall()]

    # 每小時數據功能已移至 services/hourly_database.py 模塊

    # 簡化的任務進度追蹤 (取代複雜的 build_progress.py)
    def init_task_table(self):
        """初始化任務追蹤表"""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sync_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER,
                    task_type TEXT NOT NULL,
                    status TEXT DEFAULT 'running',
                    start_date TEXT,
                    end_date TEXT,
                    total_records INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (site_id) REFERENCES sites (id)
                )
            ''')

            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_sync_tasks_status ON sync_tasks(status)')
            conn.commit()

    def start_sync_task(
            self,
            site_id: int,
            task_type: str,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None) -> int:
        """開始同步任務"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO sync_tasks (site_id, task_type, start_date, end_date)
                VALUES (?, ?, ?, ?)
            ''', (site_id, task_type, start_date, end_date))
            task_id = cursor.lastrowid
            if task_id is None:
                raise Exception("Failed to create sync task")
            return task_id

    def complete_sync_task(
            self,
            task_id: int,
            total_records: int = 0,
            status: str = 'completed'):
        """完成同步任務"""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE sync_tasks
                SET status = ?, total_records = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, total_records, task_id))
            conn.commit()

    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取最近的任務"""
        with self.get_connection() as conn:
            query = '''
                SELECT st.*, s.name as site_name
                FROM sync_tasks st
                LEFT JOIN sites s ON st.site_id = s.id
                ORDER BY st.created_at DESC
                LIMIT ?
            '''
            return [
                dict(row) for row in conn.execute(
                    query, (limit,)).fetchall()]

    # 每小時數據方法委托
    def save_hourly_ranking_data(
            self, hourly_rankings: List[Dict[str, Any]]) -> int:
        """保存每小時排名數據"""
        saved_count = 0
        with self.get_connection() as conn:
            for ranking in hourly_rankings:
                try:
                    conn.execute('''
                        INSERT OR REPLACE INTO hourly_rankings
                        (site_id, keyword_id, date, hour, hour_timestamp, query, position, clicks, impressions, ctr, page, country, device)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ranking['site_id'],
                        ranking.get('keyword_id'),
                        ranking['date'],
                        ranking['hour'],
                        ranking['hour_timestamp'],
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
                    logger.error(
                        f"Failed to save hourly ranking data: {e}, data: {ranking}")

            conn.commit()

        logger.info(f"Saved {saved_count} hourly ranking records")
        return saved_count

    def get_hourly_rankings(self, **kwargs) -> List[Dict[str, Any]]:
        """獲取每小時排名數據 - 委托給 HourlyDatabase"""
        if self.hourly_db:
            return self.hourly_db.get_hourly_rankings(**kwargs)
        return []

    def get_hourly_summary(self, site_id: int,
                           date: Optional[str] = None) -> List[Dict[str, Any]]:
        """獲取每小時數據總結 - 委托給 HourlyDatabase"""
        if self.hourly_db:
            return self.hourly_db.get_hourly_summary(site_id, date)
        return []

    def get_hourly_coverage(self, site_id: int) -> Dict[str, Any]:
        """獲取每小時數據覆蓋情況 - 委托給 HourlyDatabase"""
        if self.hourly_db:
            return self.hourly_db.get_hourly_coverage(site_id)
        return {}
