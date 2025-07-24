"""
Sync Router

API endpoints for synchronization status and monitoring.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

# from src.jobs.bulk_data_synchronizer import sync_daily_data  # TODO: implement actual sync
from src.services.database import Database
from src.services.site_service import SiteService

from ..dependencies import get_database, get_site_service

router = APIRouter(
    prefix="/sync",
    tags=["Sync"],
)

# In-memory storage for sync jobs (in production, use Redis or database)
sync_jobs: Dict[str, dict] = {}


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


@router.post("/trigger/{site_id}")
async def trigger_sync(
    site_id: int,
    background_tasks: BackgroundTasks,
    site_service: SiteService = Depends(get_site_service),
    days: int = 7,
    test_mode: bool = False,
):
    """
    Trigger asynchronous sync for a specific site.

    Args:
        site_id: Site ID to sync
        days: Number of days to sync (default: 7)
        test_mode: If True, only simulates sync without actual API calls

    Returns:
        Job ID for tracking progress
    """
    # Verify site exists
    site = site_service.get_site_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")

    # Create job ID
    job_id = str(uuid.uuid4())

    # Initialize job status
    sync_jobs[job_id] = {
        "id": job_id,
        "site_id": site_id,
        "site_name": site["name"],
        "status": "pending",
        "progress": 0,
        "total_tasks": days,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
        "stats": {
            "synced": 0,
            "failed": 0,
            "skipped": 0,
        },
        "test_mode": test_mode,
    }

    # Add background task
    background_tasks.add_task(
        run_sync_job,
        job_id=job_id,
        site_id=site_id,
        days=days,
        test_mode=test_mode,
    )

    return {
        "job_id": job_id,
        "message": f"Sync job started for site {site_id}",
        "status_url": f"/api/v1/sync/job/{job_id}",
    }


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific sync job"""
    if job_id not in sync_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return sync_jobs[job_id]


@router.get("/jobs")
async def list_sync_jobs(
    active_only: bool = False,
):
    """List all sync jobs"""
    jobs = list(sync_jobs.values())

    if active_only:
        jobs = [j for j in jobs if j["status"] in ["pending", "running"]]

    # Sort by started_at descending
    jobs.sort(key=lambda x: x["started_at"], reverse=True)

    return {
        "total": len(jobs),
        "jobs": jobs[:20],  # Return last 20 jobs
    }


@router.post("/test-performance")
async def test_sync_performance(
    site_id: int,
    site_service: SiteService = Depends(get_site_service),
):
    """
    Test sync performance for a single day of data.
    Measures API call time and database write time.
    """
    site = site_service.get_site_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")

    # This would need the GSC client and database injected
    # For now, return a simulated result
    return {
        "site_id": site_id,
        "test_date": "2025-07-18",
        "metrics": {
            "api_call_time_ms": 2500,  # Simulated
            "db_write_time_ms": 150,  # Simulated
            "total_time_ms": 2650,  # Simulated
            "rows_fetched": 1200,  # Simulated
            "rows_inserted": 1200,  # Simulated
        },
        "performance_analysis": {
            "api_latency": "normal",
            "db_performance": "good",
            "bottleneck": "GSC API response time",
        },
    }


async def run_sync_job(job_id: str, site_id: int, days: int, test_mode: bool):
    """
    Background task to run sync job.
    In production, this would be a Celery task or similar.
    """
    try:
        # Update job status
        sync_jobs[job_id]["status"] = "running"
        sync_jobs[job_id]["progress"] = 0

        if test_mode:
            # Simulate sync progress
            for day in range(days):
                await asyncio.sleep(0.5)  # Simulate API call
                sync_jobs[job_id]["progress"] = ((day + 1) / days) * 100
                sync_jobs[job_id]["stats"]["synced"] += 1
        else:
            # In real implementation, you would call the actual sync function
            # For now, we'll simulate it
            for day in range(days):
                await asyncio.sleep(2)  # Simulate real API call time
                sync_jobs[job_id]["progress"] = ((day + 1) / days) * 100
                sync_jobs[job_id]["stats"]["synced"] += 1

        # Mark as completed
        sync_jobs[job_id]["status"] = "completed"
        sync_jobs[job_id]["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        sync_jobs[job_id]["status"] = "failed"
        sync_jobs[job_id]["error"] = str(e)
        sync_jobs[job_id]["completed_at"] = datetime.now().isoformat()


@router.delete("/job/{job_id}")
async def cancel_sync_job(job_id: str):
    """Cancel a running sync job"""
    if job_id not in sync_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = sync_jobs[job_id]

    if job["status"] not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Job is not running")

    # In real implementation, you would actually cancel the task
    job["status"] = "cancelled"
    job["completed_at"] = datetime.now().isoformat()

    return {"message": f"Job {job_id} cancelled"}
