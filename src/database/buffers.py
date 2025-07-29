"""Buffer management for efficient database writes."""

import asyncio
from collections import deque
from datetime import datetime, timedelta
from typing import Generic, TypeVar

from src.models import PerformanceData

T = TypeVar("T")


class BufferedWriter(Generic[T]):
    """
    A generic buffered writer that accumulates records and flushes them in batches.

    This reduces I/O operations significantly by batching writes together.
    """

    def __init__(
        self,
        flush_callback,
        batch_size: int = 10000,
        flush_interval: float = 30.0,
        max_memory_mb: int = 100,
    ):
        """
        Initialize the buffered writer.

        Args:
            flush_callback: Async function to call when flushing the buffer
            batch_size: Number of records to accumulate before auto-flushing
            flush_interval: Maximum seconds to wait before auto-flushing
            max_memory_mb: Maximum memory usage in MB before forcing flush
        """
        self.flush_callback = flush_callback
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_memory_mb = max_memory_mb

        self.buffer: deque[T] = deque()
        self.last_flush = datetime.now()
        self._lock = asyncio.Lock()
        self._flush_task = None
        self._closed = False

    async def add(self, record: T) -> None:
        """Add a record to the buffer."""
        async with self._lock:
            if self._closed:
                raise RuntimeError("BufferedWriter is closed")

            self.buffer.append(record)

            # Check if we should flush
            if await self._should_flush():
                await self._flush()

    async def add_batch(self, records: list[T]) -> None:
        """Add multiple records to the buffer."""
        async with self._lock:
            if self._closed:
                raise RuntimeError("BufferedWriter is closed")

            self.buffer.extend(records)

            # Check if we should flush
            if await self._should_flush():
                await self._flush()

    async def _should_flush(self) -> bool:
        """Check if the buffer should be flushed."""
        # Check batch size
        if len(self.buffer) >= self.batch_size:
            return True

        # Check time interval
        if datetime.now() - self.last_flush > timedelta(seconds=self.flush_interval):
            return True

        # Check memory usage (simplified estimation)
        estimated_memory_mb = len(self.buffer) * 0.001  # Rough estimate: 1KB per record
        if estimated_memory_mb >= self.max_memory_mb:
            return True

        return False

    async def _flush(self) -> dict[str, int]:
        """Flush the buffer to the database."""
        if not self.buffer:
            return {"flushed": 0}

        # Extract records to flush
        records_to_flush = list(self.buffer)
        self.buffer.clear()

        # Call the flush callback
        stats = await self.flush_callback(records_to_flush)

        self.last_flush = datetime.now()
        return stats

    async def flush(self) -> dict[str, int]:
        """Manually flush the buffer."""
        async with self._lock:
            return await self._flush()

    async def close(self) -> dict[str, int]:
        """Close the writer and flush any remaining records."""
        async with self._lock:
            if self._closed:
                return {"flushed": 0}

            stats = await self._flush()
            self._closed = True

            if self._flush_task:
                self._flush_task.cancel()

            return stats

    def __len__(self) -> int:
        """Return the current buffer size."""
        return len(self.buffer)

    @property
    def is_empty(self) -> bool:
        """Check if the buffer is empty."""
        return len(self.buffer) == 0


class PerformanceDataBuffer(BufferedWriter[PerformanceData]):
    """Specialized buffer for GSC performance data."""

    def __init__(self, db_instance, mode: str = "skip", **kwargs):
        """
        Initialize performance data buffer.

        Args:
            db_instance: Database instance with insert_performance_data_batch method
            mode: Insert mode ('skip' or 'overwrite')
            **kwargs: Additional arguments for BufferedWriter
        """
        self.db = db_instance
        self.mode = mode

        async def flush_callback(records: list[PerformanceData]) -> dict[str, int]:
            return await self.db.insert_performance_data_batch(records, mode=self.mode)

        super().__init__(flush_callback, **kwargs)

    async def start_auto_flush(self) -> None:
        """Start automatic flushing based on time intervals."""

        async def auto_flush_loop():
            while not self._closed:
                await asyncio.sleep(self.flush_interval)
                async with self._lock:
                    if not self._closed and len(self.buffer) > 0:
                        await self._flush()

        self._flush_task = asyncio.create_task(auto_flush_loop())
