"""
Query shortcuts for common GSC data analysis patterns.

This module provides direct, optimized functions for the most commonly used queries,
bypassing the complex API layer for users who need quick data access.

Usage:
    from src.utils.query_shortcuts import get_keyword_trends, get_top_pages

    # Get keyword performance over time
    df = await get_keyword_trends("example.com", "python tutorial", days=30)

    # Get best performing pages
    pages = await get_top_pages("example.com", days=7)
"""

from datetime import datetime, timedelta
from typing import Any

import polars as pl

from ..database.hybrid import HybridDataStore


async def get_keyword_trends(
    hostname: str, keyword: str, days: int = 30, exact_match: bool = False
) -> pl.DataFrame:
    """
    Get keyword ranking and performance trends over time.

    Args:
        hostname: Site hostname (e.g., "example.com")
        keyword: Search keyword to analyze
        days: Number of days to analyze (default: 30)
        exact_match: Whether to match keyword exactly (default: False for partial matching)

    Returns:
        DataFrame with columns: date, query, avg_position, total_clicks, total_impressions, ctr
    """
    db = HybridDataStore()
    await db.initialize()

    try:
        # Get site_id from hostname
        site = await db.get_site_by_hostname(hostname)
        if not site:
            raise ValueError(f"Site not found: {hostname}")

        # Build query condition
        if exact_match:
            query_condition = "query = ?"
            query_params = [site.id, keyword]
        else:
            query_condition = "query LIKE ?"
            query_params = [site.id, f"%{keyword}%"]

        # Date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        query_params.extend([start_date.isoformat(), end_date.isoformat()])

        # Optimized query for keyword trends
        query = f"""
        SELECT
            date,
            query,
            AVG(position) as avg_position,
            SUM(clicks) as total_clicks,
            SUM(impressions) as total_impressions,
            CASE
                WHEN SUM(impressions) > 0
                THEN ROUND(SUM(clicks) * 100.0 / SUM(impressions), 2)
                ELSE 0
            END as ctr
        FROM gsc_performance_data
        WHERE site_id = ?
        AND {query_condition}
        AND date BETWEEN ? AND ?
        GROUP BY date, query
        ORDER BY date DESC, total_clicks DESC
        """

        if not db._sqlite_conn:
            raise RuntimeError("Database not initialized")

        async with db._sqlite_conn.execute(query, query_params) as cursor:
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

        return pl.DataFrame(rows, schema=columns, orient="row")

    finally:
        await db.close()


async def get_top_pages(
    hostname: str, days: int = 7, limit: int = 50, min_clicks: int = 1
) -> pl.DataFrame:
    """
    Get top performing pages by clicks.

    Args:
        hostname: Site hostname
        days: Number of days to analyze (default: 7)
        limit: Maximum number of pages to return (default: 50)
        min_clicks: Minimum clicks threshold (default: 1)

    Returns:
        DataFrame with columns: page, total_clicks, total_impressions, avg_position, ctr, unique_queries
    """
    db = HybridDataStore()
    await db.initialize()

    try:
        site = await db.get_site_by_hostname(hostname)
        if not site:
            raise ValueError(f"Site not found: {hostname}")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        query = """
        SELECT
            page,
            SUM(clicks) as total_clicks,
            SUM(impressions) as total_impressions,
            AVG(position) as avg_position,
            CASE
                WHEN SUM(impressions) > 0
                THEN ROUND(SUM(clicks) * 100.0 / SUM(impressions), 2)
                ELSE 0
            END as ctr,
            COUNT(DISTINCT query) as unique_queries
        FROM gsc_performance_data
        WHERE site_id = ?
        AND date BETWEEN ? AND ?
        GROUP BY page
        HAVING total_clicks >= ?
        ORDER BY total_clicks DESC
        LIMIT ?
        """

        if not db._sqlite_conn:
            raise RuntimeError("Database not initialized")

        async with db._sqlite_conn.execute(
            query, [site.id, start_date.isoformat(), end_date.isoformat(), min_clicks, limit]
        ) as cursor:
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

        return pl.DataFrame(rows, schema=columns, orient="row")

    finally:
        await db.close()


async def get_keyword_page_matrix(
    hostname: str, keyword: str, days: int = 30, min_impressions: int = 10
) -> pl.DataFrame:
    """
    Get keyword-page performance matrix for detailed analysis.

    Args:
        hostname: Site hostname
        keyword: Keyword to analyze (supports partial matching)
        days: Number of days to analyze (default: 30)
        min_impressions: Minimum impressions threshold (default: 10)

    Returns:
        DataFrame with keyword-page combinations and their metrics
    """
    db = HybridDataStore()
    await db.initialize()

    try:
        site = await db.get_site_by_hostname(hostname)
        if not site:
            raise ValueError(f"Site not found: {hostname}")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        query = """
        SELECT
            query,
            page,
            AVG(position) as avg_position,
            SUM(clicks) as total_clicks,
            SUM(impressions) as total_impressions,
            ROUND(AVG(ctr), 2) as avg_ctr,
            COUNT(*) as data_points
        FROM gsc_performance_data
        WHERE site_id = ?
        AND query LIKE ?
        AND date BETWEEN ? AND ?
        GROUP BY query, page
        HAVING total_impressions >= ?
        ORDER BY total_clicks DESC, avg_position ASC
        """

        if not db._sqlite_conn:
            raise RuntimeError("Database not initialized")

        async with db._sqlite_conn.execute(
            query,
            [
                site.id,
                f"%{keyword}%",
                start_date.isoformat(),
                end_date.isoformat(),
                min_impressions,
            ],
        ) as cursor:
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

        return pl.DataFrame(rows, schema=columns, orient="row")

    finally:
        await db.close()


