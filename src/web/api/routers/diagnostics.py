"""
Diagnostics Router

API endpoints for testing and diagnosing sync performance issues.
"""

import time
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.services.database import Database
from src.services.site_service import SiteService

from ..dependencies import container, get_database, get_site_service

router = APIRouter(
    prefix="/diagnostics",
    tags=["Diagnostics"],
)


class SyncTestRequest(BaseModel):
    site_ids: List[int]
    days: int = 5


@router.get("/test-db-connection")
async def test_database_connection(
    db: Database = Depends(get_database),
):
    """Test database connection and query performance"""
    results = {}

    # Test 1: Basic connection
    start = time.time()
    try:
        connection_ok = db.check_connection()
        results["connection_test"] = {
            "success": connection_ok,
            "time_ms": round((time.time() - start) * 1000, 2),
        }
    except Exception as e:
        results["connection_test"] = {
            "success": False,
            "error": str(e),
            "time_ms": round((time.time() - start) * 1000, 2),
        }

    # Test 2: Simple query
    start = time.time()
    try:
        with db._lock:
            count = db._connection.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        results["simple_query"] = {
            "success": True,
            "site_count": count,
            "time_ms": round((time.time() - start) * 1000, 2),
        }
    except Exception as e:
        results["simple_query"] = {
            "success": False,
            "error": str(e),
            "time_ms": round((time.time() - start) * 1000, 2),
        }

    # Test 3: Complex query (data coverage)
    start = time.time()
    try:
        coverage = db.get_daily_data_coverage(4)  # Test with site 4
        results["coverage_query"] = {
            "success": True,
            "days_found": len(coverage),
            "time_ms": round((time.time() - start) * 1000, 2),
        }
    except Exception as e:
        results["coverage_query"] = {
            "success": False,
            "error": str(e),
            "time_ms": round((time.time() - start) * 1000, 2),
        }

    return results


@router.get("/test-gsc-connection/{site_id}")
async def test_gsc_connection(
    site_id: int,
    site_service: SiteService = Depends(get_site_service),
):
    """Test Google Search Console API connection and response time"""
    site = site_service.get_site_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")

    # In real implementation, would test actual GSC connection
    # For now, return diagnostic info
    return {
        "site_id": site_id,
        "site_domain": site["domain"],
        "gsc_test": {
            "status": "simulated",
            "message": "Would test GSC API connection here",
            "expected_latency_ms": "2000-5000",
        },
    }


@router.get("/check-locks")
async def check_database_locks(
    db: Database = Depends(get_database),
):
    """Check for database locks and active connections"""
    try:
        with db._lock:
            # Check SQLite's internal state
            pragma_results = {}

            # Check journal mode
            journal_mode = db._connection.execute("PRAGMA journal_mode").fetchone()[0]
            pragma_results["journal_mode"] = journal_mode

            # Check busy timeout
            busy_timeout = db._connection.execute("PRAGMA busy_timeout").fetchone()[0]
            pragma_results["busy_timeout_ms"] = busy_timeout

            # Check synchronous mode
            synchronous = db._connection.execute("PRAGMA synchronous").fetchone()[0]
            pragma_results["synchronous"] = synchronous

            # Check cache size
            cache_size = db._connection.execute("PRAGMA cache_size").fetchone()[0]
            pragma_results["cache_size"] = cache_size

            # Check for locked tables (this is SQLite specific)
            locked = db._connection.execute("PRAGMA database_list").fetchall()
            pragma_results["databases"] = [dict(row) for row in locked]

        return {
            "database_state": "accessible",
            "pragma_settings": pragma_results,
            "recommendations": {
                "journal_mode": "Should be 'WAL' for better concurrency",
                "busy_timeout": "Should be at least 5000ms",
                "synchronous": "Should be 'NORMAL' for performance",
            },
        }
    except Exception as e:
        return {"database_state": "error", "error": str(e), "type": type(e).__name__}


