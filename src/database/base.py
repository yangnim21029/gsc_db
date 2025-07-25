"""Base classes and interfaces for database operations."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Protocol

import aiosqlite
from duckdb import DuckDBPyConnection


class DatabaseConnection(Protocol):
    """Protocol for database connections."""

    async def execute(self, query: str, params: Any = None) -> Any:
        """Execute a query."""
        ...

    async def commit(self) -> None:
        """Commit transaction."""
        ...

    async def close(self) -> None:
        """Close connection."""
        ...


class Repository:
    """Base repository class with common database operations."""

    def __init__(self, sqlite_conn: aiosqlite.Connection | None = None):
        self._sqlite_conn = sqlite_conn
        self._lock = None  # Will be set by DataStore

    def set_connection(self, conn: aiosqlite.Connection, lock: Any) -> None:
        """Set database connection and lock."""
        self._sqlite_conn = conn
        self._lock = lock

    def _ensure_connection(self) -> aiosqlite.Connection:
        """Ensure database connection is available."""
        if not self._sqlite_conn:
            raise RuntimeError("Database connection not initialized")
        return self._sqlite_conn

    async def _execute_query(self, query: str, params: Any = None) -> aiosqlite.Cursor:
        """Execute a query with connection check."""
        if not self._lock:
            raise RuntimeError("Lock not initialized")
        async with self._lock:
            conn = self._ensure_connection()
            return await conn.execute(query, params or ())

    async def _execute_many(self, query: str, params_list: list[Any]) -> None:
        """Execute many queries with connection check."""
        if not self._lock:
            raise RuntimeError("Lock not initialized")
        async with self._lock:
            conn = self._ensure_connection()
            await conn.executemany(query, params_list)


class AnalyticsService:
    """Base analytics service using DuckDB."""

    def __init__(self, duck_conn: DuckDBPyConnection | None = None):
        self._duck_conn = duck_conn
        self.enable_duckdb = duck_conn is not None

    def set_connection(self, conn: DuckDBPyConnection) -> None:
        """Set DuckDB connection."""
        self._duck_conn = conn
        self.enable_duckdb = True

    def _ensure_connection(self) -> DuckDBPyConnection:
        """Ensure DuckDB connection is available."""
        if not self._duck_conn:
            raise RuntimeError("DuckDB connection not initialized")
        return self._duck_conn


class TransactionManager:
    """Manages database transactions."""

    def __init__(self, conn: aiosqlite.Connection, lock: Any):
        self._conn = conn
        self._lock = lock

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Provide a database transaction context."""
        async with self._lock:
            if not self._conn:
                raise RuntimeError("Database not initialized")

            await self._conn.execute("BEGIN")
            try:
                yield self._conn
                await self._conn.execute("COMMIT")
            except Exception:
                await self._conn.execute("ROLLBACK")
                raise