async def get_daily_summary(hostname: str, days: int = 30) -> pl.DataFrame:
    """
    Get daily performance summary for a site.

    Args:
        hostname: Site hostname
        days: Number of days to analyze (default: 30)

    Returns:
        DataFrame with daily metrics: date, total_clicks, total_impressions, avg_position, unique_queries, unique_pages
    """
    db = HybridDataStore()
    await db.initialize()

    try:
        site = await db.get_site_by_hostname(hostname)
        if not site:
            raise ValueError(f"Site not found: {hostname}")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        query = """
        SELECT
            date,
            SUM(clicks) as total_clicks,
            SUM(impressions) as total_impressions,
            AVG(position) as avg_position,
            CASE
                WHEN SUM(impressions) > 0
                THEN ROUND(SUM(clicks) * 100.0 / SUM(impressions), 2)
                ELSE 0
            END as ctr,
            COUNT(DISTINCT query) as unique_queries,
            COUNT(DISTINCT page) as unique_pages
        FROM gsc_performance_data
        WHERE site_id = ?
        AND date BETWEEN ? AND ?
        GROUP BY date
        ORDER BY date DESC
        """

        if not db._sqlite_conn:
            raise RuntimeError("Database not initialized")

        async with db._sqlite_conn.execute(
            query, [site.id, start_date.isoformat(), end_date.isoformat()]
        ) as cursor:
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

        return pl.DataFrame(rows, schema=columns, orient="row")

    finally:
        await db.close()


async def get_query_opportunities(
    hostname: str, days: int = 30, min_impressions: int = 100, max_position: float = 20.0
) -> pl.DataFrame:
    """
    Find keyword opportunities (high impressions, poor position).

    Args:
        hostname: Site hostname
        days: Number of days to analyze (default: 30)
        min_impressions: Minimum impressions threshold (default: 100)
        max_position: Maximum average position to consider (default: 20.0)

    Returns:
        DataFrame with improvement opportunities
    """
    db = HybridDataStore()
    await db.initialize()

    try:
        site = await db.get_site_by_hostname(hostname)
        if not site:
            raise ValueError(f"Site not found: {hostname}")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        query = """
        SELECT
            query,
            page,
            AVG(position) as avg_position,
            SUM(clicks) as total_clicks,
            SUM(impressions) as total_impressions,
            ROUND(AVG(ctr), 2) as avg_ctr,
            -- Potential clicks if position improves to 5
            ROUND(SUM(impressions) * 0.05) as potential_clicks_top5,
            ROUND(SUM(impressions) * 0.05) - SUM(clicks) as click_opportunity
        FROM gsc_performance_data
        WHERE site_id = ?
        AND date BETWEEN ? AND ?
        GROUP BY query, page
        HAVING total_impressions >= ?
        AND avg_position <= ?
        AND avg_position > 5  -- Already top 5 positions are not opportunities
        ORDER BY click_opportunity DESC
        LIMIT 100
        """

        if not db._sqlite_conn:
            raise RuntimeError("Database not initialized")

        async with db._sqlite_conn.execute(
            query,
            [site.id, start_date.isoformat(), end_date.isoformat(), min_impressions, max_position],
        ) as cursor:
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

        return pl.DataFrame(rows, schema=columns, orient="row")

    finally:
        await db.close()


# Convenience functions for common use cases
async def quick_keyword_check(hostname: str, keyword: str) -> dict[str, Any]:
    """Quick keyword performance check - returns summary dict."""
    df = await get_keyword_trends(hostname, keyword, days=7)
    if df.is_empty():
        return {"found": False, "message": f"No data found for keyword: {keyword}"}

    latest = df.row(0, named=True)
    total_clicks = df["total_clicks"].sum()
    avg_position = df["avg_position"].mean()

    return {
        "found": True,
        "keyword": keyword,
        "latest_position": latest["avg_position"],
        "total_clicks_7d": total_clicks,
        "avg_position_7d": round(avg_position, 1),
        "data_points": len(df),
    }


async def quick_site_overview(hostname: str) -> dict[str, Any]:
    """Quick site performance overview - returns summary dict."""
    df = await get_daily_summary(hostname, days=7)
    if df.is_empty():
        return {"found": False, "message": f"No data found for site: {hostname}"}

    total_clicks = df["total_clicks"].sum()
    total_impressions = df["total_impressions"].sum()
    avg_position = df["avg_position"].mean()

    return {
        "found": True,
        "hostname": hostname,
        "total_clicks_7d": total_clicks,
        "total_impressions_7d": total_impressions,
        "avg_position_7d": round(avg_position, 1),
        "avg_ctr_7d": round((total_clicks / total_impressions * 100), 2)
        if total_impressions > 0
        else 0,
        "days_with_data": len(df),
    }
