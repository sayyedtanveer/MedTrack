import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

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
    making_charge: Optional[Decimal] = Field(None, ge=0, description="Outside making charge per unit (PER_PIECE)")
    making_charge_basis: Optional[str] = Field(None, description="Rate basis; currently only 'PER_PIECE' is supported")

    @model_validator(mode="after")
    def check_exactly_one_product(self):
        refs = [x for x in (self.template_id, self.variant_id) if x is not None]
        if len(refs) != 1:
            raise ValueError("Exactly one of template_id or variant_id must be provided.")
        return self

    @model_validator(mode="after")
    def check_making_charge_paired(self):
        if (self.making_charge is None) != (self.making_charge_basis is None):
            raise ValueError(
                "making_charge and making_charge_basis must both be provided or both be absent."
            )
        if self.making_charge_basis is not None and self.making_charge_basis.upper() != "PER_PIECE":
            raise ValueError(
                f"making_charge_basis '{self.making_charge_basis}' is not supported. "
                "Only 'PER_PIECE' is currently supported."
            )
        return self


class UpdateBOMRequest(BaseModel):
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    approved_by: Optional[uuid.UUID] = None
    lines: Optional[List[BOMLineRequest]] = None
    making_charge: Optional[Decimal] = Field(None, ge=0, description="Set/update outside making charge")
    making_charge_basis: Optional[str] = Field(None, description="Rate basis ('PER_PIECE')")
    clear_making_charge: bool = Field(False, description="Set True to remove the making charge from this BOM")


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
    making_charge: Optional[Decimal] = None
    making_charge_basis: Optional[str] = None

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
    making_cost: Decimal = Decimal("0")  # Outside making charge component
    total_cost: Decimal
    currency_code: Optional[str] = None
    currency_symbol: Optional[str] = None
    # Phase 2B: Cost completeness fields (optional for backward compatibility)
    is_complete: Optional[bool] = None
    missing_costs: Optional[List["MissingCostDetail"]] = None

class MissingCostDetail(BaseModel):
    """Details of a component (material or operation) missing cost in BOM."""
    
    component_type: Literal["material", "operation", "bom"] = Field(
        ...,
        description="Material, operation or unresolved child BOM"
    )
    component_id: UUID = Field(
        ...,
        description="ID of the material or operation"
    )
    name: str = Field(
        ...,
        description="Human-readable name of the component"
    )
    code: Optional[str] = Field(
        None,
        description="Component code (if available)"
    )
    quantity: Optional[Decimal] = Field(
        None,
        description="Quantity of component in BOM"
    )
    unit: Optional[str] = Field(
        None,
        description="Unit of measure for quantity"
    )
    reason: Optional[str] = None
    message: Optional[str] = None

