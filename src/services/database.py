#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .. import config

logger = logging.getLogger(__name__)


class SyncMode(str, Enum):
    SKIP = "skip"
    OVERWRITE = "overwrite"


class Database:
    def __init__(self, db_path: Optional[str] = None):
        """初始化數據庫連接"""
        if db_path is None:
            self.db_path = str(config.DB_PATH)
        else:
            self.db_path = db_path

        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """獲取數據庫連接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def check_connection(self) -> bool:
        """檢查數據庫連接"""
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def init_db(self):
        """初始化數據庫，創建所有必要的表"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            conn.execute("""
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
            """)
            conn.execute("""
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
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_keywords_site ON keywords(site_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_hourly_rankings_date ON hourly_rankings(date)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_hourly_rankings_site ON hourly_rankings(site_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_hourly_rankings_hour ON hourly_rankings(hour)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_hourly_rankings_timestamp ON hourly_rankings(hour_timestamp)"
            )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gsc_performance_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    page TEXT NOT NULL,
                    query TEXT NOT NULL,
                    device TEXT NOT NULL,
                    search_type TEXT NOT NULL,
                    clicks INTEGER,
                    impressions INTEGER,
                    ctr REAL,
                    position REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (site_id) REFERENCES sites (id),
                    UNIQUE(site_id, date, page, query, device, search_type)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_perf_data_site_date ON gsc_performance_data(site_id, date)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_perf_data_query ON gsc_performance_data(query)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_perf_data_page ON gsc_performance_data(page)"
            )
            conn.commit()
            logger.info("Database initialized successfully")
            self.init_task_table()

    def add_site(self, domain: str, name: str, category: Optional[str] = None) -> Optional[int]:
        """添加站點"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO sites (domain, name, category) VALUES (?, ?, ?)",
                    (domain, name, category),
                )
                site_id = cursor.lastrowid
                if site_id is None:
                    raise sqlite3.Error("Failed to get last row id.")
                return site_id
        except sqlite3.IntegrityError:
            logger.warning(f"Site with domain '{domain}' or name '{name}' already exists.")
            existing_site = self.get_site_by_domain(domain)
            if existing_site:
                return int(existing_site["id"])
            return None
        except sqlite3.Error as e:
            logger.error(f"Database error while adding site: {e}")
            return None

    def get_site_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """根據域名獲取站點"""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM sites WHERE domain = ?", (domain,)).fetchone()
            return dict(row) if row else None

    def get_site_by_id(self, site_id: int) -> Optional[Dict[str, Any]]:
        """根據 ID 獲取站點"""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
            return dict(row) if row else None

    def get_daily_data_coverage(self, site_id: int) -> Dict[str, Any]:
        """獲取指定站點的每日數據覆蓋情況。"""
        with self.get_connection() as conn:
            query = """
                SELECT COUNT(*) as total_records, MIN(date) as first_date, MAX(date) as last_date, COUNT(DISTINCT date) as unique_dates
                FROM gsc_performance_data WHERE site_id = ?
            """
            coverage_stats = conn.execute(query, (site_id,)).fetchone()
            return (
                dict(coverage_stats)
                if coverage_stats and coverage_stats["total_records"] > 0
                else {}
            )

    def get_hourly_data_coverage(self, site_id: int) -> Dict[str, Any]:
        """獲取指定站點的每小時數據覆蓋情況。"""
        with self.get_connection() as conn:
            query = """
                SELECT COUNT(*) as total_records, MIN(date) as first_date, MAX(date) as last_date, COUNT(DISTINCT date) as unique_dates
                FROM hourly_rankings WHERE site_id = ?
            """
            coverage_stats = conn.execute(query, (site_id,)).fetchone()
            return (
                dict(coverage_stats)
                if coverage_stats and coverage_stats["total_records"] > 0
                else {}
            )

    def get_site_by_url(self, site_url):
        with self.get_connection() as conn:
            return conn.execute("SELECT * FROM sites WHERE domain = ?", (site_url,)).fetchone()

    def remove_site(self, site_url: str) -> None:
        """根據網站 URL 從數據庫中移除一個網站。"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sites WHERE domain = ?", (site_url,))
            conn.commit()
            if cursor.rowcount == 0:
                print(f"⚠️ 警告：在數據庫中找不到 URL 為 {site_url} 的網站，無法刪除。")

    def get_sites(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """獲取站點列表"""
        with self.get_connection() as conn:
            query = "SELECT * FROM sites"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY name"
            return [dict(row) for row in conn.execute(query).fetchall()]

    def cleanup_duplicate_domains(self) -> int:
        """
        清理數據庫中 'sc-domain:sc-domain:...' 形式的重複網域。
        將 'sc-domain:sc-domain:example.com' 修正為 'sc-domain:example.com'。
        """
        updated_count = 0
        with self.get_connection() as conn:
            # 查找所有格式錯誤的站點
            query = "SELECT id, domain FROM sites WHERE domain LIKE 'sc-domain:sc-domain:%'"
            cursor = conn.execute(query)
            sites_to_fix = [dict(row) for row in cursor.fetchall()]

            if not sites_to_fix:
                return 0

            updates = []
            for site in sites_to_fix:
                correct_domain = "sc-domain:" + site["domain"].split("sc-domain:")[-1]
                updates.append((correct_domain, site["id"]))

            try:
                cursor.executemany("UPDATE sites SET domain = ? WHERE id = ?", updates)
                conn.commit()
                updated_count = cursor.rowcount
            except sqlite3.IntegrityError as e:
                logger.error(f"清理重複網域時發生錯誤，可能有唯一性衝突: {e}")
                conn.rollback()
            except sqlite3.Error as e:
                logger.error(f"清理重複網域時發生數據庫錯誤: {e}")
                conn.rollback()

        return updated_count

    def deactivate_prefix_sites(self, dry_run: bool = True) -> List[Dict[str, Any]] | int:
        """
        查找或停用所有非 'sc-domain' 的、且已存在對應 sc-domain 版本的站點。
        """
        from urllib.parse import urlparse

        def get_base_domain(url_str: str) -> Optional[str]:
            """從 sc-domain 或 URL 中提取基礎域名"""
            if url_str.startswith("sc-domain:"):
                return url_str.replace("sc-domain:", "")
            try:
                parsed_url = urlparse(url_str)
                netloc = parsed_url.netloc
                # 移除 'www.' 前綴
                if netloc.startswith("www."):
                    return netloc[4:]
                return netloc
            except Exception:
                return None

        with self.get_connection() as conn:
            # 1. 獲取所有活躍的 sc-domain 核心網域
            sc_domain_cursor = conn.execute(
                "SELECT domain FROM sites WHERE is_active = 1 AND domain LIKE 'sc-domain:%'"
            )
            sc_domains_set = {get_base_domain(row["domain"]) for row in sc_domain_cursor}
            # 移除任何可能的 None 值
            sc_domains_set.discard(None)

            # 2. 獲取所有活躍的前置字元站點
            prefix_sites_cursor = conn.execute(
                "SELECT id, domain FROM sites WHERE is_active = 1 AND (domain LIKE 'http://%' OR domain LIKE 'https://%')"
            )
            prefix_sites = [dict(row) for row in prefix_sites_cursor.fetchall()]

            # 3. 找出有對應 sc-domain 的前置字元站點
            sites_to_deactivate = []
            for site in prefix_sites:
                base_domain = get_base_domain(site["domain"])
                if base_domain and base_domain in sc_domains_set:
                    sites_to_deactivate.append(site)

            if dry_run:
                return sites_to_deactivate

            if not sites_to_deactivate:
                return 0

            site_ids = [site["id"] for site in sites_to_deactivate]
            try:
                placeholders = ",".join("?" for _ in site_ids)
                update_query = f"UPDATE sites SET is_active = 0 WHERE id IN ({placeholders})"

                cursor = conn.cursor()
                cursor.execute(update_query, site_ids)
                conn.commit()
                return cursor.rowcount
            except sqlite3.Error as e:
                logger.error(f"停用前置字元站點時出錯: {e}")
                conn.rollback()
                return 0

    def batch_update_site_domains(self, sites_to_update: List[Dict[str, Any]]) -> int:
        """批量更新站點的 domain 字段，使其與 name 字段一致。"""
        if not sites_to_update:
            return 0
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                update_data = [(site["name"], site["id"]) for site in sites_to_update]
                cursor.executemany("UPDATE sites SET domain = ? WHERE id = ?", update_data)
                conn.commit()
                logger.info(f"Successfully updated {cursor.rowcount} site domains.")
                return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"Failed to batch update site domains: {e}")
            return 0

    def find_duplicate_sites(self) -> Dict[str, List[Dict[str, Any]]]:
        """使用 SQL GROUP BY 高效查找重複的站點名稱和域名。"""
        duplicates: Dict[str, List[Dict[str, Any]]] = {"name": [], "domain": []}
        with self.get_connection() as conn:
            name_cursor = conn.execute(
                "SELECT name, COUNT(id) as count FROM sites GROUP BY name HAVING COUNT(id) > 1"
            )
            duplicates["name"] = [dict(row) for row in name_cursor.fetchall()]
            domain_cursor = conn.execute(
                "SELECT domain, COUNT(id) as count FROM sites GROUP BY domain HAVING COUNT(id) > 1"
            )
            duplicates["domain"] = [dict(row) for row in domain_cursor.fetchall()]
        return duplicates

    def save_data_chunk(
        self,
        chunk: List[Dict[str, Any]],
        site_id: int,
        sync_mode: str,
        date_str: str,
        device: str,
        search_type: str,
    ) -> Dict[str, int]:
        """保存一個數據塊到數據庫。"""
        stats = {"inserted": 0, "updated": 0, "skipped": 0}
        if not chunk:
            return stats
        to_insert = []
        with self.get_connection() as conn:
            if sync_mode == "skip":
                for row in chunk:
                    res = conn.execute(
                        "SELECT id FROM gsc_performance_data WHERE site_id=? AND date=? AND page=? AND query=? AND device=? AND search_type=?",
                        (
                            site_id,
                            date_str,
                            row["page"],
                            row["query"],
                            device,
                            search_type,
                        ),
                    ).fetchone()
                    if res is None:
                        to_insert.append(row)
                    else:
                        stats["skipped"] += 1
            else:
                to_insert = chunk
            if to_insert:
                insert_data = [
                    (
                        site_id,
                        date_str,
                        row["page"],
                        row["query"],
                        device,
                        search_type,
                        row["clicks"],
                        row["impressions"],
                        row["ctr"],
                        row["position"],
                    )
                    for row in to_insert
                ]
                conn.executemany(
                    "INSERT OR REPLACE INTO gsc_performance_data (site_id, date, page, query, device, search_type, clicks, impressions, ctr, position) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    insert_data,
                )
                stats["inserted"] = len(to_insert)
            conn.commit()
        return stats

    def delete_performance_data_for_day(self, site_id: int, date: str):
        """刪除指定站點和日期的性能數據。"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "DELETE FROM gsc_performance_data WHERE site_id = ? AND date = ?",
                    (site_id, date),
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error deleting performance data for site {site_id} on {date}: {e}")

    def batch_delete_sites(self, site_ids: List[int]) -> int:
        """批量刪除站點及其關聯數據。"""
        if not site_ids:
            return 0
        placeholders = ", ".join("?" for _ in site_ids)
        with self.get_connection() as conn:
            try:
                conn.execute(
                    f"DELETE FROM gsc_performance_data WHERE site_id IN ({placeholders})",
                    site_ids,
                )
                conn.execute(f"DELETE FROM keywords WHERE site_id IN ({placeholders})", site_ids)
                cursor = conn.execute(f"DELETE FROM sites WHERE id IN ({placeholders})", site_ids)
                conn.commit()
                logger.info(
                    f"Successfully deleted {cursor.rowcount} sites and their associated data."
                )
                return cursor.rowcount
            except sqlite3.Error as e:
                logger.error(f"Failed to batch delete sites: {e}")
                conn.rollback()
                return 0

    def batch_add_sites(self, site_names: List[str]) -> int:
        """批量添加站點，如果站點已存在則跳過。"""
        if not site_names:
            return 0

        sites_to_insert = []
        for name in site_names:
            # 修正：檢查 `sc-domain:` 前綴是否已存在，避免重複添加
            if name.startswith("sc-domain:"):
                domain = name
            elif "://" in name:
                domain = name
            else:
                # 假設沒有協議的就是域名屬性，但需要添加前綴
                domain = f"sc-domain:{name}"

            sites_to_insert.append((domain, name))

        with self.get_connection() as conn:
            try:
                cursor = conn.cursor()
                # 使用 INSERT OR IGNORE 來避免因 UNIQUE 約束而失敗
                cursor.executemany(
                    "INSERT OR IGNORE INTO sites (domain, name) VALUES (?, ?)",
                    sites_to_insert,
                )
                conn.commit()
                logger.info(f"Batch add sites completed. Added {cursor.rowcount} new sites.")
                return cursor.rowcount
            except sqlite3.Error as e:
                logger.error(f"Failed to batch add sites: {e}")
                return 0

    def add_keyword(
        self,
        keyword: str,
        site_id: int,
        category: Optional[str] = None,
        priority: int = 0,
    ) -> Optional[int]:
        """添加關鍵字，如果已存在則返回現有ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO keywords (keyword, site_id, category, priority) VALUES (?, ?, ?, ?)",
                    (keyword, site_id, category, priority),
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM keywords WHERE keyword = ? AND site_id = ?",
                    (keyword, site_id),
                ).fetchone()
                return row["id"] if row else None
        except sqlite3.Error as e:
            logger.error(f"Database error while adding keyword: {e}")
            return None

    def ensure_keywords_and_get_map(self, site_id: int, keyword_texts: List[str]) -> Dict[str, int]:
        """確保一組關鍵字存在於數據庫中，並返回關鍵字文本到ID的映射。"""
        if not keyword_texts:
            return {}
        to_insert = [(k, site_id) for k in set(keyword_texts)]
        with self.get_connection() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO keywords (keyword, site_id) VALUES (?, ?)",
                to_insert,
            )
            conn.commit()
            placeholders = ",".join("?" for _ in keyword_texts)
            cursor = conn.execute(
                f"SELECT keyword, id FROM keywords WHERE site_id = ? AND keyword IN ({placeholders})",
                [site_id] + list(keyword_texts),
            )
            return {row["keyword"]: row["id"] for row in cursor.fetchall()}

    def get_keywords(self, site_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """獲取關鍵字列表"""
        with self.get_connection() as conn:
            if site_id:
                rows = conn.execute(
                    "SELECT * FROM keywords WHERE site_id = ? ORDER BY priority DESC, keyword",
                    (site_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM keywords ORDER BY site_id, priority DESC, keyword"
                ).fetchall()
            return [dict(row) for row in rows]

    def get_distinct_pages_for_site(self, site_id: int) -> List[str]:
        """從 gsc_performance_data 表中獲取指定站點的所有唯一頁面。"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT DISTINCT page FROM gsc_performance_data WHERE site_id = ?",
                (site_id,),
            )
            return [row["page"] for row in cursor.fetchall()]

    def get_all_pages_for_site(self, site_id: int) -> List[str]:
        """從 gsc_performance_data 表中獲取指定站點的所有頁面。"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT page FROM gsc_performance_data WHERE site_id = ?", (site_id,)
            )
            return [row["page"] for row in cursor.fetchall()]

    def search_keywords_by_semantic(
        self, search_term: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """通過語義搜索在'keywords'表中查找與'search_term'相似的'keyword'。"""
        with self.get_connection() as conn:
            query = """
                SELECT k.*, s.name as site_name FROM keywords k JOIN sites s ON k.site_id = s.id
                WHERE k.keyword LIKE ? ORDER BY k.priority DESC LIMIT ?
            """
            cursor = conn.execute(query, (f"%{search_term}%", limit))
            results = [dict(row) for row in cursor.fetchall()]
            return results

    def get_keywords_for_sitemap(self, site_id: int) -> List[str]:
        """為生成站點地圖獲取關鍵字列表。"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT keyword FROM keywords WHERE site_id = ? ORDER BY priority DESC",
                (site_id,),
            )
            return [row["keyword"] for row in cursor.fetchall()]

    def init_task_table(self):
        """初始化任務追蹤表"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER, task_type TEXT, start_date TEXT, end_date TEXT, status TEXT,
                    started_at TIMESTAMP, completed_at TIMESTAMP, total_records INTEGER,
                    FOREIGN KEY (site_id) REFERENCES sites (id)
                )
            """)
            conn.commit()

    def start_sync_task(
        self,
        site_id: int,
        task_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        """開始一個新的同步任務並返回任務ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO sync_tasks (site_id, task_type, start_date, end_date, status, started_at) VALUES (?, ?, ?, ?, 'running', ?)",
                (site_id, task_type, start_date, end_date, datetime.now().isoformat()),
            )
            task_id = cursor.lastrowid
            if task_id is None:
                raise sqlite3.Error("Failed to create a sync task.")
            return task_id

    def complete_sync_task(self, task_id: int, total_records: int = 0, status: str = "completed"):
        """標記任務完成或失敗"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE sync_tasks SET status = ?, total_records = ?, completed_at = ? WHERE id = ?",
                (status, total_records, datetime.now().isoformat(), task_id),
            )

    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取最近的同步任務"""
        with self.get_connection() as conn:
            query = """
                SELECT t.*, s.name as site_name FROM sync_tasks t LEFT JOIN sites s ON t.site_id = s.id
                ORDER BY t.started_at DESC LIMIT ?
            """
            return [dict(row) for row in conn.execute(query, (limit,)).fetchall()]

    def get_latest_date_from_table(self, table_name: str, site_id: int) -> Optional[date]:
        """從指定表獲取指定站點的最新日期"""
        with self.get_connection() as conn:
            query = f"SELECT MAX(date) FROM {table_name} WHERE site_id = ?"
            result = conn.execute(query, (site_id,)).fetchone()
            if result and result[0]:
                return datetime.strptime(result[0], "%Y-%m-%d").date()
            return None

    def close_connection(self):
        pass
