from __future__ import annotations

import uuid
from dataclasses import dataclass

from backend.app.application.shared.query import Query


@dataclass
class GetTenantQuery(Query):
    """Retrieve a tenant by its ID."""
    target_tenant_id: uuid.UUID = None  # type: ignore[assignment]


@dataclass
class GetUserQuery(Query):
    """Retrieve a user by their ID within a tenant."""
    target_user_id: uuid.UUID = None  # type: ignore[assignment]
