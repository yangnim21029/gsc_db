#!/usr/bin/env python3
"""Direct sync script without CLI framework dependencies."""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_settings
from src.database.hybrid import HybridDataStore
from src.database.services.bulk_insert_service import BulkInsertService
from src.database.sync_progress import SyncProgressTracker
from src.services.gsc_client import ModernGSCClient


async def _initialize_sync_services(site_id: int, fast_mode: bool):
    """Initialize database, progress tracker, and bulk service."""
    db = HybridDataStore()
    await db.initialize()

    progress_tracker = SyncProgressTracker(Path("./data/gsc-data.db"))
    await progress_tracker.initialize()

    settings = get_settings()
    bulk_service = None

    if fast_mode:
        bulk_service = BulkInsertService(
            db,
            batch_size=settings.batch_insert_size,
            buffer_size=settings.buffer_flush_size,
            use_index_optimization=settings.use_index_optimization,
            fast_mode=settings.enable_fast_mode or fast_mode,
        )
        await bulk_service.initialize()
        print("🚀 Fast mode enabled - using optimized bulk insert")

    return db, progress_tracker, bulk_service


async def _determine_sync_date_range(
    progress_tracker, site_id: int, days: int, resume: bool, end_date
):
    """Determine start/end dates and handle resume logic."""
    incomplete_sync = None
    if resume:
        incomplete_sync = await progress_tracker.get_incomplete_sync(site_id)
        if incomplete_sync:
            print(f"🔄 Resuming previous sync from {incomplete_sync['last_completed_date']}")
            print(
                f"   Progress: {incomplete_sync['days_completed']}/"
                f"{incomplete_sync['total_days_requested']} days"
            )

    if incomplete_sync and resume:
        if incomplete_sync["last_completed_date"]:
            start_date = incomplete_sync["last_completed_date"] + timedelta(days=1)
        else:
            start_date = end_date - timedelta(days=incomplete_sync["total_days_requested"])
        progress_id = incomplete_sync["progress_id"]
        days_already_done = incomplete_sync["days_completed"]
    else:
        start_date = end_date - timedelta(days=days)
        progress_id = await progress_tracker.start_sync(site_id, days)
        days_already_done = 0

    return start_date, progress_id, days_already_done


async def _fetch_daily_data(client, site_domain: str, current_date, batch_size: int = 25000):
    """Fetch all data for a single day with pagination."""
    daily_records = []
    start_row = 0

    while True:
        try:
            daily_data = await client.fetch_data_for_date(
                site_url=site_domain,
                target_date=current_date,
                row_limit=batch_size,
                start_row=start_row,
            )

            if not daily_data:
                print(f"    No more data for {current_date}")
                break

            daily_records.extend(daily_data)
            print(f"    Fetched {len(daily_data)} records (daily total: {len(daily_records)})")

            if len(daily_data) < batch_size:
                break

            start_row += batch_size

        except Exception as e:
            print(f"    Error fetching data for {current_date}: {e}")
            break

    return daily_records


async def _process_daily_records(daily_records, site_id: int, sync_mode: str, db, bulk_service):
    """Process and insert daily records."""
    if not daily_records:
        return {"inserted": 0, "updated": 0, "skipped": 0}

    # Set the correct site_id for all records
    for record in daily_records:
        record.site_id = site_id

    # Store total records count before processing
    total_records = len(daily_records)

    # Use bulk service if available, otherwise use direct insert
    if bulk_service:
        stats = await bulk_service.insert_day_data(daily_records, mode=sync_mode)
    else:
        stats = await db.insert_performance_data_batch(daily_records, mode=sync_mode)

    # Show both total records processed and actual insertion stats
    print(
        f"    Day complete: {total_records} records processed → "
        f"{stats['inserted']} inserted, "
        f"{stats.get('skipped', stats.get('updated', 0))} "
        f"{'skipped' if sync_mode == 'skip' else 'updated'}"
    )

    return stats


