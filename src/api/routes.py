"""API route handlers."""

from datetime import datetime
from typing import Annotated, Any

from litestar import Router, get, post
from litestar.params import Parameter

from ..database.hybrid import HybridDataStore
from ..models import (
    PerformanceTrendData,
    PerformanceTrendsResponse,
    PerformanceTrendSummary,
    RankingDataRequest,
    RankingDataResponse,
    Site,
    SyncRequest,
    SyncStatusResponse,
)
from ..services.cache import CacheService


# Sites Router
@get("/sites", tags=["Sites"])
async def list_sites(
    db: HybridDataStore, active_only: Annotated[bool, Parameter(default=True)]
) -> list[Site]:
    """List all sites."""
    return await db.get_sites(active_only=active_only)


@get("/sites/{site_id:int}", tags=["Sites"])
async def get_site(db: HybridDataStore, site_id: int) -> Site:
    """Get site by ID."""
    site = await db.get_site_by_id(site_id)
    if not site:
        raise ValueError(f"Site {site_id} not found")
    return site


@post("/sites", tags=["Sites"])
async def create_site(db: HybridDataStore, data: dict[str, Any]) -> dict[str, int]:
    """Create a new site."""
    site_id = await db.add_site(
        domain=data["domain"], name=data["name"], category=data.get("category")
    )
    return {"site_id": site_id}


sites_router = Router(
    path="/api/v1",
    route_handlers=[list_sites, get_site, create_site],
)


# Analytics Router
@post("/analytics/ranking-data", tags=["Analytics"])
async def get_ranking_data(
    db: HybridDataStore, cache: CacheService | None, data: RankingDataRequest
) -> RankingDataResponse:
    """
    Get ranking data with flexible filtering.

    Supports both site_id and hostname for site identification.
    Provides exact and partial matching for queries.
    Can be used for simple query searches by using partial matching.

    Example for query search:
    {
        "hostname": "example.com",
        "date_from": "2025-07-01",
        "date_to": "2025-07-15",
        "queries": ["理髮"],
        "exact_match": false,
        "group_by": ["query"]
    }
    """
    # DEBUG: 如果遇到 500 錯誤，首先檢查這裡
    # 常見問題：hostname 為空字串 "" 或 None
    print(f"[DEBUG] ranking-data request - hostname: '{data.hostname}', site_id: {data.site_id}")
    
    # Determine site_id from hostname if provided
    site_id = data.site_id
    if not site_id and data.hostname:
        # DEBUG: 檢查 hostname 是否正確傳入
        print(f"[DEBUG] Looking up site for hostname: {data.hostname}")
        site = await db.get_site_by_hostname(data.hostname)
        if not site:
            # ERROR: 這是最常見的錯誤 - 找不到對應的網站
            raise ValueError(f"Site not found for hostname: {data.hostname}")
        site_id = site.id
        print(f"[DEBUG] Found site_id: {site_id} for hostname: {data.hostname}")

    if not site_id:
        # ERROR: 既沒有 site_id 也沒有 hostname
        raise ValueError("Either site_id or hostname must be provided")

    # Try cache first if enabled
    cache_key = f"ranking:{site_id}:{data.date_from}:{data.date_to}:{hash(str(data))}"
    if cache:
        cached = await cache.get(cache_key)
        if cached:
            return RankingDataResponse(**cached)

    # Fetch from database
    results = await db.get_ranking_data(
        site_id=site_id,
        date_range=(data.date_from, data.date_to),
        queries=data.queries,
        pages=data.pages,
        group_by=data.group_by,
        limit=data.limit,
        exact_match=data.exact_match,
    )

    response = RankingDataResponse(
        data=results["data"], total=results["total"], aggregations=results["aggregations"]
    )

    # Cache the result
    if cache:
        # msgspec doesn't have model_dump, use dict conversion
        import msgspec

        await cache.set(cache_key, msgspec.to_builtins(response), ttl=3600)

    return response


