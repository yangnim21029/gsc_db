#!/usr/bin/env python3
"""Test script to demonstrate resume sync functionality."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.sync_progress import SyncProgressTracker


async def show_sync_status():
    """Show current sync progress for all sites."""
    tracker = SyncProgressTracker(Path("./data/gsc_data.db"))
    await tracker.initialize()

    try:
        # Check a few common site IDs
        print("=== Sync Progress Status ===\n")

        for site_id in [1, 5, 17]:  # Check these site IDs
            progress = await tracker.get_incomplete_sync(site_id)

            if progress:
                print(f"Site ID {site_id}:")
                print(f"  Started: {progress['started_at']}")
                print(f"  Last completed date: {progress['last_completed_date']}")
                print(
                    f"  Progress: {progress['days_completed']}/{progress['total_days_requested']} days"
                )
                print(f"  Progress ID: {progress['progress_id']}")
                print()
            else:
                print(f"Site ID {site_id}: No incomplete sync found\n")

    finally:
        await tracker.close()


if __name__ == "__main__":
    asyncio.run(show_sync_status())
