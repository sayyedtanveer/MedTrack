from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Command:
    """
    Base class for all CQRS commands.

    Commands represent intent to change state.
    They carry the identity context needed for authorization and auditing.
    """

    tenant_id: uuid.UUID
    user_id: uuid.UUID
    correlation_id: uuid.UUID = field(default_factory=uuid.uuid4)
