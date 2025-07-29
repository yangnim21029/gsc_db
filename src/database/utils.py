"""Database utilities to reduce code redundancy."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import aiosqlite

T = TypeVar("T")


def ensure_connection(method: Callable[..., T]) -> Callable[..., T]:
    """Decorator to ensure database connection is available."""

    @wraps(method)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> T:
        if hasattr(self, "_ensure_connection"):
            self._ensure_connection()
        elif hasattr(self, "_sqlite_conn") and not self._sqlite_conn:
            raise RuntimeError("Database not initialized")
        return await method(self, *args, **kwargs)

    return wrapper


def with_transaction(method: Callable[..., T]) -> Callable[..., T]:
    """Decorator to wrap method in a database transaction."""

    @wraps(method)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> T:
        async with self._lock:
            conn = self._ensure_connection()
            async with conn.transaction():
                return await method(self, conn, *args, **kwargs)

    return wrapper


class SQLBuilder:
    """Builder for common SQL patterns."""

    @staticmethod
    def insert_or_replace(
        table: str,
        columns: list[str],
        mode: str = "skip",
        on_conflict: str | None = None,
    ) -> str:
        """Build INSERT or INSERT OR REPLACE query."""
        placeholders = ", ".join(["?" for _ in columns])
        columns_str = ", ".join(columns)

        if mode == "skip":
            query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
            if on_conflict:
                query = f"INSERT OR IGNORE INTO {table} ({columns_str}) VALUES ({placeholders})"
        else:  # overwrite
            query = f"INSERT OR REPLACE INTO {table} ({columns_str}) VALUES ({placeholders})"

        return query

    @staticmethod
    def build_where_clause(conditions: dict[str, Any]) -> tuple[str, list[Any]]:
        """Build WHERE clause from conditions dictionary."""
        where_parts = []
        params: list[Any] = []

        for key, value in conditions.items():
            if value is None:
                continue
            if isinstance(value, list | tuple) and len(value) == 2:
                # Range condition
                where_parts.append(f"{key} BETWEEN ? AND ?")
                params.extend(value)
            elif isinstance(value, list | tuple):
                # IN condition
                placeholders = ", ".join(["?" for _ in value])
                where_parts.append(f"{key} IN ({placeholders})")
                params.extend(value)
            elif isinstance(value, str) and "%" in value:
                # LIKE condition
                where_parts.append(f"{key} LIKE ?")
                params.append(value)
            else:
                # Equality condition
                where_parts.append(f"{key} = ?")
                params.append(value)

        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        return where_clause, params


class CSVFormatter:
    """Utility for CSV formatting."""

    @staticmethod
    def format_row(values: list[Any], types: list[str] | None = None) -> str:
        """Format a row for CSV output."""
        formatted = []
        for i, value in enumerate(values):
            if types and i < len(types):
                if types[i] == "float":
                    formatted.append(f"{value:.4f}" if value is not None else "")
                elif types[i] == "string":
                    formatted.append(f'"{value}"' if value is not None else '""')
                else:
                    formatted.append(str(value) if value is not None else "")
            else:
                formatted.append(str(value) if value is not None else "")
        return ",".join(formatted)

    @staticmethod
    def format_keywords(keywords: list[str], separator: str = "|") -> str:
        """Format keywords list for CSV."""
        return separator.join(keywords) if keywords else ""


async def execute_batch_insert(
    conn: aiosqlite.Connection,
    table: str,
    columns: list[str],
    records: list[tuple[Any, ...]],
    mode: str = "skip",
) -> dict[str, int]:
    """Execute batch insert with statistics using executemany for performance."""
    stats = {"inserted": 0, "skipped": 0}

    if not records:
        return stats

    query = SQLBuilder.insert_or_replace(table, columns, mode)

    # Use executemany for better performance
    if mode == "skip":
        # For skip mode, we need to handle integrity errors
        # Try batch insert first, fall back to individual inserts if needed
        try:
            await conn.executemany(query, records)
            stats["inserted"] = len(records)
        except aiosqlite.IntegrityError:
            # Fall back to individual inserts to track which ones fail
            for record in records:
                try:
                    await conn.execute(query, record)
                    stats["inserted"] += 1
                except aiosqlite.IntegrityError:
                    stats["skipped"] += 1
    else:
        # For overwrite mode, executemany should work without issues
        await conn.executemany(query, records)
        stats["inserted"] = len(records)

    return stats
