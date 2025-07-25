"""Streaming service for efficient data export."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from ..base import AnalyticsService, Repository


class StreamingService:
    """Service for streaming large datasets efficiently."""

    def __init__(self, repository: Repository, analytics: AnalyticsService | None = None):
        self.repository = repository
        self.analytics = analytics

    async def stream_page_keyword_performance(
        self,
        site_id: int,
        date_range: tuple[str, str] | None = None,
        url_filter: str | None = None,
        limit: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream page-keyword performance data."""
        if self.analytics and self.analytics.enable_duckdb:
            async for line in self._stream_with_duckdb(site_id, date_range, url_filter, limit):
                yield line
        else:
            async for line in self._stream_with_sqlite(site_id, date_range, url_filter, limit):
                yield line

    async def _stream_with_duckdb(
        self,
        site_id: int,
        date_range: tuple[str, str] | None = None,
        url_filter: str | None = None,
        limit: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream using DuckDB for efficient analytics."""
        # Build WHERE conditions
        conditions = [f"site_id = {site_id}"]
        if date_range:
            conditions.append(f"date BETWEEN '{date_range[0]}' AND '{date_range[1]}'")
        if url_filter:
            conditions.append(f"page LIKE '%{url_filter}%'")
        where_clause = " AND ".join(conditions)

        # DuckDB query with window functions
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

        # Execute in thread pool
        loop = asyncio.get_event_loop()
        conn = self.analytics._ensure_connection()

        def execute_query() -> Any:
            return conn.execute(query)

        result = await loop.run_in_executor(None, execute_query)

        # Yield header
        yield "url,total_clicks,total_impressions,avg_ctr,avg_position,keywords,keyword_count\n"

        # Stream results
        while True:
            row = await loop.run_in_executor(None, result.fetchone)
            if not row:
                break

            line = f'"{row[0]}",{row[1]},{row[2]},{row[3]:.4f},{row[4]:.2f},"{row[5]}",{row[6]}\n'
            yield line

    async def _stream_with_sqlite(
        self,
        site_id: int,
        date_range: tuple[str, str] | None = None,
        url_filter: str | None = None,
        limit: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """Fallback SQLite streaming implementation."""
        where_conditions = ["site_id = ?"]
        params: list[Any] = [site_id]

        if date_range:
            where_conditions.append("date BETWEEN ? AND ?")
            params.extend(date_range)

        if url_filter:
            where_conditions.append("page LIKE ?")
            params.append(f"%{url_filter}%")

        where_clause = " AND ".join(where_conditions)

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

        async with self.repository._lock:
            conn = self.repository._ensure_connection()
            cursor = await conn.execute(query, params)

            yield "url,total_clicks,total_impressions,avg_ctr,avg_position,keywords,keyword_count\n"

            async for row in cursor:
                url = row[0]

                # Fetch top 10 keywords
                keyword_query = """
                    SELECT query
                    FROM gsc_performance_data
                    WHERE site_id = ? AND page = ?
                    GROUP BY query
                    ORDER BY SUM(clicks) DESC
                    LIMIT 10
                """

                keyword_cursor = await conn.execute(keyword_query, (site_id, url))
                keywords = [kw[0] async for kw in keyword_cursor]
                keywords_str = "|".join(keywords) if keywords else ""

                line = f'"{url}",{row[1]},{row[2]},{row[3]:.4f},{row[4]:.2f},"{keywords_str}",{row[5]}\n'
                yield line
