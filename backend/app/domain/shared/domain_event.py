from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """
    Base class for all domain events.

    Domain events are raised by aggregates and dispatched by the
    InMemoryEventBus after the UnitOfWork commits.
    """

    aggregate_id: uuid.UUID
    tenant_id: uuid.UUID
    event_type: str

    # Auto-generated at creation time
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    correlation_id: Optional[uuid.UUID] = field(default=None)

    def __str__(self) -> str:
        return (
            f"{self.event_type}("
            f"event_id={self.event_id}, "
            f"aggregate_id={self.aggregate_id}, "
            f"tenant_id={self.tenant_id}, "
            f"occurred_at={self.occurred_at.isoformat()}"
            f")"
        )
