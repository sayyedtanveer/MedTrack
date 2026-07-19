"""
Work Order domain entity with lifecycle state machine.

Valid operational transitions (per Workflow Ownership Matrix):
    PLANNED → RELEASED → MATERIAL_PENDING → MATERIAL_RESERVED → MATERIAL_ISSUED → 
    IN_PRODUCTION → QC_PENDING → (QC_APPROVED | QC_REJECTED) → 
    (FG_RECEIVED | REWORK | REJECTED) → COMPLETED → CLOSED
"""
from __future__ import annotations

import uuid
import enum
from datetime import date, datetime, timezone
from typing import Optional
from decimal import Decimal


class WorkOrderStatus(str, enum.Enum):
    # Operational workflow states
    PLANNED = "PLANNED"
    RELEASED = "RELEASED"
    MATERIAL_PENDING = "MATERIAL_PENDING"
    MATERIAL_RESERVED = "MATERIAL_RESERVED"
    MATERIAL_ISSUED = "MATERIAL_ISSUED"
    IN_PRODUCTION = "IN_PRODUCTION"
    QC_PENDING = "QC_PENDING"
    QC_APPROVED = "QC_APPROVED"
    QC_REJECTED = "QC_REJECTED"
    FG_RECEIVED = "FG_RECEIVED"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"
    # Rework and scrap states
    REWORK = "REWORK"
    REJECTED = "REJECTED"


class WorkOrderPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


# Allowed status transitions based on workflow ownership matrix
_TRANSITIONS: dict[WorkOrderStatus, set[WorkOrderStatus]] = {
    # Main operational flow
    WorkOrderStatus.PLANNED: {WorkOrderStatus.RELEASED},
    WorkOrderStatus.RELEASED: {WorkOrderStatus.MATERIAL_PENDING},
    WorkOrderStatus.MATERIAL_PENDING: {WorkOrderStatus.MATERIAL_RESERVED},
    WorkOrderStatus.MATERIAL_RESERVED: {WorkOrderStatus.MATERIAL_ISSUED},
    WorkOrderStatus.MATERIAL_ISSUED: {WorkOrderStatus.IN_PRODUCTION},
    WorkOrderStatus.IN_PRODUCTION: {WorkOrderStatus.QC_PENDING},
    WorkOrderStatus.QC_PENDING: {WorkOrderStatus.QC_APPROVED, WorkOrderStatus.QC_REJECTED},
    WorkOrderStatus.QC_APPROVED: {WorkOrderStatus.FG_RECEIVED},
    WorkOrderStatus.FG_RECEIVED: {WorkOrderStatus.COMPLETED},
    WorkOrderStatus.COMPLETED: {WorkOrderStatus.CLOSED},
    # Rework and scrap flow
    WorkOrderStatus.QC_REJECTED: {WorkOrderStatus.REWORK, WorkOrderStatus.REJECTED},
    WorkOrderStatus.REWORK: {WorkOrderStatus.QC_PENDING},
    WorkOrderStatus.REJECTED: {WorkOrderStatus.CLOSED},
    # Terminal state
    WorkOrderStatus.CLOSED: set(),
    # Backward compatibility (legacy IN_PROGRESS maps to IN_PRODUCTION)
    # This will be removed after migration
}


class InvalidStatusTransitionError(Exception):
    """Raised when a lifecycle transition is not permitted."""
    error_code = "INVALID_STATUS_TRANSITION"


class WorkOrderImmutableError(Exception):
    """Raised when a locked field is edited after WO is released."""
    error_code = "WO_IMMUTABLE"


