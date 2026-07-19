from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from backend.app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True)
class TenantCreated(DomainEvent):
    """Fired when a new tenant is registered."""

    tenant_name: str = ""
    slug: str = ""
    admin_email: str = ""
    event_type: str = field(default="tenant.created", init=False)

    def __init__(
        self,
        aggregate_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_name: str,
        slug: str,
        admin_email: str,
        **kwargs,
    ) -> None:
        object.__setattr__(self, "tenant_name", tenant_name)
        object.__setattr__(self, "slug", slug)
        object.__setattr__(self, "admin_email", admin_email)
        object.__setattr__(self, "event_type", "tenant.created")
        super().__init__(
            aggregate_id=aggregate_id,
            tenant_id=tenant_id,
            event_type="tenant.created",
            **kwargs,
        )
