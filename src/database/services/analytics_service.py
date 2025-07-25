"""Analytics service using DuckDB for high-performance queries."""

import asyncio
from pathlib import Path
from typing import Any

import polars as pl

from ...models import PerformanceMetrics, RankingDataItem
from ..base import AnalyticsService


class PerformanceAnalytics(AnalyticsService):
    """Service for performance analytics using DuckDB."""

    async def analyze_trends(self, site_id: int, days: int) -> pl.DataFrame:
        """Analyze performance trends using DuckDB window functions."""
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

        conn = self._ensure_connection()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: conn.execute(query).pl())

        return result

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
        """Get ranking data with flexible filtering and grouping using DuckDB."""
        conn = self._ensure_connection()

        # Build WHERE conditions
        conditions = [
            f"site_id = {site_id}",
            f"date BETWEEN '{date_range[0]}' AND '{date_range[1]}'",
        ]

        # Add query filters
        if queries:
            if exact_match:
                query_conditions = " OR ".join([f"query = '{q}'" for q in queries])
            else:
                query_conditions = " OR ".join([f"query LIKE '%{q}%'" for q in queries])
            conditions.append(f"({query_conditions})")

        # Add page filters
        if pages:
            if exact_match:
                page_conditions = " OR ".join([f"page = '{p}'" for p in pages])
            else:
                page_conditions = " OR ".join([f"page LIKE '%{p}%'" for p in pages])
            conditions.append(f"({page_conditions})")

        where_clause = " AND ".join(conditions)

        # Build GROUP BY clause
        group_by = group_by or ["query", "page"]
        group_by_clause = ", ".join(group_by)

        # Build SELECT clause based on grouping
        select_fields = []
        for field in group_by:
            select_fields.append(f"{field}")

        query = f"""
        WITH grouped_data AS (
            SELECT
                {group_by_clause},
                SUM(clicks) as clicks,
                SUM(impressions) as impressions,
                AVG(ctr) as ctr,
                SUM(clicks * position) / NULLIF(SUM(clicks), 0) as weighted_position
            FROM sqlite_db.gsc_performance_data
            WHERE {where_clause}
            GROUP BY {group_by_clause}
        ),
        ranked_data AS (
            SELECT
                *,
                ROW_NUMBER() OVER (ORDER BY clicks DESC) as rank_by_clicks,
                PERCENT_RANK() OVER (ORDER BY clicks) as percentile_clicks
            FROM grouped_data
        )
        SELECT * FROM ranked_data
        ORDER BY clicks DESC
        LIMIT {limit}
        """

        # Execute query
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, lambda: conn.execute(query).pl())

        # Format results
        data = []
        for row in df.to_dicts():
            weighted_pos = row.get("weighted_position", 0.0) or 0.0

            item = RankingDataItem(
                query=row.get("query"),
                page=row.get("page"),
                clicks=int(row["clicks"]),
                impressions=int(row["impressions"]),
                ctr=round(float(row["ctr"]), 4),
                position=round(weighted_pos, 2),
                rank_by_clicks=int(row.get("rank_by_clicks", 0)),
                percentile_clicks=float(row.get("percentile_clicks", 0.0)),
            )
            data.append(item)

        # Calculate aggregations
        total_clicks = int(df["clicks"].sum())
        total_impressions = int(df["impressions"].sum())
        position_mean = df["weighted_position"].mean() or 0.0

        aggregations = PerformanceMetrics(
            clicks=total_clicks,
            impressions=total_impressions,
            ctr=float(total_clicks / max(total_impressions, 1)),
            position=float(position_mean),
        )

        return {"data": data, "total": len(df), "aggregations": aggregations}

    async def export_to_parquet(self, site_id: int, output_path: Path) -> None:
        """Export site data to Parquet format for archival."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        query = f"""
        COPY (
            SELECT * FROM sqlite_db.gsc_performance_data
            WHERE site_id = {site_id}
        ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """

        conn = self._ensure_connection()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, conn.execute, query)
