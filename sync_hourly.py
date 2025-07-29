#!/usr/bin/env python3
"""Direct hourly sync script without CLI framework dependencies."""

import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.hybrid import HybridDataStore
from src.database.sync_progress import SyncProgressTracker
from src.services.gsc_client import ModernGSCClient


async def process_hourly_data(
    hourly_data: list[dict], site_id: int, current_date: date
) -> list[dict]:
    """Process raw hourly data into database format."""
    hourly_records = []
    for record in hourly_data:
        # Extract hour from timestamp (e.g., "2025-04-07T00:00:00-07:00")
        timestamp = record.get("hour", "")
        if "T" in timestamp:
            hour = int(timestamp.split("T")[1].split(":")[0])
        else:
            hour = 0

        hourly_records.append(
            {
                "site_id": site_id,
                "date": current_date.isoformat(),
                "hour": hour,
                "query": record.get("query", ""),
                "page": record.get("page", ""),
                "position": record.get("position", 0.0),
                "clicks": record.get("clicks", 0),
                "impressions": record.get("impressions", 0),
                "ctr": record.get("ctr", 0.0),
            }
        )
    return hourly_records


async def _initialize_hourly_sync_components(site_id: int):
    """Initialize database, progress tracker for hourly sync."""
    db = HybridDataStore()
    await db.initialize(skip_analyze=True)

    progress_tracker = SyncProgressTracker(Path("./data/gsc-data.db"))
    await progress_tracker.initialize()

    client = ModernGSCClient()
    await client.initialize()

    return db, progress_tracker, client


async def _determine_hourly_date_range(
    progress_tracker, site_id: int, days: int, resume: bool, end_date
):
    """Determine date range for hourly sync with 10-day limit."""
    max_days = min(days, 10)  # GSC API limit

    incomplete_sync = None
    if resume:
        incomplete_sync = await progress_tracker.get_incomplete_sync(site_id, sync_type="hourly")
        if incomplete_sync:
            print(f"🔄 Resuming previous hourly sync from {incomplete_sync['last_completed_date']}")
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
        start_date = end_date - timedelta(days=max_days)
        progress_id = await progress_tracker.start_sync(site_id, max_days, sync_type="hourly")
        days_already_done = 0

    return start_date, progress_id, days_already_done, max_days


async def _sync_single_day_hourly(
    client, db, site_domain: str, site_id: int, current_date, sync_mode: str
):
    """Sync hourly data for a single day."""
    try:
        hourly_data = await client.fetch_hourly_data(site_url=site_domain, target_date=current_date)

        if not hourly_data:
            return {"inserted": 0, "updated": 0, "skipped": 0}, 0

        # Process and insert hourly data
        hourly_records = await process_hourly_data(hourly_data, site_id, current_date)

        if not hourly_records:
            return {"inserted": 0, "updated": 0, "skipped": 0}, len(hourly_data)

        # Handle overwrite mode
        if sync_mode == "overwrite":
            await db.delete_hourly_data_for_date(site_id, current_date)

        stats = await db.insert_hourly_data(hourly_records, mode=sync_mode)

        print(
            f"  Day complete: {stats['inserted']} inserted, "
            f"{stats.get('updated', 0)} updated, "
            f"{stats.get('skipped', 0)} skipped"
        )

        return stats, len(hourly_data)

    except Exception as e:
        print(f"  ⚠️  Error fetching hourly data for {current_date}: {e}")
        return {"inserted": 0, "updated": 0, "skipped": 0}, 0


def _print_hourly_summary(sync_mode: str, total_stats: dict):
    """Print hourly sync summary."""
    print("\n✅ Hourly sync complete!")
    print(f"Total: {total_stats['inserted']} inserted")
    if sync_mode == "overwrite":
        print(f"       {total_stats.get('updated', 0)} updated")
    else:
        print(f"       {total_stats.get('skipped', 0)} skipped")


async def sync_site_hourly_data(
    site_id: int, days: int = 2, sync_mode: str = "skip", resume: bool = True
):
    """Sync hourly data for specified days with configurable sync mode and resume support.

    Note: Hourly data is only available for the last 10 days from GSC API.
    """
    print(f"🕐 Syncing hourly data for site {site_id} for {days} days (mode: {sync_mode})...")

    # Initialize components
    db, progress_tracker, client = await _initialize_hourly_sync_components(site_id)
    progress_id = None

    try:
        # Get site info
        site = await db.get_site_by_id(site_id)
        if not site:
            print(f"❌ Site {site_id} not found")
            return

        print(f"📊 Syncing hourly data for {site.name} ({site.domain})")

        try:
            # Determine date range
            end_date = datetime.now().date()
            (
                start_date,
                progress_id,
                days_already_done,
                max_days,
            ) = await _determine_hourly_date_range(
                progress_tracker, site_id, days, resume, end_date
            )

            print(f"Date range: {start_date} to {end_date}")
            if days > 10:
                print("⚠️  Note: Hourly data limited to last 10 days by GSC API")

            # Track total stats
            total_stats = {"inserted": 0, "updated": 0, "skipped": 0}
            current_date = start_date
            days_processed = days_already_done

            # Process each day
            while current_date <= end_date:
                print(f"  Fetching hourly data for {current_date}...")

                # Sync single day
                stats, record_count = await _sync_single_day_hourly(
                    client, db, site.domain, site_id, current_date, sync_mode
                )

                # Update stats
                total_stats["inserted"] += stats["inserted"]
                total_stats["updated"] += stats.get("updated", 0)
                total_stats["skipped"] += stats.get("skipped", 0)
                days_processed += 1

                # Update progress
                await progress_tracker.update_progress(
                    progress_id, current_date, days_processed, record_count
                )

                current_date += timedelta(days=1)

                # Be nice to GSC API
                await asyncio.sleep(0.5)

            # Complete sync
            await progress_tracker.complete_sync(progress_id)

            # Print summary
            _print_hourly_summary(sync_mode, total_stats)

        finally:
            await client.close()
    finally:
        await db.close()
        await progress_tracker.close()


async def list_sites():
    """List all sites from database."""
    db = HybridDataStore()
    await db.initialize()

    try:
        sites = await db.get_sites()
        print("\n📋 Available sites:")
        print("-" * 50)
        for site in sites:
            status = "✅" if site.is_active else "❌"
            print(f"{status} {site.id:3d}: {site.name} ({site.domain})")
        print("-" * 50)
        print(f"Total: {len(sites)} sites\n")
    finally:
        await db.close()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python sync_hourly.py <command> [args]")
        print("\nCommands:")
        print("  list                     - List all sites")
        print("  sync <site_id> [days] [mode]  - Sync hourly data for site")
        print("                              days: 1-10 (default: 2)")
        print("                              mode: skip|overwrite (default: skip)")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        asyncio.run(list_sites())
    elif command == "sync":
        if len(sys.argv) < 3:
            print("Error: site_id required")
            sys.exit(1)

        site_id = int(sys.argv[2])
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 2
        sync_mode = sys.argv[4] if len(sys.argv) > 4 else "skip"

        if sync_mode not in ["skip", "overwrite"]:
            print(f"Error: Invalid sync mode '{sync_mode}'. Use 'skip' or 'overwrite'")
            sys.exit(1)

        asyncio.run(sync_site_hourly_data(site_id, days, sync_mode))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
