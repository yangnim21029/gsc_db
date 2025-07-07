"""
Tests for the concurrency and thread-safety of the Database service.
"""

import threading
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from src.services.database import Database


def worker_write_data(
    db: Database,
    connection: Any,
    lock: threading.RLock,
    site_id: int,
    date_str: str,
    data_chunk: List[Any],
):
    """
    A function that simulates a worker writing a chunk of data.
    It first deletes any existing data for that day, then saves the new chunk.
    This mimics the behavior of the data synchronizer.
    The entire delete-and-save operation is wrapped in a single lock and
    transaction to ensure atomicity and prevent database deadlocks.
    """
    try:
        # 整個操作在一個鎖中進行，避免死鎖
        with lock:
            # 先刪除舊數據
            connection.execute(
                "DELETE FROM gsc_performance_data WHERE site_id = ? AND date = ?",
                (site_id, date_str),
            )

            # 然後插入新數據
            for row in data_chunk:
                connection.execute(
                    """
                    INSERT INTO gsc_performance_data
                    (site_id, date, page, query, device, search_type,
                     clicks, impressions, ctr, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        site_id,
                        date_str,
                        row.keys[0],  # page
                        row.keys[1],  # query
                        row.keys[2],  # device
                        row.keys[3],  # search_type
                        row.clicks,
                        row.impressions,
                        row.ctr,
                        row.position,
                    ),
                )

            # 提交事務以釋放資料庫層級的鎖，這是避免死鎖的關鍵
            connection.commit()
    except Exception as e:
        # If any exception occurs in the thread, we want the main test to fail.
        pytest.fail(f"Worker thread failed with exception: {e}")


def test_concurrent_writes_are_safe(test_db):
    """
    Tests that multiple threads can write to the database concurrently
    without raising a 'database is locked' error, thanks to the shared lock.
    """
    db_service, connection, lock = test_db  # Unpack the tuple from test_db fixture

    # Add a test site first
    site_id = db_service.add_site(domain="sc-domain:example.com", name="Test Site")

    num_threads = 20  # Simulate 20 concurrent operations
    records_per_thread = 50
    threads: List[threading.Thread] = []

    for i in range(num_threads):
        date_str = f"2024-01-{(i + 1):02d}"
        # Create a sample data chunk with the correct format (mock objects with keys attribute)
        data_chunk = []
        for j in range(records_per_thread):
            mock_row = MagicMock()
            mock_row.keys = [f"/page/{j}", f"query {j}", "desktop", "web"]
            mock_row.clicks = float(i)
            mock_row.impressions = 100.0
            mock_row.ctr = 0.1
            mock_row.position = 1.0
            data_chunk.append(mock_row)

        thread = threading.Thread(
            target=worker_write_data,
            args=(db_service, connection, lock, site_id, date_str, data_chunk),
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # After all threads are done, verify the data integrity
    with lock:
        total_records = connection.execute("SELECT COUNT(*) FROM gsc_performance_data").fetchone()[
            0
        ]
        assert total_records == num_threads * records_per_thread