@router.post("/test-sync")
async def test_sync_timing(
    request: SyncTestRequest,
    db: Database = Depends(get_database),
    site_service: SiteService = Depends(get_site_service),
):
    """
    Test sync timing for multiple sites.
    This performs sync operations and measures the time.

    Args:
        site_ids: List of site IDs to sync
        days: Number of days to sync per site
    """
    site_ids = request.site_ids
    days = request.days

    # Verify sites exist
    sites = []
    for site_id in site_ids:
        site = site_service.get_site_by_id(site_id)
        if not site:
            raise HTTPException(status_code=404, detail=f"Site {site_id} not found")
        sites.append(site)

    # Get GSC client from container
    gsc_client = container.gsc_client()

    results = {
        "test_params": {"site_ids": site_ids, "days": days, "total_tasks": len(site_ids) * days},
        "sites": [],
        "timing": {
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "total_duration_seconds": None,
        },
    }

    overall_start = time.time()

    # Test each site
    for site in sites:
        site_result = {
            "site_id": site["id"],
            "site_name": site["name"],
            "days_synced": [],
            "total_time_ms": 0,
            "errors": [],
        }

        # Calculate date range (GSC has 2-3 day delay)
        end_date = datetime.now().date() - timedelta(days=3)
        start_date = end_date - timedelta(days=days - 1)

        # Sync each day
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            day_start = time.time()

            try:
                # Check existing data first
                existing_count = 0
                with db._lock:
                    existing_count = db._connection.execute(
                        "SELECT COUNT(*) FROM gsc_performance_data WHERE site_id = ? AND date = ?",
                        (site["id"], current_date.strftime("%Y-%m-%d")),
                    ).fetchone()[0]

                # Perform GSC API call
                api_start = time.time()
                data = gsc_client.get_search_analytics(
                    site["domain"],
                    current_date.strftime("%Y-%m-%d"),
                    current_date.strftime("%Y-%m-%d"),
                    row_limit=25000,
                )
                api_time = (time.time() - api_start) * 1000

                # Insert data (skip mode)
                insert_start = time.time()
                inserted = 0
                if data:
                    with db._lock:
                        for row in data:
                            try:
                                db._connection.execute(
                                    """
                                    INSERT OR IGNORE INTO gsc_performance_data
                                    (site_id, date, query, page, clicks, impressions, ctr, position, country, device)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        site["id"],
                                        current_date.strftime("%Y-%m-%d"),
                                        row.get("keys", [""])[0],  # query
                                        row.get("keys", ["", ""])[1]
                                        if len(row.get("keys", [])) > 1
                                        else "",  # page
                                        row.get("clicks", 0),
                                        row.get("impressions", 0),
                                        row.get("ctr", 0),
                                        row.get("position", 0),
                                        "TWN",  # default country
                                        "ALL",  # default device
                                    ),
                                )
                                if db._connection.total_changes > 0:
                                    inserted += 1
                            except Exception:
                                pass  # Skip individual row errors
                        db._connection.commit()

                insert_time = (time.time() - insert_start) * 1000
                total_time = (time.time() - day_start) * 1000

                site_result["days_synced"].append(
                    {
                        "date": current_date.strftime("%Y-%m-%d"),
                        "existing_rows": existing_count,
                        "fetched_rows": len(data) if data else 0,
                        "inserted_rows": inserted,
                        "timing_ms": {
                            "api_call": round(api_time, 2),
                            "db_insert": round(insert_time, 2),
                            "total": round(total_time, 2),
                        },
                    }
                )
                site_result["total_time_ms"] += total_time

            except Exception as e:
                site_result["errors"].append(
                    {"date": current_date.strftime("%Y-%m-%d"), "error": str(e)}
                )

        results["sites"].append(site_result)

    # Calculate totals
    overall_duration = time.time() - overall_start
    results["timing"]["end_time"] = datetime.now().isoformat()
    results["timing"]["total_duration_seconds"] = round(overall_duration, 2)

    # Analysis
    total_api_time = sum(
        sum(day["timing_ms"]["api_call"] for day in site["days_synced"])
        for site in results["sites"]
    )
    total_db_time = sum(
        sum(day["timing_ms"]["db_insert"] for day in site["days_synced"])
        for site in results["sites"]
    )

    results["analysis"] = {
        "average_time_per_task_seconds": round(overall_duration / (len(site_ids) * days), 2),
        "total_api_time_seconds": round(total_api_time / 1000, 2),
        "total_db_time_seconds": round(total_db_time / 1000, 2),
        "api_percentage": round((total_api_time / 1000) / overall_duration * 100, 1),
        "db_percentage": round((total_db_time / 1000) / overall_duration * 100, 1),
        "bottleneck": "GSC API calls" if total_api_time > total_db_time else "Database operations",
    }

    return results
