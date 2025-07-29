"""
Aggregation helper for pre-computing common metrics.

This module provides functions to pre-calculate frequently accessed aggregations,
which can significantly speed up dashboard queries and reporting.

Usage:
    from src.utils.aggregation_helper import update_daily_aggregates

    # Run after daily sync to update aggregated tables
    await update_daily_aggregates()
"""

from datetime import datetime, timedelta
from typing import Any

from ..database.hybrid import HybridDataStore


async def create_aggregation_tables() -> None:
    """
    Create aggregation tables for pre-computed metrics.
    This should be run once during setup.
    """
    db = HybridDataStore()
    await db.initialize()

    try:
        async with db._lock:
            if not db._sqlite_conn:
                raise RuntimeError("Database not initialized")

            # Daily site summary table
            await db._sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_site_summary (
                    site_id INTEGER,
                    date TEXT,
                    total_clicks INTEGER,
                    total_impressions INTEGER,
                    avg_position REAL,
                    ctr REAL,
                    unique_queries INTEGER,
                    unique_pages INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (site_id, date)
                )
            """)

            # Top queries by day table
            await db._sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_top_queries (
                    site_id INTEGER,
                    date TEXT,
                    query TEXT,
                    total_clicks INTEGER,
                    total_impressions INTEGER,
                    avg_position REAL,
                    ctr REAL,
                    ranking INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (site_id, date, query)
                )
            """)

            # Weekly aggregates table
            await db._sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS weekly_site_summary (
                    site_id INTEGER,
                    week_start_date TEXT,
                    total_clicks INTEGER,
                    total_impressions INTEGER,
                    avg_position REAL,
                    ctr REAL,
                    unique_queries INTEGER,
                    unique_pages INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (site_id, week_start_date)
                )
            """)

            # Create indexes for better performance
            await db._sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_summary_site_date
                ON daily_site_summary(site_id, date DESC)
            """)

            await db._sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_top_queries_site_date
                ON daily_top_queries(site_id, date DESC, ranking)
            """)

            await db._sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_weekly_summary_site_date
                ON weekly_site_summary(site_id, week_start_date DESC)
            """)

            await db._sqlite_conn.commit()
            print("Aggregation tables created successfully")

    finally:
        await db.close()


async def update_daily_aggregates(days_back: int = 7) -> None:
    """
    Update daily aggregation tables for the last N days.
    This should be run after each sync operation.

    Args:
        days_back: Number of days back to recalculate (default: 7)
    """
    db = HybridDataStore()
    await db.initialize()

    try:
        sites = await db.get_sites()
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)

        print(f"Updating daily aggregates for {len(sites)} sites from {start_date} to {end_date}")

        for site in sites:
            await _update_site_daily_summary(db, site.id, start_date, end_date)
            await _update_site_daily_top_queries(db, site.id, start_date, end_date)

        print("Daily aggregates updated successfully")

    finally:
        await db.close()


async def _update_site_daily_summary(
    db: HybridDataStore, site_id: int, start_date, end_date
) -> None:
    """Update daily summary for a specific site."""
    async with db._lock:
        if not db._sqlite_conn:
            raise RuntimeError("Database not initialized")

        # Delete existing data for the date range
        await db._sqlite_conn.execute(
            """
            DELETE FROM daily_site_summary
            WHERE site_id = ? AND date BETWEEN ? AND ?
        """,
            [site_id, start_date.isoformat(), end_date.isoformat()],
        )

        # Insert updated aggregates
        await db._sqlite_conn.execute(
            """
            INSERT INTO daily_site_summary
            (site_id, date, total_clicks, total_impressions, avg_position, ctr, unique_queries, unique_pages)
            SELECT
                site_id,
                date,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(position) as avg_position,
                ROUND(SUM(clicks) * 100.0 / NULLIF(SUM(impressions), 0), 2) as ctr,
                COUNT(DISTINCT query) as unique_queries,
                COUNT(DISTINCT page) as unique_pages
            FROM gsc_performance_data
            WHERE site_id = ?
            AND date BETWEEN ? AND ?
            GROUP BY site_id, date
        """,
            [site_id, start_date.isoformat(), end_date.isoformat()],
        )


async def _update_site_daily_top_queries(
    db: HybridDataStore, site_id: int, start_date, end_date, top_n: int = 20
) -> None:
    """Update daily top queries for a specific site."""
    async with db._lock:
        if not db._sqlite_conn:
            raise RuntimeError("Database not initialized")

        # Delete existing data for the date range
        await db._sqlite_conn.execute(
            """
            DELETE FROM daily_top_queries
            WHERE site_id = ? AND date BETWEEN ? AND ?
        """,
            [site_id, start_date.isoformat(), end_date.isoformat()],
        )

        # Insert updated top queries with ranking
        await db._sqlite_conn.execute(
            f"""
            INSERT INTO daily_top_queries
            (site_id, date, query, total_clicks, total_impressions, avg_position, ctr, ranking)
            SELECT
                site_id,
                date,
                query,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(position) as avg_position,
                ROUND(SUM(clicks) * 100.0 / NULLIF(SUM(impressions), 0), 2) as ctr,
                ROW_NUMBER() OVER (PARTITION BY site_id, date ORDER BY SUM(clicks) DESC) as ranking
            FROM gsc_performance_data
            WHERE site_id = ?
            AND date BETWEEN ? AND ?
            GROUP BY site_id, date, query
            HAVING ranking <= {top_n}
        """,
            [site_id, start_date.isoformat(), end_date.isoformat()],
        )


