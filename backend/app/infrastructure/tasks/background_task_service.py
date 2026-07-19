"""Background task service with exponential backoff retry.

Wraps FastAPI BackgroundTasks with retry logic and failure tracking so that
transient errors (network hiccups, DB connectivity) are retried before the
task is recorded as permanently failed.

Requirements: 46.1, 46.2, 46.4, 46.5
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import BackgroundTasks

from backend.app.infrastructure.logging.logger import get_logger
from backend.app.infrastructure.tasks.task_interface import IBackgroundTask

logger = get_logger(__name__)

# Exponential back-off delays (seconds) per attempt: 1 s, 4 s, 16 s
RETRY_DELAYS = [1, 4, 16]
MAX_RETRIES = 3


class BackgroundTaskService:
    """
    Enqueues IBackgroundTask instances via FastAPI BackgroundTasks.

    Each task is executed with up to MAX_RETRIES retries using exponential
    backoff.  If all attempts fail the failure is logged at ERROR level and
    (optionally) persisted to the ``failed_tasks`` DB table when a SQLAlchemy
    session factory is supplied.

    Usage in a route handler:
        task_service.enqueue(SendWelcomeEmailTask(...), bg_tasks=background_tasks)

    Swap for Celery/ARQ by overriding enqueue() — task implementations stay unchanged.
    """

    def __init__(self, session_factory=None) -> None:
        # Optional SQLAlchemy async session factory for persisting failed tasks.
        self._session_factory = session_factory

    def enqueue(
        self,
        task: IBackgroundTask,
        bg_tasks: BackgroundTasks,
        tenant_id: Optional[Any] = None,
    ) -> None:
        """Schedule task.execute() to run after the response is sent."""
        logger.debug("Enqueuing background task", extra={"task": task.task_name})
        bg_tasks.add_task(self._run_with_retry, task, tenant_id)

    async def _run_with_retry(
        self,
        task: IBackgroundTask,
        tenant_id: Optional[Any] = None,
    ) -> None:
        """Run *task* with exponential-backoff retry; record permanent failures."""
        last_exc: Optional[Exception] = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                await task.execute()
                if attempt > 0:
                    logger.info(
                        "Background task succeeded after retry",
                        extra={"task": task.task_name, "attempt": attempt + 1},
                    )
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(
                        "Background task failed, retrying",
                        extra={
                            "task": task.task_name,
                            "attempt": attempt + 1,
                            "retry_in_seconds": delay,
                            "error": str(exc),
                        },
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted — log and optionally persist.
        logger.error(
            "Background task permanently failed after all retries",
            extra={
                "task": task.task_name,
                "attempts": MAX_RETRIES + 1,
                "error": str(last_exc),
            },
        )
        await self._record_failure(task, last_exc, tenant_id)

    async def _record_failure(
        self,
        task: IBackgroundTask,
        exc: Optional[Exception],
        tenant_id: Optional[Any],
    ) -> None:
        """Persist the permanently failed task to the ``failed_tasks`` table."""
        if self._session_factory is None:
            # No DB wired up — failure already captured in the log above.
            return

        import json

        try:
            # Serialise task arguments where possible.
            try:
                arguments = {
                    k: v for k, v in vars(task).items() if not k.startswith("_")
                }
                arguments_json = json.loads(json.dumps(arguments, default=str))
            except Exception:  # noqa: BLE001
                arguments_json = None

            async with self._session_factory() as session:
                await session.execute(
                    # Raw INSERT so this layer has no ORM dependency.
                    __import__("sqlalchemy").text(
                        """
                        INSERT INTO failed_tasks
                          (id, tenant_id, task_name, arguments_json, error_message,
                           retry_count, failed_at, created_at)
                        VALUES
                          (:id, :tenant_id, :task_name, :args::jsonb, :error,
                           :retry_count, :failed_at, :created_at)
                        """
                    ),
                    {
                        "id": str(uuid4()),
                        "tenant_id": str(tenant_id) if tenant_id else None,
                        "task_name": task.task_name,
                        "args": json.dumps(arguments_json),
                        "error": str(exc),
                        "retry_count": MAX_RETRIES,
                        "failed_at": datetime.now(timezone.utc),
                        "created_at": datetime.now(timezone.utc),
                    },
                )
                await session.commit()
        except Exception as db_exc:  # noqa: BLE001
            logger.error(
                "Failed to persist task failure record to DB",
                extra={"task": task.task_name, "db_error": str(db_exc)},
            )


async def run_with_retry(task_name: str, coro_func, *args, **kwargs):
    """Standalone helper: run an async coroutine with exponential-backoff retry.

    Useful for one-off async calls outside the BackgroundTaskService lifecycle.

    Requirements: 46.1, 46.2
    """
    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return await coro_func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt]
                logger.warning(
                    f"Task '{task_name}' failed (attempt {attempt + 1}),"
                    f" retrying in {delay}s: {exc}"
                )
                await asyncio.sleep(delay)
    logger.error(
        f"Task '{task_name}' permanently failed after {MAX_RETRIES} retries: {last_exc}"
    )
    raise last_exc  # type: ignore[misc]
