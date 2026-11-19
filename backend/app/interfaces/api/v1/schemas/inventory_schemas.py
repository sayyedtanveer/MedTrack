from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ── Material Request Schemas ──────────────────────────────────────────────
class CreateMaterialRequest(BaseModel):
    code: Optional[str] = Field(None, max_length=50, description="Manual item code override")
    item_code: Optional[str] = Field(None, max_length=50, description="Manual item code override")
    name: str = Field(..., min_length=1, max_length=255)
    material_type: str = Field("raw", pattern="^(raw|finished|semi_finished)$")
    description: Optional[str] = Field(None, max_length=2000)
    category_id: Optional[uuid.UUID] = None
    base_unit_id: Optional[uuid.UUID] = None
    reorder_level: Optional[Decimal] = Field(None, ge=0)
    location_id: Optional[uuid.UUID] = None
    is_batch_tracked: bool = False
    is_serialized: bool = False
    code_locked: Optional[bool] = None
    opening_stock: Optional[Decimal] = Field(None, ge=0, description="Set initial stock on creation")

    @field_validator("code", "item_code", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Coerce empty/whitespace-only strings to None so frontend can send '' safely."""
        if isinstance(v, str) and not v.strip():
            return None
        return v


class UpdateMaterialRequest(BaseModel):
    code: Optional[str] = Field(None, max_length=50, description="Item code (immutable after creation)")
    item_code: Optional[str] = Field(None, max_length=50, description="Item code (immutable after creation)")
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    category_id: Optional[uuid.UUID] = None
    base_unit_id: Optional[uuid.UUID] = None
    material_type: Optional[str] = Field(None, pattern="^(raw|finished|semi_finished)$")
    reorder_level: Optional[Decimal] = Field(None, ge=0)
    location_id: Optional[uuid.UUID] = None
    is_batch_tracked: Optional[bool] = None
    is_serialized: Optional[bool] = None
    is_active: Optional[bool] = None
    current_cost: Optional[Decimal] = Field(None, ge=0, description="Standard cost per unit")
    inspection_required: Optional[bool] = None
    inspection_template_id: Optional[uuid.UUID] = None

    @field_validator("code", "item_code", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Coerce empty/whitespace-only strings to None so frontend can send '' safely."""
        if isinstance(v, str) and not v.strip():
            return None
        return v


# ── Transaction Request Schemas ───────────────────────────────────────────

class AssignExistingStockRequest(BaseModel):
    location_id: uuid.UUID
    remarks: str = Field("Opening stock location reconciliation", min_length=3, max_length=2000)


class AssignExistingStockResponse(BaseModel):
    material_id: uuid.UUID
    assigned_quantity: Decimal

class AddStockRequest(BaseModel):
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0, description="Quantity to add (must be positive)")
    unit_id: Optional[uuid.UUID] = None
    to_location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = Field(None, max_length=500)
    reference_id: Optional[uuid.UUID] = None


class RemoveStockRequest(BaseModel):
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0, description="Quantity to remove (must be positive)")
    unit_id: Optional[uuid.UUID] = None
    from_location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = Field(None, max_length=500)
    reference_id: Optional[uuid.UUID] = None


class AdjustStockRequest(BaseModel):
    material_id: uuid.UUID
    new_quantity: Decimal = Field(..., ge=0, description="New absolute stock quantity")
    unit_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = Field(None, max_length=500)


class TransactionRequest(BaseModel):
    """Unified transaction endpoint — client picks transaction_type."""
    material_id: uuid.UUID
    transaction_type: str = Field(..., pattern="^(in|out|transfer|adjustment)$")
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None
    from_location_id: Optional[uuid.UUID] = None
    to_location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = Field(None, max_length=500)
    reference_id: Optional[uuid.UUID] = None
    # For ADJUSTMENT, client may pass an absolute new_quantity instead
    new_quantity: Optional[Decimal] = Field(None, ge=0)


# ── Subcontractor Stock Detail ───────────────────────────────────────────
class SubcontractorStockDetail(BaseModel):
    """Details of stock at a specific subcontractor/vendor."""
    vendor_id: uuid.UUID
    vendor_name: str
    quantity: Decimal


