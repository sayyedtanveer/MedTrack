import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class BOMLineInput:
    quantity: Decimal
    scrap_percentage: Decimal = Decimal("0")
    unit_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None


@dataclass
class CreateBOMCommand:
    tenant_id: uuid.UUID
    created_by: uuid.UUID
    version: str
    valid_from: datetime
    lines: List[BOMLineInput] = field(default_factory=list)
    template_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None
    valid_to: Optional[datetime] = None
    approved_by: Optional[uuid.UUID] = None


@dataclass
class UpdateBOMCommand:
    bom_id: uuid.UUID
    tenant_id: uuid.UUID
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    approved_by: Optional[uuid.UUID] = None
    lines: Optional[List[BOMLineInput]] = None


@dataclass
class CopyBOMCommand:
    bom_id: uuid.UUID
    tenant_id: uuid.UUID
    new_version: str
    created_by: uuid.UUID


@dataclass
class ActivateBOMCommand:
    bom_id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass
class DeleteBOMCommand:
    bom_id: uuid.UUID
    tenant_id: uuid.UUID
