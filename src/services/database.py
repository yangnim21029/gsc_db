#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SyncMode(str, Enum):
    SKIP = "skip"
    OVERWRITE = "overwrite"


class Database:
    def __init__(self, connection: sqlite3.Connection, lock: threading.Lock):
        """初始化數據庫服務，接收共享的連接和鎖。"""
        self._connection = connection
        self._lock = lock
        logger.info("Database service initialized with shared connection and lock.")
        # 初始化資料庫表格
        self.init_db()

    def check_connection(self) -> bool:
        """檢查數據庫連接"""
        try:
            # 使用鎖來安全地執行檢查
            with self._lock:
                self._connection.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def init_db(self):
        """初始化數據庫，創建所有必要的表。線程安全。"""
        with self._lock:
            cursor = self._connection.cursor()
            cursor.execute("""
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
            cursor.execute("""
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
            cursor.execute("""
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_site ON keywords(site_id)")
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_hourly_rankings_date
                ON hourly_rankings(date)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_hourly_rankings_site
                ON hourly_rankings(site_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_hourly_rankings_hour
                ON hourly_rankings(hour)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_hourly_rankings_timestamp
                ON hourly_rankings(hour_timestamp)
                """
            )
            cursor.execute("""
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
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_perf_data_site_date
                ON gsc_performance_data(site_id, date)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_perf_data_query
                ON gsc_performance_data(query)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_perf_data_page
                ON gsc_performance_data(page)
                """
            )
            self._connection.commit()
            logger.info("Database initialized successfully")
            self.init_task_table()

    def add_site(self, domain: str, name: str, category: Optional[str] = None) -> Optional[int]:
        """添加站點。線程安全。"""
        with self._lock:
            try:
                cursor = self._connection.execute(
                    "INSERT INTO sites (domain, name, category) VALUES (?, ?, ?)",
                    (domain, name, category),
                )
                self._connection.commit()
                site_id = cursor.lastrowid
                if site_id is None:
                    # 在某些情況下（如 ON CONFLICT IGNORE），lastrowid 可能為 0 或 None
                    # 我們需要查詢以確保站點存在
                    existing_site = self.get_site_by_domain(domain, use_lock=False)
                    return int(existing_site["id"]) if existing_site else None
                return site_id
            except sqlite3.IntegrityError:
                logger.warning(f"Site with domain '{domain}' or name '{name}' already exists.")
                # 因為已經在鎖內部，所以調用一個不獲取鎖的內部版本
                existing_site = self.get_site_by_domain(domain, use_lock=False)
                if existing_site:
                    return int(existing_site["id"])
                return None
            except sqlite3.Error as e:
                logger.error(f"Database error while adding site: {e}")
                self._connection.rollback()
                return None

    def get_site_by_domain(self, domain: str, use_lock: bool = True) -> Optional[Dict[str, Any]]:
        """根據域名獲取站點。線程安全可選。"""

        def _fetch() -> Optional[Dict[str, Any]]:
            row = self._connection.execute(
                "SELECT * FROM sites WHERE domain = ?", (domain,)
            ).fetchone()
            return dict(row) if row else None

        if use_lock:
            with self._lock:
                return _fetch()
        else:
            return _fetch()

    def get_site_by_id(self, site_id: int) -> Optional[Dict[str, Any]]:
        """根據 ID 獲取站點。線程安全。"""
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM sites WHERE id = ?", (site_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_daily_data_coverage(self, site_id: int) -> Dict[str, Any]:
        """獲取指定站點的每日數據覆蓋情況。"""
        query = """
        SELECT date, COUNT(*) as count
        FROM gsc_performance_data
        WHERE site_id = ?
        GROUP BY date
        ORDER BY date DESC
        """
        with self._lock:
            rows = self._connection.execute(query, (site_id,)).fetchall()
        return {row["date"]: row["count"] for row in rows}

    def get_hourly_data_coverage(self, site_id: int) -> Dict[str, Any]:
        """獲取指定站點的每小時數據覆蓋情況。"""
        query = """
        SELECT date, COUNT(DISTINCT hour) as count
        FROM hourly_rankings
        WHERE site_id = ?
        GROUP BY date
        ORDER BY date DESC
        """
        with self._lock:
            rows = self._connection.execute(query, (site_id,)).fetchall()
        return {row["date"]: row["count"] for row in rows}

    def get_site_by_url(self, site_url):
        with self._lock:
            return self.get_site_by_domain(site_url)

    def remove_site(self, site_url: str) -> None:
        """根據網址移除站點。線程安全。"""
        with self._lock:
            site = self.get_site_by_domain(site_url, use_lock=False)
            if site:
                self._connection.execute("DELETE FROM sites WHERE id = ?", (site["id"],))
                self._connection.commit()
                logger.info(f"Site '{site_url}' removed.")
            else:
                logger.warning(f"Site '{site_url}' not found.")

    def get_sites(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """獲取所有站點。線程安全。"""
        query = "SELECT * FROM sites"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        with self._lock:
            rows = self._connection.execute(query).fetchall()
            return [dict(row) for row in rows]

    def cleanup_duplicate_domains(self) -> int:
        """清理重複的域名，保留最新的記錄。線程安全。"""
        with self._lock:
            find_duplicates_query = """
            SELECT domain, COUNT(*) as count, GROUP_CONCAT(id) as ids, MAX(id) as keep_id
            FROM sites
            GROUP BY domain
            HAVING count > 1
            """
            duplicates = self._connection.execute(find_duplicates_query).fetchall()

            deleted_count = 0
            for dup in duplicates:
                ids_to_delete = [int(i) for i in dup["ids"].split(",") if int(i) != dup["keep_id"]]
                placeholders = ",".join("?" for _ in ids_to_delete)
                delete_query = f"DELETE FROM sites WHERE id IN ({placeholders})"
                cursor = self._connection.execute(delete_query, ids_to_delete)
                deleted_count += cursor.rowcount

            if deleted_count > 0:
                self._connection.commit()

            logger.info(f"清理了 {deleted_count} 個重複的站點記錄。")
            return deleted_count

    def deactivate_prefix_sites(self, dry_run: bool = True) -> List[Dict[str, Any]] | int:
        """
        查找或停用所有非 'sc-domain' 的、且已存在對應 sc-domain 版本的站點。
        """
        from urllib.parse import urlparse

        def get_base_domain(url_str: str) -> Optional[str]:
            try:
                if not url_str.startswith(("http://", "https://")):
                    url_str = "https://" + url_str

                parsed = urlparse(url_str)
                # www.example.com -> example.com
                if parsed.netloc.startswith("www."):
                    return parsed.netloc[4:]
                return parsed.netloc
            except Exception:
                return None

        with self._lock:
            all_sites = {
                dict(row)["id"]: dict(row)
                for row in self._connection.execute("SELECT id, domain FROM sites").fetchall()
            }

            domains_map: Dict[str, List[int]] = {}
            for site_id, site_info in all_sites.items():
                base_domain = get_base_domain(site_info["domain"])
                if base_domain:
                    if base_domain not in domains_map:
                        domains_map[base_domain] = []
                    domains_map[base_domain].append(site_id)

            sites_to_deactivate = []
            for base_domain, site_ids in domains_map.items():
                if len(site_ids) > 1:
                    # 找到非 www 的那個作為主站點
                    main_site_id = None
                    for sid in site_ids:
                        if not all_sites[sid]["domain"].startswith("www."):
                            main_site_id = sid
                            break

                    if main_site_id:
                        for sid in site_ids:
                            if sid != main_site_id:
                                sites_to_deactivate.append(all_sites[sid])

            if dry_run:
                return sites_to_deactivate

            if not sites_to_deactivate:
                return 0

            site_ids = [site["id"] for site in sites_to_deactivate]
            try:
                placeholders = ",".join("?" for _ in site_ids)
                update_query = f"UPDATE sites SET is_active = 0 WHERE id IN ({placeholders})"

                cursor = self._connection.cursor()
                cursor.execute(update_query, site_ids)
                self._connection.commit()
                return cursor.rowcount
            except sqlite3.Error as e:
                logger.error(f"停用前置字元站點時出錯: {e}")
                self._connection.rollback()
                return 0

    def batch_update_site_domains(self, sites_to_update: List[Dict[str, Any]]) -> int:
        """批量更新站點域名。線程安全。"""
        with self._lock:
            cursor = self._connection.cursor()
            cursor.executemany("UPDATE sites SET domain = :domain WHERE id = :id", sites_to_update)
            count = cursor.rowcount
            self._connection.commit()
            return count

    def find_duplicate_sites(self) -> Dict[str, List[Dict[str, Any]]]:
        """查找具有相同基本域名的站點。線程安全。"""
        with self._lock:
            sites = self.get_sites(active_only=False)

        domain_map: Dict[str, List[Dict[str, Any]]] = {}
        for site in sites:
            # 簡單處理，移除 'www.'
            base_domain = site["name"].replace("www.", "")
            if base_domain not in domain_map:
                domain_map[base_domain] = []
            domain_map[base_domain].append(site)

        return {k: v for k, v in domain_map.items() if len(v) > 1}

    def save_data_chunk(
        self,
        chunk: List[Dict[str, Any]],
        site_id: int,
        sync_mode: str,
        date_str: str,
        device: str,
        search_type: str,
    ) -> Dict[str, int]:
        """保存數據塊。線程安全。"""
        stats = {"inserted": 0, "updated": 0, "skipped": 0}

        def row_to_dict(row):
            # 將 gsc_client 回傳的 Pydantic 模型轉為字典
            return {
                "clicks": row.clicks,
                "impressions": row.impressions,
                "ctr": row.ctr,
                "position": row.position,
                "page": row.keys[0],
                "query": row.keys[1],
                "device": row.keys[2],
                "search_type": row.keys[3],
            }

        data_to_insert = [row_to_dict(row) for row in chunk]

        with self._lock:
            cursor = self._connection.cursor()

            if sync_mode == "overwrite":
                # 在 OVERWRITE 模式下，我們依賴 delete_performance_data_for_day 預先刪除
                # 所以這裡總是 INSERT
                sql = """
                    INSERT INTO gsc_performance_data
                    (site_id, date, page, query, device, search_type,
                     clicks, impressions, ctr, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = [
                    (
                        site_id,
                        date_str,
                        d["page"],
                        d["query"],
                        d["device"],
                        d["search_type"],
                        d["clicks"],
                        d["impressions"],
                        d["ctr"],
                        d["position"],
                    )
                    for d in data_to_insert
                ]
                cursor.executemany(sql, params)
                stats["inserted"] += cursor.rowcount
            else:  # "skip" or other modes
                # 在 SKIP 模式下，我們插入或忽略重複
                sql = """
                    INSERT OR IGNORE INTO gsc_performance_data
                    (site_id, date, page, query, device, search_type,
                     clicks, impressions, ctr, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = [
                    (
                        site_id,
                        date_str,
                        d["page"],
                        d["query"],
                        d["device"],
                        d["search_type"],
                        d["clicks"],
                        d["impressions"],
                        d["ctr"],
                        d["position"],
                    )
                    for d in data_to_insert
                ]
                cursor.executemany(sql, params)
                stats["inserted"] += cursor.rowcount

            self._connection.commit()

        return stats

    def delete_performance_data_for_day(self, site_id: int, date: str):
        """刪除指定站點和日期的所有性能數據。線程安全。"""
        with self._lock:
            self._connection.execute(
                "DELETE FROM gsc_performance_data WHERE site_id = ? AND date = ?",
                (site_id, date),
            )
            self._connection.commit()
            logger.info(f"Deleted performance data for site {site_id} on {date}")

    def batch_delete_sites(self, site_ids: List[int]) -> int:
        """批量刪除站點及其相關數據。線程安全。"""
        with self._lock:
            try:
                placeholders = ",".join("?" * len(site_ids))

                # 刪除相關數據
                self._connection.execute(
                    f"DELETE FROM gsc_performance_data WHERE site_id IN ({placeholders})", site_ids
                )
                self._connection.execute(
                    f"DELETE FROM hourly_rankings WHERE site_id IN ({placeholders})", site_ids
                )
                self._connection.execute(
                    f"DELETE FROM keywords WHERE site_id IN ({placeholders})", site_ids
                )

                # 刪除站點本身
                cursor = self._connection.execute(
                    f"DELETE FROM sites WHERE id IN ({placeholders})", site_ids
                )

                deleted_count = cursor.rowcount
                self._connection.commit()

                logger.info(f"成功刪除 {deleted_count} 個站點及其相關數據。")
                return deleted_count
            except sqlite3.Error as e:
                logger.error(f"批量刪除站點時發生錯誤: {e}")
                self._connection.rollback()
                return 0

    def batch_add_sites(self, site_names: List[str]) -> int:
        """批量添加站點。線程安全。"""
        sites_to_insert = []
        for name in site_names:
            domain = name  # 假設 name 就是 domain
            sites_to_insert.append({"domain": domain, "name": name})

        if not sites_to_insert:
            return 0

        with self._lock:
            try:
                cursor = self._connection.cursor()
                cursor.executemany(
                    "INSERT OR IGNORE INTO sites (domain, name) VALUES (:domain, :name)",
                    sites_to_insert,
                )
                added_count = cursor.rowcount
                self._connection.commit()
                logger.info(f"成功批量添加 {added_count} 個站點。")
                return added_count
            except sqlite3.Error as e:
                logger.error(f"批量添加站點時發生錯誤: {e}")
                self._connection.rollback()
                return 0

    def add_keyword(
        self,
        keyword: str,
        site_id: int,
        category: Optional[str] = None,
        priority: int = 0,
    ) -> Optional[int]:
        """添加關鍵字。線程安全。"""
        with self._lock:
            try:
                cursor = self._connection.execute(
                    """
                    INSERT INTO keywords (keyword, site_id, category, priority)
                    VALUES (?, ?, ?, ?)
                    """,
                    (keyword, site_id, category, priority),
                )
                self._connection.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                logger.warning(f"Keyword '{keyword}' already exists for site ID {site_id}.")
                # 關鍵字已存在，返回現有 ID
                row = self._connection.execute(
                    "SELECT id FROM keywords WHERE keyword = ? AND site_id = ?", (keyword, site_id)
                ).fetchone()
                return row["id"] if row else None
            except sqlite3.Error as e:
                logger.error(f"添加關鍵字時出錯: {e}")
                self._connection.rollback()
                return None

    def ensure_keywords_and_get_map(self, site_id: int, keyword_texts: List[str]) -> Dict[str, int]:
        """確保關鍵字存在並返回 text -> id 的映射。線程安全。"""
        with self._lock:
            placeholders = ",".join("?" * len(keyword_texts))
            existing_keywords_query = f"""
                SELECT keyword, id FROM keywords
                WHERE site_id = ? AND keyword IN ({placeholders})
            """
            rows = self._connection.execute(
                existing_keywords_query, [site_id] + list(keyword_texts)
            ).fetchall()
            keyword_map = {row["keyword"]: row["id"] for row in rows}

            new_keywords = [kw for kw in keyword_texts if kw not in keyword_map]
            if new_keywords:
                to_insert = [(kw, site_id) for kw in new_keywords]
                self._connection.executemany(
                    "INSERT INTO keywords (keyword, site_id) VALUES (?, ?)", to_insert
                )
                self._connection.commit()

                # 重新查詢以獲取新插入的ID
                new_rows = self._connection.execute(
                    existing_keywords_query, [site_id] + list(keyword_texts)
                ).fetchall()
                keyword_map = {row["keyword"]: row["id"] for row in new_rows}

        return keyword_map

    def get_keywords(self, site_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """獲取指定站點的關鍵字。線程安全。"""
        with self._lock:
            if site_id:
                rows = self._connection.execute(
                    "SELECT * FROM keywords WHERE site_id = ? ORDER BY keyword", (site_id,)
                ).fetchall()
            else:
                rows = self._connection.execute(
                    "SELECT * FROM keywords ORDER BY keyword"
                ).fetchall()
            return [dict(row) for row in rows]

    def get_distinct_pages_for_site(self, site_id: int) -> List[str]:
        """獲取站點的所有不重複頁面。線程安全。"""
        with self._lock:
            rows = self._connection.execute(
                "SELECT DISTINCT page FROM gsc_performance_data WHERE site_id = ? ORDER BY page",
                (site_id,),
            ).fetchall()
            return [row["page"] for row in rows]

    def get_all_pages_for_site(self, site_id: int) -> List[str]:
        """(Legacy) 獲取站點的所有頁面，此處與 get_distinct_pages_for_site 相同。線程安全。"""
        with self._lock:
            return self.get_distinct_pages_for_site(site_id)

    def search_keywords_by_semantic(
        self, search_term: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """通過語義搜索關鍵字（此處為簡單 LIKE 搜索）。線程安全。"""
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM keywords WHERE keyword LIKE ? LIMIT ?",
                (f"%{search_term}%", limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_keywords_for_sitemap(self, site_id: int) -> List[str]:
        """獲取站點地圖的關鍵字。線程安全。"""
        with self._lock:
            rows = self._connection.execute(
                "SELECT keyword FROM keywords WHERE site_id = ?", (site_id,)
            ).fetchall()
            return [row["keyword"] for row in rows]

    def init_task_table(self):
        """初始化任務隊列/歷史記錄表。線程安全。"""
        with self._lock:
            cursor = self._connection.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER,
                task_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                start_date TEXT,
                end_date TEXT,
                total_records INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites (id)
            )
            """)
            self._connection.commit()

    def start_sync_task(
        self,
        site_id: int,
        task_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        """開始一個同步任務並返回任務ID。線程安全。"""
        with self._lock:
            cursor = self._connection.execute(
                """
                INSERT INTO sync_tasks (site_id, task_type, start_date, end_date, status)
                VALUES (?, ?, ?, ?, 'running')
                """,
                (site_id, task_type, start_date, end_date),
            )
            task_id = cursor.lastrowid
            self._connection.commit()
            if not task_id:
                raise Exception("Failed to create sync task and get task ID.")
            return task_id

    def complete_sync_task(self, task_id: int, total_records: int = 0, status: str = "completed"):
        """完成一個同步任務。線程安全。"""
        with self._lock:
            self._connection.execute(
                """
                UPDATE sync_tasks
                SET status = ?, total_records = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, total_records, task_id),
            )
            self._connection.commit()

    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取最近的任務。線程安全。"""
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM sync_tasks ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_existing_data_days_for_sites(
        self, site_ids: List[int], start_date: str, end_date: str
    ) -> set[tuple[int, str]]:
        """獲取指定站點和日期範圍內已存在數據的 (site_id, date) 組合。線程安全。"""
        with self._lock:
            placeholders = ",".join("?" for _ in site_ids)
            query = f"""
                SELECT DISTINCT site_id, date
                FROM gsc_performance_data
                WHERE site_id IN ({placeholders})
                AND date BETWEEN ? AND ?
            """
            params = list(site_ids) + [start_date, end_date]
            rows = self._connection.execute(query, params).fetchall()
            return {(row["site_id"], row["date"]) for row in rows}

    def get_latest_date_from_table(
        self, table_name: str, site_id: Optional[int] = None
    ) -> Optional[date]:
        """從指定表中獲取某個站點的最新日期。如果 site_id 為 None，則獲取整個表的最新日期。
        線程安全。"""
        query = f"SELECT MAX(date) as max_date FROM {table_name}"
        params = []
        if site_id is not None:
            query += " WHERE site_id = ?"
            params.append(site_id)

        with self._lock:
            result = self._connection.execute(query, params).fetchone()
        if result and result["max_date"]:
            return datetime.strptime(result["max_date"], "%Y-%m-%d").date()
        return None

    # --- Methods for Hourly Rankings ---

    def get_existing_hourly_dates(self, site_id: int, start_date: str, end_date: str) -> set[str]:
        """一次性獲取指定範圍內已存在每小時數據的日期集合。線程安全。"""
        with self._lock:
            cursor = self._connection.execute(
                """
                SELECT DISTINCT date
                FROM hourly_rankings
                WHERE site_id = ? AND date BETWEEN ? AND ?
                """,
                (site_id, start_date, end_date),
            )
            return {row["date"] for row in cursor.fetchall()}

    def delete_hourly_data_for_date(self, site_id: int, date: str):
        """為特定日期刪除每小時數據。線程安全。"""
        with self._lock:
            try:
                self._connection.execute(
                    "DELETE FROM hourly_rankings WHERE site_id = ? AND date = ?",
                    (site_id, date),
                )
                self._connection.commit()
                logger.info(f"Deleted hourly data for site {site_id} on {date}")
            except sqlite3.Error as e:
                logger.error(f"Failed to delete hourly data for site {site_id} on {date}: {e}")
                self._connection.rollback()
                raise

    def save_hourly_ranking_data(self, hourly_rankings: List[Dict[str, Any]]) -> int:
        """保存每小時排名數據 (使用批量操作優化)。線程安全。"""
        if not hourly_rankings:
            return 0

        data_to_insert = [
            (
                r["site_id"],
                r.get("keyword_id"),
                r["date"],
                r["hour"],
                r["hour_timestamp"],
                r["query"],
                r.get("position"),
                r.get("clicks", 0),
                r.get("impressions", 0),
                r.get("ctr", 0),
                r.get("page"),
                r.get("country", "TWN"),
                r.get("device", "ALL"),
            )
            for r in hourly_rankings
        ]

        with self._lock:
            try:
                cursor = self._connection.cursor()
                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO hourly_rankings
                    (site_id, keyword_id, date, hour, hour_timestamp, query, position,
                     clicks, impressions, ctr, page, country, device)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    data_to_insert,
                )
                self._connection.commit()
                saved_count = cursor.rowcount if cursor.rowcount != -1 else len(data_to_insert)
                logger.info(f"Saved {saved_count} hourly ranking records")
                return saved_count
            except sqlite3.Error as e:
                logger.error(f"Failed to save hourly ranking data in batch: {e}")
                self._connection.rollback()
                return 0

    def get_hourly_rankings(
        self,
        site_id: Optional[int] = None,
        keyword_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        hour: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """獲取每小時排名數據。線程安全。"""
        with self._lock:
            conditions = []
            params: List[Any] = []

            if site_id is not None:
                conditions.append("hr.site_id = ?")
                params.append(site_id)

            if keyword_id is not None:
                conditions.append("hr.keyword_id = ?")
                params.append(keyword_id)

            if start_date:
                conditions.append("hr.date >= ?")
                params.append(start_date)

            if end_date:
                conditions.append("hr.date <= ?")
                params.append(end_date)

            if hour is not None:
                conditions.append("hr.hour = ?")
                params.append(hour)

            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT
                    hr.*,
                    s.name as site_name,
                    k.keyword
                FROM hourly_rankings hr
                LEFT JOIN sites s ON hr.site_id = s.id
                LEFT JOIN keywords k ON hr.keyword_id = k.id
                {where_clause}
                ORDER BY hr.date DESC, hr.hour DESC
            """
            return [dict(row) for row in self._connection.execute(query, params).fetchall()]

    def get_hourly_summary(self, site_id: int, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """獲取每小時數據總結。線程安全。"""
        with self._lock:
            conditions = ["hr.site_id = ?"]
            params: List[Any] = [site_id]
            if date:
                conditions.append("hr.date = ?")
                params.append(date)

            where_clause = " WHERE " + " AND ".join(conditions)

            query = f"""
                SELECT
                    hr.hour,
                    COUNT(hr.id) as record_count,
                    AVG(hr.position) as avg_position,
                    SUM(hr.clicks) as total_clicks,
                    SUM(hr.impressions) as total_impressions
                FROM hourly_rankings hr
                {where_clause}
                GROUP BY hr.hour
                ORDER BY hr.hour
            """
            return [dict(row) for row in self._connection.execute(query, params).fetchall()]

    # --- API Usage Stats ---

    def init_api_usage_table(self):
        """初始化 API 使用統計表。"""
        with self._lock:
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS api_usage_stats (
                    date TEXT PRIMARY KEY,
                    requests_count INTEGER NOT NULL DEFAULT 0
                )
            """)
            self._connection.commit()

    def get_api_usage(self, date_str: str) -> int:
        """獲取指定日期的 API 請求計數。"""
        with self._lock:
            row = self._connection.execute(
                "SELECT requests_count FROM api_usage_stats WHERE date = ?", (date_str,)
            ).fetchone()
            return row[0] if row else 0

    def update_api_usage(self, date_str: str, count: int):
        """更新或插入指定日期的 API 請求計數。"""
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO api_usage_stats (date, requests_count) VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET requests_count = ?
                """,
                (date_str, count, count),
            )
            self._connection.commit()

    def close_connection(self):
        """關閉數據庫連接。在應用程序關閉時調用。"""
        # 現在由 DI 容器管理連接的生命週期，這個方法可以移除或留空
        logger.info("Connection lifecycle managed by DI container. `close_connection` is a no-op.")
        pass
