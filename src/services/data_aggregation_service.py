"""
Data Aggregation Service

Handles aggregation of hourly data to daily data with comprehensive logging.
This service bridges the gap between hourly GSC data collection and daily reporting.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.services.database import Database
from src.utils.rich_console import console


class DataAggregationService:
    """
    Service for aggregating hourly GSC data into daily summaries.

    This service provides functionality to:
    - Aggregate hourly rankings data to daily summaries
    - Handle data validation and consistency checks
    - Provide detailed logging of aggregation processes
    - Support both single-day and date-range aggregation
    """

    def __init__(self, database: Database):
        self.database = database
        self.logger = logging.getLogger(__name__)

    def aggregate_hourly_to_daily(
        self, site_id: int, target_date: str, force_overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Aggregate hourly data for a specific site and date to daily summary.

        Args:
            site_id: Site ID to aggregate data for
            target_date: Date to aggregate (YYYY-MM-DD format)
            force_overwrite: Whether to overwrite existing daily data

        Returns:
            Dict containing aggregation results and statistics
        """
        start_time = datetime.now()

        self.logger.info(
            f"Starting hourly to daily aggregation for site {site_id}, date {target_date}"
        )
        console.print(f"🔄 Aggregating hourly data to daily for site {site_id}, date {target_date}")

        try:
            # Check if daily data already exists
            existing_daily_data = self._check_existing_daily_data(site_id, target_date)
            if existing_daily_data and not force_overwrite:
                self.logger.info(
                    f"Daily data already exists for site {site_id}, date {target_date}. Skipping."
                )
                return {
                    "status": "skipped",
                    "reason": "daily_data_exists",
                    "existing_records": existing_daily_data,
                }

            # Get hourly data for aggregation
            hourly_data = self._get_hourly_data_for_date(site_id, target_date)
            if not hourly_data:
                self.logger.warning(f"No hourly data found for site {site_id}, date {target_date}")
                return {"status": "no_data", "reason": "no_hourly_data_found"}

            self.logger.info(f"Found {len(hourly_data)} hourly records to aggregate")
            console.print(f"📊 Processing {len(hourly_data)} hourly records")

            # Perform aggregation
            daily_summaries = self._aggregate_data(hourly_data, target_date)

            # Insert aggregated data
            if force_overwrite and existing_daily_data:
                self._delete_existing_daily_data(site_id, target_date)

            inserted_count = self._insert_daily_summaries(site_id, daily_summaries)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "status": "success",
                "site_id": site_id,
                "target_date": target_date,
                "hourly_records_processed": len(hourly_data),
                "daily_records_created": inserted_count,
                "duration_seconds": duration,
                "aggregation_summary": self._generate_aggregation_summary(daily_summaries),
            }

            self.logger.info(
                f"Successfully aggregated {len(hourly_data)} hourly records to {inserted_count} daily records in {duration:.2f}s"
            )
            console.print(
                f"✅ Aggregation complete: {inserted_count} daily records created in {duration:.2f}s"
            )

            return result

        except Exception as e:
            self.logger.error(
                f"Error during aggregation for site {site_id}, date {target_date}: {str(e)}"
            )
            console.print(f"❌ Aggregation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "site_id": site_id,
                "target_date": target_date,
            }

    def aggregate_date_range(
        self, site_id: int, start_date: str, end_date: str, force_overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Aggregate hourly data for a date range.

        Args:
            site_id: Site ID to aggregate data for
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            force_overwrite: Whether to overwrite existing daily data

        Returns:
            Dict containing aggregation results for all dates
        """
        self.logger.info(
            f"Starting date range aggregation for site {site_id}: {start_date} to {end_date}"
        )
        console.print(f"🔄 Aggregating date range for site {site_id}: {start_date} to {end_date}")

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        results = []
        current_date = start_dt

        while current_date <= end_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            result = self.aggregate_hourly_to_daily(site_id, date_str, force_overwrite)
            results.append(result)
            current_date += timedelta(days=1)

        # Generate summary
        summary = self._generate_range_summary(results)

        self.logger.info(
            f"Date range aggregation complete: {summary['successful_days']} successful, {summary['failed_days']} failed"
        )
        console.print(f"✅ Range aggregation complete: {summary['successful_days']} days processed")

        return {"status": "completed", "summary": summary, "detailed_results": results}

    def _check_existing_daily_data(self, site_id: int, target_date: str) -> int:
        """Check if daily data already exists for the given site and date."""
        query = """
        SELECT COUNT(*) as count
        FROM gsc_performance_data
        WHERE site_id = ? AND date = ?
        """
        with self.database._lock:
            result = self.database._connection.execute(query, (site_id, target_date)).fetchone()
        return result[0] if result else 0

    def _get_hourly_data_for_date(self, site_id: int, target_date: str) -> List[Dict]:
        """Retrieve hourly data for a specific site and date."""
        query = """
        SELECT
            site_id,
            date,
            hour,
            query,
            page,
            position,
            clicks,
            impressions,
            ctr,
            country,
            device
        FROM hourly_rankings
        WHERE site_id = ? AND date = ?
        ORDER BY query, page, hour
        """
        with self.database._lock:
            rows = self.database._connection.execute(query, (site_id, target_date)).fetchall()
        return [dict(row) for row in rows]

    def _aggregate_data(self, hourly_data: List[Dict], target_date: str) -> List[Dict]:
        """
        Aggregate hourly data into daily summaries.

        Groups by (query, page, device, country) and calculates:
        - Total clicks (sum)
        - Total impressions (sum)
        - Average CTR (weighted by impressions)
        - Average position (weighted by impressions)
        """
        aggregation_groups = {}

        for record in hourly_data:
            # Create grouping key
            key = (
                record["query"],
                record["page"] or "",
                record["device"] or "ALL",
                record["country"] or "TWN",
            )

            if key not in aggregation_groups:
                aggregation_groups[key] = {
                    "query": record["query"],
                    "page": record["page"] or "",
                    "device": record["device"] or "ALL",
                    "country": record["country"] or "TWN",
                    "total_clicks": 0,
                    "total_impressions": 0,
                    "total_ctr_weighted": 0.0,
                    "total_position_weighted": 0.0,
                    "hour_count": 0,
                }

            group = aggregation_groups[key]
            clicks = record["clicks"] or 0
            impressions = record["impressions"] or 0
            ctr = record["ctr"] or 0.0
            position = record["position"] or 0.0

            group["total_clicks"] += clicks
            group["total_impressions"] += impressions

            # Weight CTR and position by impressions for more accurate daily averages
            if impressions > 0:
                group["total_ctr_weighted"] += ctr * impressions
                group["total_position_weighted"] += position * impressions

            group["hour_count"] += 1

        # Calculate final daily metrics
        daily_summaries = []
        for key, group in aggregation_groups.items():
            total_impressions = group["total_impressions"]

            # Calculate weighted averages
            avg_ctr = (
                (group["total_ctr_weighted"] / total_impressions) if total_impressions > 0 else 0.0
            )
            avg_position = (
                (group["total_position_weighted"] / total_impressions)
                if total_impressions > 0
                else 0.0
            )

            daily_summary = {
                "date": target_date,
                "query": group["query"],
                "page": group["page"],
                "device": group["device"],
                "search_type": "web",  # Default for GSC data
                "clicks": group["total_clicks"],
                "impressions": total_impressions,
                "ctr": round(avg_ctr, 6),
                "position": round(avg_position, 2),
                "hour_count": group["hour_count"],  # For logging purposes
            }

            daily_summaries.append(daily_summary)

        self.logger.info(
            f"Aggregated {len(hourly_data)} hourly records into {len(daily_summaries)} daily summaries"
        )

        return daily_summaries

    def _delete_existing_daily_data(self, site_id: int, target_date: str):
        """Delete existing daily data for overwrite."""
        query = """
        DELETE FROM gsc_performance_data
        WHERE site_id = ? AND date = ?
        """
        with self.database._lock:
            self.database._connection.execute(query, (site_id, target_date))
            self.database._connection.commit()
        self.logger.info(f"Deleted existing daily data for site {site_id}, date {target_date}")

    def _insert_daily_summaries(self, site_id: int, daily_summaries: List[Dict]) -> int:
        """Insert daily summaries into the database."""
        if not daily_summaries:
            return 0

        query = """
        INSERT OR REPLACE INTO gsc_performance_data
        (site_id, date, page, query, device, search_type, clicks, impressions, ctr, position)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        insert_data = [
            (
                site_id,
                summary["date"],
                summary["page"],
                summary["query"],
                summary["device"],
                summary["search_type"],
                summary["clicks"],
                summary["impressions"],
                summary["ctr"],
                summary["position"],
            )
            for summary in daily_summaries
        ]

        with self.database._lock:
            self.database._connection.executemany(query, insert_data)
            self.database._connection.commit()
        self.logger.info(f"Inserted {len(daily_summaries)} daily summary records")

        return len(daily_summaries)

    def _generate_aggregation_summary(self, daily_summaries: List[Dict]) -> Dict:
        """Generate summary statistics for aggregation results."""
        if not daily_summaries:
            return {}

        total_clicks = sum(s["clicks"] for s in daily_summaries)
        total_impressions = sum(s["impressions"] for s in daily_summaries)
        unique_queries = len(set(s["query"] for s in daily_summaries))
        unique_pages = len(set(s["page"] for s in daily_summaries))

        return {
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "unique_queries": unique_queries,
            "unique_pages": unique_pages,
            "daily_records": len(daily_summaries),
        }

    def _generate_range_summary(self, results: List[Dict]) -> Dict:
        """Generate summary for date range aggregation."""
        successful = [r for r in results if r.get("status") == "success"]
        skipped = [r for r in results if r.get("status") == "skipped"]
        failed = [r for r in results if r.get("status") == "error"]
        no_data = [r for r in results if r.get("status") == "no_data"]

        total_hourly_records = sum(r.get("hourly_records_processed", 0) for r in successful)
        total_daily_records = sum(r.get("daily_records_created", 0) for r in successful)

        return {
            "total_days": len(results),
            "successful_days": len(successful),
            "skipped_days": len(skipped),
            "failed_days": len(failed),
            "no_data_days": len(no_data),
            "total_hourly_records_processed": total_hourly_records,
            "total_daily_records_created": total_daily_records,
        }
