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


async def process_hourly_data(hourly_data: list[dict], site_id: int, current_date: date) -> list[dict]:
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


async def sync_site_hourly_data(
    site_id: int, days: int = 2, sync_mode: str = "skip", resume: bool = True
):
    """Sync hourly data for specified days with configurable sync mode and resume support.

    Note: Hourly data is only available for the last 10 days from GSC API.
    """
    print(f"🕐 Syncing hourly data for site {site_id} for {days} days (mode: {sync_mode})...")

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

        print(f"📊 Syncing hourly data for {site.name} ({site.domain})")

        # Initialize GSC client
        client = ModernGSCClient()
        await client.initialize()

        try:
            # Check for incomplete sync to resume
            incomplete_sync = None
            if resume:
                incomplete_sync = await progress_tracker.get_incomplete_sync(
                    site_id, sync_type="hourly"
                )
                if incomplete_sync:
                    print(
                        f"🔄 Resuming previous hourly sync from {incomplete_sync['last_completed_date']}"
                    )
                    print(
                        f"   Progress: {incomplete_sync['days_completed']}/{incomplete_sync['total_days_requested']} days"
                    )

            # Determine date range (max 10 days for hourly data)
            end_date = datetime.now().date()
            max_days = min(days, 10)  # GSC API limit

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
                start_date = end_date - timedelta(days=max_days)
                progress_id = await progress_tracker.start_sync(
                    site_id, max_days, sync_type="hourly"
                )
                days_already_done = 0

            print(f"Date range: {start_date} to {end_date}")
            if days > 10:
                print("⚠️  Note: Hourly data limited to last 10 days by GSC API")

            # Track total stats across all days
            total_stats = {"inserted": 0, "updated": 0, "skipped": 0}
            current_date = start_date
            days_processed = days_already_done

            while current_date <= end_date:
                print(f"  Fetching hourly data for {current_date}...")

                # Fetch hourly data for the current date
                try:
                    hourly_data = await client.fetch_hourly_data(
                        site_url=site.domain, target_date=current_date
                    )

                    if hourly_data:
                        # Process and insert hourly data
                        hourly_records = await process_hourly_data(hourly_data, site_id, current_date)

                        # Insert hourly data
                        if hourly_records:
                            if sync_mode == "overwrite":
                                # Delete existing hourly data for this date first
                                await db.delete_hourly_data_for_date(site_id, current_date)

                            stats = await db.insert_hourly_data(hourly_records, mode=sync_mode)
                            total_stats["inserted"] += stats["inserted"]
                            total_stats["updated"] += stats.get("updated", 0)
                            total_stats["skipped"] += stats.get("skipped", 0)

                            print(
                                f"  Day complete: {stats['inserted']} inserted, "
                                f"{stats.get('updated', 0)} updated, "
                                f"{stats.get('skipped', 0)} skipped"
                            )

                    # Update progress
                    days_processed += 1
                    await progress_tracker.update_progress(
                        progress_id, current_date, days_processed, len(hourly_data or [])
                    )

                except Exception as e:
                    print(f"  ⚠️  Error fetching hourly data for {current_date}: {e}")

                # Move to next day
                current_date += timedelta(days=1)

                # Be nice to GSC API
                await asyncio.sleep(0.5)

            # Mark sync as complete
            await progress_tracker.complete_sync(progress_id)

            print("\n✅ Hourly sync complete!")
            print(f"Total: {total_stats['inserted']} inserted")
            if sync_mode == "overwrite":
                print(f"       {total_stats.get('updated', 0)} updated")
            else:
                print(f"       {total_stats.get('skipped', 0)} skipped")

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
