"""
Multi-Process FastAPI Application

This is an alternative API configuration that supports multi-process deployments
such as Gunicorn with multiple workers or uvicorn with multiple processes.
"""

import csv
import io
import os
from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

# 使用多程序容器
from src.containers_multiprocess import MultiProcessContainer as Container
from src.services.analysis_service import AnalysisService
from src.services.data_aggregation_service import DataAggregationService
from src.services.database import Database
from src.services.site_service import SiteService

from . import schemas

# Initialize the application container and FastAPI instance
container = Container()
app = FastAPI(
    title="GSC-CLI API (Multi-Process)",
    description="Multi-process ready API for accessing and managing Google Search Console data.",
    version="0.1.0",
)


# Add startup event to log process information
@app.on_event("startup")
async def startup_event():
    """Log startup information including process ID"""
    print(f"FastAPI starting in process {os.getpid()}")
    # Ensure database is initialized for this process
    db = container.database()
    if hasattr(db, "get_connection_info"):
        info = db.get_connection_info()
        print(f"Database connection info: {info}")


# Add shutdown event to clean up connections
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connections on shutdown"""
    print(f"FastAPI shutting down in process {os.getpid()}")
    db = container.database()
    if hasattr(db, "close_all_connections"):
        db.close_all_connections()


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


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint that also shows process information"""
    db = get_database()
    connection_ok = db.check_connection()

    response = {
        "status": "healthy" if connection_ok else "unhealthy",
        "process_id": os.getpid(),
        "database_connected": connection_ok,
    }

    if hasattr(db, "get_connection_info"):
        response["connection_info"] = db.get_connection_info()

    if not connection_ok:
        raise HTTPException(status_code=503, detail=response)

    return response


# Copy all other endpoints from the original api.py
# (The endpoints remain the same, only the container import changes)


@app.get("/api/v1/sites", response_model=List[schemas.Site])
async def list_sites(
    site_service: SiteService = Depends(get_site_service),
    active_only: bool = Query(True, description="Only return active sites"),
):
    """Get all sites"""
    sites = site_service.db.get_sites(active_only=active_only)
    return sites


@app.get("/api/v1/sites/{site_id}", response_model=schemas.Site)
async def get_site(
    site_id: int,
    site_service: SiteService = Depends(get_site_service),
):
    """Get a specific site by ID"""
    site = site_service.db.get_site_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@app.get("/api/v1/sites/{site_id}/pages", response_model=List[str])
async def list_site_pages(
    site_id: int,
    db: Database = Depends(get_database),
):
    """Get all pages for a specific site"""
    pages = db.get_distinct_pages_for_site(site_id)
    return pages


@app.get("/api/v1/sites/{site_id}/keywords", response_model=List[schemas.Keyword])
async def list_site_keywords(
    site_id: int,
    db: Database = Depends(get_database),
):
    """Get all keywords for a specific site"""
    keywords = db.get_keywords(site_id)
    return keywords


@app.get("/api/v1/sites/{site_id}/performance")
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


@app.get("/api/v1/sites/{site_id}/ranking-data")
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


@app.get("/api/v1/sites/{site_id}/page-keyword-performance")
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


@app.get("/api/v1/analysis/hourly-performance/{site_id}")
async def analyze_hourly_performance(
    site_id: int,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    date: str = Query(None, description="Specific date to analyze (YYYY-MM-DD)"),
):
    """Analyze hourly performance patterns for a site"""
    try:
        if date:
            datetime.strptime(date, "%Y-%m-%d")
        results = analysis_service.analyze_hourly_performance(site_id, date)
        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/v1/sync/status/{site_id}")
async def get_sync_status(
    site_id: int,
    db: Database = Depends(get_database),
):
    """Get synchronization status for a specific site"""
    daily_coverage = db.get_daily_data_coverage(site_id)
    hourly_coverage = db.get_hourly_data_coverage(site_id)

    return {
        "site_id": site_id,
        "daily_data": {
            "total_days": len(daily_coverage),
            "latest_date": max(daily_coverage.keys()) if daily_coverage else None,
            "oldest_date": min(daily_coverage.keys()) if daily_coverage else None,
        },
        "hourly_data": {
            "total_days": len(hourly_coverage),
            "latest_date": max(hourly_coverage.keys()) if hourly_coverage else None,
            "oldest_date": min(hourly_coverage.keys()) if hourly_coverage else None,
        },
    }
