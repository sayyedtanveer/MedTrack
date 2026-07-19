from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from backend.app.domain.shared.domain_event import DomainEvent

E = TypeVar("E", bound=DomainEvent)


class IEventHandler(Generic[E]):
    """
    Base class for all domain event handlers.

    Register with InMemoryEventBus.subscribe(event_type, handler) at startup
    (via Container or main.py lifespan).

    Example:
        class AuditLogEventHandler(IEventHandler[TenantCreated]):
            @property
            def event_type(self) -> str:
                return "tenant.created"

            async def handle(self, event: TenantCreated) -> None:
                await self.audit_service.log_action(...)
    """

    @abstractmethod
    async def handle(self, event: E) -> None:
        """Process the given domain event."""
        ...

    @property
    @abstractmethod
    def event_type(self) -> str:
        """
        The event_type string this handler subscribes to.
        Use "*" to subscribe to all events (wildcard).
        """
        ...
