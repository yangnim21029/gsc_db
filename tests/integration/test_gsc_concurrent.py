#!/usr/bin/env python3
"""Test GSC API concurrent sync capabilities."""

import asyncio
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.hybrid import HybridDataStore


async def test_single_site_sync(site_id: int, days: int = 1) -> dict[str, Any]:
    """Test syncing a single site."""
    start_time = time.time()
    result = {
        "site_id": site_id,
        "success": False,
        "duration_seconds": 0,
        "records_synced": 0,
        "error": None,
    }

    try:
        # Initialize database
        db = HybridDataStore()
        await db.initialize()

        try:
            # Get site info
            site = await db.get_site_by_id(site_id)
            if not site:
                result["error"] = f"Site {site_id} not found"
                return result

            print(f"  Testing sync for {site.name} (ID: {site_id})")

            # Try to import and use the old GSC client from the original project
            try:
                # Import the working GSC client from original project
                import importlib.util

                original_gsc_path = (
                    Path(__file__).parent.parent / "src" / "services" / "gsc_client.py"
                )

                if original_gsc_path.exists():
                    spec = importlib.util.spec_from_file_location("original_gsc", original_gsc_path)
                    original_gsc = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(original_gsc)

                    # Use the original client
                    client = original_gsc.GSCClient()
                    client.authenticate()

                    if not client.is_authenticated():
                        result["error"] = "Failed to authenticate with GSC API"
                        return result

                    # Sync data for the last few days
                    end_date = datetime.now().date()
                    start_date = end_date - timedelta(days=days)

                    total_records = 0

                    # Test sync for each day
                    current_date = start_date
                    while current_date <= end_date:
                        try:
                            # Sync one day of data
                            for device, search_type, rows in client.fetch_daily_data(
                                site.domain,
                                current_date.strftime("%Y-%m-%d"),
                                search_types=["web"],  # Only web search for testing
                            ):
                                if rows:
                                    print(
                                        f"    {current_date}: Got {len(rows)} records "
                                        f"for {device}/{search_type}"
                                    )
                                    total_records += len(rows)
                                    break  # Just test one batch
                        except Exception as day_error:
                            print(f"    {current_date}: Error - {day_error}")

                        current_date += timedelta(days=1)

                    result["records_synced"] = total_records
                    result["success"] = total_records > 0

                    client.close_connection()
                else:
                    result["error"] = "Original GSC client not found"

            except Exception as gsc_error:
                result["error"] = f"GSC client error: {str(gsc_error)}"

        finally:
            await db.close()

    except Exception as e:
        result["error"] = f"Database error: {str(e)}"

    finally:
        result["duration_seconds"] = round(time.time() - start_time, 2)

    return result


async def test_concurrent_site_sync(site_ids: list[int], days: int = 1) -> dict[str, Any]:
    """Test syncing multiple sites concurrently."""
    print(f"\n🔄 Testing concurrent sync for {len(site_ids)} sites...")

    start_time = time.time()

    # Create tasks for concurrent execution
    tasks = [test_single_site_sync(site_id, days) for site_id in site_ids]

    try:
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "site_id": site_ids[i],
                        "success": False,
                        "duration_seconds": 0,
                        "records_synced": 0,
                        "error": str(result),
                    }
                )
            else:
                processed_results.append(result)

        total_duration = time.time() - start_time

        return {
            "concurrent_sites": len(site_ids),
            "total_duration": round(total_duration, 2),
            "results": processed_results,
        }

    except Exception as e:
        return {
            "concurrent_sites": len(site_ids),
            "total_duration": round(time.time() - start_time, 2),
            "error": str(e),
            "results": [],
        }


async def test_sequential_vs_concurrent():
    """Compare sequential vs concurrent sync performance."""
    print("🚀 GSC API Concurrent Sync Test")
    print("=" * 60)

    # Test sites (using a few different sites)
    test_site_ids = [1, 2, 3]  # businessfocus.io, mamidaily.com, test site

    print(f"\nTesting with sites: {test_site_ids}")

    # Test 1: Sequential sync
    print("\n1️⃣ Sequential Sync Test")
    sequential_start = time.time()
    sequential_results = []

    for site_id in test_site_ids:
        result = await test_single_site_sync(site_id, days=1)
        sequential_results.append(result)
        print(
            f"   Site {site_id}: {'✅' if result['success'] else '❌'} "
            f"({result['records_synced']} records, {result['duration_seconds']}s)"
        )

    sequential_total = time.time() - sequential_start

    # Test 2: Concurrent sync
    print("\n2️⃣ Concurrent Sync Test")
    concurrent_result = await test_concurrent_site_sync(test_site_ids, days=1)

    for result in concurrent_result["results"]:
        print(
            f"   Site {result['site_id']}: {'✅' if result['success'] else '❌'} "
            f"({result['records_synced']} records, {result['duration_seconds']}s)"
        )

    # Analysis
    print("\n" + "=" * 60)
    print("                    SYNC ANALYSIS")
    print("=" * 60)

    successful_sequential = sum(1 for r in sequential_results if r["success"])
    successful_concurrent = sum(1 for r in concurrent_result["results"] if r["success"])

    print("\n📊 Performance Comparison:")
    print("   Sequential:")
    print(f"     - Total time: {sequential_total:.2f}s")
    print(f"     - Successful: {successful_sequential}/{len(test_site_ids)}")
    print(f"     - Total records: {sum(r['records_synced'] for r in sequential_results)}")

    print("   Concurrent:")
    print(f"     - Total time: {concurrent_result['total_duration']:.2f}s")
    print(f"     - Successful: {successful_concurrent}/{len(test_site_ids)}")
    print(f"     - Total records: {sum(r['records_synced'] for r in concurrent_result['results'])}")

    # Speed improvement
    if concurrent_result["total_duration"] > 0:
        speedup = sequential_total / concurrent_result["total_duration"]
        print(f"     - Speedup: {speedup:.2f}x {'faster' if speedup > 1 else 'slower'}")

    # Error analysis
    print("\n🔍 Error Analysis:")
    all_results = sequential_results + concurrent_result["results"]
    errors = [r for r in all_results if not r["success"]]

    if errors:
        print(f"   Found {len(errors)} errors:")
        error_types = {}
        for r in errors:
            error = r["error"][:50] if r["error"] else "Unknown error"
            error_types[error] = error_types.get(error, 0) + 1

        for error, count in error_types.items():
            print(f"     - {error}: {count} occurrences")
    else:
        print("   ✅ No errors detected")

    # Recommendations
    print("\n💡 Recommendations:")

    if successful_concurrent < successful_sequential:
        print("   ⚠️  Concurrent sync has lower success rate")
        print("   - GSC API may not support concurrent access")
        print("   - Consider using sequential sync with rate limiting")
    elif speedup > 1.5:
        print("   ✅ Concurrent sync provides significant improvement")
        print("   - Safe to use concurrent sync for multiple sites")
    else:
        print("   ℹ️  Limited benefit from concurrent sync")
        print("   - GSC API may have internal rate limiting")
        print("   - Sequential sync might be more reliable")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_sequential_vs_concurrent())
