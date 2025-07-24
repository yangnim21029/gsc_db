"""Performance data endpoints."""

from datetime import datetime, timedelta
from typing import Annotated, Optional

from litestar import Router, Response, get, post
from litestar.datastructures import Headers
from litestar.params import Parameter

from ..database.hybrid import HybridDataStore
from ..models import PageKeywordPerformanceRequest, PageKeywordPerformanceResponse


@post("/page-keyword-performance/", tags=["Performance"])
async def get_page_keyword_performance(
    db: HybridDataStore,
    data: PageKeywordPerformanceRequest
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
    
    # Get performance data
    results = await db.get_page_keyword_performance(
        site_id=site_id,
        date_range=date_range,
        url_filter=data.query
    )
    
    return PageKeywordPerformanceResponse(
        site_id=site_id,
        data=results["data"],
        total_pages=results["total_pages"],
        total_keywords=results["total_keywords"]
    )


@get("/page-keyword-performance/csv/", tags=["Performance"])
async def download_performance_csv(
    db: HybridDataStore,
    site_id: Annotated[Optional[int], Parameter(query="site_id")] = None,
    hostname: Annotated[Optional[str], Parameter(query="hostname")] = None,
    days: Annotated[Optional[int], Parameter(query="days")] = None,
    query_filter: Annotated[Optional[str], Parameter(query="query")] = None  # Fixed: renamed to avoid reserved keyword conflict
) -> Response:
    """
    Download page-keyword performance data as CSV.
    
    Keywords are exported as pipe-separated values in the CSV.
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
        date_range = (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))  # Fixed: convert dates to strings
    
    # Get performance data
    results = await db.get_page_keyword_performance(
        site_id=site_id,
        date_range=date_range,
        url_filter=query_filter  # Fixed: use renamed parameter
    )
    
    # Convert to CSV
    csv_content = await db.export_performance_csv(results["data"])
    
    # Return CSV response
    headers = Headers({
        "Content-Type": "text/csv",
        "Content-Disposition": f"attachment; filename=page_keyword_performance_{site_id}.csv"
    })
    
    return Response(content=csv_content, headers=headers)


performance_router = Router(
    path="/api/v1",
    route_handlers=[get_page_keyword_performance, download_performance_csv],
)