#!/usr/bin/env python3
"""Demonstrate fast mode improvements."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.models import PerformanceData


def create_test_data(count: int) -> list[PerformanceData]:
    """Create test performance data."""
    records = []
    for i in range(count):
        record = PerformanceData(
            site_id=17,
            date=date(2025, 7, 1),
            page=f"https://urbanlifehk.com/article/{i}",
            query=f"香港美食 {i}",
            device="MOBILE",
            search_type="WEB",
            clicks=i % 100,
            impressions=i * 10,
            ctr=0.05,
            position=float(i % 50 + 1),
        )
        records.append(record)
    return records


def simulate_io_operations():
    """Simulate I/O operations comparison."""
    print("🔍 I/O Operations Comparison\n")

    # Test data
    test_records = create_test_data(25000)  # One day's worth of data

    # Old method: Individual inserts
    print("❌ OLD METHOD: Individual Inserts")
    print("─" * 50)
    old_io_ops = len(test_records) * 6  # 1 insert + 5 index updates
    old_time = len(test_records) * 0.01  # 10ms per operation on HDD
    print(f"Records: {len(test_records):,}")
    print(f"I/O Operations: {old_io_ops:,}")
    print(f"Estimated Time: {old_time:.1f} seconds ({old_time/60:.1f} minutes)")
    print(f"Operations/sec: {len(test_records)/old_time:.0f}")

    print("\n✅ NEW METHOD: Batch Insert with Fast Mode")
    print("─" * 50)
    # Batch with executemany
    batch_ops = len(test_records) // 10000 * 6  # Batches of 10,000
    # No index updates during insert
    new_io_ops = batch_ops + 5  # Batch inserts + recreate indexes once
    new_time = new_io_ops * 0.01  # Same 10ms per operation
    print(f"Records: {len(test_records):,}")
    print(f"I/O Operations: {new_io_ops:,}")
    print(f"Estimated Time: {new_time:.1f} seconds")
    print(f"Operations/sec: {len(test_records)/new_time:.0f}")

    print(f"\n📊 IMPROVEMENT: {old_time/new_time:.1f}x faster!")
    print(f"   I/O Reduction: {(1 - new_io_ops/old_io_ops)*100:.1f}%")
    print(f"   Time Saved: {(old_time - new_time)/60:.1f} minutes per day")

    # For 30 days
    print("\n📅 30-DAY SYNC COMPARISON:")
    print(f"   Old Method: {(old_time * 30)/60:.1f} minutes")
    print(f"   New Method: {(new_time * 30)/60:.1f} minutes")
    print(f"   Time Saved: {((old_time - new_time) * 30)/60:.1f} minutes!")


def show_optimization_features():
    """Show all optimization features."""
    print("\n\n🚀 FAST MODE FEATURES\n")

    features = [
        ("executemany()", "Batch insert multiple records in one operation"),
        ("BufferedWriter", "Accumulate records in memory before writing"),
        ("Index Management", "Drop indexes during bulk load, recreate after"),
        ("Fast Insert Mode", "Disable synchronous writes temporarily"),
        ("Smart Caching", "50,000 page cache for frequently accessed data"),
        ("WAL Optimization", "Larger WAL checkpoint interval"),
    ]

    for feature, description in features:
        print(f"✓ {feature:20} - {description}")

    print("\n\n📝 USAGE EXAMPLES\n")

    examples = [
        ("Normal sync", "python sync.py sync 17 7"),
        ("Fast mode sync", "python sync.py sync 17 30 --fast-mode"),
        ("Large historical sync", "python sync.py sync 17 365 --fast-mode --no-resume"),
        (
            "With custom batch size",
            "GSC__BATCH_INSERT_SIZE=5000 python sync.py sync 17 30 --fast-mode",
        ),
    ]

    for title, command in examples:
        print(f"{title:25} $ {command}")


if __name__ == "__main__":
    print("=" * 70)
    print("GSC DATABASE FAST MODE DEMONSTRATION")
    print("=" * 70)

    simulate_io_operations()
    show_optimization_features()

    print("\n\n💡 RECOMMENDATIONS FOR SLOW STORAGE:")
    print("─" * 50)
    print("1. Always use --fast-mode for syncs > 7 days")
    print("2. Run syncs during off-peak hours")
    print("3. Consider copying DB to local SSD for processing:")
    print("   cp /Volumes/USB/gsc.db ~/Desktop/gsc_temp.db")
    print("4. Monitor with: watch -n 1 'ls -lh data/*.db*'")
    print("\n✅ Implementation ready for testing!")
    print("=" * 70)
