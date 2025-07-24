#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Multi-Process Database Access

This test suite verifies that the multiprocess database implementation works correctly
and resolves the SQLite locking issues.
"""

import multiprocessing
import os
import sqlite3
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor

import pytest

from src.services.process_safe_database import ConnectionPool, ProcessSafeDatabase


# Define worker functions at module level to make them picklable
def read_worker(worker_id, db_path):
    """Worker function for concurrent read tests"""
    from src.services.process_safe_database import ProcessSafeDatabase

    db = ProcessSafeDatabase(db_path)
    conn = db._get_database()._connection

    results = []
    for i in range(10):
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM test_data")
        result = cursor.fetchone()
        results.append(result["count"])
        time.sleep(0.01)  # Small delay to increase concurrency

    return worker_id, results


def write_worker(worker_id, db_path, num_writes=50):
    """Worker function for concurrent write tests"""
    from src.services.process_safe_database import ProcessSafeDatabase

    db = ProcessSafeDatabase(db_path)
    conn = db._get_database()._connection

    successful_writes = 0
    errors = []

    for i in range(num_writes):
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO test_data (process_id, thread_id, value) VALUES (?, ?, ?)",
                (os.getpid(), f"worker_{worker_id}", f"value_{i}"),
            )
            conn.commit()
            successful_writes += 1
        except sqlite3.OperationalError as e:
            errors.append(str(e))
            time.sleep(0.1)  # Retry after delay

    return worker_id, successful_writes, errors


def mixed_worker(worker_id, db_path):
    """Worker function for mixed operations test"""
    from src.services.process_safe_database import ProcessSafeDatabase

    db = ProcessSafeDatabase(db_path)
    conn = db._get_database()._connection

    operations = []

    for i in range(20):
        if i % 3 == 0:
            # Write operation
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO test_data (process_id, value) VALUES (?, ?)",
                    (os.getpid(), f"worker_{worker_id}_value_{i}"),
                )
                conn.commit()
                operations.append(("write", True, None))
            except Exception as e:
                operations.append(("write", False, str(e)))
        else:
            # Read operation
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM test_data")
                result = cursor.fetchone()
                operations.append(("read", True, result["count"]))
            except Exception as e:
                operations.append(("read", False, str(e)))

        time.sleep(0.01)

    return worker_id, operations


def child_process(db_path, initial_pid):
    """Worker function for fork detection test"""
    from src.services.process_safe_database import ProcessSafeDatabase

    # This runs in a different process
    db = ProcessSafeDatabase(db_path)
    info = db.get_connection_info()

    # Should have different PID
    assert info["current_pid"] != initial_pid

    # Should be able to perform database operations
    conn = db._get_database()._connection
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO test_data (process_id, value) VALUES (?, ?)",
        (os.getpid(), "child_process_data"),
    )
    conn.commit()

    return info["current_pid"]


class TestMultiProcessDatabase:
    """Test suite for multi-process database access"""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Initialize database with test data
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Enable WAL mode
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        # Create test table
        conn.execute("""
            CREATE TABLE test_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_id INTEGER,
                thread_id TEXT,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        os.unlink(db_path)
        # Also remove WAL and SHM files if they exist
        for suffix in ["-wal", "-shm"]:
            wal_file = db_path + suffix
            if os.path.exists(wal_file):
                os.unlink(wal_file)

    def test_single_process_access(self, temp_db_path):
        """Test basic single process access works"""
        db = ProcessSafeDatabase(temp_db_path)

        # Write data
        conn = db._get_database()._connection
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO test_data (process_id, thread_id, value) VALUES (?, ?, ?)",
            (os.getpid(), "main", "test_value"),
        )
        conn.commit()

        # Read data
        cursor.execute("SELECT COUNT(*) as count FROM test_data")
        result = cursor.fetchone()
        assert result["count"] == 1

    def test_concurrent_reads(self, temp_db_path):
        """Test multiple processes can read simultaneously"""

        # Insert some test data first
        db = ProcessSafeDatabase(temp_db_path)
        conn = db._get_database()._connection
        cursor = conn.cursor()
        for i in range(100):
            cursor.execute(
                "INSERT INTO test_data (process_id, value) VALUES (?, ?)",
                (os.getpid(), f"value_{i}"),
            )
        conn.commit()

        # Test concurrent reads - using module-level read_worker function
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(4):
                future = executor.submit(read_worker, i, temp_db_path)
                futures.append(future)

            results = [future.result() for future in futures]

            # All workers should read the same count
            for worker_id, counts in results:
                assert all(count == 100 for count in counts), (
                    f"Worker {worker_id} got inconsistent counts"
                )

    def test_concurrent_writes(self, temp_db_path):
        """Test multiple processes can write without locking issues"""

        # Test concurrent writes - using module-level write_worker function
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(4):
                future = executor.submit(write_worker, i, temp_db_path)
                futures.append(future)

            results = [future.result() for future in futures]

            # Check results
            total_writes = sum(result[1] for result in results)
            total_errors = sum(len(result[2]) for result in results)

            print(f"Total successful writes: {total_writes}")
            print(f"Total errors: {total_errors}")

            # With WAL mode, most writes should succeed
            assert total_writes >= 180, f"Too few successful writes: {total_writes}/200"

            # Verify data integrity
            db = ProcessSafeDatabase(temp_db_path)
            conn = db._get_database()._connection
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM test_data")
            result = cursor.fetchone()
            assert result["count"] == total_writes

    def test_mixed_read_write_operations(self, temp_db_path):
        """Test mixed read/write operations from multiple processes"""

        # Run mixed operations - using module-level mixed_worker function
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(4):
                future = executor.submit(mixed_worker, i, temp_db_path)
                futures.append(future)

            results = [future.result() for future in futures]

            # Analyze results
            total_operations = sum(len(result[1]) for result in results)
            successful_operations = sum(1 for result in results for op in result[1] if op[1])

            print(f"Total operations: {total_operations}")
            print(f"Successful operations: {successful_operations}")

            # Most operations should succeed with WAL mode
            success_rate = successful_operations / total_operations
            assert success_rate > 0.9, f"Low success rate: {success_rate:.2%}"

    def test_process_fork_detection(self, temp_db_path):
        """Test that process forks are detected and handled correctly"""
        db = ProcessSafeDatabase(temp_db_path)

        # Get initial connection info
        info1 = db.get_connection_info()
        initial_pid = info1["current_pid"]

        # Run in child process - using module-level child_process function
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(child_process, temp_db_path, initial_pid)
            child_pid = future.result()

        # Verify child had different PID
        assert child_pid != initial_pid

        # Verify data was written
        conn = db._get_database()._connection
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM test_data WHERE value = 'child_process_data'")
        result = cursor.fetchone()
        assert result is not None

    def test_connection_pool(self, temp_db_path):
        """Test connection pool functionality"""
        pool = ConnectionPool(temp_db_path, pool_size=3)

        # Test getting connections
        connections = []
        for i in range(3):
            conn = pool.get_connection()
            connections.append(conn)

            # Verify connection works
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

        # Return connections
        for conn in connections:
            pool.return_connection(conn)

        # Test connection reuse
        conn1 = pool.get_connection()
        pool.return_connection(conn1)
        conn2 = pool.get_connection()

        # Should get the same connection object
        assert conn1 is conn2

        # Cleanup
        pool.close_all()

    def test_wal_mode_enabled(self, temp_db_path):
        """Verify WAL mode is properly enabled"""
        db = ProcessSafeDatabase(temp_db_path)
        conn = db._get_database()._connection

        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        result = cursor.fetchone()

        assert result[0].lower() == "wal", f"Expected WAL mode, got {result[0]}"

        # Verify WAL files exist after a write
        cursor.execute(
            "INSERT INTO test_data (process_id, value) VALUES (?, ?)", (os.getpid(), "wal_test")
        )
        conn.commit()

        # Check for WAL file
        wal_file = temp_db_path + "-wal"
        assert os.path.exists(wal_file), "WAL file not created"


if __name__ == "__main__":
    # Set spawn method for consistency across platforms
    multiprocessing.set_start_method("spawn", force=True)

    # Run tests
    pytest.main([__file__, "-v"])
