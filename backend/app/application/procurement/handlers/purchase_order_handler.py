"""
Purchase Order application handler with domain entity integration.

Coordinates PO lifecycle transitions using PurchaseOrder domain entity.
"""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel
from backend.app.domain.procurement.entities import (
    PurchaseOrder,
    PurchaseOrderStatus,
    InvalidPOTransitionError,
    POCancelledError,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork

_PO_STATUS_ALIASES = {
    "draft": PurchaseOrderStatus.DRAFT.value,
    "sent": PurchaseOrderStatus.SENT.value,
    "acknowledged": PurchaseOrderStatus.ACKNOWLEDGED.value,
    "partial": PurchaseOrderStatus.PARTIAL_RECEIPT.value,
    "partial_receipt": PurchaseOrderStatus.PARTIAL_RECEIPT.value,
    "partial-receipt": PurchaseOrderStatus.PARTIAL_RECEIPT.value,
    "partial receipt": PurchaseOrderStatus.PARTIAL_RECEIPT.value,
    "received": PurchaseOrderStatus.COMPLETED.value,
    "completed": PurchaseOrderStatus.COMPLETED.value,
    "complete": PurchaseOrderStatus.COMPLETED.value,
    "cancelled": PurchaseOrderStatus.CANCELLED.value,
    "canceled": PurchaseOrderStatus.CANCELLED.value,
}


def _normalize_po_status(value: PurchaseOrderStatus | str | None) -> PurchaseOrderStatus:
    if isinstance(value, PurchaseOrderStatus):
        return value

    normalized = str(value or "").strip().lower()
    mapped = _PO_STATUS_ALIASES.get(normalized)
    if not mapped:
        raise ValueError(f"Unsupported purchase order status '{value}'")

    return PurchaseOrderStatus(mapped)


class PurchaseOrderHandler:
    """Handler for purchase order business logic with state machine validation."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.uow: Optional[SQLAlchemyUnitOfWork] = None

    def with_uow(self, uow: SQLAlchemyUnitOfWork) -> PurchaseOrderHandler:
        """Fluent setter for UnitOfWork (for event dispatch)."""
        self.uow = uow
        return self

    async def send_po(self, po_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """
        Transition PO from DRAFT → SENT.
        
        Raises:
            HTTPException: If PO not found or invalid transition
        """
        po_model = await self.session.get(PurchaseOrderModel, po_id)
        if not po_model or po_model.tenant_id != tenant_id or po_model.is_deleted:
            raise ValueError(f"PO {po_id} not found")

        # Create domain entity from model
        po_entity = PurchaseOrder(
            id=po_model.id,
            tenant_id=po_model.tenant_id,
            supplier_id=po_model.supplier_id,
            po_number=po_model.po_number,
            expected_delivery_date=po_model.expected_delivery,
            created_by=po_model.created_by,
            status=_normalize_po_status(po_model.status),
            notes=po_model.notes,
            is_deleted=po_model.is_deleted,
            created_at=po_model.created_at,
            updated_at=po_model.updated_at,
        )

        # Validate transition
        try:
            po_entity.send()
        except InvalidPOTransitionError as e:
            raise ValueError(str(e))
        except POCancelledError as e:
            raise ValueError(str(e))

        # Update model
        po_model.status = po_entity.status.value
        po_model.updated_at = po_entity.updated_at
        await self.session.flush()

        return {"status": "ok", "po_id": str(po_id)}

    async def acknowledge_po(self, po_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """
        Transition PO from SENT → ACKNOWLEDGED.
        
        Raises:
            ValueError: If PO not found or invalid transition
        """
        po_model = await self.session.get(PurchaseOrderModel, po_id)
        if not po_model or po_model.tenant_id != tenant_id or po_model.is_deleted:
            raise ValueError(f"PO {po_id} not found")

        # Create domain entity
        po_entity = PurchaseOrder(
            id=po_model.id,
            tenant_id=po_model.tenant_id,
            supplier_id=po_model.supplier_id,
            po_number=po_model.po_number,
            expected_delivery_date=po_model.expected_delivery,
            created_by=po_model.created_by,
            status=_normalize_po_status(po_model.status),
            notes=po_model.notes,
            is_deleted=po_model.is_deleted,
            created_at=po_model.created_at,
            updated_at=po_model.updated_at,
        )

        # Validate transition
        try:
            po_entity.acknowledge()
        except InvalidPOTransitionError as e:
            raise ValueError(str(e))
        except POCancelledError as e:
            raise ValueError(str(e))

        # Update model
        po_model.status = po_entity.status.value
        po_model.updated_at = po_entity.updated_at
        await self.session.flush()

        return {"status": "ok", "po_id": str(po_id)}

    async def cancel_po(self, po_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """
        Transition PO to CANCELLED from any state.
        
        Raises:
            ValueError: If PO not found or already cancelled
        """
        po_model = await self.session.get(PurchaseOrderModel, po_id)
        if not po_model or po_model.tenant_id != tenant_id or po_model.is_deleted:
            raise ValueError(f"PO {po_id} not found")

        # Create domain entity
        po_entity = PurchaseOrder(
            id=po_model.id,
            tenant_id=po_model.tenant_id,
            supplier_id=po_model.supplier_id,
            po_number=po_model.po_number,
            expected_delivery_date=po_model.expected_delivery,
            created_by=po_model.created_by,
            status=_normalize_po_status(po_model.status),
            notes=po_model.notes,
            is_deleted=po_model.is_deleted,
            created_at=po_model.created_at,
            updated_at=po_model.updated_at,
        )

        # Validate transition
        try:
            po_entity.cancel()
        except InvalidPOTransitionError as e:
            raise ValueError(str(e))
        except POCancelledError as e:
            raise ValueError(str(e))

        # Update model
        po_model.status = po_entity.status.value
        po_model.updated_at = po_entity.updated_at
        await self.session.flush()

        return {"status": "cancelled", "po_id": str(po_id)}
