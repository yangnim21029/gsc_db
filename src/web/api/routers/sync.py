"""
Sync Router

API endpoints for synchronization status and monitoring.
"""

from fastapi import APIRouter, Depends

from src.services.database import Database

from ..dependencies import get_database

router = APIRouter(
    prefix="/sync",
    tags=["Sync"],
)


@router.get("/status/{site_id}")
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