def _print_sync_summary(sync_mode: str, days_processed: int, total_stats: dict):
    """Print final sync summary."""
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


async def sync_site_data(
    site_id: int,
    days: int = 7,
    sync_mode: str = "skip",
    resume: bool = True,
    fast_mode: bool = False,
):
    """Sync site data for specified days with configurable sync mode and resume support."""
    print(f"🔄 Syncing site {site_id} for {days} days (mode: {sync_mode})...")

    # Initialize services
    db, progress_tracker, bulk_service = await _initialize_sync_services(site_id, fast_mode)
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
            # Determine date range
            end_date = datetime.now().date()
            start_date, progress_id, days_already_done = await _determine_sync_date_range(
                progress_tracker, site_id, days, resume, end_date
            )
            print(f"Date range: {start_date} to {end_date}")

            # Track total stats
            total_stats = {"inserted": 0, "updated": 0, "skipped": 0}
            current_date = start_date
            days_processed = days_already_done

            # Process each day
            while current_date <= end_date:
                print(f"  Fetching data for {current_date}...")

                # Fetch daily data
                daily_records = await _fetch_daily_data(client, site.domain, current_date)

                # Process records
                stats = await _process_daily_records(
                    daily_records, site_id, sync_mode, db, bulk_service
                )

                # Update stats
                total_stats["inserted"] += stats["inserted"]
                total_stats["updated"] += stats.get("updated", 0)
                total_stats["skipped"] += stats.get("skipped", 0)
                days_processed += 1

                # Update progress
                if progress_id and daily_records:
                    await progress_tracker.update_progress(
                        progress_id,
                        current_date,
                        days_processed,
                        total_stats["inserted"] + total_stats.get("updated", 0),
                    )

                current_date += timedelta(days=1)

                # Be nice to GSC API
                if current_date <= end_date:
                    await asyncio.sleep(0.5)

            # Complete sync
            if progress_id:
                await progress_tracker.complete_sync(progress_id)

            # Print summary
            _print_sync_summary(sync_mode, days_processed, total_stats)

            # Finalize bulk service
            if bulk_service:
                final_stats = await bulk_service.finalize()
                print(f"   Bulk insert finalized with total stats: {final_stats}")

        except Exception as e:
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
        print("  python sync.py sync <site_id> [days] [sync_mode] [options]  # Sync site data")
        print("")
        print("Sync Modes:")
        print("  skip (default)     - Skip existing records, insert new ones only")
        print("  overwrite          - Replace existing records (useful for corrections)")
        print("")
        print("Options:")
        print("  --no-resume        - Start fresh sync, ignore previous incomplete syncs")
        print("  --fast-mode        - Enable optimized bulk insert (drops indexes temporarily)")
        print("")
        print("Examples:")
        print(
            "  python sync.py sync 17 7               "
            "# Sync site 17, 7 days (resume if interrupted)"
        )
        print("  python sync.py sync 17 7 skip          # Same as above")
        print("  python sync.py sync 17 7 overwrite     # Sync with overwrite mode")
        print("  python sync.py sync 17 183 --no-resume # Fresh 183-day sync")
        print(
            "  python sync.py sync 17 183 --fast-mode # Fast bulk sync (optimized for slow storage)"
        )
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

        # Parse sync_mode, handling flags that might be in position 4
        sync_mode = "skip"  # default
        if len(sys.argv) > 4 and not sys.argv[4].startswith("--"):
            sync_mode = sys.argv[4]

        # Validate sync mode
        if sync_mode not in ["skip", "overwrite"]:
            print(f"Error: sync_mode must be 'skip' or 'overwrite', got '{sync_mode}'")
            return

        # Check for flags
        no_resume = "--no-resume" in sys.argv
        fast_mode = "--fast-mode" in sys.argv

        await sync_site_data(site_id, days, sync_mode, resume=not no_resume, fast_mode=fast_mode)
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
