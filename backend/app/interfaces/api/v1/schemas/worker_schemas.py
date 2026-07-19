"""Worker API schemas."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from datetime import date, datetime

from pydantic import BaseModel, Field


# ── Queue Schemas ────────────────────────────────────────────────────────────

class JobCardResponse(BaseModel):
    """Job card in worker queue."""
    job_card_id: uuid.UUID
    operation_id: uuid.UUID
    operation_name: Optional[str] = None
    sequence: int
    status: str
    assigned_to: Optional[uuid.UUID] = None
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_downtime_seconds: float = 0
    actual_duration_seconds: Optional[float] = None
    produced_quantity: Decimal = Decimal("0")
    scrap_quantity: Decimal = Decimal("0")
    rework_quantity: Decimal = Decimal("0")
    rejected_quantity: Decimal = Decimal("0")
    yield_percent: float = 0
    progress_percent: float = 0
    pause_reason: Optional[str] = None
    operator_notes: Optional[str] = None


class WorkerQueueResponse(BaseModel):
    """Work Order in worker queue."""
    work_order_id: uuid.UUID
    wo_number: str
    product_id: uuid.UUID
    due_date: date
    priority: str
    status: str
    job_cards: list[JobCardResponse]


# ── Request Schemas ───────────────────────────────────────────────────────────

class StartOperationRequest(BaseModel):
    """Request to start operation."""
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID


class PauseOperationRequest(BaseModel):
    """Request to pause operation."""
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID
    pause_reason: Optional[str] = None
    operator_notes: Optional[str] = None


class ResumeOperationRequest(BaseModel):
    """Request to resume operation."""
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID
    operator_notes: Optional[str] = None


class CompleteOperationRequest(BaseModel):
    """Request to complete operation."""
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID
    remarks: Optional[str] = None
    operator_notes: Optional[str] = None
    produced_quantity: Optional[Decimal] = Field(default=None, ge=0)
    scrap_quantity: Optional[Decimal] = Field(default=None, ge=0)
    rework_quantity: Optional[Decimal] = Field(default=None, ge=0)
    rejected_quantity: Optional[Decimal] = Field(default=None, ge=0)


class ReportWastageRequest(BaseModel):
    """Request to report wastage."""
    work_order_id: uuid.UUID
    scrap_quantity: Decimal = Field(..., ge=0)
    notes: Optional[str] = None


class RecordProductionRequest(BaseModel):
    """Request to record production."""
    work_order_id: uuid.UUID
    produced_quantity: Decimal = Field(..., gt=0)
    scrap_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    job_card_id: Optional[uuid.UUID] = None
    operation_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
