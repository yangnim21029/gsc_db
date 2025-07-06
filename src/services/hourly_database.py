"""
每小時數據數據庫操作模塊
處理 2025年新增的每小時數據存儲和查詢
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..services.database import SyncMode

logger = logging.getLogger(__name__)


class HourlyDatabase:
    """處理每小時數據的數據庫操作"""

    def __init__(self, db_connection_func, site_url: str):
        self.get_connection = db_connection_func
        self.site_url = site_url

    def get_existing_dates(self, site_id: int, start_date: str, end_date: str) -> set[str]:
        """一次性獲取指定範圍內已存在數據的日期集合。"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT date
                FROM hourly_rankings
                WHERE site_id = ? AND date BETWEEN ? AND ?
                """,
                (site_id, start_date, end_date),
            )
            return {row["date"] for row in cursor.fetchall()}

    def _delete_data_for_date(self, site_id: int, date: str):
        """為特定日期刪除每小時數據"""
        with self.get_connection() as conn:
            try:
                conn.execute(
                    "DELETE FROM hourly_rankings WHERE site_id = ? AND date = ?",
                    (site_id, date),
                )
                conn.commit()
            except Exception as e:
                logger.error(f"刪除站點 {self.site_url} 日期 {date} 的每小時數據時失敗: {e}")
                conn.rollback()
                raise

    def sync_data(
        self, client, start_date: str, end_date: str, mode: SyncMode = SyncMode.SKIP
    ) -> int:
        """
        同步指定時間範圍內的每小時數據。
        這是一個高階方法，協調 GSC 客戶端和數據庫保存。
        """
        total_inserted_count = 0
        logger.info(
            f"開始為站點 {self.site_url} 同步 {start_date} 到 {end_date} 的每小時數據，模式: {mode.value}。"
        )

        try:
            # 1. 從主數據庫獲取 site_id
            with self.get_connection() as conn:
                site_row = conn.execute(
                    "SELECT id FROM sites WHERE domain = ?", (self.site_url,)
                ).fetchone()
                if not site_row:
                    logger.error(f"在 'sites' 表中找不到站點 {self.site_url}，無法進行每小時同步。")
                    return 0
                site_id = site_row["id"]

            # ================= 計劃 (Planning) 階段 =================
            all_possible_dates = set()
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            current_dt = start_dt
            while current_dt <= end_dt:
                all_possible_dates.add(current_dt.strftime("%Y-%m-%d"))
                current_dt += timedelta(days=1)

            dates_to_sync = sorted(list(all_possible_dates))

            if mode == SyncMode.SKIP:
                existing_dates = self.get_existing_dates(site_id, start_date, end_date)
                dates_to_sync = sorted(list(all_possible_dates - existing_dates))

            logger.info(
                f"計劃同步 {len(all_possible_dates)} 天 ({start_date} 到 {end_date}). "
                f"模式: {mode.value}. "
                f"將要同步 {len(dates_to_sync)} 天."
            )

            if not dates_to_sync:
                logger.info(f"站點 {self.site_url} 在指定期間無需同步。")
                return 0

            # ================= 執行 (Execution) 階段 =================
            for date_str in dates_to_sync:
                try:
                    if mode == SyncMode.OVERWRITE:
                        logger.info(
                            f"覆蓋模式: 正在刪除站點 {self.site_url} 日期 {date_str} 的舊數據..."
                        )
                        self._delete_data_for_date(site_id, date_str)

                    data_stream = client.stream_hourly_data(
                        site_url=self.site_url, start_date=date_str, end_date=date_str
                    )

                    chunk: List[Dict[str, Any]] = []
                    chunk_size = 200

                    for item in data_stream:
                        item["site_id"] = site_id
                        chunk.append(item)
                        if len(chunk) >= chunk_size:
                            inserted_count = self.save_hourly_ranking_data(chunk)
                            total_inserted_count += inserted_count
                            chunk = []

                    if chunk:
                        inserted_count = self.save_hourly_ranking_data(chunk)
                        total_inserted_count += inserted_count

                    logger.info(f"站點 {self.site_url} 日期 {date_str} 每小時數據同步完成")

                except Exception as e:
                    logger.error(
                        f"同步站點 {self.site_url} 日期 {date_str} 的每小時數據時發生錯誤: {e}"
                    )
                    continue

            logger.info(
                f"站點 {self.site_url} 的每小時數據同步完成，共新增 {total_inserted_count} 條記錄。"
            )
            return total_inserted_count

        except AttributeError as e:
            logger.error(
                "GSCClient 中缺少 'stream_hourly_data' 方法，無法執行每小時同步。請實現此方法。"
            )
            logger.debug(e)
            return 0
        except Exception as e:
            logger.error(f"同步站點 {self.site_url} 的每小時數據時發生錯誤: {e}")
            return 0

    # Table creation is handled by Database.init_db() to avoid duplication

    def save_hourly_ranking_data(self, hourly_rankings: List[Dict[str, Any]]) -> int:
        """保存每小時排名數據 (使用批量操作優化)"""
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

        with self.get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO hourly_rankings
                    (site_id, keyword_id, date, hour, hour_timestamp, query, position, clicks, impressions, ctr, page, country, device)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    data_to_insert,
                )
                conn.commit()
                saved_count = cursor.rowcount if cursor.rowcount != -1 else len(data_to_insert)
                logger.info(f"Saved {saved_count} hourly ranking records")
                return saved_count
            except Exception as e:
                logger.error(f"Failed to save hourly ranking data in batch: {e}")
                conn.rollback()
                return 0

    def get_hourly_rankings(
        self,
        site_id: Optional[int] = None,
        keyword_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        hour: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """獲取每小時排名數據"""
        with self.get_connection() as conn:
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

            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def get_hourly_summary(self, site_id: int, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """獲取每小時數據總結"""
        with self.get_connection() as conn:
            conditions = ["hr.site_id = ?"]
            params: List[Any] = [site_id]

            if date:
                conditions.append("hr.date = ?")
                params.append(date)
            else:
                conditions.append('hr.date >= date("now", "-3 days")')

            where_clause = " WHERE " + " AND ".join(conditions)

            query = f"""
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
            """

            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def get_hourly_coverage(self, site_id: int) -> Dict[str, Any]:
        """獲取每小時數據覆蓋情況"""
        with self.get_connection() as conn:
            # 檢查是否有每小時數據
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total_records,
                    MIN(date) as first_date,
                    MAX(date) as last_date,
                    COUNT(DISTINCT date) as unique_dates,
                    COUNT(DISTINCT hour) as unique_hours
                FROM hourly_rankings
                WHERE site_id = ?
            """,
                (site_id,),
            ).fetchone()

            result = dict(row) if row else {}

            # 獲取最近的數據點（按日期和小時分組）
            recent_data = conn.execute(
                """
                SELECT date, hour, COUNT(*) as records
                FROM hourly_rankings
                WHERE site_id = ?
                GROUP BY date, hour
                ORDER BY date DESC, hour DESC
                LIMIT 24
            """,
                (site_id,),
            ).fetchall()

            result["recent_data"] = [dict(r) for r in recent_data]

            return result
