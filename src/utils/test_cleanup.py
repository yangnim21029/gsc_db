"""Test data cleanup utility."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from ..config import get_settings


class TestDataCleaner:
    """Clean up test data from database."""

    def __init__(self, db_path: Path | None = None):
        """Initialize cleaner with database path."""
        if db_path is None:
            settings = get_settings()
            db_path = settings.database_path
        self.db_path = db_path

    def clean_test_site_data(self, site_id: int = 3, days_to_keep: int = 0) -> dict[str, int]:
        """
        Clean test data for a specific site.

        Args:
            site_id: Site ID to clean (default: 3 for test site)
            days_to_keep: Number of recent days to keep (0 = delete all)

        Returns:
            Dictionary with counts of deleted records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Calculate cutoff date
            if days_to_keep > 0:
                cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).date()
                date_condition = f"AND date < '{cutoff_date}'"
            else:
                date_condition = ""

            # Count records before deletion
            cursor.execute(
                f"SELECT COUNT(*) FROM gsc_performance_data WHERE site_id = ? {date_condition}",
                (site_id,),
            )
            performance_count = cursor.fetchone()[0]

            cursor.execute(
                f"SELECT COUNT(*) FROM hourly_rankings WHERE site_id = ? {date_condition}",
                (site_id,),
            )
            hourly_count = cursor.fetchone()[0]

            # Delete records
            cursor.execute(
                f"DELETE FROM gsc_performance_data WHERE site_id = ? {date_condition}", (site_id,)
            )

            cursor.execute(
                f"DELETE FROM hourly_rankings WHERE site_id = ? {date_condition}", (site_id,)
            )

            conn.commit()

            return {
                "performance_data": performance_count,
                "hourly_rankings": hourly_count,
                "total": performance_count + hourly_count,
            }

        finally:
            conn.close()

    def clean_future_data(self) -> dict[str, int]:
        """
        Clean any data with future dates (likely test data).

        Returns:
            Dictionary with counts of deleted records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            today = datetime.now().date()

            # Count and delete future data
            cursor.execute("SELECT COUNT(*) FROM gsc_performance_data WHERE date > ?", (today,))
            performance_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM hourly_rankings WHERE date > ?", (today,))
            hourly_count = cursor.fetchone()[0]

            # Delete future data
            cursor.execute("DELETE FROM gsc_performance_data WHERE date > ?", (today,))

            cursor.execute("DELETE FROM hourly_rankings WHERE date > ?", (today,))

            conn.commit()

            return {
                "performance_data": performance_count,
                "hourly_rankings": hourly_count,
                "total": performance_count + hourly_count,
            }

        finally:
            conn.close()

    def clean_recent_days_data(self, site_id: int, days: int) -> dict[str, int]:
        """
        Clean data from recent N days for a specific site.
        Useful for cleaning up after tests that insert recent data.

        Args:
            site_id: Site ID to clean
            days: Number of recent days to clean

        Returns:
            Dictionary with counts of deleted records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            start_date = (datetime.now() - timedelta(days=days)).date()

            # Count and delete recent data
            cursor.execute(
                "SELECT COUNT(*) FROM gsc_performance_data WHERE site_id = ? AND date >= ?",
                (site_id, start_date),
            )
            performance_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM hourly_rankings WHERE site_id = ? AND date >= ?",
                (site_id, start_date),
            )
            hourly_count = cursor.fetchone()[0]

            # Delete recent data
            cursor.execute(
                "DELETE FROM gsc_performance_data WHERE site_id = ? AND date >= ?",
                (site_id, start_date),
            )

            cursor.execute(
                "DELETE FROM hourly_rankings WHERE site_id = ? AND date >= ?", (site_id, start_date)
            )

            conn.commit()

            return {
                "performance_data": performance_count,
                "hourly_rankings": hourly_count,
                "total": performance_count + hourly_count,
            }

        finally:
            conn.close()


def cleanup_after_test(site_id: int = 3, recent_days: int = 7) -> None:
    """
    Convenience function to clean up after tests.

    Args:
        site_id: Site ID to clean (default: 3 for test site)
        recent_days: Clean data from last N days
    """
    cleaner = TestDataCleaner()

    # Clean recent test data
    result = cleaner.clean_recent_days_data(site_id, recent_days)

    if result["total"] > 0:
        print(f"🧹 Cleaned {result['total']} test records:")
        print(f"   - Performance data: {result['performance_data']}")
        print(f"   - Hourly rankings: {result['hourly_rankings']}")
    else:
        print("✅ No test data to clean")

    # Also clean any future data
    future_result = cleaner.clean_future_data()
    if future_result["total"] > 0:
        print(f"🧹 Cleaned {future_result['total']} future-dated records")
