"""Commands for the Work Order application layer."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, model_validator


class WorkOrderLineCommand(BaseModel):
    """Represents one product line in a multi-product Work Order creation request."""
    product_id: uuid.UUID
    bom_id: uuid.UUID
    planned_quantity: Decimal = Field(..., gt=0)


class CreateWorkOrderCommand(BaseModel):
    tenant_id: uuid.UUID

    # Single-product fields — required when lines is empty/absent
    product_id: Optional[uuid.UUID] = None
    bom_id: Optional[uuid.UUID] = None
    planned_quantity: Optional[Decimal] = Field(None, gt=0)

    # Multi-product lines — when provided, product_id/bom_id/planned_quantity
    # describe the "primary" product for backward compat display; the lines list
    # drives actual WO Line + BOM snapshot creation.
    lines: Optional[List[WorkOrderLineCommand]] = None

    # Canonical fields
    start_date: date
    due_date: date

    priority: str = "NORMAL"
    sales_order_id: Optional[uuid.UUID] = None
    sales_order_line_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_by: uuid.UUID

    # Backward compatibility for older/incorrect E2E payloads:
    # - quantity -> planned_quantity
    # - due_date provided as datetime -> date
    # - missing start_date -> set to due_date.date()
    # - missing bom_id -> set to a deterministic placeholder UUID
    @model_validator(mode="before")
    @classmethod
    def _backward_compat(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        incoming = dict(data)

        if "quantity" in incoming and "planned_quantity" not in incoming:
            incoming["planned_quantity"] = incoming.pop("quantity")

        # Convert due_date datetime -> date
        if "due_date" in incoming and isinstance(incoming["due_date"], datetime):
            incoming["due_date"] = incoming["due_date"].date()

        if "due_date" in incoming and isinstance(incoming["due_date"], str) and len(incoming["due_date"]) >= 19:
            try:
                incoming["due_date"] = incoming["due_date"][:10]
            except Exception:
                pass

        # Default start_date when missing
        if "start_date" not in incoming:
            if "due_date" in incoming:
                if isinstance(incoming["due_date"], str):
                    incoming["start_date"] = incoming["due_date"]
                elif isinstance(incoming["due_date"], date):
                    incoming["start_date"] = incoming["due_date"]
            else:
                incoming["start_date"] = date.today()

        # Provide a deterministic bom_id placeholder if missing AND no lines provided.
        has_lines = bool(incoming.get("lines"))
        if not has_lines and ("bom_id" not in incoming or incoming["bom_id"] is None):
            incoming["bom_id"] = uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"placeholder:bom:{incoming.get('product_id')}:{incoming.get('tenant_id')}",
            )

        return incoming

    @model_validator(mode="after")
    def due_after_start(self) -> "CreateWorkOrderCommand":
        if self.due_date < self.start_date:
            raise ValueError("due_date must be on or after start_date")

        # Ensure we have enough information to create a WO
        has_lines = bool(self.lines)
        has_single = self.product_id is not None and self.bom_id is not None and self.planned_quantity is not None
        if not has_lines and not has_single:
            raise ValueError(
                "Either provide product_id + bom_id + planned_quantity (single-product) "
                "or a non-empty lines list (multi-product)."
            )
        return self


class ReleaseWorkOrderCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID


class AllocateMaterialsCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID


class StartWorkOrderCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID


# Backward-compatible alias:
# Some tests/flows refer to StartProductionCommand while the actual command name
# in this codebase is StartWorkOrderCommand.
class StartProductionCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID


class IssueMaterialCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: uuid.UUID
    issued_by: uuid.UUID


class RecordProductionCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    produced_quantity: Decimal = Field(..., gt=0)
    scrap_quantity: Decimal = Field(Decimal("0"), ge=0)
    job_card_id: Optional[uuid.UUID] = None
    operation_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    recorded_by: uuid.UUID


class CompleteWorkOrderCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID


class CloseWorkOrderCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID


class StartJobCardCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID
    assigned_to: Optional[uuid.UUID] = None


class CompleteJobCardCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    job_card_id: uuid.UUID
    remarks: Optional[str] = None
    operator_notes: Optional[str] = None
    produced_quantity: Optional[Decimal] = Field(default=None, ge=0)
    scrap_quantity: Optional[Decimal] = Field(default=None, ge=0)
    rework_quantity: Optional[Decimal] = Field(default=None, ge=0)
    rejected_quantity: Optional[Decimal] = Field(default=None, ge=0)


class QCApproveCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    approved_by: uuid.UUID
    remarks: Optional[str] = None


class QCRejectCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    rejected_by: uuid.UUID
    reason: str
    send_to_rework: bool = False


class QCSendToReworkCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    sent_by: uuid.UUID
    remarks: Optional[str] = None


class FGReceiveCommand(BaseModel):
    tenant_id: uuid.UUID
    work_order_id: uuid.UUID
    received_by: uuid.UUID
    remarks: Optional[str] = None
