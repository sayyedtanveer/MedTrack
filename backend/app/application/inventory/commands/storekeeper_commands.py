"""Commands for Storekeeper operational flow."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ReserveStockCommand(BaseModel):
    """Reserve stock for Work Order.
    
    Triggers WO transition: MATERIAL_PENDING → MATERIAL_RESERVED.
    Inventory: AVAILABLE → RESERVED.
    """
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    reserved_by: uuid.UUID


class IssueMaterialCommand(BaseModel):
    """Issue reserved stock to Work Order.
    
    Triggers WO transition: MATERIAL_RESERVED → MATERIAL_ISSUED.
    Inventory: RESERVED → ISSUED.
    """
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    issued_by: uuid.UUID


class PartialIssueCommand(BaseModel):
    """Partially issue stock to Work Order.
    
    WO stays in MATERIAL_RESERVED until all materials issued.
    """
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    issued_by: uuid.UUID


class RejectIssueCommand(BaseModel):
    """Reject material issue request."""
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    reason: str
    rejected_by: uuid.UUID


class ReturnMaterialCommand(BaseModel):
    """Return issued material back to inventory.
    
    Inventory: ISSUED → RESERVED.
    """
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    returned_by: uuid.UUID
