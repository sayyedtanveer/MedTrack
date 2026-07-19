"""Quality Control API schemas."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional, List, Dict, Any
from decimal import Decimal

from pydantic import BaseModel, Field


# ── Queue Schemas ────────────────────────────────────────────────────────────

class InspectionQueueResponse(BaseModel):
    """Work Order in QC inspection queue."""
    work_order_id: uuid.UUID
    wo_number: str
    product_id: uuid.UUID
    produced_quantity: Decimal
    due_date: date
    priority: str
    status: str


class RejectedQueueResponse(BaseModel):
    """Work Order in rejected queue."""
    work_order_id: uuid.UUID
    wo_number: str
    product_id: uuid.UUID
    produced_quantity: Decimal
    due_date: date
    priority: str
    status: str


class ReworkQueueResponse(BaseModel):
    """Work Order in rework queue."""
    work_order_id: uuid.UUID
    wo_number: str
    product_id: uuid.UUID
    produced_quantity: Decimal
    due_date: date
    priority: str
    status: str


# ── Inspection Detail Schema ───────────────────────────────────────────────────

class InspectionDetailSchema(BaseModel):
    """Inspection parameter detail."""
    parameter: str
    measured_value: Optional[str] = None
    tolerance_min: Optional[float] = None
    tolerance_max: Optional[float] = None
    is_passed: bool = True


# ── Request Schemas ───────────────────────────────────────────────────────────

class ApproveInspectionRequest(BaseModel):
    """Request to approve QC inspection."""
    work_order_id: uuid.UUID
    inspection_date: Optional[date] = None
    remarks: Optional[str] = None
    details: Optional[List[InspectionDetailSchema]] = None


class RejectInspectionRequest(BaseModel):
    """Request to reject QC inspection."""
    work_order_id: uuid.UUID
    inspection_date: Optional[date] = None
    reason: str
    defect_details: Optional[Dict[str, Any]] = None
    rework_required: bool = False
    scrap_quantity: Optional[Decimal] = None
    details: Optional[List[InspectionDetailSchema]] = None


class SendToReworkRequest(BaseModel):
    """Request to send batch to rework."""
    work_order_id: uuid.UUID
    rework_reason: str
    additional_material_required: bool = False
    additional_materials: Optional[List[Dict[str, Any]]] = None


class ScrapBatchRequest(BaseModel):
    """Request to scrap batch."""
    work_order_id: uuid.UUID
    scrap_reason: str
    scrap_quantity: Decimal


# ── Response Schemas ───────────────────────────────────────────────────────────

class InspectionResponse(BaseModel):
    """QC inspection response."""
    id: str
    tenant_id: str
    reference_type: str
    reference_id: str
    inspection_date: str
    inspector_id: Optional[str] = None
    result: str
    remarks: Optional[str] = None
    details: List[InspectionDetailSchema] = []
    defect_details: Dict[str, Any] = {}
    rework_required: bool = False
    scrap_quantity: Optional[str] = None
