"""
Tests for the concurrency and thread-safety of the Database service.
"""

import threading
from typing import Any, Dict, List

import pytest

from src.containers import Container
from src.services.database import Database


@pytest.fixture(scope="module")
def di_container() -> Container:
    """
    Provides a DI container configured for in-memory testing.
    This fixture has 'module' scope to ensure all tests in this module
    share the same container, and thus the same singleton connection and lock.
    """
    container = Container()
    container.config.from_dict({"paths": {"database_path": ":memory:"}})
    # We need to explicitly wire the modules that use the container
    container.wire(modules=[__name__])
    return container


@pytest.fixture
def thread_safe_db(di_container: Container) -> Database:
    """
    Provides a thread-safe, in-memory database instance for testing.
    It gets the singleton Database service from the container.
    """
    db_service = di_container.database()
    # Clean up table before each test run
    with di_container.db_lock():
        di_container.db_connection().execute("DELETE FROM gsc_performance_data")
        di_container.db_connection().execute("DELETE FROM sites")
        di_container.db_connection().commit()

    db_service.add_site(domain="sc-domain:example.com", name="Test Site")
    return db_service


def worker_write_data(db: Database, site_id: int, date_str: str, data_chunk: List[Dict[str, Any]]):
    """
    A function that simulates a worker writing a chunk of data.
    It first deletes any existing data for that day, then saves the new chunk.
    This mimics the behavior of the data synchronizer.
    """
    try:
        db.delete_performance_data_for_day(site_id, date_str)
        db.save_data_chunk(
            chunk=data_chunk,
            site_id=site_id,
            sync_mode="overwrite",
            date_str=date_str,
            device="desktop",
            search_type="web",
        )
    except Exception as e:
        # If any exception occurs in the thread, we want the main test to fail.
        pytest.fail(f"Worker thread failed with exception: {e}")


def test_concurrent_writes_are_safe(thread_safe_db: Database, di_container: Container):
    """
    Tests that multiple threads can write to the database concurrently
    without raising a 'database is locked' error, thanks to the shared lock.
    """
    site_id = 1
    num_threads = 20  # Simulate 20 concurrent operations
    records_per_thread = 50
    threads: List[threading.Thread] = []

    for i in range(num_threads):
        date_str = f"2024-01-{(i + 1):02d}"
        # Create a sample data chunk for each thread
        data_chunk = [
            {
                "keys": [f"/page/{j}", f"query {j}", "desktop", "web"],
                "clicks": float(i),
                "impressions": 100.0,
                "ctr": 0.1,
                "position": 1.0,
            }
            for j in range(records_per_thread)
        ]

        thread = threading.Thread(
            target=worker_write_data, args=(thread_safe_db, site_id, date_str, data_chunk)
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # After all threads are done, verify the data integrity
    with di_container.db_lock():
        conn = di_container.db_connection()
        total_records = conn.execute("SELECT COUNT(*) FROM gsc_performance_data").fetchone()[0]
        assert total_records == num_threads * records_per_thread
