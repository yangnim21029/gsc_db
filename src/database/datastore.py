"""Modern DataStore implementation with separated concerns."""

import asyncio
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
        self.db_path = db_path or settings.paths.database
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
    async def transaction(self):
        """Provide a database transaction context."""
        if not self._transaction_manager:
            raise RuntimeError("Database not initialized")
        async with self._transaction_manager.transaction() as conn:
            yield conn

    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        if not self._sqlite_conn:
            raise RuntimeError("Database not initialized")

        # Sites table
        await self._sqlite_conn.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                category TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Performance data table
        await self._sqlite_conn.execute("""
            CREATE TABLE IF NOT EXISTS gsc_performance_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                date DATE NOT NULL,
                page TEXT NOT NULL,
                query TEXT NOT NULL,
                device TEXT DEFAULT 'DESKTOP',
                search_type TEXT DEFAULT 'WEB',
                clicks INTEGER NOT NULL,
                impressions INTEGER NOT NULL,
                ctr REAL NOT NULL,
                position REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id),
                UNIQUE(site_id, date, page, query, device, search_type)
            )
        """)

        # Hourly rankings table
        await self._sqlite_conn.execute("""
            CREATE TABLE IF NOT EXISTS hourly_rankings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                date DATE NOT NULL,
                hour INTEGER NOT NULL,
                query TEXT NOT NULL,
                page TEXT NOT NULL,
                position REAL NOT NULL,
                clicks INTEGER NOT NULL,
                impressions INTEGER NOT NULL,
                ctr REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id),
                UNIQUE(site_id, date, hour, query, page)
            )
        """)

        # Basic indexes
        await self._sqlite_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_performance_site_date
            ON gsc_performance_data(site_id, date)
        """)

        await self._sqlite_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_performance_query
            ON gsc_performance_data(query)
        """)

        await self._sqlite_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_hourly_site_date
            ON hourly_rankings(site_id, date, hour)
        """)

        await self._sqlite_conn.commit()

    async def _optimize_performance(self) -> None:
        """Apply performance optimizations to the database."""
        if not self._sqlite_conn:
            raise RuntimeError("Database not initialized")

        # Additional performance indexes
        indexes = [
            """CREATE INDEX IF NOT EXISTS idx_gsc_performance_site_page_clicks
               ON gsc_performance_data(site_id, page, clicks DESC)""",
            """CREATE INDEX IF NOT EXISTS idx_gsc_performance_site_query_clicks
               ON gsc_performance_data(site_id, query, clicks DESC)""",
            """CREATE INDEX IF NOT EXISTS idx_gsc_performance_composite
               ON gsc_performance_data(site_id, date, page, query, clicks DESC)""",
        ]

        for index_sql in indexes:
            await self._sqlite_conn.execute(index_sql)

        # Update statistics
        await self._sqlite_conn.execute("ANALYZE gsc_performance_data")
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
    ):
        """Stream page-keyword performance data."""
        if not self.streaming:
            raise RuntimeError("Streaming service not initialized")

        async for line in self.streaming.stream_page_keyword_performance(
            site_id, date_range, url_filter, limit
        ):
            yield line

    async def export_performance_csv(self, data: list[dict]) -> str:
        """Export performance data as CSV."""
        if not data:
            return (
                "url,total_clicks,total_impressions,avg_ctr,avg_position,keywords,keyword_count\n"
            )

        lines = ["url,total_clicks,total_impressions,avg_ctr,avg_position,keywords,keyword_count"]

        for item in data:
            keywords_str = "|".join(item["keywords"]) if item["keywords"] else ""
            lines.append(
                f'"{item["url"]}",{item["total_clicks"]},{item["total_impressions"]},'
                f'{item["avg_ctr"]:.4f},{item["avg_position"]:.2f},"{keywords_str}",'
                f"{item['keyword_count']}"
            )

        return "\n".join(lines)

    # Legacy compatibility
    async def get_site_by_hostname(self, hostname: str):
        """Get site by hostname."""
        return await self.sites.get_by_hostname(hostname)
