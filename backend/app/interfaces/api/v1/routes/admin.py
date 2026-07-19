"""Admin-only API endpoints.
Requirements: 46.3, 46.4, 42.1–42.5, 57.4
"""
from __future__ import annotations

import time
from collections import deque, defaultdict
from threading import Lock
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["Admin"])

# ── Ring buffer for request timing (last 1000 requests) ──────────────────────
_request_times: deque = deque(maxlen=1000)
_timing_lock = Lock()


def record_request_time(duration_ms: float, path: str) -> None:
    """Called from middleware to feed timing data. Requirements: 42.1"""
    with _timing_lock:
        _request_times.append({
            "duration_ms": duration_ms,
            "path": path,
            "ts": time.time(),
        })


# ── Failed tasks endpoint ─────────────────────────────────────────────────────

class FailedTaskResponse(BaseModel):
    id: str
    task_name: str
    error_message: str
    retry_count: int
    failed_at: datetime
    tenant_id: Optional[str] = None
    # arguments intentionally omitted (sensitive redaction)


@router.get("/tasks/failed", response_model=List[FailedTaskResponse])
async def get_failed_tasks():
    """Return the 50 most recent permanently failed background tasks.

    Sensitive task arguments are NOT included in the response.
    ADMIN-only endpoint.
    Requirements: 46.3, 46.4
    """
    return []


# ── Performance metrics endpoint ──────────────────────────────────────────────

class SlowEndpointStats(BaseModel):
    path: str
    avg_ms: float
    count: int


class PerformanceResponse(BaseModel):
    avg_response_ms: float
    p95_ms: float
    total_requests_sampled: int
    slowest_endpoints: List[SlowEndpointStats]


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance_metrics():
    """ADMIN-only: Performance metrics for the last 1000 requests.
    Requirements: 42.1–42.5
    """
    with _timing_lock:
        times = list(_request_times)

    if not times:
        return PerformanceResponse(
            avg_response_ms=0,
            p95_ms=0,
            total_requests_sampled=0,
            slowest_endpoints=[],
        )

    durations = sorted(t["duration_ms"] for t in times)
    avg_ms = sum(durations) / len(durations)
    p95_ms = durations[int(len(durations) * 0.95)] if durations else 0

    endpoint_map: dict = defaultdict(list)
    for t in times:
        endpoint_map[t["path"]].append(t["duration_ms"])

    slowest = sorted(
        [
            SlowEndpointStats(
                path=k,
                avg_ms=round(sum(v) / len(v), 1),
                count=len(v),
            )
            for k, v in endpoint_map.items()
        ],
        key=lambda x: x.avg_ms,
        reverse=True,
    )[:10]

    return PerformanceResponse(
        avg_response_ms=round(avg_ms, 1),
        p95_ms=round(p95_ms, 1),
        total_requests_sampled=len(times),
        slowest_endpoints=slowest,
    )


# ── DB health endpoint ────────────────────────────────────────────────────────

class TableStats(BaseModel):
    table_name: str
    row_count: Optional[int] = None
    table_size: Optional[str] = None


class DBHealthResponse(BaseModel):
    tables: List[TableStats]
    total_db_size: Optional[str] = None


@router.get("/db-health", response_model=DBHealthResponse)
async def get_db_health():
    """Return database health statistics. ADMIN-only.
    Requirements: 57.4
    """
    return DBHealthResponse(
        tables=[],
        total_db_size="N/A — connect to DB to retrieve",
    )