class WorkOrder:
    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: uuid.UUID,
        wo_number: str,
        product_id: uuid.UUID,
        bom_id: uuid.UUID,
        planned_quantity: Decimal,
        start_date: date,
        due_date: date,
        created_by: uuid.UUID,
        status: WorkOrderStatus = WorkOrderStatus.PLANNED,
        priority: WorkOrderPriority = WorkOrderPriority.NORMAL,
        produced_quantity: Decimal = Decimal("0"),
        scrap_quantity: Decimal = Decimal("0"),
        sales_order_id: Optional[uuid.UUID] = None,
        sales_order_line_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        is_deleted: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id or uuid.uuid4()
        self.tenant_id = tenant_id
        self.wo_number = wo_number
        self.product_id = product_id
        self.bom_id = bom_id
        self.planned_quantity = planned_quantity
        self.start_date = start_date
        self.due_date = due_date
        self.created_by = created_by
        self.status = status
        self.priority = priority
        self.produced_quantity = produced_quantity
        self.scrap_quantity = scrap_quantity
        self.sales_order_id = sales_order_id
        self.sales_order_line_id = sales_order_line_id
        self.notes = notes
        self.is_deleted = is_deleted
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    # ── Lifecycle guards ────────────────────────────────────────────────────────

    def can_transition_to(self, new_status: WorkOrderStatus) -> bool:
        """Check if transition to new_status is allowed."""
        allowed = _TRANSITIONS.get(self.status, set())
        return new_status in allowed

    def require_material_issued(self) -> None:
        """Guard: Ensure at least one material is issued before production."""
        # This will be checked by handler when transitioning to IN_PRODUCTION
        # The actual material issue tracking is in WorkOrderMaterialModel
        pass

    def require_qc_approved(self) -> None:
        """Guard: Ensure QC is approved before FG receipt."""
        if self.status != WorkOrderStatus.QC_APPROVED:
            raise InvalidStatusTransitionError(
                f"Cannot receive FG: WO must be in QC_APPROVED status, current: {self.status}"
            )

    def _transition_to(self, new_status: WorkOrderStatus) -> None:
        allowed = _TRANSITIONS[self.status]
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                f"Cannot transition from {self.status} to {new_status}. "
                f"Allowed: {[s.value for s in allowed] or 'none'}"
            )
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    # ── Lifecycle transition methods ─────────────────────────────────────────────

    def release(self) -> None:
        """PLANNED → RELEASED. Locks immutable fields."""
        self._transition_to(WorkOrderStatus.RELEASED)

    def reserve_material(self) -> None:
        """RELEASED → MATERIAL_PENDING → MATERIAL_RESERVED."""
        if self.status == WorkOrderStatus.RELEASED:
            self._transition_to(WorkOrderStatus.MATERIAL_PENDING)
        if self.status == WorkOrderStatus.MATERIAL_PENDING:
            self._transition_to(WorkOrderStatus.MATERIAL_RESERVED)

    def issue_material(self) -> None:
        """MATERIAL_RESERVED → MATERIAL_ISSUED."""
        self._transition_to(WorkOrderStatus.MATERIAL_ISSUED)

    def start_production(self) -> None:
        """MATERIAL_ISSUED → IN_PRODUCTION."""
        self._transition_to(WorkOrderStatus.IN_PRODUCTION)

    # Legacy methods for backward compatibility
    def start(self) -> None:
        """RELEASED → IN_PROGRESS. Legacy - use start_production instead."""
        self._transition_to(WorkOrderStatus.IN_PRODUCTION)

    def submit_for_qc(self) -> None:
        """IN_PRODUCTION → QC_PENDING."""
        self._transition_to(WorkOrderStatus.QC_PENDING)

    def approve_qc(self) -> None:
        """QC_PENDING → QC_APPROVED."""
        self._transition_to(WorkOrderStatus.QC_APPROVED)

    def reject_qc(self) -> None:
        """QC_PENDING → QC_REJECTED."""
        self._transition_to(WorkOrderStatus.QC_REJECTED)

    def send_to_rework(self) -> None:
        """QC_REJECTED → REWORK."""
        self._transition_to(WorkOrderStatus.REWORK)

    def scrap_batch(self) -> None:
        """QC_REJECTED → REJECTED."""
        self._transition_to(WorkOrderStatus.REJECTED)

    def receive_fg(self) -> None:
        """QC_APPROVED → FG_RECEIVED."""
        self.require_qc_approved()
        self._transition_to(WorkOrderStatus.FG_RECEIVED)

    def complete(self) -> None:
        """FG_RECEIVED → COMPLETED. Requires produced_quantity > 0."""
        from backend.app.domain.manufacturing.exceptions import MaterialNotIssuedError
        if self.produced_quantity <= 0:
            raise MaterialNotIssuedError("Cannot complete: no production has been recorded.")
        self._transition_to(WorkOrderStatus.COMPLETED)

    def close(self) -> None:
        """COMPLETED → CLOSED."""
        self._transition_to(WorkOrderStatus.CLOSED)

    # ── Immutability guard ──────────────────────────────────────────────────────

    @property
    def is_locked(self) -> bool:
        """Once released, core fields cannot be edited."""
        return self.status not in (WorkOrderStatus.PLANNED,)

    def update_quantities(self, produced: Decimal, scrap: Decimal) -> None:
        self.produced_quantity = produced
        self.scrap_quantity = scrap
        self.updated_at = datetime.now(timezone.utc)
