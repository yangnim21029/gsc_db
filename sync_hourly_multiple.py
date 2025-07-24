#!/usr/bin/env python3
"""Batch hourly sync script for multiple sites - sequential execution for GSC API stability."""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sync_hourly import sync_site_hourly_data


async def sync_multiple_sites_hourly(site_ids: list[int], days: int = 2, sync_mode: str = "skip"):
    """Sync hourly data for multiple sites sequentially.

    IMPORTANT: GSC API requires sequential processing. Concurrent requests fail.
    """
    print(f"🕐 Starting hourly batch sync for {len(site_ids)} sites")
    print(f"📅 Days: {days} (max 10 due to GSC API limit)")
    print(f"🔄 Mode: {sync_mode}")
    print(f"📋 Sites: {', '.join(map(str, site_ids))}")
    print("-" * 60)

    start_time = time.time()
    results = {"success": [], "failed": []}

    for i, site_id in enumerate(site_ids, 1):
        print(f"\n[{i}/{len(site_ids)}] Processing site {site_id}...")
        try:
            await sync_site_hourly_data(site_id, days, sync_mode)
            results["success"].append(site_id)
            print(f"✅ Site {site_id} hourly sync completed successfully")
        except Exception as e:
            results["failed"].append((site_id, str(e)))
            print(f"❌ Site {site_id} failed: {e}")

        # Add delay between sites to be nice to GSC API
        if i < len(site_ids):
            print("\n⏳ Waiting 2 seconds before next site...")
            await asyncio.sleep(2)

    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("📊 HOURLY BATCH SYNC SUMMARY")
    print("=" * 60)
    print(f"✅ Successful: {len(results['success'])} sites")
    if results["success"]:
        print(f"   Sites: {', '.join(map(str, results['success']))}")

    print(f"❌ Failed: {len(results['failed'])} sites")
    if results["failed"]:
        for site_id, error in results["failed"]:
            print(f"   Site {site_id}: {error}")

    print(f"⏱️  Total time: {elapsed:.1f} seconds")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def parse_site_ids(site_ids_str: str) -> list[int]:
    """Parse site IDs from string input.

    Supports:
    - Space separated: "1 2 3"
    - Comma separated: "1,2,3"
    - Mixed: "1, 2, 3"
    """
    # Replace commas with spaces and split
    ids_str = site_ids_str.replace(",", " ")
    site_ids = []

    for id_str in ids_str.split():
        try:
            site_ids.append(int(id_str.strip()))
        except ValueError:
            print(f"Warning: Skipping invalid site ID: {id_str}")

    return site_ids


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Hourly Batch Sync Tool - Sync multiple sites hourly data sequentially")
        print("\nUsage: python sync_hourly_multiple.py <site_ids> [days] [mode]")
        print("\nArguments:")
        print('  site_ids - Space or comma separated site IDs (e.g., "1 2 3" or "1,2,3")')
        print("  days     - Number of days to sync, 1-10 (default: 2)")
        print("  mode     - Sync mode: skip|overwrite (default: skip)")
        print("\nExamples:")
        print('  python sync_hourly_multiple.py "1 3 5" 2')
        print('  python sync_hourly_multiple.py "1,3,5" 3 overwrite')
        print("\nNote: Hourly data is only available for the last 10 days")
        sys.exit(1)

    # Parse arguments
    site_ids = parse_site_ids(sys.argv[1])
    if not site_ids:
        print("Error: No valid site IDs provided")
        sys.exit(1)

    days = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    if days < 1 or days > 10:
        print(f"Error: Days must be between 1 and 10 (got {days})")
        sys.exit(1)

    sync_mode = sys.argv[3] if len(sys.argv) > 3 else "skip"
    if sync_mode not in ["skip", "overwrite"]:
        print(f"Error: Invalid sync mode '{sync_mode}'. Use 'skip' or 'overwrite'")
        sys.exit(1)

    # Run the sync
    asyncio.run(sync_multiple_sites_hourly(site_ids, days, sync_mode))


if __name__ == "__main__":
    main()
