"""
GSC-CLI's FastAPI Application

This module defines the API endpoints and connects them with the application's
service layer. It acts as the "storefront" for the data, providing a standard
HTTP interface for future AI Agents or Web UIs.
"""

import csv
import io
from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.containers import Container
from src.services.analysis_service import AnalysisService
from src.services.data_aggregation_service import DataAggregationService
from src.services.database import Database
from src.services.site_service import SiteService

from . import schemas

# Initialize the application container and FastAPI instance
container = Container()
app = FastAPI(
    title="GSC-CLI API",
    description="API for accessing and managing Google Search Console data.",
    version="0.1.0",
)


# Dependency provider functions for FastAPI
def get_site_service() -> SiteService:
    """Get SiteService instance from container"""
    return container.site_service()


def get_analysis_service() -> AnalysisService:
    """Get AnalysisService instance from container"""
    return container.analysis_service()


def get_data_aggregation_service() -> DataAggregationService:
    """Get DataAggregationService instance from container"""
    return container.data_aggregation_service()


def get_database() -> Database:
    """Get Database instance from container"""
    return container.database()


@app.get("/api/v1/sites/", response_model=List[schemas.Site], tags=["Sites"])
def list_sites(
    site_service: SiteService = Depends(get_site_service),
):
    """
    Retrieve a list of all configured active sites from the database.
    """
    # The list of dicts returned by site_service.get_all_sites
    # will be automatically converted by Pydantic into a list of Site schemas.
    sites = site_service.get_all_sites(active_only=True)
    return sites


