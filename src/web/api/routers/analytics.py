"""
Analytics Router

API endpoints for data analysis and reporting.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.services.analysis_service import AnalysisService
from src.services.site_service import SiteService
from src.web import schemas

from ..dependencies import (
    get_analysis_service,
    get_site_service,
)

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.post("/ranking-data", response_model=schemas.RankingDataResponse)
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
    - Filter by specific keywords/queries (EXACT MATCH - supporting spaces)
    - Filter by specific page URLs
    - Group results by 'query' or 'page'
    - Choose between raw data or daily aggregated data

    ## Aggregation Modes
    - **raw** (default): Original GSC data, may have multiple entries per day for different devices/search types
    - **daily**: Aggregated data with one entry per query/page per day, positions rounded to integers

    ### Raw Mode Output
    Returns individual GSC records as-is from the database.

    ### Daily Mode Output
    For each unique date+query/page combination:
    - **clicks**: Sum of all clicks
    - **impressions**: Sum of all impressions
    - **ctr**: Average CTR weighted by impressions
    - **position**: Average position weighted by impressions (rounded to nearest integer)

    ## Hostname formats supported:
    - `example.com` - Domain only
    - `www.example.com` - With subdomain
    - `sc-domain:example.com` - GSC format
    - `https://example.com` - Full URL with protocol

    ## Default Limits
    - **raw mode**: Default 1000 results, max 10000
    - **daily mode**: Default 365 results, max 10000

    ## Example usage:
    - Get raw data: {"aggregation_mode": "raw", ...}
    - Get clean daily data: {"aggregation_mode": "daily", ...}
    - Filter by EXACT keywords: {"queries": ["男士 理髮", "男士理髮"]} - these are different queries!
    - Filter by specific pages like "/hotels" and "/restaurants"

    ## IMPORTANT: Query Matching Behavior
    The 'queries' parameter uses EXACT MATCH:
    - "男士 理髮" (with space) will ONLY match "男士 理髮"
    - "男士理髮" (no space) will ONLY match "男士理髮"
    - "是" will ONLY match the single character "是", NOT "什麼是" or "是不是"

    For PARTIAL MATCHING (finding queries containing keywords), use:
    GET /api/v1/sites/{site_id}/queries/search?search_term=理髮
    """
    # Validate that either site_id or hostname is provided
    if not request.site_id and not request.hostname:
        raise HTTPException(status_code=400, detail="Either site_id or hostname must be provided")

    # If hostname is provided, resolve it to site_id
    if request.hostname and not request.site_id:
        site = site_service.get_site_by_hostname(request.hostname)
        if not site:
            raise HTTPException(status_code=404, detail=f"Site not found: {request.hostname}")
        site_id = site["id"]
    else:
        site_id = request.site_id

    # Prepare data structure
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

        daily_aggregated: defaultdict[tuple[str, Any], dict[str, Any]] = defaultdict(
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

        # Convert to list format
        result_data = []
        for (date_str, term), metrics in daily_aggregated.items():
            # Calculate weighted averages
            avg_position = (
                round(sum(metrics["positions"]) / len(metrics["positions"]))
                if metrics["positions"]
                else None
            )
            avg_ctr = sum(metrics["ctrs"]) / len(metrics["ctrs"]) if metrics["ctrs"] else 0

            result_data.append(
                {
                    "date": date_str,
                    request.group_by: term,
                    "clicks": metrics["clicks"],
                    "impressions": metrics["impressions"],
                    "ctr": avg_ctr,
                    "position": avg_position,
                }
            )

        # Sort by date descending
        result_data.sort(key=lambda x: x["date"], reverse=True)

        # Apply limit
        if request.max_results:
            result_data = result_data[: request.max_results]

    else:  # raw mode
        # Return raw data with optional limit
        result_data = all_data
        if request.max_results:
            result_data = result_data[: request.max_results]

    # Prepare response metadata
    total_results = len(result_data)

    # Convert result_data to RankingDataItem objects
    ranking_items = []
    for item in result_data:
        ranking_items.append(
            schemas.RankingDataItem(
                date=item["date"],
                query=item.get("query"),
                page=item.get("page"),
                clicks=item["clicks"],
                impressions=item["impressions"],
                ctr=item["ctr"],
                position=item["position"],
            )
        )

    return schemas.RankingDataResponse(
        site_id=site_id,
        start_date=request.start_date,
        end_date=request.end_date,
        group_by=request.group_by,
        total_results=total_results,
        data=ranking_items,
    )