# ── Material Response Schemas ─────────────────────────────────────────────
class MaterialResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    item_code: str
    item_type: str
    name: str
    material_type: str
    description: Optional[str]
    category_id: Optional[uuid.UUID]
    base_unit_id: Optional[uuid.UUID]
    current_stock: Decimal
    reserved_stock: Decimal
    available_stock: Decimal
    reorder_level: Optional[Decimal]
    location_id: Optional[uuid.UUID]
    is_batch_tracked: bool
    is_serialized: bool
    code_locked: bool
    inspection_required: bool = False
    inspection_template_id: Optional[uuid.UUID] = None
    is_active: bool
    is_low_stock: bool
    current_cost: Decimal = Decimal("0")
    created_at: Optional[datetime] = None
    
    # Purchasing summary fields
    latest_purchase_price: Optional[Decimal] = None
    last_purchase_date: Optional[date] = None
    last_supplier_name: Optional[str] = None
    last_supplier_id: Optional[uuid.UUID] = None
    purchase_count: int = 0
    
    # Location-based stock breakdown
    warehouse_stock: Decimal = Decimal("0")
    subcontractor_stock: Decimal = Decimal("0")
    subcontractor_details: List[SubcontractorStockDetail] = []
    
    # Phase 2C: Cost governance status (optional for backward compatibility)
    cost_status: Optional[Literal["CONFIGURED", "NOT_CONFIGURED", "PENDING_APPROVAL", "LEGACY"]] = Field(
        None,
        description="Material cost readiness status (only in list results)"
    )

    model_config = {"from_attributes": True}


class MaterialListResponse(BaseModel):
    items: List[MaterialResponse]
    total: int
    page: int
    page_size: int


# ── Stock Response Schemas ────────────────────────────────────────────────
class StockResponse(BaseModel):
    material_id: uuid.UUID
    material_code: str
    material_name: str
    current_stock: Decimal
    reserved_stock: Decimal
    available_stock: Decimal
    base_unit_id: Optional[uuid.UUID]
    is_low_stock: bool
    reorder_level: Optional[Decimal]


# ── Transaction Response Schemas ──────────────────────────────────────────
class TransactionResponse(BaseModel):
    id: uuid.UUID
    material_id: uuid.UUID
    transaction_type: str
    quantity: Decimal
    unit_id: Optional[uuid.UUID]
    from_location_id: Optional[uuid.UUID]
    to_location_id: Optional[uuid.UUID]
    reference_type: str
    reference_id: Optional[uuid.UUID]
    remarks: Optional[str]
    created_by: uuid.UUID
    created_at: str

    model_config = {"from_attributes": True}


# ── Phase 1.2 — Batch Schemas ────────────────────────────────────────────

class AddStockWithBatchRequest(BaseModel):
    material_id: uuid.UUID
    batch_number: str = Field(..., min_length=1, max_length=100)
    quantity: Decimal = Field(..., gt=0, description="Quantity to add (positive)")
    expiry_date: Optional[date] = None
    unit_id: Optional[uuid.UUID] = None
    to_location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = Field(None, max_length=500)
    reference_id: Optional[uuid.UUID] = None


class RemoveStockFromBatchRequest(BaseModel):
    material_id: uuid.UUID
    batch_number: str = Field(..., min_length=1, max_length=100)
    quantity: Decimal = Field(..., gt=0, description="Quantity to remove (positive)")
    unit_id: Optional[uuid.UUID] = None
    from_location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = Field(None, max_length=500)
    reference_id: Optional[uuid.UUID] = None


class BatchResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    batch_number: str
    quantity: Decimal
    remaining_quantity: Decimal
    expiry_date: Optional[date]
    location_id: Optional[uuid.UUID]
    status: str
    is_expired: bool
    days_until_expiry: Optional[int]
    created_at: str

    model_config = {"from_attributes": True}


class BatchListResponse(BaseModel):
    items: List[BatchResponse]
    total: int


# ── Phase 1.3 — Serial Schemas ────────────────────────────────────────────

class AddSerialStockRequest(BaseModel):
    material_id: uuid.UUID
    serial_numbers: List[str] = Field(..., min_length=1, description="List of unique serial number strings")
    location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = Field(None, max_length=500)


