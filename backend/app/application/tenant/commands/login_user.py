from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from backend.app.application.shared.command import Command


@dataclass
class LoginUserCommand(Command):
    """Authenticate a user and return a JWT access token."""

    email: str = ""
    password: str = ""

    # Before authentication, tenant_id must be identified from request context
    tenant_id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
