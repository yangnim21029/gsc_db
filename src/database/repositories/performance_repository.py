"""Performance data repository for GSC data operations."""

from datetime import date, timedelta
from typing import Any

from ...models import PerformanceData
from ..base import Repository
from ..utils import execute_batch_insert


class PerformanceRepository(Repository):
    """Repository for performance data operations."""

    async def insert_batch(self, data: list[PerformanceData], mode: str = "skip") -> dict[str, int]:
        """Insert performance data in batch."""
        if not data:
            return {"inserted": 0, "skipped": 0}

        columns = [
            "site_id",
            "date",
            "page",
            "query",
            "device",
            "search_type",
            "clicks",
            "impressions",
            "ctr",
            "position",
        ]

        records = [
            (
                record.site_id,
                record.date.isoformat(),
                record.page,
                record.query,
                record.device or "DESKTOP",
                record.search_type or "WEB",
                record.clicks,
                record.impressions,
                record.ctr,
                record.position,
            )
            for record in data
        ]

        async with self._lock:
            conn = self._ensure_connection()
            return await execute_batch_insert(conn, "gsc_performance_data", columns, records, mode)

    async def get_sync_coverage(self, site_id: int, days: int) -> dict[str, bool]:
        """Get sync coverage for a site over the specified days."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        query = """
            SELECT DISTINCT date
            FROM gsc_performance_data
            WHERE site_id = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC
        """
        params = (site_id, start_date.isoformat(), end_date.isoformat())
        cursor = await self._execute_query(query, params)
        synced_dates = {row[0] for row in await cursor.fetchall()}

        # Create coverage map
        coverage = {}
        current_date = start_date
        while current_date <= end_date:
            coverage[current_date.isoformat()] = current_date.isoformat() in synced_dates
            current_date += timedelta(days=1)

        return coverage

    async def get_total_records(self, site_id: int) -> int:
        """Get total number of records for a site."""
        cursor = await self._execute_query(
            "SELECT COUNT(*) FROM gsc_performance_data WHERE site_id = ?", (site_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0

    async def get_keyword_trends(self, site_id: int, days: int = 30) -> list[dict[str, Any]]:
        """Get keyword trends for a site."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        query = """
            SELECT
                query,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(position) as avg_position,
                ROUND(SUM(CAST(clicks AS REAL)) / NULLIF(SUM(impressions), 0), 4) as avg_ctr,
                COUNT(DISTINCT date) as days_appeared
            FROM gsc_performance_data
            WHERE site_id = ? AND date BETWEEN ? AND ?
            GROUP BY query
            HAVING total_clicks > 0
            ORDER BY total_clicks DESC
            LIMIT 100
        """

        async with self._lock:
            conn = self._ensure_connection()
            cursor = await conn.execute(
                query, (site_id, start_date.isoformat(), end_date.isoformat())
            )

        results = []
        async for row in cursor:
            results.append(
                {
                    "query": row[0],
                    "total_clicks": row[1],
                    "total_impressions": row[2],
                    "avg_position": row[3],
                    "avg_ctr": row[4],
                    "days_appeared": row[5],
                }
            )

        return results
