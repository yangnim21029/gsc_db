#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Process-Safe Database Connection Manager

This module provides a process-safe wrapper around the Database class that ensures
each process has its own database connection. This is essential for multi-process
applications like web servers with multiple workers.
"""

import logging
import os
import sqlite3
import threading

from .database import Database

logger = logging.getLogger(__name__)


class ProcessSafeDatabase:
    """
    A process-safe database wrapper that ensures each process has its own connection.

    This class detects when it's being used in a different process (e.g., after a fork)
    and automatically creates a new connection for that process.
    """

    def __init__(self, database_path: str):
        """
        Initialize the process-safe database manager.

        Args:
            database_path: Path to the SQLite database file
        """
        self._database_path = database_path
        self._lock = threading.RLock()
        self._connections = {}  # Maps process ID to (connection, Database instance)
        self._current_pid = None

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with proper settings."""
        conn = sqlite3.connect(
            self._database_path,
            check_same_thread=False,
            timeout=30.0,
            isolation_level=None,  # Autocommit mode
        )
        conn.row_factory = sqlite3.Row

        # Enable WAL mode and other optimizations
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA cache_size=-64000")
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
        cursor.execute("PRAGMA page_size=4096")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

        return conn

    def _get_database(self) -> Database:
        """Get or create a Database instance for the current process."""
        current_pid = os.getpid()

        with self._lock:
            # Check if we need a new connection (new process or first time)
            if current_pid not in self._connections:
                # Clean up old connections from other processes
                if self._current_pid and self._current_pid != current_pid:
                    logger.info(f"Process fork detected: {self._current_pid} -> {current_pid}")
                    # Close connections from the parent process
                    for pid, (conn, _) in list(self._connections.items()):
                        if pid != current_pid:
                            try:
                                conn.close()
                            except Exception as e:
                                logger.warning(f"Error closing connection for PID {pid}: {e}")
                            del self._connections[pid]

                # Create new connection for this process
                logger.info(f"Creating new database connection for process {current_pid}")
                conn = self._create_connection()
                db = Database(conn, self._lock)
                self._connections[current_pid] = (conn, db)
                self._current_pid = current_pid

            return self._connections[current_pid][1]

    def __getattr__(self, name):
        """
        Proxy all attribute access to the underlying Database instance.

        This ensures that all method calls go through the process-safe wrapper.
        """
        db = self._get_database()
        return getattr(db, name)

    def close_all_connections(self):
        """Close all database connections across all processes."""
        with self._lock:
            for pid, (conn, _) in self._connections.items():
                try:
                    conn.close()
                    logger.info(f"Closed database connection for process {pid}")
                except Exception as e:
                    logger.error(f"Error closing connection for process {pid}: {e}")
            self._connections.clear()

    def get_connection_info(self) -> dict:
        """Get information about current connections."""
        with self._lock:
            return {
                "current_pid": os.getpid(),
                "connection_pids": list(self._connections.keys()),
                "total_connections": len(self._connections),
            }


class ConnectionPool:
    """
    A simple connection pool for SQLite databases.

    This is useful when you need multiple connections within the same process
    for truly concurrent read operations.
    """

    def __init__(self, database_path: str, pool_size: int = 5):
        """
        Initialize the connection pool.

        Args:
            database_path: Path to the SQLite database file
            pool_size: Maximum number of connections in the pool
        """
        self._database_path = database_path
        self._pool_size = pool_size
        self._connections = []
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(pool_size)

        # Pre-create connections
        for _ in range(pool_size):
            conn = self._create_connection()
            self._connections.append(conn)

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with proper settings."""
        conn = sqlite3.connect(
            self._database_path, check_same_thread=False, timeout=30.0, isolation_level=None
        )
        conn.row_factory = sqlite3.Row

        # Enable WAL mode
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool."""
        self._semaphore.acquire()
        with self._lock:
            return self._connections.pop()

    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool."""
        with self._lock:
            self._connections.append(conn)
        self._semaphore.release()

    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing pooled connection: {e}")
            self._connections.clear()
