"""Storekeeper API schemas."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from datetime import date, datetime

from pydantic import BaseModel, Field


# ── Queue Schemas ────────────────────────────────────────────────────────────

class IssueQueueResponse(BaseModel):
    """Pending material issue."""
    work_order_id: uuid.UUID
    wo_number: str
    material_id: uuid.UUID
    material_code: Optional[str] = None
    material_name: Optional[str] = None
    batch_id: Optional[uuid.UUID] = None
    batch_number: Optional[str] = None
    required_quantity: Decimal
    reserved_quantity: Decimal = Decimal("0")
    issued_quantity: Decimal = Decimal("0")
    consumed_quantity: Decimal = Decimal("0")
    returned_quantity: Decimal = Decimal("0")
    remaining_quantity: Decimal
    available_quantity: Optional[Decimal] = None
    due_date: Optional[datetime] = None
    status: str


class ShortageQueueResponse(BaseModel):
    """Material shortage."""
    shortage_id: uuid.UUID
    work_order_id: uuid.UUID
    wo_number: Optional[str] = None
    material_id: uuid.UUID
    material_code: Optional[str] = None
    material_name: Optional[str] = None
    required_quantity: Decimal
    available_quantity: Decimal
    shortage_quantity: Decimal
    status: str
    created_at: datetime


class PartiallyIssuedWOResponse(BaseModel):
    """Partially issued Work Order."""
    work_order_id: uuid.UUID
    wo_number: str
    product_id: uuid.UUID
    due_date: datetime
    status: str


class PendingReservationResponse(BaseModel):
    """Reservation waiting for issue."""
    reservation_id: uuid.UUID
    work_order_id: uuid.UUID
    wo_number: str
    material_id: uuid.UUID
    material_code: str
    material_name: str
    batch_id: Optional[uuid.UUID] = None
    batch_number: Optional[str] = None
    reserved_quantity: Decimal
    issued_quantity: Decimal
    pending_quantity: Decimal
    status: str
    created_at: datetime


class PendingReturnResponse(BaseModel):
    """Issued material available to return."""
    reservation_id: uuid.UUID
    work_order_id: uuid.UUID
    wo_number: str
    material_id: uuid.UUID
    material_code: str
    material_name: str
    batch_id: Optional[uuid.UUID] = None
    batch_number: Optional[str] = None
    issued_quantity: Decimal
    consumed_quantity: Decimal
    returned_quantity: Decimal
    returnable_quantity: Decimal
    status: str
    updated_at: datetime


class InventoryAlertResponse(BaseModel):
    """Storekeeper inventory alert."""
    alert_type: str
    severity: str
    material_id: uuid.UUID
    material_code: str
    material_name: str
    batch_id: Optional[uuid.UUID] = None
    batch_number: Optional[str] = None
    current_stock: Optional[Decimal] = None
    reorder_level: Optional[Decimal] = None
    remaining_quantity: Optional[Decimal] = None
    message: str


class OperationalBatchResponse(BaseModel):
    """Operator-facing batch visibility card."""
    batch_id: uuid.UUID
    batch_number: str
    material_id: uuid.UUID
    material_code: str
    material_name: str
    original_quantity: Decimal
    remaining_quantity: Decimal
    reserved_quantity: Decimal
    consumed_quantity: Decimal
    returned_quantity: Decimal
    location_id: Optional[uuid.UUID] = None
    location_name: Optional[str] = None
    location_type: Optional[str] = None
    expiry_date: Optional[date] = None
    status: str
    is_blocked: bool
    is_near_empty: bool


# ── Request Schemas ───────────────────────────────────────────────────────────

class ReserveStockRequest(BaseModel):
    """Request to reserve stock."""
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None


class IssueMaterialRequest(BaseModel):
    """Request to issue material."""
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None


class PartialIssueRequest(BaseModel):
    """Request to partially issue material."""
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None


class RejectIssueRequest(BaseModel):
    """Request to reject material issue."""
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    reason: str


class ReturnMaterialRequest(BaseModel):
    """Request to return material."""
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
