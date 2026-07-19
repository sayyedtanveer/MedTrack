from __future__ import annotations

from abc import abstractmethod


class IBackgroundTask:
    """
    Abstract base for all background tasks.

    Implement execute() with the task's async logic.
    Swap BackgroundTaskService for Celery/ARQ later by changing the enqueue logic only.
    """

    @abstractmethod
    async def execute(self) -> None: ...

    @property
    def task_name(self) -> str:
        return self.__class__.__name__
