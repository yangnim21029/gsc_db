#!/usr/bin/env python3
"""Test fast mode functionality."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from datetime import date

from src.database.hybrid import HybridDataStore
from src.database.services.bulk_insert_service import BulkInsertService
from src.models import PerformanceData


async def test_fast_mode():
    """Test the fast mode implementation."""
    print("Testing fast mode implementation...")

    # Initialize database
    db = HybridDataStore()
    await db.initialize()

    # Create test data
    test_records = []
    for i in range(1000):
        record = PerformanceData(
            site_id=3,  # Test site
            date=date(2025, 1, 1),
            page=f"https://test.com/page{i}",
            query=f"test query {i}",
            device="DESKTOP",
            search_type="WEB",
            clicks=i % 100,
            impressions=i * 10,
            ctr=0.1,
            position=float(i % 50),
        )
        test_records.append(record)

    print(f"Created {len(test_records)} test records")

    # Test normal insert
    print("\n1. Testing normal batch insert...")
    start_time = asyncio.get_event_loop().time()
    stats = await db.insert_performance_data_batch(test_records[:100], mode="skip")
    duration = asyncio.get_event_loop().time() - start_time
    print(f"   Normal insert: {stats} in {duration:.2f}s")

    # Test with BulkInsertService
    print("\n2. Testing BulkInsertService...")
    bulk_service = BulkInsertService(
        db,
        batch_size=100,
        buffer_size=500,
        use_index_optimization=False,  # Don't drop indexes for small test
        fast_mode=True,
    )

    await bulk_service.initialize()

    start_time = asyncio.get_event_loop().time()
    stats = await bulk_service.insert_batch(test_records[100:200], mode="skip")
    await bulk_service.finalize()
    duration = asyncio.get_event_loop().time() - start_time
    print(f"   Bulk service insert: {bulk_service.total_stats} in {duration:.2f}s")

    # Test index management
    print("\n3. Testing index management...")
    await db.drop_performance_indexes()
    print("   Indexes dropped")

    await db.recreate_performance_indexes()
    print("   Indexes recreated")

    # Close database
    await db.close()
    print("\n✅ Fast mode test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_fast_mode())
