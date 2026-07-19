"""QC Commands for approve/reject/rework operations."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional, Dict, Any
from decimal import Decimal

from pydantic import BaseModel, Field


class ApproveInspectionCommand(BaseModel):
    """Command to approve a QC inspection.
    
    Triggers WO transition: QC_PENDING → QC_APPROVED.
    Downstream: FG receipt.
    """
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    inspector_id: uuid.UUID
    inspection_date: date = Field(default_factory=date.today)
    remarks: Optional[str] = None
    details: Optional[list[dict]] = None  # Inspection parameters


class RejectInspectionCommand(BaseModel):
    """Command to reject a QC inspection.
    
    Triggers WO transition: QC_PENDING → QC_REJECTED.
    Downstream: Rework or Scrap decision.
    """
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    inspector_id: uuid.UUID
    inspection_date: date = Field(default_factory=date.today)
    reason: str
    defect_details: Optional[Dict[str, Any]] = None
    rework_required: bool = False
    scrap_quantity: Optional[Decimal] = None
    details: Optional[list[dict]] = None


class SendToReworkCommand(BaseModel):
    """Command to send rejected batch to rework.
    
    Triggers WO transition: QC_REJECTED → REWORK.
    Downstream: Worker executes rework operations.
    """
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    inspector_id: uuid.UUID
    rework_reason: str
    additional_material_required: bool = False
    additional_materials: Optional[list[dict]] = None


class ScrapBatchCommand(BaseModel):
    """Command to scrap rejected batch.
    
    Triggers WO transition: QC_REJECTED → REJECTED → CLOSED.
    Inventory impact: ISSUED → REJECTED.
    """
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    inspector_id: uuid.UUID
    scrap_reason: str
    scrap_quantity: Decimal
