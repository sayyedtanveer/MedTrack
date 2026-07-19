from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Optional, Type


class IUnitOfWork(ABC):
    """
    Unit of Work interface — groups repository operations into a
    single atomic transaction.

    Usage (in a command handler):
        async with uow:
            uow.tenant_repo.save(tenant)
            await uow.commit()   # also dispatches domain events
    """

    @abstractmethod
    async def __aenter__(self) -> "IUnitOfWork":
        ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        ...

    @abstractmethod
    async def commit(self) -> None:
        """Commit the transaction and dispatch domain events."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the transaction."""
        ...