@app.post("/api/v1/ranking-data/", response_model=schemas.RankingDataResponse, tags=["Analytics"])
def get_ranking_data(
    request: schemas.RankingDataRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    site_service: SiteService = Depends(get_site_service),
):
    """
    Get ranking data for specific site, time period, queries, and pages.

    This endpoint allows you to:
    - Query ranking data for a specific site within a date range
    - Identify site by either site_id or hostname
    - Filter by specific keywords/queries (supporting spaces)
    - Filter by specific page URLs
    - Group results by 'query' or 'page'
    - Choose between raw data or daily aggregated data

    ## Aggregation Modes
    - **raw** (default): Original GSC data, may have multiple entries per day for different devices/search types
    - **daily**: Aggregated data with one entry per query/page per day, positions rounded to integers

    ## Site Identification
    You can now use either `site_id` or `hostname` to identify the site:

    ### Using hostname with daily aggregation:
    ```json
    {
      "hostname": "hkg.hankyu-hanshin-dept.co.jp",
      "start_date": "2025-07-01",
      "end_date": "2025-07-31",
      "group_by": "query",
      "aggregation_mode": "daily",
      "max_results": 365
    }
    ```

    ### Supported hostname formats:
    - `example.com` - Plain domain name
    - `sc-domain:example.com` - GSC format
    - `https://example.com` - Full URL with protocol

    ## Default Limits
    - **raw mode**: Default 1000 results, max 10000
    - **daily mode**: Default 365 results, max 10000

    ## Example usage:
    - Get raw data: {"aggregation_mode": "raw", ...}
    - Get clean daily data: {"aggregation_mode": "daily", ...}
    - Filter by specific keywords like "best hotels" and "台北美食"
    - Filter by specific pages like "/hotels" and "/restaurants"
    """
    # Validate that either site_id or hostname is provided
    if not request.site_id and not request.hostname:
        raise HTTPException(status_code=400, detail="Either site_id or hostname must be provided")

    if request.site_id and request.hostname:
        raise HTTPException(
            status_code=400, detail="Only one of site_id or hostname should be provided"
        )

    # Resolve site_id from hostname if needed
    site_id = request.site_id
    if request.hostname:
        site = site_service.get_site_by_domain(request.hostname)
        if not site:
            raise HTTPException(
                status_code=404, detail=f"Site with hostname '{request.hostname}' not found"
            )
        site_id = site["id"]

    # Validate site exists (for site_id case)
    if request.site_id:
        site = site_service.get_site_by_id(request.site_id)
        if not site:
            raise HTTPException(status_code=404, detail=f"Site with ID {request.site_id} not found")

    # Validate group_by parameter
    if request.group_by not in ["query", "page"]:
        raise HTTPException(status_code=400, detail="group_by must be 'query' or 'page'")

    # Validate max_results parameter
    if request.max_results and (request.max_results < 1 or request.max_results > 10000):
        raise HTTPException(status_code=400, detail="max_results must be between 1 and 10000")

    all_data = []

    # If specific queries or pages are requested, we need to query them individually
    if request.queries and request.group_by == "query":
        # Query each specific keyword
        for query in request.queries:
            data = analysis_service.get_performance_data_for_visualization(
                site_id=site_id,
                start_date=request.start_date,
                end_date=request.end_date,
                group_by="query",
                filter_term=query,
            )
            all_data.extend(data)
    elif request.pages and request.group_by == "page":
        # Query each specific page
        for page in request.pages:
            data = analysis_service.get_performance_data_for_visualization(
                site_id=site_id,
                start_date=request.start_date,
                end_date=request.end_date,
                group_by="page",
                filter_term=page,
            )
            all_data.extend(data)
    else:
        # Get all data without specific filtering
        all_data = analysis_service.get_performance_data_for_visualization(
            site_id=site_id,
            start_date=request.start_date,
            end_date=request.end_date,
            group_by=request.group_by,
        )

    # Process data based on aggregation_mode
    if request.aggregation_mode == "daily":
        # Aggregate data by day (similar to daily-data endpoint)
        from collections import defaultdict

        daily_aggregated = defaultdict(
            lambda: {"clicks": 0, "impressions": 0, "positions": [], "ctrs": []}
        )

        # Group data by date and query/page
        for item in all_data:
            key = (item["date"], item.get(request.group_by))
            daily_aggregated[key]["clicks"] += item["clicks"] or 0
            daily_aggregated[key]["impressions"] += item["impressions"] or 0
            if item["position"]:
                daily_aggregated[key]["positions"].append(item["position"])
            if item["ctr"] is not None:
                daily_aggregated[key]["ctrs"].append(item["ctr"])

        # Convert aggregated data to list
        processed_data = []
        for (date, term), metrics in daily_aggregated.items():
            avg_position = (
                sum(metrics["positions"]) / len(metrics["positions"]) if metrics["positions"] else 0
            )
            avg_ctr = sum(metrics["ctrs"]) / len(metrics["ctrs"]) if metrics["ctrs"] else 0

            processed_data.append(
                {
                    "date": date,
                    request.group_by: term,
                    "clicks": metrics["clicks"],
                    "impressions": metrics["impressions"],
                    "ctr": avg_ctr,
                    "position": avg_position,
                }
            )

        # Sort by date and term
        processed_data.sort(key=lambda x: (x["date"], x.get(request.group_by) or ""))

        # Apply different default limits based on mode
        max_results = request.max_results or (365 if request.aggregation_mode == "daily" else 1000)
    else:
        # Raw mode - use original data
        processed_data = all_data
        max_results = request.max_results or 1000

    # Apply max_results limit
    limited_data = processed_data[:max_results]

    # Convert to response format
    ranking_items = []
    for item in limited_data:
        # Round position for daily mode
        position = item["position"] or 0.0
        if request.aggregation_mode == "daily" and position:
            position = round(position)

        ranking_item = schemas.RankingDataItem(
            date=item["date"],
            query=item.get("query") if request.group_by == "query" else None,
            page=item.get("page") if request.group_by == "page" else None,
            clicks=item["clicks"] or 0,
            impressions=item["impressions"] or 0,
            ctr=item["ctr"] or 0.0,
            position=float(position),
        )
        ranking_items.append(ranking_item)

    return schemas.RankingDataResponse(
        site_id=site_id,
        start_date=request.start_date,
        end_date=request.end_date,
        group_by=request.group_by,
        total_results=len(ranking_items),
        data=ranking_items,
    )


