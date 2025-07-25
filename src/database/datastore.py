"""Modern DataStore implementation with separated concerns."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import aiosqlite
import duckdb

from ..config import get_settings
from .base import TransactionManager
from .repositories import HourlyRepository, PerformanceRepository, SiteRepository
from .services import PerformanceAnalytics, StreamingService


class DataStore:
    """Modern data store with repository pattern and service layer."""

    def __init__(self, db_path: Path | None = None, enable_duckdb: bool = True):
        """Initialize data store with optional custom database path."""
        settings = get_settings()
        self.db_path = db_path or Path(settings.database_path)
        self.enable_duckdb = enable_duckdb

        # Connections
        self._sqlite_conn: aiosqlite.Connection | None = None
        self._duck_conn: duckdb.DuckDBPyConnection | None = None
        self._lock = asyncio.Lock()

        # Repositories
        self.sites = SiteRepository()
        self.performance = PerformanceRepository()
        self.hourly = HourlyRepository()

        # Services
        self.analytics: PerformanceAnalytics | None = None
        self.streaming: StreamingService | None = None

        # Transaction manager
        self._transaction_manager: TransactionManager | None = None

    async def initialize(self) -> None:
        """Initialize database connections and repositories."""
        async with self._lock:
            # Initialize SQLite
            self._sqlite_conn = await aiosqlite.connect(
                self.db_path,
                isolation_level=None,  # Autocommit mode
                detect_types=0,
            )

            # Enable WAL mode for better concurrency
            await self._sqlite_conn.execute("PRAGMA journal_mode=WAL")
            await self._sqlite_conn.execute("PRAGMA synchronous=NORMAL")
            await self._sqlite_conn.execute("PRAGMA cache_size=10000")
            await self._sqlite_conn.execute("PRAGMA temp_store=MEMORY")

            # Create tables
            await self._create_tables()

            # Apply performance optimizations
            await self._optimize_performance()

            # Initialize repositories with connection
            self.sites.set_connection(self._sqlite_conn, self._lock)
            self.performance.set_connection(self._sqlite_conn, self._lock)
            self.hourly.set_connection(self._sqlite_conn, self._lock)

            # Initialize DuckDB if enabled
            if self.enable_duckdb:
                self._duck_conn = duckdb.connect(":memory:")
                self._duck_conn.execute(f"""
                    ATTACH DATABASE '{self.db_path}' AS sqlite_db (TYPE SQLITE);
                """)

                # Initialize analytics service
                self.analytics = PerformanceAnalytics(self._duck_conn)

            # Initialize streaming service
            self.streaming = StreamingService(self.performance, self.analytics)

            # Initialize transaction manager
            self._transaction_manager = TransactionManager(self._sqlite_conn, self._lock)

    async def close(self) -> None:
        """Close all database connections."""
        async with self._lock:
            if self._sqlite_conn:
                await self._sqlite_conn.close()
                self._sqlite_conn = None

            if self._duck_conn:
                self._duck_conn.close()
                self._duck_conn = None

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Provide a database transaction context."""
        if not self._transaction_manager:
            raise RuntimeError("Database not initialized")
        async with self._transaction_manager.transaction() as conn:
            yield conn

    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        if not self._sqlite_conn:
            raise RuntimeError("Database not initialized")

        from .schema import DatabaseSchema

        # Execute all schema statements
        for statement in DatabaseSchema.get_all_create_statements():
            await self._sqlite_conn.execute(statement)

        await self._sqlite_conn.commit()

    async def _optimize_performance(self) -> None:
        """Apply performance optimizations to the database."""
        if not self._sqlite_conn:
            raise RuntimeError("Database not initialized")

        # Update statistics
        await self._sqlite_conn.execute("ANALYZE")
        await self._sqlite_conn.commit()

    # Convenience methods for backward compatibility
    async def get_page_keyword_performance(
        self,
        site_id: int,
        date_range: tuple[str, str] | None = None,
        url_filter: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Get page-keyword performance data."""
        # This would be implemented using repositories
        # For now, return empty result
        return {"data": [], "total_pages": 0, "total_keywords": 0}

    async def get_page_keyword_performance_stream(
        self,
        site_id: int,
        date_range: tuple[str, str] | None = None,
        url_filter: str | None = None,
        limit: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream page-keyword performance data."""
        if not self.streaming:
            raise RuntimeError("Streaming service not initialized")

        async for line in self.streaming.stream_page_keyword_performance(
            site_id, date_range, url_filter, limit
        ):
            yield line

    async def export_performance_csv(self, data: list[dict]) -> str:
        """Export performance data as CSV."""
        from .utils import CSVFormatter

        if not data:
            return (
                "url,total_clicks,total_impressions,avg_ctr,avg_position,keywords,keyword_count\n"
            )

        lines = ["url,total_clicks,total_impressions,avg_ctr,avg_position,keywords,keyword_count"]
        formatter = CSVFormatter()

        for item in data:
            keywords_str = formatter.format_keywords(item.get("keywords", []))
            values = [
                item["url"],
                item["total_clicks"],
                item["total_impressions"],
                item["avg_ctr"],
                item["avg_position"],
                keywords_str,
                item["keyword_count"],
            ]
            types = ["string", "int", "int", "float", "float", "string", "int"]
            lines.append(formatter.format_row(values, types))

        return "\n".join(lines)

    # Legacy compatibility
    async def get_site_by_hostname(self, hostname: str) -> Any:
        """Get site by hostname."""
        return await self.sites.get_by_hostname(hostname)