class IssueSerialRequest(BaseModel):
    serial_number: str = Field(..., min_length=1, max_length=255)
    reference_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = Field(None, max_length=500)


class ReturnSerialRequest(BaseModel):
    serial_number: str = Field(..., min_length=1, max_length=255)
    location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = Field(None, max_length=500)


class SerialNumberResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    serial_number: str
    status: str
    current_location_id: Optional[uuid.UUID]
    reference_id: Optional[uuid.UUID]
    created_at: str

    model_config = {"from_attributes": True}


class SerialNumberListResponse(BaseModel):
    items: List[SerialNumberResponse]
    total: int


class PurchaseHistoryItemResponse(BaseModel):
    date: Optional[str] = None
    supplier_id: uuid.UUID
    supplier_name: str
    po_number: str
    grn_number: str
    quantity: float
    uom: str
    unit_price: float
    total_value: float
    currency: str


class PurchaseHistoryPaginatedResponse(BaseModel):
    items: List[PurchaseHistoryItemResponse]
    total: int
    page: int
    page_size: int

# ── Material Cost Status Response Schema ────────────────────────────────────
class MaterialCostStatusResponse(BaseModel):
    """Cost readiness and governance status for a material."""
    
    material_id: uuid.UUID = Field(..., description="Material ID")
    has_approved_cost: bool = Field(
        ..., 
        description="True if material has an approved StandardCostRevision"
    )
    cost_status: Literal["CONFIGURED", "NOT_CONFIGURED", "PENDING_APPROVAL", "LEGACY"] = Field(
        ...,
        description="Current cost governance status"
    )
    current_cost: Decimal | None = None
    approved_cost: Optional[Decimal] = Field(
        None,
        description="Approved standard cost value (if exists)"
    )
    pending_revision_id: Optional[uuid.UUID] = Field(
        None,
        description="ID of pending revision awaiting approval (if exists)"
    )
    pending_revision_status: Optional[Literal["PENDING"]] = Field(
        None,
        description="Status of pending revision"
    )
    currency_code: str = Field(
        ...,
        description="Tenant currency code (e.g., INR)"
    )
    base_unit_code: Optional[str] = Field(
        None,
        description="Base unit of measure code for cost"
    )
    
    model_config = {"from_attributes": True}


# ── Set Standard Cost (Direct Save) ────────────────────────────────────────────
class SetStandardCostRequest(BaseModel):
    """
    Request body for the direct standard-cost save endpoint.

    Used by the Material Buy tab when the tenant workflow does NOT require a
    separate manager approval.  The actor (extracted from the JWT) becomes the
    cost-configuration owner recorded in history.
    """
    new_cost: Decimal = Field(
        ...,
        ge=0,
        le=Decimal("999999999.9999"),
        description="New standard cost per base unit of measure; saved to four decimal places.",
    )
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description=(
            "Required when changing an existing cost. "
            "Optional (auto-set to INITIAL_SETUP) when no cost has been configured yet."
        ),
    )
    # Optimistic-lock: client passes back the cost it last saw.
    # Backend rejects if material.current_cost has changed since the client loaded.
    # The Buy tab passes zero for first setup too, to detect concurrent changes.
    expected_current_cost: Optional[Decimal] = Field(
        None,
        ge=0,
        description=(
            "Cost the client last read from the server. "
            "If the server's current cost differs, the request is rejected "
            "to prevent silent concurrent overwrites."
        ),
    )


class SetStandardCostResponse(BaseModel):
    """Response returned after a successful direct standard-cost save."""
    material_id: uuid.UUID
    previous_cost: Optional[Decimal] = Field(
        None, description="Cost before this save (None for first-time setup)."
    )
    new_cost: Decimal = Field(..., description="Effective cost after the save.")
    change_type: str = Field(
        ..., description="INITIAL_SETUP or DIRECT_REVISION depending on prior state."
    )
    cost_history_id: uuid.UUID = Field(
        ..., description="ID of the immutable MaterialCostHistory record created."
    )
    revision_id: uuid.UUID = Field(
        ...,
        description=(
            "ID of the StandardCostRevision record (status=APPROVED, approved_by=NULL) "
            "that was created so BOM costing can recognise this cost."
        ),
    )
    currency_code: str

    model_config = {"from_attributes": True}
