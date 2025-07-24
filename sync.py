#!/usr/bin/env python3
"""Direct sync script without CLI framework dependencies."""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.hybrid import HybridDataStore
from src.services.gsc_client import ModernGSCClient
from src.config import get_settings


async def sync_site_data(site_id: int, days: int = 7, sync_mode: str = "skip"):
    """Sync site data for specified days with configurable sync mode."""
    print(f"🔄 Syncing site {site_id} for {days} days (mode: {sync_mode})...")
    
    # Initialize database
    db = HybridDataStore()
    await db.initialize()
    
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
            # Sync data
            from datetime import datetime, timedelta
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            print(f"Date range: {start_date} to {end_date}")
            
            # Fetch data from GSC day by day with pagination
            # CRITICAL: Must be sequential - GSC API fails with concurrent access
            # Tested 2025-07-25: concurrent=0% success, sequential=100% success
            performance_records = []
            current_date = start_date
            
            while current_date <= end_date:
                print(f"  Fetching data for {current_date}...")
                
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
                            start_row=start_row  # Add start_row parameter for pagination
                        )
                        
                        if not daily_data:
                            print(f"    No more data for {current_date}")
                            break
                        
                        performance_records.extend(daily_data)
                        print(f"    Fetched {len(daily_data)} records (total: {len(performance_records)})")
                        
                        # If we got less than the batch size, we're done with this date
                        if len(daily_data) < batch_size:
                            break
                            
                        start_row += batch_size
                        
                    except Exception as e:
                        print(f"    Error fetching data for {current_date}: {e}")
                        break
                
                current_date += timedelta(days=1)
            
            if performance_records:
                # Insert into database with specified sync mode
                stats = await db.insert_performance_data(performance_records, mode=sync_mode)
                if sync_mode == "skip":
                    print(f"✅ Sync complete: {stats['inserted']} inserted, {stats['skipped']} skipped")
                else:  # overwrite mode
                    print(f"✅ Sync complete: {stats['inserted']} inserted, {stats['updated']} updated")
            else:
                print("⚠️ No data returned from GSC API")
                
        finally:
            await client.close()
            
    finally:
        await db.close()


async def list_sites():
    """List all sites."""
    db = HybridDataStore()
    await db.initialize()
    
    try:
        sites = await db.get_sites()
        
        print("\n" + "="*60)
        print(" "*20 + "Registered Sites")
        print("="*60)
        print(f"{'ID':<4} {'Domain':<25} {'Name':<25} {'Active':<8}")
        print("-"*60)
        
        for site in sites:
            domain = site.domain[:24] + "..." if len(site.domain) > 24 else site.domain
            name = site.name[:24] + "..." if len(site.name) > 24 else site.name
            active = "✓" if site.is_active else "✗"
            print(f"{site.id:<4} {domain:<25} {name:<25} {active:<8}")
        
        print("="*60 + "\n")
        
    finally:
        await db.close()


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python sync.py list                                    # List all sites")
        print("  python sync.py sync <site_id> [days] [sync_mode]       # Sync site data")
        print("")
        print("Sync Modes:")
        print("  skip (default)     - Skip existing records, insert new ones only")
        print("  overwrite          - Replace existing records (useful for corrections)")
        print("")
        print("Examples:")
        print("  python sync.py sync 17 7               # Sync site 17, 7 days, skip mode")
        print("  python sync.py sync 17 7 skip          # Same as above")
        print("  python sync.py sync 17 7 overwrite     # Sync with overwrite mode")
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
        
        await sync_site_data(site_id, days, sync_mode)
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())