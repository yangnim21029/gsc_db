#!/usr/bin/env python3
"""Direct sync script without CLI framework dependencies."""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.hybrid import HybridDataStore
from src.database.sync_progress import SyncProgressTracker
from src.services.gsc_client import ModernGSCClient


async def sync_site_data(site_id: int, days: int = 7, sync_mode: str = "skip", resume: bool = True):
    """Sync site data for specified days with configurable sync mode and resume support."""
    print(f"🔄 Syncing site {site_id} for {days} days (mode: {sync_mode})...")

    # Initialize database and progress tracker
    db = HybridDataStore()
    await db.initialize()

    progress_tracker = SyncProgressTracker(Path("./data/gsc_data.db"))
    await progress_tracker.initialize()

    progress_id = None

    try:
        # Get site info
        site = await db.get_site_by_id(site_id)
        if not site:
            print(f"❌ Site {site_id} not found")
            return

        print(f"📊 Syncing {site.name} ({site.domain})")

        # Initialize GSC client
        client = ModernGSCClient()
        await client.initialize()

        try:
            # Check for incomplete sync to resume
            incomplete_sync = None
            if resume:
                incomplete_sync = await progress_tracker.get_incomplete_sync(site_id)
                if incomplete_sync:
                    print(
                        f"🔄 Resuming previous sync from {incomplete_sync['last_completed_date']}"
                    )
                    print(
                        f"   Progress: {incomplete_sync['days_completed']}/{incomplete_sync['total_days_requested']} days"
                    )

            # Determine date range
            end_date = datetime.now().date()

            if incomplete_sync and resume:
                # Resume from the day after last completed
                if incomplete_sync["last_completed_date"]:
                    start_date = incomplete_sync["last_completed_date"] + timedelta(days=1)
                else:
                    # No days completed yet, start from beginning
                    start_date = end_date - timedelta(days=incomplete_sync["total_days_requested"])
                progress_id = incomplete_sync["progress_id"]
                days_already_done = incomplete_sync["days_completed"]
            else:
                # Fresh sync
                start_date = end_date - timedelta(days=days)
                progress_id = await progress_tracker.start_sync(site_id, days)
                days_already_done = 0

            print(f"Date range: {start_date} to {end_date}")

            # Fetch data from GSC day by day with pagination
            # CRITICAL: Must be sequential - GSC API fails with concurrent access
            # Tested 2025-07-25: concurrent=0% success, sequential=100% success

            # Track total stats across all days
            total_stats = {"inserted": 0, "updated": 0, "skipped": 0}
            current_date = start_date
            days_processed = days_already_done

            while current_date <= end_date:
                print(f"  Fetching data for {current_date}...")

                # Process each day's data independently to avoid memory issues
                daily_records = []

                # Fetch data in batches to handle API limits
                # Reset start_row for each new date
                start_row = 0
                batch_size = 25000

                while True:
                    try:
                        daily_data = await client.fetch_data_for_date(
                            site_url=site.domain,
                            target_date=current_date,
                            row_limit=batch_size,
                            start_row=start_row,  # Add start_row parameter for pagination
                        )

                        if not daily_data:
                            print(f"    No more data for {current_date}")
                            break

                        daily_records.extend(daily_data)
                        print(
                            f"    Fetched {len(daily_data)} records "
                            f"(daily total: {len(daily_records)})"
                        )

                        # If we got less than the batch size, we're done with this date
                        if len(daily_data) < batch_size:
                            break

                        start_row += batch_size

                    except Exception as e:
                        print(f"    Error fetching data for {current_date}: {e}")
                        break

                # Insert this day's data immediately to avoid memory buildup
                if daily_records:
                    # Set the correct site_id for all records
                    for record in daily_records:
                        record.site_id = site_id

                    stats = await db.insert_performance_data(daily_records, mode=sync_mode)
                    total_stats["inserted"] += stats["inserted"]
                    total_stats["updated"] += stats.get("updated", 0)
                    total_stats["skipped"] += stats.get("skipped", 0)

                    print(
                        f"    Day complete: {stats['inserted']} inserted, "
                        f"{stats.get('skipped', stats.get('updated', 0))} "
                        f"{'skipped' if sync_mode == 'skip' else 'updated'}"
                    )

                days_processed += 1

                # Update progress after each successful day
                if progress_id:
                    await progress_tracker.update_progress(
                        progress_id,
                        current_date,
                        days_processed,
                        stats["inserted"] + stats.get("updated", 0),
                    )

                current_date += timedelta(days=1)

                # Optional: Add a small delay between days to be nice to GSC API
                if current_date <= end_date:
                    await asyncio.sleep(0.5)

            # Mark sync as complete
            if progress_id:
                await progress_tracker.complete_sync(progress_id)

            # Print final summary
            if sync_mode == "skip":
                print(
                    f"✅ Sync complete: {days_processed} days processed, "
                    f"{total_stats['inserted']} inserted, "
                    f"{total_stats['skipped']} skipped"
                )
            else:  # overwrite mode
                print(
                    f"✅ Sync complete: {days_processed} days processed, "
                    f"{total_stats['inserted']} inserted, "
                    f"{total_stats['updated']} updated"
                )

        except Exception as e:
            # Record error in progress tracker
            if progress_id:
                await progress_tracker.fail_sync(progress_id, str(e))
            raise
        finally:
            await client.close()

    finally:
        await db.close()
        await progress_tracker.close()


async def list_sites():
    """List all sites."""
    db = HybridDataStore()
    await db.initialize()

    try:
        sites = await db.get_sites()

        print("\n" + "=" * 60)
        print(" " * 20 + "Registered Sites")
        print("=" * 60)
        print(f"{'ID':<4} {'Domain':<25} {'Name':<25} {'Active':<8}")
        print("-" * 60)

        for site in sites:
            domain = site.domain[:24] + "..." if len(site.domain) > 24 else site.domain
            name = site.name[:24] + "..." if len(site.name) > 24 else site.name
            active = "✓" if site.is_active else "✗"
            print(f"{site.id:<4} {domain:<25} {name:<25} {active:<8}")

        print("=" * 60 + "\n")

    finally:
        await db.close()


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python sync.py list                                    # List all sites")
        print("  python sync.py sync <site_id> [days] [sync_mode] [--no-resume]  # Sync site data")
        print("")
        print("Sync Modes:")
        print("  skip (default)     - Skip existing records, insert new ones only")
        print("  overwrite          - Replace existing records (useful for corrections)")
        print("")
        print("Options:")
        print("  --no-resume        - Start fresh sync, ignore previous incomplete syncs")
        print("")
        print("Examples:")
        print(
            "  python sync.py sync 17 7               # Sync site 17, 7 days (resume if interrupted)"
        )
        print("  python sync.py sync 17 7 skip          # Same as above")
        print("  python sync.py sync 17 7 overwrite     # Sync with overwrite mode")
        print("  python sync.py sync 17 183 --no-resume # Fresh 183-day sync")
        return

    command = sys.argv[1]

    if command == "list":
        await list_sites()
    elif command == "sync":
        if len(sys.argv) < 3:
            print("Error: site_id required for sync command")
            return

        site_id = int(sys.argv[2])
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 7
        sync_mode = sys.argv[4] if len(sys.argv) > 4 else "skip"

        # Validate sync mode
        if sync_mode not in ["skip", "overwrite"]:
            print(f"Error: sync_mode must be 'skip' or 'overwrite', got '{sync_mode}'")
            return

        # Check for --no-resume flag
        no_resume = "--no-resume" in sys.argv
        await sync_site_data(site_id, days, sync_mode, resume=not no_resume)
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