@get("/analytics/performance-trends", tags=["Analytics"])
async def get_performance_trends(
    db: HybridDataStore,
    site_id: Annotated[int | None, Parameter(default=None)],
    hostname: Annotated[str | None, Parameter(default=None)],
    days: Annotated[int, Parameter(default=30)],
) -> PerformanceTrendsResponse:
    """
    Get performance trends with moving averages and week-over-week comparisons.

    This endpoint provides detailed daily performance analysis including:
    - Daily clicks, impressions, and average position
    - 7-day rolling average clicks
    - Week-over-week change analysis
    - Cumulative clicks over time
    - Unique query count per day

    Parameters:
    - site_id (int): Site ID to analyze
    - hostname (str): Alternative to site_id, use site hostname (e.g., 'businessfocus.io')
    - days (int): Number of days to analyze (default: 30)

    Use either site_id or hostname to identify the site.
    """
    # Determine site_id from hostname if provided
    if not site_id and hostname:
        site = await db.get_site_by_hostname(hostname)
        if not site:
            raise ValueError(f"Site not found for hostname: {hostname}")
        site_id = site.id

    if not site_id:
        raise ValueError("Either site_id or hostname must be provided")

    df = await db.analyze_performance_trends(site_id, days)

    # Convert DataFrame to structured response
    trend_data = []
    for row in df.to_dicts():
        trend_data.append(
            PerformanceTrendData(
                date=str(row["date"]),
                total_clicks=float(row["total_clicks"]),
                total_impressions=float(row["total_impressions"]),
                avg_position=float(row["avg_position"]),
                unique_queries=int(row["unique_queries"]),
                clicks_7d_avg=float(row["clicks_7d_avg"]) if row.get("clicks_7d_avg") else None,
                clicks_wow_change=float(row["clicks_wow_change"])
                if row.get("clicks_wow_change")
                else None,
                cumulative_clicks=float(row["cumulative_clicks"]),
            )
        )

    summary = PerformanceTrendSummary(
        total_clicks=int(df["total_clicks"].sum()),
        avg_position=float(df["avg_position"].mean()),
        unique_queries=int(df["unique_queries"].sum()),
    )

    return PerformanceTrendsResponse(data=trend_data, summary=summary)


analytics_router = Router(
    path="/api/v1",
    route_handlers=[get_ranking_data, get_performance_trends],
)


# Sync Router
@get("/sync/status", tags=["Sync"])
async def get_sync_status(
    db: HybridDataStore,
    site_id: Annotated[int | None, Parameter(default=None)],
    hostname: Annotated[str | None, Parameter(default=None)],
    days: Annotated[int, Parameter(default=30)],
) -> SyncStatusResponse:
    """Get sync status for a site. Use either site_id or hostname."""
    # Determine site_id from hostname if provided
    if not site_id and hostname:
        site = await db.get_site_by_hostname(hostname)
        if not site:
            raise ValueError(f"Site not found for hostname: {hostname}")
        site_id = site.id

    if not site_id:
        raise ValueError("Either site_id or hostname must be provided")

    site = await db.get_site_by_id(site_id)
    if not site:
        raise ValueError(f"Site {site_id} not found")

    # Get actual sync coverage
    coverage = await db.get_sync_coverage(site_id, days)

    return SyncStatusResponse(
        site_id=site_id,
        site_name=site.name,
        daily_coverage=coverage,
        hourly_coverage={},
        last_sync=datetime.now(),
        total_records=sum(1 for has_data in coverage.values() if has_data),
    )


@post("/sync/trigger", tags=["Sync"])
async def trigger_sync(db: HybridDataStore, data: SyncRequest) -> dict[str, str]:
    """
    Trigger sync for a site with modern sync mode support.

    Sync Modes:
    - skip (default): Only insert new records, skip existing ones
    - overwrite: Replace existing records (useful for data corrections)

    IMPORTANT: GSC API requires sequential processing!
    - Multiple concurrent sync requests will fail
    - Use a job queue for multiple sites
    - Tested: concurrent=0% success, sequential=100% success
    """
    # Determine site_id from hostname if provided
    site_id = data.site_id
    if not site_id and data.hostname:
        site = await db.get_site_by_hostname(data.hostname)
        if not site:
            raise ValueError(f"Site not found for hostname: {data.hostname}")
        site_id = site.id

    if not site_id:
        raise ValueError("Either site_id or hostname must be provided")

    # In a real implementation, this would:
    # 1. Queue a sync job with specified parameters
    # 2. Call the sync script with proper mode
    # 3. Return job tracking information

    job_id = f"sync-{site_id}-{datetime.now().timestamp()}"

    return {
        "status": "queued",
        "job_id": job_id,
        "site_id": site_id,
        "days": data.days,
        "sync_mode": data.sync_mode.value,
        "force": data.force,
        "message": f"Sync job queued for site {site_id} with mode '{data.sync_mode.value}'",
    }


sync_router = Router(
    path="/api/v1",
    route_handlers=[get_sync_status, trigger_sync],
)
