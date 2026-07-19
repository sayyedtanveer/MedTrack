"""Commands for Worker operational flow."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class StartOperationCommand(BaseModel):
    """Start a job card operation.
    
    Triggers WO transition: MATERIAL_ISSUED → IN_PRODUCTION (if first operation).
    """
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID
    assigned_to: uuid.UUID


class PauseOperationCommand(BaseModel):
    """Pause a job card operation."""
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID
    pause_reason: Optional[str] = None
    operator_notes: Optional[str] = None


class ResumeOperationCommand(BaseModel):
    """Resume a paused job card operation."""
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID
    operator_notes: Optional[str] = None


class CompleteOperationCommand(BaseModel):
    """Complete a job card operation."""
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID
    remarks: Optional[str] = None
    operator_notes: Optional[str] = None
    produced_quantity: Optional[Decimal] = Field(default=None, ge=0)
    scrap_quantity: Optional[Decimal] = Field(default=None, ge=0)
    rework_quantity: Optional[Decimal] = Field(default=None, ge=0)
    rejected_quantity: Optional[Decimal] = Field(default=None, ge=0)


class ReportWastageCommand(BaseModel):
    """Report scrap/wastage during production.
    
    Inventory impact: CONSUMED → REJECTED.
    """
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    scrap_quantity: Decimal = Field(..., ge=0)
    recorded_by: uuid.UUID
    notes: Optional[str] = None


class RecordProductionCommand(BaseModel):
    """Record production quantity.
    
    Triggers WO transition: IN_PRODUCTION → QC_PENDING.
    Inventory impact: ISSUED → CONSUMED.
    """
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    produced_quantity: Decimal = Field(..., gt=0)
    scrap_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    job_card_id: Optional[uuid.UUID] = None
    operation_id: Optional[uuid.UUID] = None
    recorded_by: uuid.UUID
    notes: Optional[str] = None
