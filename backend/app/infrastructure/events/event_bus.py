from __future__ import annotations

from backend.app.domain.shared.domain_event import DomainEvent
from backend.app.infrastructure.events.event_handler_interface import IEventHandler  # noqa: F401


class InMemoryEventBus:
    """
    In-memory event bus — dispatches domain events to registered handlers.

    Designed for drop-in replacement with Redis Pub/Sub or Kafka by
    swapping this class behind the EventDispatcher.

    Thread-safe for asyncio (single-threaded event loop).
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[IEventHandler]] = {}

    def subscribe(self, event_type: str, handler: IEventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: IEventHandler) -> None:
        """Subscribe to ALL events (wildcard). Useful for audit logging."""
        self.subscribe("*", handler)

    async def publish(self, event: DomainEvent) -> None:
        """Dispatch event to matching handlers + wildcard handlers."""
        handlers = (
            self._handlers.get(event.event_type, [])
            + self._handlers.get("*", [])
        )
        for handler in handlers:
            await handler.handle(event)
