from __future__ import annotations

from backend.app.domain.shared.domain_event import DomainEvent
from backend.app.infrastructure.events.event_bus import InMemoryEventBus
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class EventDispatcher:
    """
    Singleton-style event dispatcher.

    Wraps InMemoryEventBus and adds logging. Registered at startup
    via Container, passed to UnitOfWork for post-commit dispatch.
    """

    def __init__(self, bus: InMemoryEventBus) -> None:
        self._bus = bus

    async def dispatch(self, event: DomainEvent) -> None:
        logger.debug(
            "Dispatching domain event",
            extra={
                "event_type": event.event_type,
                "event_id": str(event.event_id),
                "aggregate_id": str(event.aggregate_id),
                "tenant_id": str(event.tenant_id),
            },
        )
        await self._bus.publish(event)

    def subscribe(self, event_type: str, handler) -> None:
        self._bus.subscribe(event_type, handler)

    def subscribe_all(self, handler) -> None:
        self._bus.subscribe_all(handler)
