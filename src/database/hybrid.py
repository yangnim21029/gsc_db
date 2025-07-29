"""Hybrid database implementation using SQLite + DuckDB for analytics."""

import asyncio
import sqlite3
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite
import duckdb
import polars as pl

from ..config import get_settings
from ..models import PerformanceData, PerformanceMetrics, Site


class HybridDataStore:
    """Hybrid data store combining SQLite for storage and DuckDB for analytics."""

    def __init__(self, sqlite_path: Path | None = None):
        """Initialize hybrid data store."""
        settings = get_settings()
        self.sqlite_path = sqlite_path or settings.database_path
        self.enable_duckdb = settings.enable_duckdb

        # Ensure database directory exists
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize connections
        self._sqlite_conn: aiosqlite.Connection | None = None
        self._duck_conn: duckdb.DuckDBPyConnection | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize database connections and create tables."""
        async with self._lock:
            # Initialize SQLite
            self._sqlite_conn = await aiosqlite.connect(
                self.sqlite_path,
                isolation_level=None,  # Autocommit mode
                detect_types=0,  # Disable automatic date parsing to avoid deprecation warning
            )

            # Enable WAL mode for better concurrency
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")
            await self._sqlite_conn.execute("PRAGMA journal_mode=WAL")
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")
            await self._sqlite_conn.execute("PRAGMA synchronous=NORMAL")

            # Create tables
            await self._create_tables()

            # Create performance indexes
            await self._optimize_performance()

            # Apply standard mode optimizations
            settings = get_settings()
            await self._sqlite_conn.execute(f"PRAGMA cache_size = {settings.standard_cache_size}")
            await self._sqlite_conn.execute("PRAGMA temp_store = MEMORY")
            await self._sqlite_conn.execute("PRAGMA mmap_size = 134217728")  # 128MB

            # Initialize DuckDB if enabled
            if self.enable_duckdb:
                self._duck_conn = duckdb.connect(":memory:")
                self._duck_conn.execute(
                    f"""
                    ATTACH DATABASE '{self.sqlite_path}' AS sqlite_db (TYPE SQLITE);
                """
                )

    async def close(self) -> None:
        """Close all database connections."""
        async with self._lock:
            if self._sqlite_conn:
                await self._sqlite_conn.close()
                self._sqlite_conn = None

            if self._duck_conn:
                self._duck_conn.close()
                self._duck_conn = None

    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        if not self._sqlite_conn:
            raise RuntimeError("Database not initialized")

        await self._sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                category TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        await self._sqlite_conn.execute(
            """
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
        """
        )

        await self._sqlite_conn.execute(
            """
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
        """
        )

        # Create indexes for better performance
        await self._sqlite_conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_performance_site_date
            ON gsc_performance_data(site_id, date)
        """
        )

        await self._sqlite_conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_performance_query
            ON gsc_performance_data(query)
        """
        )

        await self._sqlite_conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_hourly_site_date
            ON hourly_rankings(site_id, date, hour)
        """
        )

        await self._sqlite_conn.commit()

    async def _optimize_performance(self) -> None:
        """Create performance indexes for the database."""
        if not self._sqlite_conn:
            raise RuntimeError("Database not initialized")

        # Create additional performance indexes
        indexes = [
            """CREATE INDEX IF NOT EXISTS idx_gsc_performance_site_page_clicks
               ON gsc_performance_data(site_id, page, clicks DESC)""",
            """CREATE INDEX IF NOT EXISTS idx_gsc_performance_site_query_clicks
               ON gsc_performance_data(site_id, query, clicks DESC)""",
            """CREATE INDEX IF NOT EXISTS idx_gsc_performance_composite
               ON gsc_performance_data(site_id, date, page, query, clicks DESC)""",
        ]

        for index_sql in indexes:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")
            await self._sqlite_conn.execute(index_sql)

        await self._sqlite_conn.commit()

    async def update_statistics(self, table: str | None = None) -> None:
        """Update database statistics for query optimization.

        Args:
            table: Specific table to analyze. If None, analyzes all tables.
        """
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")

            if table:
                print(f"Updating statistics for table: {table}")
                await self._sqlite_conn.execute(f"ANALYZE {table}")
            else:
                print("Updating statistics for all tables...")
                await self._sqlite_conn.execute("ANALYZE")

            await self._sqlite_conn.commit()
            print("Statistics update complete")

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Provide a database transaction context."""
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")

            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")
            await self._sqlite_conn.execute("BEGIN")
            try:
                yield self._sqlite_conn
                await self._sqlite_conn.execute("COMMIT")
            except Exception:
                await self._sqlite_conn.execute("ROLLBACK")
                raise

    # Site Management
    async def get_sites(self, active_only: bool = True) -> list[Site]:
        """Get all sites."""
        query = "SELECT * FROM sites"
        if active_only:
            query += " WHERE is_active = 1"

        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")
            cursor = await self._sqlite_conn.execute(query)
            rows = await cursor.fetchall()

        return [
            Site(
                id=row[0],
                domain=row[1],
                name=row[2],
                category=row[3],
                is_active=bool(row[4]),
                created_at=row[5],
                updated_at=row[6],
            )
            for row in rows
        ]

    async def get_site_by_id(self, site_id: int) -> Site | None:
        """Get site by ID."""
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")
            cursor = await self._sqlite_conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
            row = await cursor.fetchone()

        if row:
            return Site(
                id=row[0],
                domain=row[1],
                name=row[2],
                category=row[3],
                is_active=bool(row[4]),
                created_at=row[5],
                updated_at=row[6],
            )
        return None

    async def add_site(self, domain: str, name: str, category: str | None = None) -> int:
        """Add a new site."""
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")
            cursor = await self._sqlite_conn.execute(
                """
                INSERT INTO sites (domain, name, category)
                VALUES (?, ?, ?)
                """,
                (domain, name, category),
            )
            await self._sqlite_conn.commit()
            return cursor.lastrowid or 0

    # Performance Data Management
    async def insert_performance_data(
        self, data: list[PerformanceData], mode: str = "skip"
    ) -> dict[str, int]:
        """
        Insert performance data with skip or overwrite mode.

        Note: This method processes data sequentially to maintain consistency
        with GSC API's sequential-only data fetching pattern.
        """
        stats = {"inserted": 0, "updated": 0, "skipped": 0}

        async with self.transaction() as conn:
            for record in data:
                if mode == "skip":
                    # Try to insert, skip if exists
                    try:
                        await conn.execute(
                            """
                            INSERT INTO gsc_performance_data
                            (site_id, date, page, query, device, search_type,
                             clicks, impressions, ctr, position)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                record.site_id,
                                record.date,
                                record.page,
                                record.query,
                                record.device,
                                record.search_type,
                                record.clicks,
                                record.impressions,
                                record.ctr,
                                record.position,
                            ),
                        )
                        stats["inserted"] += 1
                    except sqlite3.IntegrityError:
                        stats["skipped"] += 1
                else:  # overwrite mode
                    await conn.execute(
                        """
                        INSERT OR REPLACE INTO gsc_performance_data
                        (site_id, date, page, query, device, search_type,
                         clicks, impressions, ctr, position)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record.site_id,
                            record.date,
                            record.page,
                            record.query,
                            record.device,
                            record.search_type,
                            record.clicks,
                            record.impressions,
                            record.ctr,
                            record.position,
                        ),
                    )
                    stats["inserted"] += 1

        return stats

    async def insert_performance_data_batch(
        self, data: list[PerformanceData], mode: str = "skip"
    ) -> dict[str, int]:
        """
        Insert performance data using executemany for better performance.

        This is an optimized version that reduces I/O operations significantly.
        """
        stats = {"inserted": 0, "updated": 0, "skipped": 0}

        if not data:
            return stats

        # Convert PerformanceData objects to tuples for executemany
        records = [
            (
                record.site_id,
                record.date,
                record.page,
                record.query,
                record.device,
                record.search_type,
                record.clicks,
                record.impressions,
                record.ctr,
                record.position,
            )
            for record in data
        ]

        async with self.transaction() as conn:
            if mode == "skip":
                # For skip mode, try batch insert first
                try:
                    await conn.executemany(
                        """
                        INSERT INTO gsc_performance_data
                        (site_id, date, page, query, device, search_type,
                         clicks, impressions, ctr, position)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        records,
                    )
                    stats["inserted"] = len(records)
                except sqlite3.IntegrityError:
                    # Fall back to individual inserts to track which ones fail
                    for record in data:
                        try:
                            await conn.execute(
                                """
                                INSERT INTO gsc_performance_data
                                (site_id, date, page, query, device, search_type,
                                 clicks, impressions, ctr, position)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    record.site_id,
                                    record.date,
                                    record.page,
                                    record.query,
                                    record.device,
                                    record.search_type,
                                    record.clicks,
                                    record.impressions,
                                    record.ctr,
                                    record.position,
                                ),
                            )
                            stats["inserted"] += 1
                        except sqlite3.IntegrityError:
                            stats["skipped"] += 1
            else:  # overwrite mode
                await conn.executemany(
                    """
                    INSERT OR REPLACE INTO gsc_performance_data
                    (site_id, date, page, query, device, search_type,
                     clicks, impressions, ctr, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    records,
                )
                stats["inserted"] = len(records)

        return stats

    async def insert_hourly_data(self, data: list[dict], mode: str = "skip") -> dict[str, int]:
        """
        Insert hourly ranking data with skip or overwrite mode.
        """
        stats = {"inserted": 0, "updated": 0, "skipped": 0}

        async with self.transaction() as conn:
            for record in data:
                if mode == "skip":
                    # Try to insert, skip if exists
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

    async def delete_hourly_data_for_date(self, site_id: int, date: date) -> None:
        """Delete all hourly data for a specific site and date."""
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")

            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")
            await self._sqlite_conn.execute(
                "DELETE FROM hourly_rankings WHERE site_id = ? AND date = ?",
                (site_id, date.isoformat()),
            )
            await self._sqlite_conn.commit()

    # Analytics with DuckDB
    async def analyze_performance_trends(self, site_id: int, days: int) -> pl.DataFrame:
        """Analyze performance trends using DuckDB window functions."""
        if not self.enable_duckdb:
            raise RuntimeError("DuckDB is not enabled")

        query = f"""
        WITH daily_stats AS (
            SELECT
                date,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(position) as avg_position,
                COUNT(DISTINCT query) as unique_queries
            FROM sqlite_db.gsc_performance_data
            WHERE site_id = {site_id}
            GROUP BY date
            ORDER BY date DESC
            LIMIT {days}
        )
        SELECT
            *,
            AVG(total_clicks) OVER (
                ORDER BY date
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ) as clicks_7d_avg,
            total_clicks - LAG(total_clicks, 7) OVER (ORDER BY date) as clicks_wow_change,
            SUM(total_clicks) OVER (ORDER BY date) as cumulative_clicks
        FROM daily_stats
        ORDER BY date DESC
        """

        # Execute in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        if not self._duck_conn:
            raise RuntimeError("DuckDB not initialized")

        result = await loop.run_in_executor(None, lambda: self._duck_conn.execute(query).pl())

        return result

    # Diagnostics and Testing Methods
    async def test_connection(self) -> bool:
        """Test database connection."""
        if not self._sqlite_conn:
            return False

        try:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")
            await self._sqlite_conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    async def get_sync_coverage(self, site_id: int, days: int) -> dict[str, bool]:
        """Get sync coverage for a site over the specified days."""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        cursor = await self._sqlite_conn.execute(
            """
            SELECT DISTINCT date
            FROM gsc_performance_data
            WHERE site_id = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC
            """,
            (site_id, start_date, end_date),
        )

        synced_dates = {row[0] for row in await cursor.fetchall()}

        # Build coverage dict
        coverage = {}
        current_date = start_date
        while current_date <= end_date:
            coverage[current_date.isoformat()] = current_date.isoformat() in synced_dates
            current_date += timedelta(days=1)

        return coverage

    async def get_pragma_info(self) -> dict[str, Any]:
        """Get SQLite pragma settings."""
        pragmas = [
            "journal_mode",
            "synchronous",
            "cache_size",
            "busy_timeout",
            "temp_store",
        ]

        info = {}
        for pragma in pragmas:
            cursor = await self._sqlite_conn.execute(f"PRAGMA {pragma}")
            result = await cursor.fetchone()
            info[pragma] = result[0] if result else None

        return info

    async def get_site_by_hostname(self, hostname: str) -> Site | None:
        """Get site by hostname (supports various formats)."""
        # Normalize hostname to domain format
        domain_variants = [
            hostname,
            f"sc-domain:{hostname}",
            f"https://{hostname}",
            f"http://{hostname}",
            hostname.replace("www.", ""),
            (
                f"www.{hostname}"
                if not hostname.startswith("www.")
                else hostname.replace("www.", "")
            ),
        ]

        for variant in domain_variants:
            cursor = await self._sqlite_conn.execute(
                "SELECT * FROM sites WHERE domain = ? AND is_active = 1 LIMIT 1",
                (variant,),
            )
            row = await cursor.fetchone()
            if row:
                return Site(
                    id=row[0],
                    domain=row[1],
                    name=row[2],
                    category=row[3],
                    is_active=bool(row[4]),
                    created_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    updated_at=datetime.fromisoformat(row[6]) if row[6] else None,
                )

        return None

    async def search_queries(
        self,
        site_id: int,
        search_term: str,
        date_range: tuple[str, str],
        limit: int = 100,
    ) -> list[dict]:
        """Search queries containing the search term."""
        cursor = await self._sqlite_conn.execute(
            """
            SELECT
                query,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(ctr) as avg_ctr,
                AVG(position) as avg_position,
                COUNT(DISTINCT date) as days_appeared
            FROM gsc_performance_data
            WHERE site_id = ?
            AND query LIKE ?
            AND date BETWEEN ? AND ?
            GROUP BY query
            ORDER BY total_impressions DESC
            LIMIT ?
            """,
            (site_id, f"%{search_term}%", date_range[0], date_range[1], limit),
        )

        results = []
        async for row in cursor:
            results.append(
                {
                    "query": row[0],
                    "total_clicks": row[1],
                    "total_impressions": row[2],
                    "avg_ctr": row[3],
                    "avg_position": row[4],
                    "days_appeared": row[5],
                }
            )

        return results

    async def get_page_keyword_performance(
        self,
        site_id: int,
        date_range: tuple[str, str] | None = None,
        url_filter: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Get page-keyword performance data."""
        # Build query conditions
        where_conditions = ["site_id = ?"]
        params: list[Any] = [site_id]

        if date_range:
            where_conditions.append("date BETWEEN ? AND ?")
            params.extend(date_range)

        if url_filter:
            where_conditions.append("page LIKE ?")
            params.append(f"%{url_filter}%")

        where_clause = " AND ".join(where_conditions)

        # Build query with optional LIMIT
        query = f"""
            SELECT
                page as url,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(ctr) as avg_ctr,
                AVG(position) as avg_position,
                GROUP_CONCAT(query) as keywords,
                COUNT(DISTINCT query) as keyword_count
            FROM gsc_performance_data
            WHERE {where_clause}
            GROUP BY page
            ORDER BY total_clicks DESC
            """

        if limit:
            query += f" LIMIT {limit}"

        cursor = await self._sqlite_conn.execute(query, params)

        results = []
        async for row in cursor:
            results.append(
                {
                    "url": row[0],
                    "total_clicks": row[1],
                    "total_impressions": row[2],
                    "avg_ctr": row[3],
                    "avg_position": row[4],
                    "keywords": row[5].split(",") if row[5] else [],
                    "keyword_count": row[6],
                }
            )

        return {
            "data": results,
            "total_pages": len(results),
            "total_keywords": sum(item["keyword_count"] for item in results),
        }

    def _build_performance_where_clause(
        self, site_id: int, date_range: tuple[str, str] | None, url_filter: str | None
    ) -> str:
        """Build WHERE clause for performance query."""
        conditions = [f"site_id = {site_id}"]
        if date_range:
            conditions.append(f"date BETWEEN '{date_range[0]}' AND '{date_range[1]}'")
        if url_filter:
            conditions.append(f"page LIKE '%{url_filter}%'")
        return " AND ".join(conditions)

    def _build_performance_query(self, where_clause: str, limit: int | None) -> str:
        """Build the DuckDB performance query."""
        query = f"""
        WITH page_stats AS (
            SELECT
                page as url,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(ctr) as avg_ctr,
                AVG(position) as avg_position,
                COUNT(DISTINCT query) as keyword_count
            FROM sqlite_db.gsc_performance_data
            WHERE {where_clause}
            GROUP BY page
        ),
        ranked_keywords AS (
            SELECT
                page,
                query,
                SUM(clicks) as query_clicks,
                ROW_NUMBER() OVER (PARTITION BY page ORDER BY SUM(clicks) DESC) as rn
            FROM sqlite_db.gsc_performance_data
            WHERE {where_clause}
            GROUP BY page, query
        ),
        page_keywords AS (
            SELECT
                page,
                STRING_AGG(query, '|' ORDER BY rn) as keywords
            FROM ranked_keywords
            WHERE rn <= 10
            GROUP BY page
        )
        SELECT
            ps.url,
            ps.total_clicks,
            ps.total_impressions,
            ps.avg_ctr,
            ps.avg_position,
            COALESCE(pk.keywords, '') as keywords,
            ps.keyword_count
        FROM page_stats ps
        LEFT JOIN page_keywords pk ON ps.url = pk.page
        ORDER BY ps.total_clicks DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        return query

    async def _stream_duckdb_results(self, query: str) -> AsyncGenerator[str, None]:
        """Stream results from DuckDB query."""
        loop = asyncio.get_event_loop()

        def execute_query() -> Any:  # DuckDBPyResult
            return self._duck_conn.execute(query)

        result = await loop.run_in_executor(None, execute_query)

        while True:
            row = await loop.run_in_executor(None, result.fetchone)
            if not row:
                break
            line = f'"{row[0]}",{row[1]},{row[2]},{row[3]:.4f},{row[4]:.2f},"{row[5]}",{row[6]}\n'
            yield line

    async def get_page_keyword_performance_stream(
        self,
        site_id: int,
        date_range: tuple[str, str] | None = None,
        url_filter: str | None = None,
        limit: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream page-keyword performance data using DuckDB for efficient analytics."""
        # Handle SQLite fallback
        if not self.enable_duckdb:
            # Simple SQLite implementation without legacy module
            conditions = [f"site_id = {site_id}"]
            if date_range:
                conditions.append(f"date BETWEEN '{date_range[0]}' AND '{date_range[1]}'")
            if url_filter:
                conditions.append(f"page LIKE '%{url_filter}%'")
            where_clause = " AND ".join(conditions)

            query = f"""
            SELECT
                page as url,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(ctr) as avg_ctr,
                AVG(position) as avg_position,
                COUNT(DISTINCT query) as keyword_count
            FROM gsc_performance_data
            WHERE {where_clause}
            GROUP BY page
            ORDER BY total_clicks DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            if not self._sqlite_conn:
                raise RuntimeError("SQLite connection not initialized")

            cursor = await self._sqlite_conn.execute(query)

            while True:
                row = await cursor.fetchone()
                if not row:
                    break
                # Format CSV line (simplified - no keywords for SQLite)
                line = f'"{row[0]}",{row[1]},{row[2]},{row[3]:.4f},{row[4]:.2f},"",{row[5]}\n'
                yield line
            return

        # Check DuckDB connection
        if not self._duck_conn:
            raise RuntimeError("DuckDB not initialized")

        # Build query
        where_clause = self._build_performance_where_clause(site_id, date_range, url_filter)
        query = self._build_performance_query(where_clause, limit)

        # Yield header
        yield "url,total_clicks,total_impressions,avg_ctr,avg_position,keywords,keyword_count\n"

        # Stream results
        async for line in self._stream_duckdb_results(query):
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
        """Get ranking data with flexible filtering and grouping."""
        if group_by is None:
            group_by = ["query"]
        if self.enable_duckdb and len(group_by) > 1:
            # Use DuckDB for complex aggregations
            return await self._get_ranking_data_duckdb(
                site_id, date_range, queries, pages, group_by, limit, exact_match
            )
        else:
            # Use SQLite for simple queries
            return await self._get_ranking_data_sqlite(
                site_id, date_range, queries, pages, group_by, limit, exact_match
            )

    async def _get_ranking_data_duckdb(
        self,
        site_id: int,
        date_range: tuple[str, str],
        queries: list[str] | None,
        pages: list[str] | None,
        group_by: list[str],
        limit: int,
        exact_match: bool,
    ) -> dict[str, Any]:
        """Get ranking data using DuckDB for complex queries."""
        # Build dynamic query
        select_cols = ", ".join(group_by)
        group_cols = ", ".join(group_by)

        where_clauses = ["site_id = ?", "date BETWEEN ? AND ?"]
        params = [site_id, date_range[0], date_range[1]]

        if queries:
            if exact_match:
                placeholders = ", ".join(["?" for _ in queries])
                where_clauses.append(f"query IN ({placeholders})")
                params.extend(queries)
            else:
                for query in queries:
                    where_clauses.append("query LIKE ?")
                    params.append(f"%{query}%")

        if pages:
            placeholders = ", ".join(["?" for _ in pages])
            where_clauses.append(f"page IN ({placeholders})")
            params.extend(pages)

        where_sql = " AND ".join(where_clauses)

        query = f"""
        WITH aggregated AS (
            SELECT
                {select_cols},
                SUM(clicks) as clicks,
                SUM(impressions) as impressions,
                SUM(clicks * position) / NULLIF(SUM(clicks), 0) as weighted_position,
                SUM(clicks) / NULLIF(SUM(impressions), 0.0) as ctr
            FROM sqlite_db.gsc_performance_data
            WHERE {where_sql}
            GROUP BY {group_cols}
        )
        SELECT
            *,
            RANK() OVER (ORDER BY clicks DESC) as rank_by_clicks,
            PERCENT_RANK() OVER (ORDER BY clicks DESC) as percentile_clicks
        FROM aggregated
        ORDER BY clicks DESC
        LIMIT ?
        """

        params.append(limit)

        # Execute query
        loop = asyncio.get_event_loop()

        if not self._duck_conn:
            raise RuntimeError("DuckDB not initialized")

        df = await loop.run_in_executor(None, lambda: self._duck_conn.execute(query, params).pl())

        # Format results with proper typing
        from ..models import RankingDataItem

        data = []
        for row in df.to_dicts():
            # DEBUG: 處理可能的 None 值
            # weighted_position 可能為 None，特別是當沒有數據時
            weighted_pos = row.get("weighted_position")
            if weighted_pos is None:
                # 如果沒有 position 數據，使用預設值 0.0
                print(f"[WARNING] weighted_position is None for query: {row.get('query')}")
                weighted_pos = 0.0

            item = RankingDataItem(
                query=row.get("query"),
                page=row.get("page"),
                clicks=int(row["clicks"]),
                impressions=int(row["impressions"]),
                ctr=round(float(row["ctr"]), 4),
                position=round(weighted_pos, 2),  # 使用處理過的值
                rank_by_clicks=int(row.get("rank_by_clicks", 0)),
                percentile_clicks=float(row.get("percentile_clicks", 0.0)),
            )
            data.append(item)

        # Calculate aggregations
        # DEBUG: 處理聚合計算時的 None 值
        total_clicks = int(df["clicks"].sum())
        total_impressions = int(df["impressions"].sum())

        # 計算平均 position 時需要處理 None 值
        position_mean = df["weighted_position"].mean()
        if position_mean is None:
            position_mean = 0.0

        aggregations = PerformanceMetrics(
            clicks=total_clicks,
            impressions=total_impressions,
            ctr=float(total_clicks / max(total_impressions, 1)),
            position=float(position_mean),
        )

        return {"data": data, "total": len(df), "aggregations": aggregations}

    async def _get_ranking_data_sqlite(
        self,
        site_id: int,
        date_range: tuple[str, str],
        queries: list[str] | None,
        pages: list[str] | None,
        group_by: list[str],
        limit: int,
        exact_match: bool = True,
    ) -> dict[str, Any]:
        """Get ranking data using SQLite (simplified version)."""
        # Build WHERE clause
        conditions = [f"site_id = {site_id}"]

        if date_range:
            conditions.append(f"date BETWEEN '{date_range[0]}' AND '{date_range[1]}'")

        if queries:
            if exact_match:
                query_conditions = " OR ".join([f"query = '{q}'" for q in queries])
            else:
                query_conditions = " OR ".join([f"query LIKE '%{q}%'" for q in queries])
            conditions.append(f"({query_conditions})")

        if pages:
            page_conditions = " OR ".join([f"page LIKE '%{p}%'" for p in pages])
            conditions.append(f"({page_conditions})")

        where_clause = " AND ".join(conditions)

        # Simplified query without window functions
        query = f"""
        SELECT
            query,
            page,
            SUM(clicks) as clicks,
            SUM(impressions) as impressions,
            AVG(ctr) as ctr,
            AVG(position) as position,
            COUNT(*) as days_appeared
        FROM gsc_performance_data
        WHERE {where_clause}
        GROUP BY query, page
        ORDER BY clicks DESC
        LIMIT {limit}
        """

        if not self._sqlite_conn:
            raise RuntimeError("SQLite connection not initialized")

        cursor = await self._sqlite_conn.execute(query)
        rows = await cursor.fetchall()

        # Format results
        from ..models import RankingDataItem

        data = []
        total_clicks = 0
        total_impressions = 0

        for row in rows:
            item = RankingDataItem(
                query=row[0],
                page=row[1],
                clicks=int(row[2]),
                impressions=int(row[3]),
                ctr=round(float(row[4]), 4),
                position=round(float(row[5]), 2),
                weighted_position=round(float(row[5]), 2),  # Same as position for SQLite
                days_appeared=int(row[6]),
            )
            data.append(item)
            total_clicks += item.clicks
            total_impressions += item.impressions

        # Calculate aggregations
        aggregations = PerformanceMetrics(
            clicks=total_clicks,
            impressions=total_impressions,
            ctr=float(total_clicks / max(total_impressions, 1)),
            position=float(sum(d.position for d in data) / max(len(data), 1)),
        )

        return {"data": data, "total": len(data), "aggregations": aggregations}

    async def export_to_parquet(self, site_id: int, output_path: Path) -> None:
        """Export site data to Parquet format for archival."""
        if not self.enable_duckdb:
            raise RuntimeError("DuckDB is not enabled")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        query = f"""
        COPY (
            SELECT * FROM sqlite_db.gsc_performance_data
            WHERE site_id = {site_id}
        ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """

        loop = asyncio.get_event_loop()

        if not self._duck_conn:
            raise RuntimeError("DuckDB not initialized")

        await loop.run_in_executor(None, self._duck_conn.execute, query)

    # Index Management for Bulk Operations
    async def drop_performance_indexes(self) -> None:
        """Drop performance indexes for faster bulk inserts."""
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")

            print("Dropping performance indexes for bulk insert...")

            indexes_to_drop = [
                "idx_performance_site_date",
                "idx_performance_query",
                "idx_gsc_performance_site_page_clicks",
                "idx_gsc_performance_site_query_clicks",
                "idx_gsc_performance_composite",
            ]

            for index_name in indexes_to_drop:
                try:
                    await self._sqlite_conn.execute(f"DROP INDEX IF EXISTS {index_name}")
                except Exception as e:
                    print(f"  Warning: Failed to drop index {index_name}: {e}")

            await self._sqlite_conn.commit()
            print("Performance indexes dropped successfully")

    async def recreate_performance_indexes(self) -> None:
        """Recreate performance indexes after bulk insert."""
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")

            print("Recreating performance indexes...")

            indexes_to_create = [
                """CREATE INDEX IF NOT EXISTS idx_performance_site_date
                   ON gsc_performance_data(site_id, date)""",
                """CREATE INDEX IF NOT EXISTS idx_performance_query
                   ON gsc_performance_data(query)""",
                """CREATE INDEX IF NOT EXISTS idx_gsc_performance_site_page_clicks
                   ON gsc_performance_data(site_id, page, clicks DESC)""",
                """CREATE INDEX IF NOT EXISTS idx_gsc_performance_site_query_clicks
                   ON gsc_performance_data(site_id, query, clicks DESC)""",
                """CREATE INDEX IF NOT EXISTS idx_gsc_performance_composite
                   ON gsc_performance_data(site_id, date, page, query, clicks DESC)""",
            ]

            for i, index_sql in enumerate(indexes_to_create, 1):
                print(f"  Creating index {i}/{len(indexes_to_create)}...")
                await self._sqlite_conn.execute(index_sql)

            await self._sqlite_conn.commit()
            print("Performance indexes recreated successfully")

    async def set_fast_insert_mode(self, enabled: bool = True) -> None:
        """Enable or disable fast insert mode for bulk operations."""
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")

            settings = get_settings()

            if enabled:
                print("Enabling fast insert mode...")
                # Disable synchronous writes temporarily (main performance boost)
                await self._sqlite_conn.execute("PRAGMA synchronous = OFF")
                # Increase cache size significantly
                await self._sqlite_conn.execute("PRAGMA cache_size = 50000")
                # Use memory for temporary tables
                await self._sqlite_conn.execute("PRAGMA temp_store = MEMORY")
                # Disable foreign key checks
                await self._sqlite_conn.execute("PRAGMA foreign_keys = OFF")
                # Additional optimizations for old computers
                await self._sqlite_conn.execute("PRAGMA journal_size_limit = 67108864")  # 64MB
                await self._sqlite_conn.execute("PRAGMA mmap_size = 268435456")  # 256MB
                print("Fast insert mode enabled")
            else:
                print("Disabling fast insert mode...")
                # Restore safe settings with standard optimizations
                await self._sqlite_conn.execute("PRAGMA synchronous = NORMAL")
                # Use standard cache size from config
                await self._sqlite_conn.execute(
                    f"PRAGMA cache_size = {settings.standard_cache_size}"
                )
                await self._sqlite_conn.execute("PRAGMA foreign_keys = ON")
                # Keep some optimizations for standard mode
                await self._sqlite_conn.execute("PRAGMA temp_store = MEMORY")
                await self._sqlite_conn.execute("PRAGMA mmap_size = 134217728")  # 128MB
                print("Fast insert mode disabled")

    # Optimized query methods for common use cases
    async def get_keyword_performance_fast(
        self, site_id: int, keyword: str, days: int = 30, exact_match: bool = False
    ) -> list[dict[str, Any]]:
        """
        Fast keyword performance query with minimal overhead.
        Optimized for the most common use case of checking keyword trends.
        """
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")

            # Use index hint for better performance on large datasets
            query_condition = "query = ?" if exact_match else "query LIKE ?"
            keyword_param = keyword if exact_match else f"%{keyword}%"

            # Optimized query with proper indexing
            query = f"""
            SELECT
                date,
                query,
                AVG(position) as avg_position,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                ROUND(SUM(clicks) * 100.0 / NULLIF(SUM(impressions), 0), 2) as ctr
            FROM gsc_performance_data
            WHERE site_id = ?
            AND {query_condition}
            AND date >= date('now', '-{days} days')
            GROUP BY date, query
            ORDER BY date DESC, total_clicks DESC
            """

            async with self._sqlite_conn.execute(query, [site_id, keyword_param]) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

            return [dict(zip(columns, row, strict=False)) for row in rows]

    async def get_site_daily_summary_fast(
        self, site_id: int, days: int = 30
    ) -> list[dict[str, Any]]:
        """
        Fast daily summary query for site overview.
        Pre-aggregated data for dashboard displays.
        """
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")

            # Single optimized query for all daily metrics
            query = """
            SELECT
                date,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(position) as avg_position,
                ROUND(SUM(clicks) * 100.0 / NULLIF(SUM(impressions), 0), 2) as ctr,
                COUNT(DISTINCT query) as unique_queries,
                COUNT(DISTINCT page) as unique_pages
            FROM gsc_performance_data
            WHERE site_id = ?
            AND date >= date('now', '-? days')
            GROUP BY date
            ORDER BY date DESC
            """

            async with self._sqlite_conn.execute(query, [site_id, days]) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

            return [dict(zip(columns, row, strict=False)) for row in rows]

    async def get_top_queries_fast(
        self, site_id: int, days: int = 7, limit: int = 50, min_clicks: int = 1
    ) -> list[dict[str, Any]]:
        """
        Fast top queries retrieval with aggregation.
        Optimized for quick performance overviews.
        """
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")

            query = """
            SELECT
                query,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(position) as avg_position,
                ROUND(SUM(clicks) * 100.0 / NULLIF(SUM(impressions), 0), 2) as ctr,
                COUNT(DISTINCT page) as unique_pages
            FROM gsc_performance_data
            WHERE site_id = ?
            AND date >= date('now', '-? days')
            GROUP BY query
            HAVING total_clicks >= ?
            ORDER BY total_clicks DESC
            LIMIT ?
            """

            async with self._sqlite_conn.execute(
                query, [site_id, days, min_clicks, limit]
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

            return [dict(zip(columns, row, strict=False)) for row in rows]

    async def get_page_keyword_summary_fast(
        self, site_id: int, page_pattern: str = "", days: int = 30, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Fast page-keyword performance matrix.
        Optimized for content analysis workflows.
        """
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")

            where_clause = "site_id = ? AND date >= date('now', '-? days')"
            params = [site_id, days]

            if page_pattern:
                where_clause += " AND page LIKE ?"
                params.append(f"%{page_pattern}%")

            query = f"""
            SELECT
                page,
                query as keyword,
                AVG(position) as avg_position,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                ROUND(AVG(ctr), 2) as avg_ctr
            FROM gsc_performance_data
            WHERE {where_clause}
            GROUP BY page, query
            HAVING total_impressions >= 5
            ORDER BY total_clicks DESC, avg_position ASC
            LIMIT ?
            """

            params.append(limit)

            async with self._sqlite_conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

            return [dict(zip(columns, row, strict=False)) for row in rows]

    async def check_data_coverage_fast(self, site_id: int, days: int = 30) -> dict[str, Any]:
        """
        Quick data coverage check for sync status monitoring.
        Returns summary statistics about data availability.
        """
        async with self._lock:
            if not self._sqlite_conn:
                raise RuntimeError("Database not initialized")

            query = """
            SELECT
                COUNT(DISTINCT date) as days_with_data,
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                SUM(clicks) as total_clicks,
                COUNT(*) as total_records
            FROM gsc_performance_data
            WHERE site_id = ?
            AND date >= date('now', '-? days')
            """

            async with self._sqlite_conn.execute(query, [site_id, days]) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return {"days_with_data": 0, "coverage_percent": 0}

                columns = [desc[0] for desc in cursor.description]
                result = dict(zip(columns, row, strict=False))

                # Calculate coverage percentage
                result["coverage_percent"] = round((result["days_with_data"] / days) * 100, 1)

                return result