@app.post(
    "/api/v1/daily-data/",
    response_model=schemas.DailyDataResponse,
    tags=["Analytics"],
    deprecated=True,
)
def get_daily_data(
    request: schemas.DailyDataRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    site_service: SiteService = Depends(get_site_service),
):
    """
    **DEPRECATED**: Use `/api/v1/ranking-data/` with `aggregation_mode: "daily"` instead.

    Get daily data similar to /ranking-data/ but with cleaner aggregation.

    This endpoint returns the same granular data as /ranking-data/, but:
    - Each query/page has exactly one record per day (no device/search type duplicates)
    - Position values are rounded to integers for easier analysis
    - Data is pre-aggregated across all devices and search types

    ## Migration Guide
    Replace calls to this endpoint with `/api/v1/ranking-data/` and add `"aggregation_mode": "daily"`:

    ### Old way:
    ```json
    POST /api/v1/daily-data/
    {
      "site_id": 1,
      "start_date": "2025-01-01",
      "end_date": "2025-01-31",
      "group_by": "query"
    }
    ```

    ### New way:
    ```json
    POST /api/v1/ranking-data/
    {
      "site_id": 1,
      "start_date": "2025-01-01",
      "end_date": "2025-01-31",
      "group_by": "query",
      "aggregation_mode": "daily"
    }
    ```

    ## Limits
    - **Date Range**: Maximum 1000 days between start_date and end_date
    - **Max Results**: Default 365 records, Maximum 1000 records
    """
    # Validate that either site_id or hostname is provided
    if not request.site_id and not request.hostname:
        raise HTTPException(status_code=400, detail="Either site_id or hostname must be provided")

    if request.site_id and request.hostname:
        raise HTTPException(
            status_code=400, detail="Only one of site_id or hostname should be provided"
        )

    # Resolve site_id from hostname if needed
    site_id = request.site_id
    if request.hostname:
        site = site_service.get_site_by_domain(request.hostname)
        if not site:
            raise HTTPException(
                status_code=404, detail=f"Site with hostname '{request.hostname}' not found"
            )
        site_id = site["id"]

    # Validate site exists (for site_id case)
    if request.site_id:
        site = site_service.get_site_by_id(request.site_id)
        if not site:
            raise HTTPException(status_code=404, detail=f"Site with ID {request.site_id} not found")

    # Validate date range
    from datetime import datetime

    try:
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")

        if start_date > end_date:
            raise HTTPException(
                status_code=400, detail="start_date must be before or equal to end_date"
            )

        # Calculate number of days
        days_diff = (end_date - start_date).days + 1
        if days_diff > 1000:
            raise HTTPException(
                status_code=400,
                detail=f"Date range too large ({days_diff} days). Maximum allowed is 1000 days.",
            )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Validate max_results parameter
    if request.max_results and (request.max_results < 1 or request.max_results > 1000):
        raise HTTPException(status_code=400, detail="max_results must be between 1 and 1000")

    # First, let's understand that GSC data can have multiple rows per query/page/date
    # due to different devices (mobile/desktop/tablet) and search types
    # We need to aggregate these properly

    # Validate group_by parameter
    if request.group_by not in ["query", "page"]:
        raise HTTPException(status_code=400, detail="group_by must be 'query' or 'page'")

    # Get the raw data - note this is already grouped by the visualization method
    # which gives us one row per query/page/date combination
    group_by = request.group_by

    all_data = []

    # If specific queries or pages are requested, query them individually
    if request.queries:
        for query in request.queries:
            data = analysis_service.get_performance_data_for_visualization(
                site_id=site_id,
                start_date=request.start_date,
                end_date=request.end_date,
                group_by="query",
                filter_term=query,
            )
            all_data.extend(data)
    elif request.pages:
        for page in request.pages:
            data = analysis_service.get_performance_data_for_visualization(
                site_id=site_id,
                start_date=request.start_date,
                end_date=request.end_date,
                group_by="page",
                filter_term=page,
            )
            all_data.extend(data)
    else:
        # Get all data
        all_data = analysis_service.get_performance_data_for_visualization(
            site_id=site_id,
            start_date=request.start_date,
            end_date=request.end_date,
            group_by=group_by,
        )

    # The data is already aggregated by date/query or date/page
    # Just need to format it properly
    daily_items = []
    for item in all_data:
        # Round position to integer as requested
        position = round(item["position"]) if item["position"] else 0

        daily_item = schemas.DailyDataItem(
            date=item["date"],
            query=item.get("query") if group_by == "query" else None,
            page=item.get("page") if group_by == "page" else None,
            clicks=item["clicks"] or 0,
            impressions=item["impressions"] or 0,
            ctr=item["ctr"] or 0.0,
            position=float(position),  # Convert to float for schema
        )
        daily_items.append(daily_item)

    # Sort by date and query/page for consistent output
    daily_items.sort(key=lambda x: (x.date, x.query or x.page or ""))

    # Apply max_results limit
    max_results = request.max_results or 365
    if len(daily_items) > max_results:
        daily_items = daily_items[:max_results]

    return schemas.DailyDataResponse(
        site_id=site_id,
        start_date=request.start_date,
        end_date=request.end_date,
        group_by=request.group_by,
        total_results=len(daily_items),
        data=daily_items,
    )


