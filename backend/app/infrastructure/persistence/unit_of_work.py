from __future__ import annotations

from types import TracebackType
from typing import List, Optional, Type

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.shared.interfaces.unit_of_work_interface import IUnitOfWork
from backend.app.domain.shared.domain_event import DomainEvent
from backend.app.infrastructure.events.event_dispatcher import EventDispatcher


class SQLAlchemyUnitOfWork(IUnitOfWork):
    """
    SQLAlchemy async UnitOfWork implementation.

    On commit():
    1. Flushes the session
    2. Commits the transaction
    3. Collects all pending domain events from tracked entities
    4. Dispatches them via EventDispatcher

    On rollback(): rolls back and clears the session.
    """

    def __init__(
        self,
        session: AsyncSession,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._session = session
        self._dispatcher = event_dispatcher
        self._pending_events: List[DomainEvent] = []

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        await self._session.close()

    @property
    def session(self) -> AsyncSession:
        return self._session

    def register_events(self, events: List[DomainEvent]) -> None:
        """Called by handlers to queue domain events before commit."""
        self._pending_events.extend(events)

    async def commit(self) -> None:
        await self._session.flush()
        await self._session.commit()
        # Dispatch events AFTER commit so handlers see committed data
        events = list(self._pending_events)
        self._pending_events.clear()
        for event in events:
            await self._dispatcher.dispatch(event)

    async def work(self) -> None:
        """Alias for commit() — used by command handlers for semantic clarity."""
        await self.commit()

    async def rollback(self) -> None:
        self._pending_events.clear()
        await self._session.rollback()
