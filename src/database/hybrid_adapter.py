"""Adapter to maintain backward compatibility with HybridDataStore."""

from datetime import date
from pathlib import Path
from typing import Any

from ..models import PerformanceData, Site
from .datastore import DataStore
from .utils import ensure_connection


class HybridDataStore(DataStore):
    """Backward compatible adapter for the modern DataStore."""

    def __init__(self, sqlite_path: Path | None = None, enable_duckdb: bool = True):
        """Initialize with backward compatible parameters."""
        super().__init__(db_path=sqlite_path, enable_duckdb=enable_duckdb)
        self.sqlite_path = self.db_path

    # Site management - delegate to repository
    async def get_sites(self, active_only: bool = True) -> list[Site]:
        """Get all sites."""
        return await self.sites.get_all(active_only)

    async def get_site_by_id(self, site_id: int) -> Site | None:
        """Get site by ID."""
        return await self.sites.get_by_id(site_id)

    async def add_site(self, domain: str, name: str, category: str | None = None) -> int:
        """Add a new site."""
        return await self.sites.create(domain, name, category)

    # Performance data - delegate to repository
    async def insert_performance_data(
        self, data: list[PerformanceData], mode: str = "skip"
    ) -> dict[str, int]:
        """Insert performance data."""
        return await self.performance.insert_batch(data, mode)

    async def get_sync_coverage(self, site_id: int, days: int) -> dict[str, bool]:
        """Get sync coverage for a site."""
        return await self.performance.get_sync_coverage(site_id, days)

    async def get_total_records(self, site_id: int) -> int:
        """Get total number of records for a site."""
        return await self.performance.get_total_records(site_id)

    async def get_keyword_trends(self, site_id: int, days: int = 30) -> list[dict[str, Any]]:
        """Get keyword trends."""
        return await self.performance.get_keyword_trends(site_id, days)

    # Hourly data - delegate to repository
    async def insert_hourly_data(
        self, records: list[dict[str, Any]], sync_mode: str = "skip"
    ) -> dict[str, int]:
        """Insert hourly rankings data."""
        return await self.hourly.insert_batch(records, sync_mode)

    async def delete_hourly_data_for_date(self, site_id: int, date: date) -> None:
        """Delete hourly data for a specific date."""
        await self.hourly.delete_for_date(site_id, date)

    async def get_hourly_coverage(self, site_id: int, days: int) -> dict[str, dict[int, bool]]:
        """Get hourly sync coverage."""
        return await self.hourly.get_hourly_coverage(site_id, days)

    # Analytics - delegate to service
    async def analyze_performance_trends(self, site_id: int, days: int) -> Any:
        """Analyze performance trends."""
        if not self.analytics:
            raise RuntimeError("Analytics service not initialized")
        return await self.analytics.analyze_trends(site_id, days)

    async def get_ranking_data(
        self,
        site_id: int,
        date_range: tuple[str, str],
        queries: list[str] | None = None,
        pages: list[str] | None = None,
        group_by: list[str] | None = None,
        limit: int = 1000,
        exact_match: bool = True,
    ) -> dict[str, Any]:
        """Get ranking data with filtering."""
        if not self.analytics:
            raise RuntimeError("Analytics service not initialized")
        return await self.analytics.get_ranking_data(
            site_id, date_range, queries, pages, group_by, limit, exact_match
        )

    async def export_to_parquet(self, site_id: int, output_path: Path) -> None:
        """Export to Parquet format."""
        if not self.analytics:
            raise RuntimeError("Analytics service not initialized")
        await self.analytics.export_to_parquet(site_id, output_path)

    # Diagnostics
    async def test_connection(self) -> bool:
        """Test database connection."""
        if not self._sqlite_conn:
            return False
        try:
            await self._sqlite_conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    @ensure_connection
    async def check_locks(self) -> dict[str, Any]:
        """Check database locks and settings."""
        async with self._lock:
            # Get pragma settings
            pragmas = {}
            for pragma in ["journal_mode", "synchronous", "cache_size", "temp_store"]:
                cursor = await self._sqlite_conn.execute(f"PRAGMA {pragma}")
                result = await cursor.fetchone()
                pragmas[pragma] = result[0] if result else None

        return {
            "pragmas": pragmas,
            "recommendations": [
                "journal_mode should be WAL for better concurrency",
                "synchronous can be NORMAL for better performance",
                "cache_size should be >= 10000 for better performance",
            ],
        }
