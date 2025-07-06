"""
每小時數據處理模塊
Google Search Console 2025年4月推出的每小時數據功能
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class HourlyDataHandler:
    """處理每小時數據的專用類"""

    def __init__(self, service, database):
        self.service = service
        self.database = database

    def get_search_analytics_hourly(
        self,
        site_url: str,
        start_date: str,
        end_date: str,
        dimensions: Optional[List[str]] = None,
        additional_dimensions: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """獲取每小時搜索分析數據"""
        if self.service is None:
            raise Exception("GSC service not initialized")

        if dimensions is None:
            dimensions = ["HOUR"]

        try:
            if "HOUR" not in dimensions:
                dimensions = ["HOUR"] + dimensions
            if additional_dimensions:
                dimensions.extend(additional_dimensions)

            request = {
                "startDate": start_date,
                "endDate": end_date,
                "dataState": "HOURLY_ALL",
                "dimensions": dimensions,
                "rowLimit": 1000,
            }

            response = (
                self.service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            )

            rows = response.get("rows", [])
            logger.info(f"Retrieved {len(rows)} hourly data rows for {site_url}")
            # 確保返回正確的類型
            return list(rows) if rows else []

        except HttpError as e:
            logger.error(f"Failed to get hourly analytics for {site_url}: {e}")
            return []

    def get_hourly_data_batch(
        self,
        site_url: str,
        start_date: str,
        end_date: str,
        additional_dimensions: Optional[List[str]] = None,
        max_total_rows: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """批次獲取每小時數據"""
        if self.service is None:
            raise Exception("GSC service not initialized")

        all_rows: List[Dict[str, Any]] = []
        max_rows_per_request = 25000
        start_row = 0

        try:
            dimensions = ["HOUR"]
            if additional_dimensions:
                dimensions.extend(additional_dimensions)

            while max_total_rows is None or len(all_rows) < max_total_rows:
                # 計算這次請求的行數限制
                if max_total_rows is None:
                    row_limit = max_rows_per_request
                else:
                    row_limit = min(max_rows_per_request, max_total_rows - len(all_rows))

                request = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "dataState": "HOURLY_ALL",
                    "dimensions": dimensions,
                    "rowLimit": row_limit,
                    "startRow": start_row,
                }

                response = (
                    self.service.searchanalytics().query(siteUrl=site_url, body=request).execute()
                )

                rows = response.get("rows", [])
                if not rows:
                    break

                all_rows.extend(rows)
                start_row += len(rows)

                # 修復：不要因為返回行數少就停止！GSC API 可能有隱藏限制
                if len(rows) == 0:
                    logger.info("No more hourly rows returned, stopping")
                    break

                if len(rows) < max_rows_per_request and len(rows) < 1000:
                    logger.info(
                        f"Received only {len(rows)} hourly rows (< 1000), likely end of data"
                    )
                    break

                logger.info(f"Retrieved {len(all_rows)} hourly rows so far for {site_url}")

        except HttpError as e:
            logger.error(f"Failed to get hourly analytics batch for {site_url}: {e}")
            return []

        logger.info(f"Total retrieved {len(all_rows)} hourly rows for {site_url}")
        return all_rows

    def sync_hourly_data(self, site_url: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """同步每小時數據到數據庫"""
        try:
            # 獲取或創建站點記錄
            site = self.database.get_site_by_domain(site_url)
            if not site:
                site_id = self.database.add_site(site_url, site_url.replace("sc-domain:", ""))
                site = {"id": site_id, "domain": site_url}

            # 獲取每小時數據
            hourly_data = self.get_hourly_data_batch(
                site_url, start_date, end_date, additional_dimensions=["query", "page"]
            )

            # 處理每小時數據
            hourly_rankings = []
            processed_items = set()
            skipped_rows = 0

            logger.info(f"Processing {len(hourly_data)} hourly data rows")

            for row in hourly_data:
                keys = row.get("keys", [])
                if len(keys) < 1:
                    skipped_rows += 1
                    continue

                # 解析時間戳 (ISO 8601 格式)
                hour_timestamp = keys[0]
                query = keys[1] if len(keys) > 1 else ""
                page = keys[2] if len(keys) > 2 else ""

                # 提取日期和小時
                try:
                    dt = datetime.fromisoformat(hour_timestamp.replace("Z", "+00:00"))
                    date_str = dt.strftime("%Y-%m-%d")
                    hour = dt.hour
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp {hour_timestamp}: {e}")
                    skipped_rows += 1
                    continue

                # 獲取或創建關鍵字記錄
                keyword_id = None
                if query:
                    keyword_id = self.database.add_keyword(query, site["id"])

                # 構建每小時排名記錄
                ranking = {
                    "site_id": site["id"],
                    "keyword_id": keyword_id,
                    "date": date_str,
                    "hour": hour,
                    "hour_timestamp": hour_timestamp,
                    "query": query,
                    "position": row.get("position", 0),
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": row.get("ctr", 0),
                    "page": page,
                }

                hourly_rankings.append(ranking)
                processed_items.add(f"{date_str}_{hour}_{query}")

            # 保存到數據庫
            logger.info(
                f"About to save {len(hourly_rankings)} hourly rankings (skipped {skipped_rows} rows)"
            )
            saved_count = self.database.save_hourly_ranking_data(hourly_rankings)

            logger.info(
                f"Synced {saved_count} hourly records for {site_url} from {start_date} to {end_date}"
            )

            return {
                "site": site_url,
                "start_date": start_date,
                "end_date": end_date,
                "hourly_count": saved_count,
                "unique_items": len(processed_items),
                "type": "hourly",
            }

        except Exception as e:
            logger.error(f"Failed to sync hourly data for {site_url}: {e}")
            raise
