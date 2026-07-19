from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from backend.app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True)
class UserCreated(DomainEvent):
    """Fired when a new user is created within a tenant."""

    user_email: str = ""
    user_role: str = ""
    event_type: str = field(default="user.created", init=False)

    def __init__(
        self,
        aggregate_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_email: str,
        user_role: str,
        **kwargs,
    ) -> None:
        object.__setattr__(self, "user_email", user_email)
        object.__setattr__(self, "user_role", user_role)
        object.__setattr__(self, "event_type", "user.created")
        super().__init__(
            aggregate_id=aggregate_id,
            tenant_id=tenant_id,
            event_type="user.created",
            **kwargs,
        )
