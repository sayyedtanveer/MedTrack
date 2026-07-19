from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, model_validator


class WorkOrderCreateRequest(BaseModel):
    product_id: uuid.UUID
    bom_id: uuid.UUID
    planned_quantity: Decimal = Field(..., gt=0)
    start_date: date
    due_date: date
    priority: str = Field("NORMAL", pattern="^(LOW|NORMAL|HIGH|URGENT)$")
    sales_order_id: Optional[uuid.UUID] = None
    sales_order_line_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "WorkOrderCreateRequest":
        if self.due_date < self.start_date:
            raise ValueError("due_date must be on or after start_date")
        return self


class IssueMaterialRequest(BaseModel):
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: uuid.UUID


class RecordProductionRequest(BaseModel):
    produced_quantity: Decimal = Field(..., gt=0)
    scrap_quantity: Decimal = Field(Decimal("0"), ge=0)
    job_card_id: Optional[uuid.UUID] = None
    operation_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class MaterialAvailabilityLineResponse(BaseModel):
    material_id: uuid.UUID
    material_code: str
    material_name: str
    unit_id: Optional[uuid.UUID] = None
    unit_code: Optional[str] = None
    unit_name: Optional[str] = None
    required_quantity: Decimal
    available_quantity: Decimal
    shortage_quantity: Decimal
    status: str


class MaterialAvailabilityResponse(BaseModel):
    product_id: uuid.UUID
    bom_id: uuid.UUID
    planned_quantity: Decimal
    has_shortage: bool
    shortage_count: int
    message: Optional[str] = None
    lines: List[MaterialAvailabilityLineResponse]


class StartJobCardRequest(BaseModel):
    assigned_to: Optional[uuid.UUID] = None


class CompleteJobCardRequest(BaseModel):
    remarks: Optional[str] = None
    operator_notes: Optional[str] = None
    produced_quantity: Optional[Decimal] = Field(default=None, ge=0)
    scrap_quantity: Optional[Decimal] = Field(default=None, ge=0)
    rework_quantity: Optional[Decimal] = Field(default=None, ge=0)
    rejected_quantity: Optional[Decimal] = Field(default=None, ge=0)


# ── Response Schemas ────────────────────────────────────────────────────────────

class JobCardResponse(BaseModel):
    id: uuid.UUID
    operation_id: uuid.UUID
    operation_name: str
    sequence: int
    status: str
    assigned_to: Optional[uuid.UUID]
    started_at: Optional[datetime]
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime]
    total_downtime_seconds: Decimal = Decimal("0")
    actual_duration_seconds: Optional[float] = None
    produced_quantity: Decimal = Decimal("0")
    scrap_quantity: Decimal = Decimal("0")
    rework_quantity: Decimal = Decimal("0")
    rejected_quantity: Decimal = Decimal("0")
    yield_percent: float = 0
    progress_percent: float = 0
    pause_reason: Optional[str] = None
    operator_notes: Optional[str] = None
    remarks: Optional[str]

    model_config = {"from_attributes": True}


class WorkOrderMaterialResponse(BaseModel):
    id: uuid.UUID
    material_id: uuid.UUID
    material_code: Optional[str] = None
    material_name: Optional[str] = None
    unit_id: Optional[uuid.UUID]
    required_quantity: Decimal
    issued_quantity: Decimal

    model_config = {"from_attributes": True}


class WorkOrderSummary(BaseModel):
    id: uuid.UUID
    wo_number: str
    product_id: uuid.UUID
    bom_id: uuid.UUID
    status: str
    priority: str
    planned_quantity: Decimal
    produced_quantity: Decimal
    scrap_quantity: Decimal
    start_date: date
    due_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkOrderDetail(WorkOrderSummary):
    notes: Optional[str]
    sales_order_id: Optional[uuid.UUID]
    sales_order_line_id: Optional[uuid.UUID]
    materials: List[WorkOrderMaterialResponse] = []
    job_cards: List[JobCardResponse] = []


class WorkOrderErrorResponse(BaseModel):
    error_code: str
    message: str
    validation_errors: List[str] = []
