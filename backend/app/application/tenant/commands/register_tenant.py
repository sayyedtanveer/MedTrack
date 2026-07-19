from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from backend.app.application.shared.command import Command


@dataclass
class RegisterTenantCommand(Command):
    """Register a new tenant and create its first admin user."""

    name: str = ""
    slug: str = ""
    admin_email: str = ""
    admin_password: str = ""
    admin_first_name: str = ""
    admin_last_name: str = ""
    plan: str = "starter"

    # Override: no user_id yet at registration time
    tenant_id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
