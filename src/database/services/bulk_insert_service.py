"""Bulk insert service for optimized database operations."""

from datetime import datetime

from ...models import PerformanceData
from ..buffers import PerformanceDataBuffer


class BulkInsertService:
    """Service for high-performance bulk data insertion with index management."""

    def __init__(
        self,
        db_instance,
        batch_size: int = 10000,
        buffer_size: int = 50000,
        use_index_optimization: bool = True,
        fast_mode: bool = False,
    ):
        """
        Initialize bulk insert service.

        Args:
            db_instance: HybridDataStore instance
            batch_size: Number of records per database batch
            buffer_size: Maximum buffer size before auto-flush
            use_index_optimization: Whether to drop/recreate indexes for large imports
            fast_mode: Enable aggressive optimizations (less safe)
        """
        self.db = db_instance
        self.batch_size = batch_size
        self.buffer_size = buffer_size
        self.use_index_optimization = use_index_optimization
        self.fast_mode = fast_mode

        self._buffer: PerformanceDataBuffer | None = None
        self._total_stats = {"inserted": 0, "skipped": 0, "updated": 0}
        self._index_dropped = False

    async def __aenter__(self):
        """Context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.finalize()

    async def initialize(self) -> None:
        """Initialize the bulk insert service."""
        # Enable fast insert mode if requested
        if self.fast_mode:
            await self.db.set_fast_insert_mode(True)

        # Start auto-flush for buffer
        if self._buffer:
            await self._buffer.start_auto_flush()

    async def finalize(self) -> dict[str, int]:
        """Finalize bulk insert and return statistics."""
        # Flush any remaining data
        if self._buffer:
            stats = await self._buffer.close()
            self._update_stats(stats)

        # Recreate indexes if they were dropped
        if self._index_dropped:
            await self.db.recreate_performance_indexes()
            self._index_dropped = False

        # Disable fast insert mode
        if self.fast_mode:
            await self.db.set_fast_insert_mode(False)

        # Run ANALYZE to update statistics
        # COMMENTED OUT: ANALYZE is too slow for large datasets (2M+ records)
        # Run manually with 'just analyze' when needed
        # print("Updating database statistics...")
        # async with self.db._lock:
        #     if self.db._sqlite_conn:
        #         await self.db._sqlite_conn.execute("ANALYZE gsc_performance_data")
        #         await self.db._sqlite_conn.commit()

        return self._total_stats

    async def insert_batch(
        self, records: list[PerformanceData], mode: str = "skip"
    ) -> dict[str, int]:
        """
        Insert a batch of records with optimal performance.

        Args:
            records: List of PerformanceData objects
            mode: Insert mode ('skip' or 'overwrite')

        Returns:
            Dictionary with insertion statistics
        """
        if not records:
            return {"inserted": 0, "skipped": 0}

        # Check if we should drop indexes for large batches
        total_records = self._total_stats["inserted"] + len(records)
        if (
            self.use_index_optimization
            and not self._index_dropped
            and total_records > 100000  # Threshold for dropping indexes
        ):
            await self.db.drop_performance_indexes()
            self._index_dropped = True

        # Initialize buffer if not exists
        if not self._buffer:
            self._buffer = PerformanceDataBuffer(
                self.db,
                mode=mode,
                batch_size=self.batch_size,
                flush_interval=60.0,  # Flush every minute
                max_memory_mb=100,
            )

        # Add records to buffer
        await self._buffer.add_batch(records)

        # Check if we should flush
        if len(self._buffer) >= self.buffer_size:
            stats = await self._buffer.flush()
            self._update_stats(stats)
            return stats

        return {"inserted": 0, "skipped": 0, "buffered": len(records)}

    async def insert_day_data(
        self,
        daily_records: list[PerformanceData],
        mode: str = "skip",
        progress_callback=None,
    ) -> dict[str, int]:
        """
        Insert data for a single day with progress tracking.

        Args:
            daily_records: Records for a single day
            mode: Insert mode
            progress_callback: Optional callback for progress updates

        Returns:
            Statistics dictionary
        """
        start_time = datetime.now()

        # Process in chunks
        total_processed = 0
        day_stats = {"inserted": 0, "skipped": 0, "updated": 0}

        for i in range(0, len(daily_records), self.batch_size):
            chunk = daily_records[i : i + self.batch_size]
            stats = await self.insert_batch(chunk, mode)

            # Update statistics
            day_stats["inserted"] += stats.get("inserted", 0)
            day_stats["skipped"] += stats.get("skipped", 0)
            day_stats["updated"] += stats.get("updated", 0)

            total_processed += len(chunk)

            # Call progress callback if provided
            if progress_callback:
                await progress_callback(total_processed, len(daily_records))

        # Force flush after each day
        if self._buffer and not self._buffer.is_empty:
            flush_stats = await self._buffer.flush()
            day_stats["inserted"] += flush_stats.get("inserted", 0)
            day_stats["skipped"] += flush_stats.get("skipped", 0)

        duration = (datetime.now() - start_time).total_seconds()
        if daily_records:
            records_per_sec = len(daily_records) / duration if duration > 0 else 0
            print(
                f"    Processed {len(daily_records)} records in {duration:.2f}s "
                f"({records_per_sec:.0f} records/sec)"
            )

        self._update_stats(day_stats)
        return day_stats

    def _update_stats(self, stats: dict[str, int]) -> None:
        """Update total statistics."""
        self._total_stats["inserted"] += stats.get("inserted", 0)
        self._total_stats["skipped"] += stats.get("skipped", 0)
        self._total_stats["updated"] += stats.get("updated", 0)

    @property
    def total_stats(self) -> dict[str, int]:
        """Get total statistics."""
        return self._total_stats.copy()

    async def optimize_for_bulk_load(self) -> None:
        """Apply all optimizations for bulk loading."""
        # Drop indexes
        if self.use_index_optimization and not self._index_dropped:
            await self.db.drop_performance_indexes()
            self._index_dropped = True

        # Enable fast mode
        await self.db.set_fast_insert_mode(True)

        # Additional optimizations
        async with self.db._lock:
            if self.db._sqlite_conn:
                # Increase page size for bulk operations
                await self.db._sqlite_conn.execute("PRAGMA page_size = 8192")
                # Disable auto-vacuum during bulk load
                await self.db._sqlite_conn.execute("PRAGMA auto_vacuum = NONE")
                # Increase WAL size
                await self.db._sqlite_conn.execute("PRAGMA wal_autocheckpoint = 10000")
