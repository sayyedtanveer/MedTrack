"""
Purchase Order domain entity with lifecycle state machine.

Valid transitions:
    DRAFT → SENT → ACKNOWLEDGED → PARTIAL_RECEIPT → COMPLETED
    STATE → CANCELLED (from any state)
"""
from __future__ import annotations

import uuid
import enum
from datetime import date, datetime, timezone
from typing import Optional
from decimal import Decimal


class PurchaseOrderStatus(str, enum.Enum):
    """Purchase Order lifecycle states."""
    DRAFT = "draft"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    PARTIAL_RECEIPT = "partial"
    COMPLETED = "received"
    CANCELLED = "cancelled"


class InvalidPOTransitionError(Exception):
    """Raised when a PO lifecycle transition is not permitted."""
    error_code = "INVALID_PO_TRANSITION"


class POCancelledError(Exception):
    """Raised when attempting operations on a cancelled PO."""
    error_code = "PO_CANCELLED"


# Allowed status transitions
_TRANSITIONS: dict[PurchaseOrderStatus, set[PurchaseOrderStatus]] = {
    PurchaseOrderStatus.DRAFT: {
        PurchaseOrderStatus.SENT,
        PurchaseOrderStatus.CANCELLED,
    },
    PurchaseOrderStatus.SENT: {
        PurchaseOrderStatus.ACKNOWLEDGED,
        PurchaseOrderStatus.CANCELLED,
    },
    PurchaseOrderStatus.ACKNOWLEDGED: {
        PurchaseOrderStatus.PARTIAL_RECEIPT,
        PurchaseOrderStatus.COMPLETED,
        PurchaseOrderStatus.CANCELLED,
    },
    PurchaseOrderStatus.PARTIAL_RECEIPT: {
        PurchaseOrderStatus.COMPLETED,
        PurchaseOrderStatus.CANCELLED,
    },
    PurchaseOrderStatus.COMPLETED: set(),  # Terminal state
    PurchaseOrderStatus.CANCELLED: set(),  # Terminal state
}


class PurchaseOrder:
    """Domain entity for purchase orders with state machine enforcement."""
    
    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        po_number: str,
        expected_delivery_date: date,
        created_by: uuid.UUID,
        status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT,
        notes: Optional[str] = None,
        is_deleted: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id or uuid.uuid4()
        self.tenant_id = tenant_id
        self.supplier_id = supplier_id
        self.po_number = po_number
        self.expected_delivery_date = expected_delivery_date
        self.created_by = created_by
        self.status = status
        self.notes = notes
        self.is_deleted = is_deleted
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    # ── Lifecycle guards ────────────────────────────────────────────────────────

    def _transition_to(self, new_status: PurchaseOrderStatus) -> None:
        """Enforce allowed status transitions."""
        if self.status == PurchaseOrderStatus.CANCELLED:
            raise POCancelledError(
                f"Cannot transition from CANCELLED state. "
                f"PO #{self.po_number} is permanently closed."
            )
        
        allowed = _TRANSITIONS[self.status]
        if new_status not in allowed:
            raise InvalidPOTransitionError(
                f"Cannot transition from {self.status} to {new_status}. "
                f"Allowed: {[s.value for s in allowed] or 'none'}"
            )
        
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def send(self) -> None:
        """DRAFT → SENT. Submits PO to supplier."""
        self._transition_to(PurchaseOrderStatus.SENT)

    def acknowledge(self) -> None:
        """SENT → ACKNOWLEDGED. Supplier confirms PO acceptance."""
        self._transition_to(PurchaseOrderStatus.ACKNOWLEDGED)

    def receive_partial(self) -> None:
        """ACKNOWLEDGED → PARTIAL_RECEIPT. Goods partly received."""
        self._transition_to(PurchaseOrderStatus.PARTIAL_RECEIPT)

    def complete(self) -> None:
        """PARTIAL_RECEIPT|ACKNOWLEDGED → COMPLETED. All goods received."""
        self._transition_to(PurchaseOrderStatus.COMPLETED)

    def cancel(self) -> None:
        """STATE → CANCELLED. Cancels PO from any state except already CANCELLED."""
        self._transition_to(PurchaseOrderStatus.CANCELLED)

    # ── State query ─────────────────────────────────────────────────────────────

    @property
    def is_locked(self) -> bool:
        """PO is locked (immutable) once sent."""
        return self.status not in (PurchaseOrderStatus.DRAFT,)

    @property
    def is_cancelled(self) -> bool:
        """Whether PO has been cancelled."""
        return self.status == PurchaseOrderStatus.CANCELLED

    @property
    def is_completed(self) -> bool:
        """Whether all goods received."""
        return self.status == PurchaseOrderStatus.COMPLETED