async def update_weekly_aggregates(weeks_back: int = 4) -> None:
    """
    Update weekly aggregation tables.
    Run this weekly or after major sync operations.

    Args:
        weeks_back: Number of weeks back to recalculate (default: 4)
    """
    db = HybridDataStore()
    await db.initialize()

    try:
        sites = await db.get_sites()

        print(f"Updating weekly aggregates for {len(sites)} sites, {weeks_back} weeks back")

        for site in sites:
            await _update_site_weekly_summary(db, site.id, weeks_back)

        print("Weekly aggregates updated successfully")

    finally:
        await db.close()


async def _update_site_weekly_summary(db: HybridDataStore, site_id: int, weeks_back: int) -> None:
    """Update weekly summary for a specific site."""
    async with db._lock:
        if not db._sqlite_conn:
            raise RuntimeError("Database not initialized")

        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(weeks=weeks_back)

        # Delete existing data for the date range
        await db._sqlite_conn.execute(
            """
            DELETE FROM weekly_site_summary
            WHERE site_id = ?
            AND week_start_date >= ?
        """,
            [site_id, start_date.isoformat()],
        )

        # Insert weekly aggregates
        await db._sqlite_conn.execute(
            """
            INSERT INTO weekly_site_summary
            (site_id, week_start_date, total_clicks, total_impressions, avg_position, ctr, unique_queries, unique_pages)
            SELECT
                site_id,
                date(date, 'weekday 0', '-6 days') as week_start_date,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(position) as avg_position,
                ROUND(SUM(clicks) * 100.0 / NULLIF(SUM(impressions), 0), 2) as ctr,
                COUNT(DISTINCT query) as unique_queries,
                COUNT(DISTINCT page) as unique_pages
            FROM gsc_performance_data
            WHERE site_id = ?
            AND date >= ?
            GROUP BY site_id, week_start_date
        """,
            [site_id, start_date.isoformat()],
        )


# Fast query functions using pre-aggregated data
async def get_daily_summary_from_cache(site_id: int, days: int = 30) -> list[dict[str, Any]]:
    """
    Get daily summary from pre-aggregated cache.
    Much faster than real-time aggregation for dashboard displays.
    """
    db = HybridDataStore()
    await db.initialize()

    try:
        async with db._lock:
            if not db._sqlite_conn:
                raise RuntimeError("Database not initialized")

            query = """
            SELECT
                date,
                total_clicks,
                total_impressions,
                avg_position,
                ctr,
                unique_queries,
                unique_pages
            FROM daily_site_summary
            WHERE site_id = ?
            ORDER BY date DESC
            LIMIT ?
            """

            async with db._sqlite_conn.execute(query, [site_id, days]) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

            return [dict(zip(columns, row, strict=False)) for row in rows]

    finally:
        await db.close()


async def get_top_queries_from_cache(
    site_id: int, date_str: str, limit: int = 20
) -> list[dict[str, Any]]:
    """
    Get top queries for a specific date from pre-aggregated cache.
    Perfect for daily/weekly reports.
    """
    db = HybridDataStore()
    await db.initialize()

    try:
        async with db._lock:
            if not db._sqlite_conn:
                raise RuntimeError("Database not initialized")

            query = """
            SELECT
                query,
                total_clicks,
                total_impressions,
                avg_position,
                ctr,
                ranking
            FROM daily_top_queries
            WHERE site_id = ?
            AND date = ?
            ORDER BY ranking
            LIMIT ?
            """

            async with db._sqlite_conn.execute(query, [site_id, date_str, limit]) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

            return [dict(zip(columns, row, strict=False)) for row in rows]

    finally:
        await db.close()


# Utility function to check if aggregation tables need updates
async def check_aggregation_freshness() -> dict[str, Any]:
    """
    Check the freshness of aggregation tables.
    Returns info about when aggregations were last updated.
    """
    db = HybridDataStore()
    await db.initialize()

    try:
        async with db._lock:
            if not db._sqlite_conn:
                raise RuntimeError("Database not initialized")

            # Check daily summary freshness
            async with db._sqlite_conn.execute("""
                SELECT
                    MAX(date) as latest_date,
                    COUNT(DISTINCT site_id) as sites_count,
                    MAX(created_at) as last_updated
                FROM daily_site_summary
            """) as cursor:
                daily_info = await cursor.fetchone()

            # Check main data freshness
            async with db._sqlite_conn.execute("""
                SELECT
                    MAX(date) as latest_raw_date,
                    COUNT(DISTINCT site_id) as raw_sites_count
                FROM gsc_performance_data
            """) as cursor:
                raw_info = await cursor.fetchone()

            return {
                "daily_aggregates": {
                    "latest_date": daily_info[0] if daily_info else None,
                    "sites_count": daily_info[1] if daily_info else 0,
                    "last_updated": daily_info[2] if daily_info else None,
                },
                "raw_data": {
                    "latest_date": raw_info[0] if raw_info else None,
                    "sites_count": raw_info[1] if raw_info else 0,
                },
                "needs_update": daily_info[0] != raw_info[0] if daily_info and raw_info else True,
            }

    finally:
        await db.close()
