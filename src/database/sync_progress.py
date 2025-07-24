"""Sync progress tracking for resume capability."""

from datetime import date, datetime
from pathlib import Path

import aiosqlite
import msgspec


class SyncProgress(msgspec.Struct, kw_only=True):
    """Sync progress tracking model."""

    site_id: int
    sync_type: str = "daily"  # daily or hourly
    last_completed_date: date | None = None
    total_days_requested: int
    days_completed: int = 0
    records_synced: int = 0
    started_at: datetime
    last_updated: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class SyncProgressTracker:
    """Track sync progress for resume capability."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Initialize progress tracking table."""
        self._conn = await aiosqlite.connect(self.db_path)

        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                sync_type TEXT NOT NULL DEFAULT 'daily',
                last_completed_date DATE,
                total_days_requested INTEGER NOT NULL,
                days_completed INTEGER DEFAULT 0,
                records_synced INTEGER DEFAULT 0,
                started_at TIMESTAMP NOT NULL,
                last_updated TIMESTAMP,
                completed_at TIMESTAMP,
                error TEXT,
                UNIQUE(site_id, sync_type, started_at)
            )
        """)

        # Index for quick lookups
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sync_progress_lookup
            ON sync_progress(site_id, sync_type, completed_at)
        """)

        if self._conn:
            await self._conn.commit()

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()

    async def start_sync(self, site_id: int, total_days: int, sync_type: str = "daily") -> int:
        """Start a new sync session and return progress ID."""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        cursor = await self._conn.execute(
            """
            INSERT INTO sync_progress
            (site_id, sync_type, total_days_requested, started_at)
            VALUES (?, ?, ?, ?)
        """,
            (site_id, sync_type, total_days, datetime.now()),
        )

        if self._conn:
            await self._conn.commit()
        return cursor.lastrowid or 0

    async def update_progress(
        self,
        progress_id: int,
        last_completed_date: date,
        days_completed: int,
        records_synced_today: int,
    ) -> None:
        """Update sync progress after completing a day."""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        await self._conn.execute(
            """
            UPDATE sync_progress
            SET last_completed_date = ?,
                days_completed = ?,
                records_synced = records_synced + ?,
                last_updated = ?
            WHERE id = ?
        """,
            (
                last_completed_date.isoformat(),
                days_completed,
                records_synced_today,
                datetime.now(),
                progress_id,
            ),
        )

        if self._conn:
            await self._conn.commit()

    async def complete_sync(self, progress_id: int) -> None:
        """Mark sync as completed."""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        await self._conn.execute(
            """
            UPDATE sync_progress
            SET completed_at = ?
            WHERE id = ?
        """,
            (datetime.now(), progress_id),
        )

        if self._conn:
            await self._conn.commit()

    async def fail_sync(self, progress_id: int, error: str) -> None:
        """Mark sync as failed with error."""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        await self._conn.execute(
            """
            UPDATE sync_progress
            SET error = ?,
                last_updated = ?
            WHERE id = ?
        """,
            (error[:500], datetime.now(), progress_id),
        )  # Limit error message length

        if self._conn:
            await self._conn.commit()

    async def get_incomplete_sync(self, site_id: int, sync_type: str = "daily") -> dict | None:
        """Get the most recent incomplete sync for a site."""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        cursor = await self._conn.execute(
            """
            SELECT id, last_completed_date, days_completed,
                   total_days_requested, started_at
            FROM sync_progress
            WHERE site_id = ?
                AND sync_type = ?
                AND completed_at IS NULL
                AND error IS NULL
            ORDER BY started_at DESC
            LIMIT 1
        """,
            (site_id, sync_type),
        )

        row = await cursor.fetchone()
        if row:
            return {
                "progress_id": row[0],
                "last_completed_date": date.fromisoformat(row[1]) if row[1] else None,
                "days_completed": row[2],
                "total_days_requested": row[3],
                "started_at": datetime.fromisoformat(row[4]),
            }
        return None

    async def cleanup_old_progress(self, days_to_keep: int = 30) -> None:
        """Clean up old completed sync records."""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        await self._conn.execute(
            """
            DELETE FROM sync_progress
            WHERE completed_at IS NOT NULL
                AND completed_at < datetime('now', '-' || ? || ' days')
        """,
            (days_to_keep,),
        )

        if self._conn:
            await self._conn.commit()
