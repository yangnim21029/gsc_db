"""Hourly rankings repository for hourly GSC data."""

import sqlite3
from datetime import date
from typing import Any

from ..base import Repository


class HourlyRepository(Repository):
    """Repository for hourly rankings data operations."""

    async def insert_batch(
        self, records: list[dict[str, Any]], sync_mode: str = "skip"
    ) -> dict[str, int]:
        """Insert hourly data records in batch."""
        if not records:
            return {"inserted": 0, "skipped": 0}

        stats = {"inserted": 0, "skipped": 0}

        async with self._lock:
            conn = self._ensure_connection()
            async with conn.transaction():
                for record in records:
                    if sync_mode == "skip":
                        try:
                            await conn.execute(
                                """
                                INSERT INTO hourly_rankings
                                (site_id, date, hour, query, page, position, clicks, impressions, ctr)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    record["site_id"],
                                    record["date"],
                                    record["hour"],
                                    record["query"],
                                    record["page"],
                                    record["position"],
                                    record["clicks"],
                                    record["impressions"],
                                    record["ctr"],
                                ),
                            )
                            stats["inserted"] += 1
                        except sqlite3.IntegrityError:
                            stats["skipped"] += 1
                    else:  # overwrite mode
                        await conn.execute(
                            """
                            INSERT OR REPLACE INTO hourly_rankings
                            (site_id, date, hour, query, page, position, clicks, impressions, ctr)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                record["site_id"],
                                record["date"],
                                record["hour"],
                                record["query"],
                                record["page"],
                                record["position"],
                                record["clicks"],
                                record["impressions"],
                                record["ctr"],
                            ),
                        )
                        stats["inserted"] += 1

        return stats

    async def delete_for_date(self, site_id: int, target_date: date) -> None:
        """Delete all hourly data for a specific site and date."""
        async with self._lock:
            conn = self._ensure_connection()
            await conn.execute(
                "DELETE FROM hourly_rankings WHERE site_id = ? AND date = ?",
                (site_id, target_date.isoformat()),
            )
            await conn.commit()

    async def get_hourly_coverage(self, site_id: int, days: int) -> dict[str, dict[int, bool]]:
        """Get hourly sync coverage for a site."""
        from datetime import datetime, timedelta

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        async with self._lock:
            conn = self._ensure_connection()
            cursor = await conn.execute(
                """
                SELECT DISTINCT date, hour
                FROM hourly_rankings
                WHERE site_id = ? AND date BETWEEN ? AND ?
                ORDER BY date DESC, hour DESC
                """,
                (site_id, start_date.isoformat(), end_date.isoformat()),
            )

        # Build coverage map
        synced_hours = {}
        async for row in cursor:
            date_str = row[0]
            hour = row[1]
            if date_str not in synced_hours:
                synced_hours[date_str] = set()
            synced_hours[date_str].add(hour)

        # Create full coverage map
        coverage = {}
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            coverage[date_str] = {
                hour: hour in synced_hours.get(date_str, set()) for hour in range(24)
            }
            current_date += timedelta(days=1)

        return coverage
