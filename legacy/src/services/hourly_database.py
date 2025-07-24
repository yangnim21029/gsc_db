"""
每小時數據同步服務
- 負責協調 GSC 客戶端和數據庫服務，以同步每小時數據。
- 服務是無狀態的，可以重複使用於不同的站點。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from .database import Database, SyncMode
from .gsc_client import GSCClient

logger = logging.getLogger(__name__)


class HourlyDatabase:
    """處理每小時數據的同步協調"""

    def __init__(self, db: Database, gsc_client: GSCClient):
        """
        初始化服務。
        :param db: 已初始化的 Database 服務實例。
        :param gsc_client: 已初始化的 GSCClient 服務實例。
        """
        self.db = db
        self.gsc_client = gsc_client

    def sync_hourly_data(
        self,
        site_url: str,
        start_date: str,
        end_date: str,
        sync_mode: SyncMode = SyncMode.SKIP,
    ) -> Dict[str, int]:
        """
        同步指定站點和時間範圍內的每小時數據。
        這是一個高階方法，協調 GSC 客戶端和數據庫保存。
        """
        total_inserted_count = 0
        logger.info(
            f"開始為站點 {site_url} 同步 {start_date} 到 {end_date} 的每小時數據，"
            f"模式: {sync_mode.value}。"
        )

        try:
            # 1. 從主數據庫獲取 site_id
            site_row = self.db.get_site_by_domain(site_url)
            if not site_row:
                logger.error(f"在 'sites' 表中找不到站點 {site_url}，無法進行每小時同步。")
                return {"inserted": 0}
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

            if sync_mode == SyncMode.SKIP:
                existing_dates = self.db.get_existing_hourly_dates(site_id, start_date, end_date)
                dates_to_sync = sorted(list(all_possible_dates - existing_dates))

            logger.info(
                f"計劃同步 {len(all_possible_dates)} 天 ({start_date} 到 {end_date}). "
                f"模式: {sync_mode.value}. "
                f"將要同步 {len(dates_to_sync)} 天."
            )

            if not dates_to_sync:
                logger.info(f"站點 {site_url} 在指定期間無需同步。")
                return {"inserted": 0}

            # ================= 執行 (Execution) 階段 =================
            for date_str in dates_to_sync:
                try:
                    if sync_mode == SyncMode.OVERWRITE:
                        logger.info(
                            f"覆蓋模式: 正在刪除站點 {site_url} 日期 {date_str} 的舊數據..."
                        )
                        self.db.delete_hourly_data_for_date(site_id, date_str)

                    data_stream = self.gsc_client.stream_hourly_data(
                        site_url=site_url, start_date=date_str, end_date=date_str
                    )

                    chunk: List[Dict[str, Any]] = []
                    chunk_size = 200

                    for item in data_stream:
                        item["site_id"] = site_id
                        chunk.append(item)
                        if len(chunk) >= chunk_size:
                            inserted_count = self.db.save_hourly_ranking_data(chunk)
                            total_inserted_count += inserted_count
                            chunk = []

                    if chunk:
                        inserted_count = self.db.save_hourly_ranking_data(chunk)
                        total_inserted_count += inserted_count

                    logger.info(f"站點 {site_url} 日期 {date_str} 每小時數據同步完成")

                except Exception as e:
                    logger.error(f"同步站點 {site_url} 日期 {date_str} 的每小時數據時發生錯誤: {e}")
                    continue

            logger.info(
                f"站點 {site_url} 的每小時數據同步完成，共新增 {total_inserted_count} 條記錄。"
            )
            return {"inserted": total_inserted_count}

        except AttributeError as e:
            logger.error(
                "GSCClient 中缺少 'stream_hourly_data' 方法，無法執行每小時同步。請實現此方法。"
            )
            logger.debug(e)
            return {"inserted": 0}
        except Exception as e:
            logger.error(f"同步站點 {site_url} 的每小時數據時發生錯誤: {e}")
            return {"inserted": 0}
