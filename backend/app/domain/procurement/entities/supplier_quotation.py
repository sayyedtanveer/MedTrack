"""
Supplier Quotation domain entity with lifecycle state machine.

Valid transitions:
    DRAFT → SUBMITTED → APPROVED
    STATE → REJECTED (from any state)
"""
from __future__ import annotations

import uuid
import enum
from datetime import datetime, timezone
from typing import Optional
from decimal import Decimal


class SupplierQuotationStatus(str, enum.Enum):
    """Supplier Quotation lifecycle states."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class InvalidQuotationTransitionError(Exception):
    """Raised when a quotation lifecycle transition is not permitted."""
    error_code = "INVALID_QUOTATION_TRANSITION"


class QuotationRejectedError(Exception):
    """Raised when attempting operations on a rejected quotation."""
    error_code = "QUOTATION_REJECTED"


# Allowed status transitions
_TRANSITIONS: dict[SupplierQuotationStatus, set[SupplierQuotationStatus]] = {
    SupplierQuotationStatus.DRAFT: {
        SupplierQuotationStatus.SUBMITTED,
        SupplierQuotationStatus.REJECTED,
    },
    SupplierQuotationStatus.SUBMITTED: {
        SupplierQuotationStatus.APPROVED,
        SupplierQuotationStatus.REJECTED,
    },
    SupplierQuotationStatus.APPROVED: set(),  # Terminal state
    SupplierQuotationStatus.REJECTED: set(),  # Terminal state
}


class SupplierQuotation:
    """Domain entity for supplier quotations with state machine enforcement."""
    
    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        material_id: uuid.UUID,
        purchase_order_id: Optional[uuid.UUID] = None,
        quoted_price: Decimal,
        quantity: Decimal,
        delivery_days: int,
        created_by: uuid.UUID,
        status: SupplierQuotationStatus = SupplierQuotationStatus.DRAFT,
        notes: Optional[str] = None,
        is_deleted: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id or uuid.uuid4()
        self.tenant_id = tenant_id
        self.supplier_id = supplier_id
        self.material_id = material_id
        self.purchase_order_id = purchase_order_id
        self.quoted_price = quoted_price
        self.quantity = quantity
        self.delivery_days = delivery_days
        self.created_by = created_by
        self.status = status
        self.notes = notes
        self.is_deleted = is_deleted
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    # ── Lifecycle guards ────────────────────────────────────────────────────────

    def _transition_to(self, new_status: SupplierQuotationStatus) -> None:
        """Enforce allowed status transitions."""
        if self.status == SupplierQuotationStatus.REJECTED:
            raise QuotationRejectedError(
                f"Cannot transition from REJECTED state. "
                f"Quotation is permanently closed."
            )
        
        allowed = _TRANSITIONS[self.status]
        if new_status not in allowed:
            raise InvalidQuotationTransitionError(
                f"Cannot transition from {self.status} to {new_status}. "
                f"Allowed: {[s.value for s in allowed] or 'none'}"
            )
        
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def submit(self) -> None:
        """DRAFT → SUBMITTED. Supplier submits quote."""
        self._transition_to(SupplierQuotationStatus.SUBMITTED)

    def approve(self) -> None:
        """SUBMITTED → APPROVED. Admin approves the quote."""
        self._transition_to(SupplierQuotationStatus.APPROVED)

    def reject(self) -> None:
        """STATE → REJECTED. Rejects quotation from any state."""
        self._transition_to(SupplierQuotationStatus.REJECTED)

    # ── State query ─────────────────────────────────────────────────────────────

    @property
    def is_locked(self) -> bool:
        """Quotation is locked (immutable) once submitted."""
        return self.status not in (SupplierQuotationStatus.DRAFT,)

    @property
    def is_rejected(self) -> bool:
        """Whether quotation has been rejected."""
        return self.status == SupplierQuotationStatus.REJECTED

    @property
    def is_approved(self) -> bool:
        """Whether quotation has been approved."""
        return self.status == SupplierQuotationStatus.APPROVED
