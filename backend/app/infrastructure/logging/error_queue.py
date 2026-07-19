from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

# Maximum queue size (to prevent unbounded memory usage)
MAX_QUEUE_SIZE = 1000


@dataclass
class ErrorLogPayload:
    """Serializable representation of an error log for queuing."""

    id: str  # UUID string
    trace_id: str  # UUID string
    timestamp: str  # ISO format datetime
    status_code: int
    error_code: str
    error_type: str
    error_message: str
    file_name: Optional[str]
    line_number: Optional[int]
    stack_trace: Optional[str]
    path: str
    method: str
    request_body: Optional[str]
    request_body_truncated: bool
    query_params: Optional[Dict[str, Any]]
    headers: Optional[Dict[str, Any]]
    tenant_id: Optional[str]  # UUID string
    user_id: Optional[str]  # UUID string
    ip_address: Optional[str]
    correlation_id: Optional[str]


class ErrorLogQueue:
    """
    In-memory FIFO queue for error logs.
    
    Used for fallback persistence when database write fails.
    Allows graceful degradation: errors are queued locally
    and replayed when database becomes available.
    
    Thread-safe queue (uses asyncio.Queue or deque with lock).
    Bounded to MAX_QUEUE_SIZE to prevent memory bloat.
    
    Typically used by ErrorLogger when repository.save_error() fails.
    Drained by background worker in ErrorLogQueueWorker (Phase 2).
    """

    def __init__(self):
        """Initialize empty queue."""
        self._queue: deque = deque(maxlen=MAX_QUEUE_SIZE)
        self._lock = asyncio.Lock()
        self._stats = {"enqueued": 0, "discarded": 0, "current_size": 0}

    async def enqueue(self, payload: ErrorLogPayload) -> bool:
        """
        Add error log to queue.
        
        Args:
            payload: ErrorLogPayload instance
            
        Returns:
            True if enqueued, False if queue was full
        """
        try:
            async with self._lock:
                if len(self._queue) >= MAX_QUEUE_SIZE:
                    self._stats["discarded"] += 1
                    logger.warning(
                        "Error log queue full, dropping oldest entry",
                        extra={
                            "queue_size": len(self._queue),
                            "max_size": MAX_QUEUE_SIZE,
                        },
                    )
                
                self._queue.append(asdict(payload))
                self._stats["enqueued"] += 1
                self._stats["current_size"] = len(self._queue)
                return True
        except Exception as exc:
            logger.error("Failed to enqueue error log", extra={"error": str(exc)})
            return False

    async def dequeue_batch(self, batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve up to batch_size error logs from queue (FIFO).
        
        Args:
            batch_size: Maximum number of items to pop
            
        Returns:
            List of error log payloads (dicts)
        """
        try:
            async with self._lock:
                batch = []
                for _ in range(min(batch_size, len(self._queue))):
                    batch.append(self._queue.popleft())
                self._stats["current_size"] = len(self._queue)
                return batch
        except Exception as exc:
            logger.error("Failed to dequeue error log batch", extra={"error": str(exc)})
            return []

    async def size(self) -> int:
        """Return current queue size."""
        async with self._lock:
            return len(self._queue)

    def get_stats(self) -> Dict[str, Any]:
        """
        Return queue statistics.
        
        Returns:
            Dict with keys: enqueued, discarded, current_size
        """
        return self._stats.copy()

    async def clear(self) -> None:
        """Clear all items from queue (for testing/admin)."""
        async with self._lock:
            self._queue.clear()
            self._stats["current_size"] = 0


# Global singleton instance (created per application)
_error_log_queue: Optional[ErrorLogQueue] = None


def get_error_log_queue() -> ErrorLogQueue:
    """Get or create the singleton error log queue."""
    global _error_log_queue
    if _error_log_queue is None:
        _error_log_queue = ErrorLogQueue()
    return _error_log_queue
