#!/usr/bin/env python3
"""
Multi-site sequential sync script.

CRITICAL: GSC API requires sequential processing!
- Tested 2025-07-25: concurrent requests = 100% failure rate
- Sequential requests = 100% success rate
- Never use concurrent/parallel processing for GSC API calls
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.hybrid import HybridDataStore


async def sync_multiple_sites_sequential(
    site_ids: list[int], days: int = 7, sync_mode: str = "skip"
) -> dict[str, Any]:
    """
    Sync multiple sites sequentially (NEVER concurrent).

    GSC API limitation: Concurrent requests result in 100% failure.
    Must process one site at a time with delays between requests.
    """
    print(
        f"🔄 Starting SEQUENTIAL sync for {len(site_ids)} sites "
        f"({days} days each, mode: {sync_mode})"
    )
    print("⚠️  Sequential processing required - GSC API does not support concurrency")

    # Initialize database once
    db = HybridDataStore()
    await db.initialize()

    results = []
    total_start_time = time.time()

    try:
        for i, site_id in enumerate(site_ids, 1):
            site_start_time = time.time()
            site_result = {
                "site_id": site_id,
                "site_name": "Unknown",
                "success": False,
                "duration_seconds": 0,
                "records_synced": 0,
                "error": None,
            }

            try:
                # Get site info
                site = await db.get_site_by_id(site_id)
                if not site:
                    site_result["error"] = f"Site {site_id} not found"
                    results.append(site_result)
                    continue

                site_result["site_name"] = site.name
                print(f"\n[{i}/{len(site_ids)}] Syncing {site.name} (ID: {site_id})")

                # Call the existing sync script for this site
                # Using subprocess to maintain isolation and proper error handling

                sync_cmd = [
                    "poetry",
                    "run",
                    "python",
                    "sync.py",
                    "sync",
                    str(site_id),
                    str(days),
                    sync_mode,
                ]

                print(f"    Executing: {' '.join(sync_cmd)}")

                # Run sync with timeout
                process = await asyncio.create_subprocess_exec(
                    *sync_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=Path(__file__).parent,
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=300,  # 5 minute timeout per site
                    )

                    if process.returncode == 0:
                        # Parse output for success indicators
                        output_text = stdout.decode()
                        print("    ✅ Sync completed")

                        # Try to extract record count from output
                        import re

                        match = re.search(r"(\d+)\s+inserted", output_text)
                        if match:
                            site_result["records_synced"] = int(match.group(1))

                        site_result["success"] = True
                    else:
                        error_text = stderr.decode() if stderr else "Unknown error"
                        print(f"    ❌ Sync failed: {error_text[:100]}")
                        site_result["error"] = error_text[:200]

                except TimeoutError:
                    process.kill()
                    site_result["error"] = "Sync timeout after 5 minutes"
                    print("    ⏰ Sync timeout")

            except Exception as e:
                site_result["error"] = str(e)
                print(f"    ❌ Error: {e}")

            finally:
                site_result["duration_seconds"] = round(time.time() - site_start_time, 2)
                results.append(site_result)

                # CRITICAL: Add delay between sites to respect GSC API limits
                if i < len(site_ids):  # Don't delay after last site
                    delay = 2.0  # 2 second delay between sites
                    print(f"    💤 Waiting {delay}s before next site (GSC API rate limiting)")
                    await asyncio.sleep(delay)

    finally:
        await db.close()

    total_duration = time.time() - total_start_time

    # Summary
    successful = sum(1 for r in results if r["success"])
    total_records = sum(r["records_synced"] for r in results)

    print("\n" + "=" * 60)
    print("                SEQUENTIAL SYNC SUMMARY")
    print("=" * 60)
    print(f"Total sites processed: {len(site_ids)}")
    print(
        f"Successful syncs: {successful}/{len(site_ids)} ({successful / len(site_ids) * 100:.1f}%)"
    )
    print(f"Total records synced: {total_records:,}")
    print(f"Total time: {total_duration:.1f}s ({total_duration / 60:.1f} minutes)")
    print(f"Average time per site: {total_duration / len(site_ids):.1f}s")

    # Show individual results
    print("\n📊 Individual Results:")
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(
            f"  {status} {result['site_name']} (ID: {result['site_id']}): "
            f"{result['records_synced']:,} records in {result['duration_seconds']}s"
        )
        if result["error"]:
            print(f"      Error: {result['error']}")

    print("=" * 60)

    return {
        "total_sites": len(site_ids),
        "successful_sites": successful,
        "total_records": total_records,
        "total_duration": total_duration,
        "results": results,
    }


async def main():
    """Main entry point for multi-site sync."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python sync_multiple.py <site_ids> [days] [sync_mode]")
        print("")
        print("Sync Modes:")
        print("  skip (default)     - Skip existing records, insert new ones only")
        print("  overwrite          - Replace existing records (useful for corrections)")
        print("")
        print("Examples:")
        print("  python sync_multiple.py '1,2,17' 7")
        print("  python sync_multiple.py '1 2 17' 3 skip")
        print("  python sync_multiple.py '1,2,17' 14 overwrite")
        return

    # Parse site IDs
    site_ids_str = sys.argv[1]
    try:
        # Support both comma and space separated
        if "," in site_ids_str:
            site_ids = [int(x.strip()) for x in site_ids_str.split(",")]
        else:
            site_ids = [int(x.strip()) for x in site_ids_str.split()]
    except ValueError:
        print("❌ Invalid site IDs. Use format: '1,2,3' or '1 2 3'")
        return

    # Parse days and sync mode
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    sync_mode = sys.argv[3] if len(sys.argv) > 3 else "skip"

    # Validate sync mode
    if sync_mode not in ["skip", "overwrite"]:
        print(f"❌ Invalid sync mode '{sync_mode}'. Must be 'skip' or 'overwrite'")
        return

    if not site_ids:
        print("❌ No site IDs provided")
        return

    print("🚀 Multi-Site Sequential Sync")
    print(f"Sites: {site_ids}")
    print(f"Days per site: {days}")
    print(f"Sync mode: {sync_mode}")
    print("⚠️  Using sequential processing (GSC API requirement)")

    # Execute sequential sync
    await sync_multiple_sites_sequential(site_ids, days, sync_mode)


if __name__ == "__main__":
    asyncio.run(main())