@app.post(
    "/api/v1/ranking-data-hourly/", response_model=schemas.HourlyRankingResponse, tags=["Analytics"]
)
def get_hourly_ranking_data(
    request: schemas.HourlyRankingRequest,
    db: Database = Depends(get_database),
    site_service: SiteService = Depends(get_site_service),
):
    """
    Get hourly ranking data for specific site, time period, queries, and pages.

    This endpoint provides hourly granularity data for detailed analysis:
    - Hour-by-hour performance metrics
    - Useful for identifying peak traffic hours
    - Limited to recent dates (GSC provides hourly data for last few days only)

    ## Important Notes
    - Google Search Console typically provides hourly data only for the last 2-3 days
    - Older dates will return empty results
    - Use daily endpoints for historical data analysis

    ## Site Identification
    You can use either `site_id` or `hostname` to identify the site:

    ### Using hostname:
    ```json
    {
      "hostname": "hkg.hankyu-hanshin-dept.co.jp",
      "start_date": "2025-07-16",
      "end_date": "2025-07-17",
      "group_by": "query",
      "max_results": 1000
    }
    ```

    ### Supported hostname formats:
    - `example.com` - Plain domain name
    - `sc-domain:example.com` - GSC format
    - `https://example.com` - Full URL with protocol

    ## Response Format
    Returns one record per query/page per hour, showing hourly traffic patterns.

    ## Limits
    - **Date Range**: Recommended 1-3 days (hourly data is only available for recent dates)
    - **Max Results**: Default 1000 records, Maximum 10000 records
    """
    # Validate that either site_id or hostname is provided
    if not request.site_id and not request.hostname:
        raise HTTPException(status_code=400, detail="Either site_id or hostname must be provided")

    if request.site_id and request.hostname:
        raise HTTPException(
            status_code=400, detail="Only one of site_id or hostname should be provided"
        )

    # Resolve site_id from hostname if needed
    site_id = request.site_id
    if request.hostname:
        site = site_service.get_site_by_domain(request.hostname)
        if not site:
            raise HTTPException(
                status_code=404, detail=f"Site with hostname '{request.hostname}' not found"
            )
        site_id = site["id"]

    # Validate site exists (for site_id case)
    if request.site_id:
        site = site_service.get_site_by_id(request.site_id)
        if not site:
            raise HTTPException(status_code=404, detail=f"Site with ID {request.site_id} not found")

    # Validate date range
    from datetime import datetime

    try:
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")

        if start_date > end_date:
            raise HTTPException(
                status_code=400, detail="start_date must be before or equal to end_date"
            )

        # Warn if date range is too old (hourly data is only available for recent dates)
        days_diff = (datetime.now() - start_date).days
        if days_diff > 7:
            raise HTTPException(
                status_code=400,
                detail="Date range too old. Hourly data is typically only available for the last 2-3 days.",
            )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Validate group_by parameter
    if request.group_by not in ["query", "page"]:
        raise HTTPException(status_code=400, detail="group_by must be 'query' or 'page'")

    # Validate max_results parameter
    if request.max_results and (request.max_results < 1 or request.max_results > 10000):
        raise HTTPException(status_code=400, detail="max_results must be between 1 and 10000")

    # Get hourly data from database
    # Note: The database stores hourly data with site_id and keyword_id
    # We need to handle the query/page filtering appropriately

    # For now, we'll query all hourly data for the site and date range
    # then filter by queries/pages if specified
    hourly_data = []

    # Query hourly rankings from database
    # The get_hourly_rankings method expects keyword_id, but we can pass None to get all
    raw_hourly_data = db.get_hourly_rankings(
        site_id=site_id,
        keyword_id=None,  # Get all keywords
        start_date=request.start_date,
        end_date=request.end_date,
        hour=None,  # Get all hours
    )

    # Group and filter the data
    for row in raw_hourly_data:
        # Filter by queries if specified
        if request.queries and row["keyword"] not in request.queries:
            continue

        # Note: The hourly data table doesn't store page URLs directly
        # This would need to be enhanced if page filtering is required

        # Format datetime with hour
        datetime_str = f"{row['date']} {row['hour']:02d}:00"

        hourly_item = schemas.HourlyRankingItem(
            datetime=datetime_str,
            query=row["keyword"] if request.group_by == "query" else None,
            page=None,  # Hourly data doesn't include page info in current schema
            clicks=row["clicks"] or 0,
            impressions=row["impressions"] or 0,
            ctr=row["ctr"] or 0.0,
            position=row["avg_position"] or 0.0,
        )
        hourly_data.append(hourly_item)

    # Sort by datetime and query/page
    hourly_data.sort(key=lambda x: (x.datetime, x.query or ""))

    # Apply max_results limit
    max_results = request.max_results or 1000
    if len(hourly_data) > max_results:
        hourly_data = hourly_data[:max_results]

    return schemas.HourlyRankingResponse(
        site_id=site_id,
        start_date=request.start_date,
        end_date=request.end_date,
        group_by=request.group_by,
        total_results=len(hourly_data),
        data=hourly_data,
    )


