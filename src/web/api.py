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
    - Filter by specific keywords/queries (supporting spaces)
    - Filter by specific page URLs
    - Group results by 'query' or 'page'

    Example usage:
    - Get all query performance for site 1 in January 2024
    - Get specific keywords like "best hotels" and "台北美食"
    - Filter by specific pages like "/hotels" and "/restaurants"
    """
    # Validate site exists
    sites = site_service.get_all_sites()
    site_exists = any(site["id"] == request.site_id for site in sites)
    if not site_exists:
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
                site_id=request.site_id,
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
                site_id=request.site_id,
                start_date=request.start_date,
                end_date=request.end_date,
                group_by="page",
                filter_term=page,
            )
            all_data.extend(data)
    else:
        # Get all data without specific filtering
        all_data = analysis_service.get_performance_data_for_visualization(
            site_id=request.site_id,
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
        site_id=request.site_id,
        start_date=request.start_date,
        end_date=request.end_date,
        group_by=request.group_by,
        total_results=len(ranking_items),
        data=ranking_items,
    )
