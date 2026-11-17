"""Read-side contract shared by BOM browsing and current cost calculation."""
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from backend.app.domain.bom.entities.bom import BillOfMaterial
from backend.app.domain.bom.entities.bom_line import BOMLine


class BOMResolutionError(ValueError):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass
class ComponentResolution:
    child_bom: BillOfMaterial | None = None
    details: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    message: str | None = None


class ComponentResolver(Protocol):
    async def resolve_component(self, tenant_id: UUID, line: BOMLine) -> ComponentResolution:
        ...