@app.post(
    "/api/v1/page-keyword-performance/",
    response_model=schemas.PageKeywordPerformanceResponse,
    tags=["Analytics"],
)
def get_page_keyword_performance(
    request: schemas.PageKeywordPerformanceRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    site_service: SiteService = Depends(get_site_service),
):
    """
    Get page performance data with aggregated keywords for each URL.

    This endpoint provides a comprehensive view of page performance including:
    - Total clicks and impressions per URL
    - All keywords that drive traffic to each URL
    - Keyword count for each URL
    - Results sorted by total clicks (highest performing pages first)

    ## Site Identification
    You can use either `site_id` or `hostname` to identify the site:

    ### Using hostname:
    ```json
    {
      "hostname": "hkg.hankyu-hanshin-dept.co.jp",
      "days": 30,
      "max_results": 100
    }
    ```

    ### Supported hostname formats:
    - `example.com` - Plain domain name
    - `sc-domain:example.com` - GSC format
    - `https://example.com` - Full URL with protocol

    ## Response Format
    Returns one record per URL with:
    - Aggregated performance metrics (clicks, impressions, CTR, position)
    - List of all keywords that brought traffic to that URL
    - Total keyword count

    ## Use Cases
    - Identify top performing pages and their driving keywords
    - Analyze keyword diversity for each page
    - Find pages with high impressions but low clicks
    - Content optimization based on keyword-page relationships

    ## Limits
    - **Max Results**: Default 1000 records, Maximum 10000 records
    - **Keywords per URL**: Limited to first 50 keywords to avoid oversized responses
    """
    # Validate that either site_id or hostname is provided
    if not request.site_id and not request.hostname:
        raise HTTPException(status_code=400, detail="Either site_id or hostname must be provided")

    if request.site_id and request.hostname:
        raise HTTPException(
            status_code=400, detail="Only one of site_id or hostname should be provided"
        )

    # Resolve site_id from hostname if needed
    site_id = request.site_id
    if request.hostname:
        site = site_service.get_site_by_domain(request.hostname)
        if not site:
            raise HTTPException(
                status_code=404, detail=f"Site with hostname '{request.hostname}' not found"
            )
        site_id = site["id"]

    # Validate site exists (for site_id case)
    if request.site_id:
        site = site_service.get_site_by_id(request.site_id)
        if not site:
            raise HTTPException(status_code=404, detail=f"Site with ID {request.site_id} not found")

    # Validate max_results parameter
    if request.max_results and (request.max_results < 1 or request.max_results > 10000):
        raise HTTPException(status_code=400, detail="max_results must be between 1 and 10000")

    # Get page keyword performance data
    performance_data = analysis_service.get_page_keyword_performance(
        site_id=site_id, days=request.days, max_results=request.max_results or 1000
    )

    # Convert to response format
    performance_items = []
    for item in performance_data:
        performance_item = schemas.PageKeywordPerformanceItem(
            url=item["url"],
            total_clicks=item["total_clicks"],
            total_impressions=item["total_impressions"],
            avg_ctr=item["avg_ctr"],
            avg_position=item["avg_position"],
            keywords=item["keywords"],
            keyword_count=item["keyword_count"],
        )
        performance_items.append(performance_item)

    # Determine time range description
    if request.days:
        time_range = f"Last {request.days} days"
    else:
        time_range = "All time"

    return schemas.PageKeywordPerformanceResponse(
        site_id=site_id,
        time_range=time_range,
        total_results=len(performance_items),
        data=performance_items,
    )


