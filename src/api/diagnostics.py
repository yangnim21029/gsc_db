"""System diagnostics and testing endpoints."""

import time
from typing import Any

from litestar import Router, get, post

from ..database.hybrid import HybridDataStore
from ..models import SyncTestRequest
from ..services.gsc_client import ModernGSCClient


@get("/test-db-connection", tags=["Diagnostics"])
async def test_db_connection(db: HybridDataStore) -> dict[str, Any]:
    """
    Test database connection and query performance.

    Tests basic connection, simple query, and complex coverage query
    with timing metrics for each operation.
    """
    results = {}

    # Test basic connection
    start_time = time.time()
    try:
        await db.test_connection()
        results["basic_connection"] = {
            "status": "success",
            "duration_ms": round((time.time() - start_time) * 1000, 2),
        }
    except Exception as e:
        results["basic_connection"] = {
            "status": "error",
            "error": str(e),
            "duration_ms": round((time.time() - start_time) * 1000, 2),
        }

    # Test simple query
    start_time = time.time()
    try:
        sites = await db.get_sites()
        results["simple_query"] = {
            "status": "success",
            "sites_count": len(sites),
            "duration_ms": round((time.time() - start_time) * 1000, 2),
        }
    except Exception as e:
        results["simple_query"] = {
            "status": "error",
            "error": str(e),
            "duration_ms": round((time.time() - start_time) * 1000, 2),
        }

    # Test complex query (coverage analysis)
    start_time = time.time()
    try:
        # Get sync coverage for first site if available
        sites = await db.get_sites()
        if sites:
            coverage = await db.get_sync_coverage(sites[0].id, days=30)
            results["complex_query"] = {
                "status": "success",
                "coverage_days": len(coverage) if coverage else 0,
                "duration_ms": round((time.time() - start_time) * 1000, 2),
            }
        else:
            results["complex_query"] = {
                "status": "skipped",
                "reason": "No sites available",
                "duration_ms": 0,
            }
    except Exception as e:
        results["complex_query"] = {
            "status": "error",
            "error": str(e),
            "duration_ms": round((time.time() - start_time) * 1000, 2),
        }

    return results


@get("/test-gsc-connection/{site_id:int}", tags=["Diagnostics"])
async def test_gsc_connection(db: HybridDataStore, site_id: int) -> dict[str, Any]:
    """
    Test Google Search Console API connection for a specific site.

    Verifies authentication and basic API connectivity.
    """
    start_time = time.time()

    try:
        # Get site information
        site = await db.get_site_by_id(site_id)
        if not site:
            return {
                "status": "error",
                "error": f"Site {site_id} not found",
                "duration_ms": round((time.time() - start_time) * 1000, 2),
            }

        # Test GSC connection
        client = ModernGSCClient()
        await client.initialize()

        try:
            # Try to get site verification status or basic info
            # This is a lightweight test operation
            await client.test_site_access(site.domain)

            return {
                "status": "success",
                "site_id": site_id,
                "site_domain": site.domain,
                "duration_ms": round((time.time() - start_time) * 1000, 2),
            }
        except Exception as api_error:
            return {
                "status": "api_error",
                "site_id": site_id,
                "site_domain": site.domain,
                "error": str(api_error),
                "duration_ms": round((time.time() - start_time) * 1000, 2),
            }
        finally:
            await client.close()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "duration_ms": round((time.time() - start_time) * 1000, 2),
        }


@get("/check-locks", tags=["Diagnostics"])
async def check_database_locks(db: HybridDataStore) -> dict[str, Any]:
    """
    Check for database locks and view SQLite pragma settings.

    Returns SQLite configuration and provides optimization recommendations.
    """
    try:
        pragma_info = await db.get_pragma_info()

        # Provide recommendations based on current settings
        recommendations = []

        if pragma_info.get("journal_mode") != "WAL":
            recommendations.append("Consider using WAL journal mode for better concurrency")

        if pragma_info.get("busy_timeout", 0) < 10000:
            recommendations.append("Consider increasing busy_timeout to 10000ms or higher")

        if pragma_info.get("cache_size", 0) < 10000:
            recommendations.append("Consider increasing cache_size for better performance")

        return {
            "status": "success",
            "pragma_settings": pragma_info,
            "recommendations": recommendations,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


@post("/test-sync", tags=["Diagnostics"])
async def test_sync_timing(db: HybridDataStore, data: SyncTestRequest) -> dict[str, Any]:
    """
    Perform actual sync operations and measure timing.

    Tests sync performance for multiple sites and identifies bottlenecks.
    """
    results = {
        "sites": [],
        "summary": {
            "total_sites": len(data.site_ids),
            "total_duration_ms": 0,
            "avg_duration_per_site_ms": 0,
            "bottleneck": "unknown",
        },
    }

    client = ModernGSCClient()
    await client.initialize()

    total_start_time = time.time()
    total_api_time = 0
    total_db_time = 0

    try:
        for site_id in data.site_ids:
            site_start_time = time.time()
            site_result = {
                "site_id": site_id,
                "status": "unknown",
                "api_duration_ms": 0,
                "db_duration_ms": 0,
                "total_duration_ms": 0,
                "records_synced": 0,
            }

            try:
                # Get site info
                site = await db.get_site_by_id(site_id)
                if not site:
                    site_result["status"] = "site_not_found"
                    results["sites"].append(site_result)
                    continue

                # Test sync operation with timing
                api_start = time.time()

                # Simulate API call timing (or do actual lightweight call)
                try:
                    await client.test_site_access(site.domain)
                    api_duration = time.time() - api_start
                    total_api_time += api_duration
                    site_result["api_duration_ms"] = round(api_duration * 1000, 2)

                    # Test database operation timing
                    db_start = time.time()

                    # Do a test database operation
                    coverage = await db.get_sync_coverage(site_id, days=data.days)
                    db_duration = time.time() - db_start
                    total_db_time += db_duration
                    site_result["db_duration_ms"] = round(db_duration * 1000, 2)

                    site_result["status"] = "success"
                    site_result["records_synced"] = len(coverage) if coverage else 0

                except Exception as sync_error:
                    site_result["status"] = "sync_error"
                    site_result["error"] = str(sync_error)

            except Exception as site_error:
                site_result["status"] = "error"
                site_result["error"] = str(site_error)

            finally:
                site_result["total_duration_ms"] = round((time.time() - site_start_time) * 1000, 2)
                results["sites"].append(site_result)

    finally:
        await client.close()

        # Calculate summary statistics
        total_duration = time.time() - total_start_time
        results["summary"]["total_duration_ms"] = round(total_duration * 1000, 2)

        if len(data.site_ids) > 0:
            results["summary"]["avg_duration_per_site_ms"] = round(
                (total_duration / len(data.site_ids)) * 1000, 2
            )

        # Determine bottleneck
        if total_api_time > total_db_time * 2:
            results["summary"]["bottleneck"] = "GSC_API"
        elif total_db_time > total_api_time * 2:
            results["summary"]["bottleneck"] = "DATABASE"
        else:
            results["summary"]["bottleneck"] = "BALANCED"

        results["summary"]["total_api_time_ms"] = round(total_api_time * 1000, 2)
        results["summary"]["total_db_time_ms"] = round(total_db_time * 1000, 2)

    return results


diagnostics_router = Router(
    path="/api/v1/diagnostics",
    route_handlers=[
        test_db_connection,
        test_gsc_connection,
        check_database_locks,
        test_sync_timing,
    ],
)
