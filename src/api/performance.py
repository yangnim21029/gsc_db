"""Performance data endpoints."""

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import Annotated

from litestar import Router, get, post
from litestar.params import Parameter
from litestar.response import Stream

from ..database.hybrid import HybridDataStore
from ..models import PageKeywordPerformanceRequest, PageKeywordPerformanceResponse


@post("/page-keyword-performance/", tags=["Performance"])
async def get_page_keyword_performance(
    db: HybridDataStore, data: PageKeywordPerformanceRequest
) -> PageKeywordPerformanceResponse:
    """
    Get combined page and keyword performance data.

    Shows which keywords drive traffic to each page with aggregated metrics.
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

    # Calculate date range
    date_range = None
    if data.days:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=data.days)
        date_range = (start_date, end_date)

    # Get performance data - convert dates to strings for database
    str_date_range = None
    if date_range:
        str_date_range = (date_range[0].isoformat(), date_range[1].isoformat())

    results = await db.get_page_keyword_performance(
        site_id=site_id,
        date_range=str_date_range,
        url_filter=data.query,
        limit=data.limit,  # Pass limit to database method
    )

    return PageKeywordPerformanceResponse(
        site_id=site_id,
        data=results["data"],
        total_pages=results["total_pages"],
        total_keywords=results["total_keywords"],
    )


@get("/page-keyword-performance/csv/", tags=["Performance"])
async def download_performance_csv(
    db: HybridDataStore,
    site_id: Annotated[int | None, Parameter(query="site_id")] = None,
    hostname: Annotated[str | None, Parameter(query="hostname")] = None,
    days: Annotated[int | None, Parameter(query="days")] = None,
    query_filter: Annotated[
        str | None, Parameter(query="query")
    ] = None,  # Fixed: renamed to avoid reserved keyword conflict
    max_results: Annotated[
        int | None,
        Parameter(query="max_results", description="Maximum number of results to return"),
    ] = None,
) -> Stream:
    """
    Download page-keyword performance data as CSV with streaming.

    Keywords are exported as pipe-separated values in the CSV.
    Uses DuckDB for efficient analytics on large datasets.
    """
    # Determine site_id
    if not site_id and hostname:
        site = await db.get_site_by_hostname(hostname)
        if not site:
            raise ValueError(f"Site not found for hostname: {hostname}")
        site_id = site.id

    if not site_id:
        raise ValueError("Either site_id or hostname must be provided")

    # Calculate date range
    date_range = None
    if days:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        date_range = (
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )

    # Create async generator for streaming
    async def stream_csv() -> AsyncGenerator[bytes, None]:
        async for line in db.get_page_keyword_performance_stream(
            site_id=site_id,
            date_range=date_range,
            url_filter=query_filter,
            limit=max_results,
        ):
            yield line.encode("utf-8")

    # Return streaming response
    return Stream(
        stream_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=page_keyword_performance_{site_id}_{datetime.now().strftime('%Y%m%d')}.csv"
        },
    )


performance_router = Router(
    path="/api/v1",
    route_handlers=[get_page_keyword_performance, download_performance_csv],
)