@app.get(
    "/api/v1/page-keyword-performance/csv/",
    tags=["Analytics"],
    response_class=StreamingResponse,
)
def download_page_keyword_performance_csv(
    site_id: int = Query(None, description="Site ID to query"),
    hostname: str = Query(None, description="Site hostname"),
    days: int = Query(None, description="Number of days to look back from today"),
    max_results: int = Query(5000, description="Maximum number of results", le=10000),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    site_service: SiteService = Depends(get_site_service),
):
    """
    Download page keyword performance data as CSV file.

    This endpoint provides the same data as `/api/v1/page-keyword-performance/`
    but returns it as a downloadable CSV file with one row per URL.

    ## Parameters
    - **site_id** or **hostname**: Site identification (one required)
    - **days**: Number of days to look back (optional, default: all time)
    - **max_results**: Maximum results (default: 5000, max: 10000)

    ## Examples
    - `/api/v1/page-keyword-performance/csv/?site_id=14&days=30`
    - `/api/v1/page-keyword-performance/csv/?hostname=example.com&max_results=1000`

    ## CSV Format
    Each row contains:
    - URL
    - Total clicks
    - Total impressions
    - Average CTR (%)
    - Average position
    - Keyword count
    - Keywords list (pipe-separated)

    ## Note
    For very large datasets, consider using the command-line export script.
    """
    # Validate that either site_id or hostname is provided
    if not site_id and not hostname:
        raise HTTPException(status_code=400, detail="Either site_id or hostname must be provided")

    if site_id and hostname:
        raise HTTPException(
            status_code=400, detail="Only one of site_id or hostname should be provided"
        )

    # Resolve site_id from hostname if needed
    if hostname:
        site = site_service.get_site_by_domain(hostname)
        if not site:
            raise HTTPException(
                status_code=404, detail=f"Site with hostname '{hostname}' not found"
            )
        site_id = site["id"]
    else:
        # Validate site exists
        site = site_service.get_site_by_id(site_id)
        if not site:
            raise HTTPException(status_code=404, detail=f"Site with ID {site_id} not found")

    # Get page keyword performance data
    performance_data = analysis_service.get_page_keyword_performance(
        site_id=site_id, days=days, max_results=max_results
    )

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    site_name = site.get("name", f"site_{site_id}").replace(" ", "_").replace("/", "_")
    filename = f"page_keywords_{site_name}_{timestamp}.csv"

    # Generate CSV content
    content = generate_summary_csv(performance_data)

    # Return streaming response
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8-sig",
        },
    )


def generate_summary_csv(data: List[dict]) -> str:
    """Generate summary CSV content (one row per URL)"""
    output = io.StringIO()
    # Use utf-8-sig BOM for Excel compatibility
    output.write("\ufeff")  # BOM

    writer = csv.writer(output)
    writer.writerow(
        ["網址", "總點擊數", "總曝光數", "平均點擊率(%)", "平均排名", "關鍵字數量", "關鍵字列表"]
    )

    for item in data:
        writer.writerow(
            [
                item["url"],
                item["total_clicks"],
                item["total_impressions"],
                f"{item['avg_ctr']:.2f}",
                f"{item['avg_position']:.1f}",
                item["keyword_count"],
                " | ".join(item["keywords"]),
            ]
        )

    return output.getvalue()
