"""
GSC-CLI's FastAPI Application

This module defines the API endpoints and connects them with the application's
service layer. It acts as the "storefront" for the data, providing a standard
HTTP interface for future AI Agents or Web UIs.
"""

from typing import List

from fastapi import Depends, FastAPI, HTTPException

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

    ## Site Identification
    You can now use either `site_id` or `hostname` to identify the site:

    ### Using hostname:
    ```json
    {
      "hostname": "hkg.hankyu-hanshin-dept.co.jp",
      "start_date": "2025-07-01",
      "end_date": "2025-07-31",
      "group_by": "query",
      "max_results": 1000
    }
    ```

    ### Supported hostname formats:
    - `example.com` - Plain domain name
    - `sc-domain:example.com` - GSC format
    - `https://example.com` - Full URL with protocol

    ## Example usage:
    - Get all query performance for site 1 in January 2024
    - Get data using hostname: {"hostname": "example.com", ...}
    - Get specific keywords like "best hotels" and "台北美食"
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

    # Apply max_results limit
    max_results = request.max_results or 1000
    limited_data = all_data[:max_results]

    # Convert to response format
    ranking_items = []
    for item in limited_data:
        ranking_item = schemas.RankingDataItem(
            date=item["date"],
            query=item.get("query") if request.group_by == "query" else None,
            page=item.get("page") if request.group_by == "page" else None,
            clicks=item["clicks"] or 0,
            impressions=item["impressions"] or 0,
            ctr=item["ctr"] or 0.0,
            position=item["position"] or 0.0,
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


@app.post("/api/v1/daily-data/", response_model=schemas.DailyDataResponse, tags=["Analytics"])
def get_daily_data(
    request: schemas.DailyDataRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    site_service: SiteService = Depends(get_site_service),
):
    """
    Get daily data similar to /ranking-data/ but with cleaner aggregation.

    This endpoint returns the same granular data as /ranking-data/, but:
    - Each query/page has exactly one record per day (no device/search type duplicates)
    - Position values are rounded to integers for easier analysis
    - Data is pre-aggregated across all devices and search types

    ## Key Differences from /ranking-data/
    - **Aggregation**: Multiple device/search type entries are combined into daily totals
    - **Position**: Averaged and rounded to nearest integer
    - **Performance**: Faster for large date ranges due to pre-aggregation

    ## Site Identification
    You can use either `site_id` or `hostname` to identify the site:

    ### Using hostname:
    ```json
    {
      "hostname": "hkg.hankyu-hanshin-dept.co.jp",
      "start_date": "2025-07-01",
      "end_date": "2025-07-31",
      "group_by": "query",
      "max_results": 1000
    }
    ```

    ### Supported hostname formats:
    - `example.com` - Plain domain name
    - `sc-domain:example.com` - GSC format
    - `https://example.com` - Full URL with protocol

    ## Response Format
    Returns one record per query/page per day, making it cleaner than raw GSC data
    which can have multiple entries due to different devices and search types.

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
