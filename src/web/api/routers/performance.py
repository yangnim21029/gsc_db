"""
Performance Router

API endpoints for performance data and metrics.
"""

import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.services.analysis_service import AnalysisService
from src.services.data_aggregation_service import DataAggregationService
from src.services.site_service import SiteService
from src.web import schemas

from ..dependencies import (
    get_analysis_service,
    get_data_aggregation_service,
    get_site_service,
)

router = APIRouter(tags=["Performance"])


@router.get("/api/v1/sites/{site_id}/performance")
async def get_site_performance(
    site_id: int,
    aggregation_service: DataAggregationService = Depends(get_data_aggregation_service),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    aggregation_mode: str = Query(
        "daily", description="Aggregation mode: daily, weekly, or monthly"
    ),
    dimension: str = Query("query", description="Dimension to aggregate by: query or page"),
    limit: int = Query(100, description="Number of results to return"),
):
    """Get aggregated performance data for a site"""
    try:
        data = aggregation_service.get_aggregated_data(
            site_id=site_id,
            start_date=start_date,
            end_date=end_date,
            aggregation_mode=aggregation_mode,
            dimension=dimension,
            limit=limit,
        )
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/sites/{site_id}/ranking-data")
async def get_ranking_data(
    site_id: int,
    aggregation_service: DataAggregationService = Depends(get_data_aggregation_service),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    aggregation_mode: str = Query(
        "daily", description="Aggregation mode: daily, weekly, or monthly"
    ),
    url: str = Query(None, description="Filter by specific URL/page"),
    limit: int = Query(100, description="Maximum number of results to return"),
    export_format: str = Query(None, description="Export format: csv"),
):
    """Get keyword ranking data with filtering and export options"""
    try:
        # Get the aggregated data
        data = aggregation_service.get_aggregated_data(
            site_id=site_id,
            start_date=start_date,
            end_date=end_date,
            aggregation_mode=aggregation_mode,
            dimension="query",
            limit=limit,
            url=url,
        )

        # If CSV export is requested
        if export_format == "csv":
            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

            output.seek(0)
            filename = f"ranking_data_{site_id}_{start_date}_to_{end_date}.csv"
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        return {"total": len(data), "results": data}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/sites/{site_id}/page-keyword-performance")
async def get_page_keyword_performance(
    site_id: int,
    aggregation_service: DataAggregationService = Depends(get_data_aggregation_service),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    url: str = Query(None, description="Filter by specific URL/page"),
    export_format: str = Query(None, description="Export format: csv"),
):
    """
    Get page and keyword performance data together.
    Returns a list of page-keyword combinations with their performance metrics.
    """
    try:
        # Get the page keyword performance data
        data = aggregation_service.get_page_keyword_performance(
            site_id=site_id,
            start_date=start_date,
            end_date=end_date,
            url=url,
        )

        # If CSV export is requested
        if export_format == "csv":
            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

            output.seek(0)
            filename = f"page_keyword_performance_{site_id}_{start_date}_to_{end_date}.csv"
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        return {"total": len(data), "results": data}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/api/v1/page-keyword-performance/", response_model=schemas.PageKeywordPerformanceResponse
)
def get_page_keyword_performance_post(
    request: schemas.PageKeywordPerformanceRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    site_service: SiteService = Depends(get_site_service),
):
    """
    Get page and keyword performance data for a site.

    This endpoint combines page-level and keyword-level metrics,
    showing which keywords drive traffic to each page.

    ## Request Parameters:
    - **site_id** or **hostname**: Identify the site (one is required)
    - **days**: Number of days to look back (optional, defaults to all data)
    - **query**: URL query filter (optional, filters pages containing this text)

    ## Response Format:
    Each row contains:
    - Page URL
    - Total clicks and impressions for the page
    - Average CTR and position
    - List of keywords driving traffic to that page
    - Keyword count

    ## Hostname formats supported:
    - `example.com`
    - `www.example.com`
    - `sc-domain:example.com`
    - `https://example.com`
    """
    # Validate that either site_id or hostname is provided
    if not request.site_id and not request.hostname:
        raise HTTPException(status_code=400, detail="Either site_id or hostname must be provided")

    # If hostname is provided, resolve it to site_id
    if request.hostname and not request.site_id:
        site = site_service.get_site_by_host(request.hostname)
        if not site:
            raise HTTPException(status_code=404, detail=f"Site not found: {request.hostname}")
        site_id = site["id"]
    else:
        site_id = request.site_id

    # Calculate date range if days is specified
    if request.days:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=request.days)
        performance_data = analysis_service.get_page_keyword_performance_with_date_range(
            site_id=site_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
    else:
        # Get all-time data
        performance_data = analysis_service.get_page_keyword_performance(
            site_id=site_id,
        )

    # Apply query filter if specified
    if request.query:
        # Use substring matching to filter pages
        performance_data = [item for item in performance_data if request.query in item["url"]]

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


@router.get("/api/v1/page-keyword-performance/csv/", response_class=StreamingResponse)
def download_page_keyword_performance_csv(
    site_id: int = Query(None, description="Site ID to query"),
    hostname: str = Query(None, description="Site hostname"),
    days: int = Query(None, description="Number of days to look back from today"),
    query: str = Query(None, description="URL query filter"),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    site_service: SiteService = Depends(get_site_service),
):
    """
    Download page-keyword performance data as CSV.

    Returns a CSV file with columns:
    - url: Page URL
    - total_clicks: Total clicks for the page
    - total_impressions: Total impressions
    - avg_ctr: Average click-through rate
    - avg_position: Average position
    - keywords: Pipe-separated list of keywords
    - keyword_count: Number of unique keywords
    """
    # Use the same logic as the JSON endpoint
    request = schemas.PageKeywordPerformanceRequest(
        site_id=site_id,
        hostname=hostname,
        days=days,
        query=query,
    )

    # Get the data using the same method
    response_data = get_page_keyword_performance_post(
        request=request,
        analysis_service=analysis_service,
        site_service=site_service,
    )

    # Convert to CSV format
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "url",
            "total_clicks",
            "total_impressions",
            "avg_ctr",
            "avg_position",
            "keywords",
            "keyword_count",
        ]
    )

    # Write data rows
    for item in response_data.data:
        writer.writerow(
            [
                item.url,
                item.total_clicks,
                item.total_impressions,
                f"{item.avg_ctr:.4f}",
                f"{item.avg_position:.1f}",
                "|".join(item.keywords),  # Join keywords with pipe separator
                item.keyword_count,
            ]
        )

    # Create filename
    site_info = site_service.db.get_site_by_id(response_data.site_id)
    site_name = site_info["name"] if site_info else f"site_{response_data.site_id}"
    safe_site_name = "".join(c for c in site_name if c.isalnum() or c in ("-", "_")).rstrip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"page_keyword_performance_{safe_site_name}_{timestamp}.csv"

    # Return as streaming response
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
