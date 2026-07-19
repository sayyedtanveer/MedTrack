import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


# ── Line Schemas ─────────────────────────────────────────────────────────────

class BOMLineRequest(BaseModel):
    quantity: Decimal = Field(gt=0, description="Must be greater than zero")
    unit_id: Optional[uuid.UUID] = None
    scrap_percentage: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    material_id: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def check_exactly_one_component(self):
        refs = [x for x in (self.material_id, self.template_id, self.variant_id) if x is not None]
        if len(refs) != 1:
            raise ValueError("Exactly one of material_id, template_id, or variant_id must be provided.")
        return self


class BOMLineResponse(BaseModel):
    id: uuid.UUID
    bom_id: uuid.UUID
    quantity: Decimal
    scrap_percentage: Decimal
    unit_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class BOMOperationResponse(BaseModel):
    id: uuid.UUID
    bom_id: uuid.UUID
    operation_id: uuid.UUID
    sequence: int

    model_config = {"from_attributes": True}


# ── BOM Schemas ───────────────────────────────────────────────────────────────

class CreateBOMRequest(BaseModel):
    version: str = Field(min_length=1, max_length=50, examples=["v1.0"])
    valid_from: datetime
    template_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None
    valid_to: Optional[datetime] = None
    approved_by: Optional[uuid.UUID] = None
    lines: List[BOMLineRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_exactly_one_product(self):
        refs = [x for x in (self.template_id, self.variant_id) if x is not None]
        if len(refs) != 1:
            raise ValueError("Exactly one of template_id or variant_id must be provided.")
        return self


class UpdateBOMRequest(BaseModel):
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    approved_by: Optional[uuid.UUID] = None
    lines: Optional[List[BOMLineRequest]] = None


class CopyBOMRequest(BaseModel):
    new_version: str = Field(min_length=1, max_length=50, examples=["v1.1"])


class BOMResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    version: str
    is_active: bool
    valid_from: datetime
    valid_to: Optional[datetime] = None
    created_by: uuid.UUID
    approved_by: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    operations_count: int = 0
    lines: List[BOMLineResponse] = []
    operations: List[BOMOperationResponse] = []

    model_config = {"from_attributes": True}


class BOMListResponse(BaseModel):
    items: List[BOMResponse]
    total: int
    page: int
    page_size: int

class BOMCostResponse(BaseModel):
    bom_id: uuid.UUID
    material_cost: Decimal
    operation_cost: Decimal
    total_cost: Decimal
    currency_code: Optional[str] = None
    currency_symbol: Optional[str] = None
