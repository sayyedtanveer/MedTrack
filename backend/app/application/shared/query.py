from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Query:
    """
    Base class for all CQRS queries.

    Queries are read-only — no state changes.
    """

    tenant_id: uuid.UUID
    page: int = 1
    page_size: int = 20
    filters: Dict[str, Any] = field(default_factory=dict)
    correlation_id: uuid.UUID = field(default_factory=uuid.uuid4)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
