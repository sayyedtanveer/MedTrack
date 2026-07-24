from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

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
    inspection_required: Optional[bool] = None
    inspection_template_id: Optional[uuid.UUID] = None
    current_cost: Optional[Decimal] = Field(
        None,
        ge=0,
        le=Decimal("999999999.9999"),
        description="Standard Purchase Cost",
    )

    @field_validator("code", "item_code", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Coerce empty/whitespace-only strings to None so frontend can send '' safely."""
        if isinstance(v, str) and not v.strip():
            return None
        return v


# ── Transaction Request Schemas ───────────────────────────────────────────
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
    
    # Purchasing summary fields
    latest_purchase_price: Optional[Decimal] = None
    last_purchase_date: Optional[date] = None
    last_supplier_name: Optional[str] = None
    last_supplier_id: Optional[uuid.UUID] = None
    purchase_count: int = 0

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
