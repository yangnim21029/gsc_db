"""
每小時數據數據庫操作模塊
處理 2025年新增的每小時數據存儲和查詢
"""

import logging
import sqlite3
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class HourlyDatabase:
    """處理每小時數據的數據庫操作"""
    
    def __init__(self, db_connection_func):
        self.get_connection = db_connection_func
    
    def init_hourly_tables(self):
        """初始化每小時數據表"""
        with self.get_connection() as conn:
            # 每小時排名數據表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS hourly_rankings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    keyword_id INTEGER,
                    date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    hour_timestamp TEXT NOT NULL,
                    query TEXT,
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
                    UNIQUE(site_id, hour_timestamp, query, page)
                )
            ''')
            
            # 每小時數據專用索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_hourly_rankings_date ON hourly_rankings(date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_hourly_rankings_site ON hourly_rankings(site_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_hourly_rankings_hour ON hourly_rankings(hour)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_hourly_rankings_timestamp ON hourly_rankings(hour_timestamp)')
            
            conn.commit()
    
    def save_hourly_ranking_data(self, hourly_rankings: List[Dict[str, Any]]) -> int:
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
                    logger.error(f"Failed to save hourly ranking: {e}")
            
            conn.commit()
        return saved_count
    
    def get_hourly_rankings(self, site_id: Optional[int] = None, keyword_id: Optional[int] = None,
                           start_date: Optional[str] = None, end_date: Optional[str] = None,
                           hour: Optional[int] = None) -> List[Dict[str, Any]]:
        """獲取每小時排名數據"""
        with self.get_connection() as conn:
            conditions = []
            params = []
            
            if site_id:
                conditions.append('hr.site_id = ?')
                params.append(site_id)
            
            if keyword_id:
                conditions.append('hr.keyword_id = ?')
                params.append(keyword_id)
            
            if start_date:
                conditions.append('hr.date >= ?')
                params.append(start_date)
            
            if end_date:
                conditions.append('hr.date <= ?')
                params.append(end_date)
            
            if hour is not None:
                conditions.append('hr.hour = ?')
                params.append(hour)
            
            where_clause = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
            
            query = f'''
                SELECT 
                    hr.*,
                    s.name as site_name,
                    k.keyword
                FROM hourly_rankings hr
                LEFT JOIN sites s ON hr.site_id = s.id
                LEFT JOIN keywords k ON hr.keyword_id = k.id
                {where_clause}
                ORDER BY hr.date DESC, hr.hour DESC
            '''
            
            return [dict(row) for row in conn.execute(query, params).fetchall()]
    
    def get_hourly_summary(self, site_id: int, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """獲取每小時數據總結"""
        with self.get_connection() as conn:
            conditions = ['hr.site_id = ?']
            params = [site_id]
            
            if date:
                conditions.append('hr.date = ?')
                params.append(date)
            else:
                conditions.append('hr.date >= date("now", "-3 days")')
            
            where_clause = ' WHERE ' + ' AND '.join(conditions)
            
            query = f'''
                SELECT 
                    hr.date,
                    hr.hour,
                    COUNT(*) as query_count,
                    SUM(hr.clicks) as total_clicks,
                    SUM(hr.impressions) as total_impressions,
                    AVG(hr.position) as avg_position,
                    AVG(hr.ctr) as avg_ctr
                FROM hourly_rankings hr
                {where_clause}
                GROUP BY hr.date, hr.hour
                ORDER BY hr.date DESC, hr.hour DESC
            '''
            
            return [dict(row) for row in conn.execute(query, params).fetchall()]
    
    def get_hourly_coverage(self, site_id: int) -> Dict[str, Any]:
        """獲取每小時數據覆蓋情況"""
        with self.get_connection() as conn:
            # 檢查是否有每小時數據
            row = conn.execute('''
                SELECT 
                    COUNT(*) as total_records,
                    MIN(date) as first_date,
                    MAX(date) as last_date,
                    COUNT(DISTINCT date) as unique_dates,
                    COUNT(DISTINCT hour) as unique_hours
                FROM hourly_rankings 
                WHERE site_id = ?
            ''', (site_id,)).fetchone()
            
            result = dict(row) if row else {}
            
            # 獲取最近的數據點
            recent_data = conn.execute('''
                SELECT date, hour, COUNT(*) as records
                FROM hourly_rankings 
                WHERE site_id = ?
                ORDER BY date DESC, hour DESC
                LIMIT 24
            ''', (site_id,)).fetchall()
            
            result['recent_data'] = [dict(r) for r in recent_data]
            
            return result 