"""
Domain entities for procurement pricing (Phase 2).

This module contains:
- SupplierPriceAgreement: Supplier pricing contract with state machine
- MaterialCostHistory: Immutable cost audit log entry
- StandardCostRevision: Cost approval workflow
- PriceOverrideRecord: Manual price override tracking

All entities inherit from BaseEntity and follow DDD patterns:
- Private fields with properties (read-only or mutable with _touch())
- Business logic methods that validate and raise domain exceptions
- State machines for workflow entities
- Domain events for state changes
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from backend.app.domain.shared.base_entity import BaseEntity
from backend.app.domain.shared.exceptions import (
    DomainException,
    InvalidStateTransitionError,
)
from backend.app.domain.procurement.pricing.exceptions import (
    AgreementAlreadyActiveError,
    CostRevisionAlreadyReviewedError,
    CostRevisionNotFoundError,
    InvalidAgreementStateTransitionError,
    PriceOverrideRecordNotFoundError,
    RequesterCannotApproveOwnRevisionError,
    SupplierPriceAgreementNotFoundError,
)
from backend.app.domain.procurement.pricing.value_objects import PricingTier


# ── State Enums ──


class SupplierPriceAgreementStatus(str, Enum):
    """Supplier price agreement workflow states."""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class StandardCostRevisionStatus(str, Enum):
    """Cost revision approval workflow states."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ── State Machine: SupplierPriceAgreement ──


_SUPPLIER_AGREEMENT_TRANSITIONS = {
    SupplierPriceAgreementStatus.DRAFT: {
        SupplierPriceAgreementStatus.PENDING,
        SupplierPriceAgreementStatus.CANCELLED,
    },
    SupplierPriceAgreementStatus.PENDING: {
        SupplierPriceAgreementStatus.APPROVED,
        SupplierPriceAgreementStatus.DRAFT,  # Rejected back to Draft for resubmission
        SupplierPriceAgreementStatus.CANCELLED,
    },
    SupplierPriceAgreementStatus.APPROVED: {
        SupplierPriceAgreementStatus.ACTIVE,
        SupplierPriceAgreementStatus.CANCELLED,
    },
    SupplierPriceAgreementStatus.ACTIVE: {
        SupplierPriceAgreementStatus.EXPIRED,
        SupplierPriceAgreementStatus.CANCELLED,
    },
    SupplierPriceAgreementStatus.EXPIRED: set(),  # Terminal state
    SupplierPriceAgreementStatus.CANCELLED: set(),  # Terminal state
}


class SupplierPriceAgreement(BaseEntity):
    """
    Domain entity for supplier pricing agreements.

    Represents a contract for material pricing with a specific supplier,
    including tiered discounts and validity dates.

    State Machine:
        DRAFT → PENDING → APPROVED → ACTIVE → EXPIRED/CANCELLED
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        supplier_id: uuid.UUID,
        material_id: uuid.UUID,
        base_price: Decimal,
        currency_code: str,
        purchase_uom_id: Optional[uuid.UUID] = None,
        minimum_order_quantity: Optional[Decimal] = None,
        effective_from: datetime,
        effective_to: Optional[datetime] = None,
        quantity_tiers: Optional[List[PricingTier]] = None,
        notes: Optional[str] = None,
        status: SupplierPriceAgreementStatus = SupplierPriceAgreementStatus.DRAFT,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        """Initialize supplier price agreement."""
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )

        self._supplier_id = supplier_id
        self._material_id = material_id
        self._base_price = Decimal(str(base_price))
        self._currency_code = currency_code.upper()
        self._purchase_uom_id = purchase_uom_id
        self._minimum_order_quantity = (
            Decimal(str(minimum_order_quantity))
            if minimum_order_quantity is not None
            else None
        )
        self._effective_from = effective_from
        self._effective_to = effective_to
        self._quantity_tiers = quantity_tiers or []
        self._notes = notes
        self._status = status

        self._validate_pricing()

    # ── Properties (read-only) ──

    @property
    def supplier_id(self) -> uuid.UUID:
        return self._supplier_id

    @property
    def material_id(self) -> uuid.UUID:
        return self._material_id

    @property
    def base_price(self) -> Decimal:
        return self._base_price

    @property
    def currency_code(self) -> str:
        return self._currency_code

    @property
    def purchase_uom_id(self) -> Optional[uuid.UUID]:
        return self._purchase_uom_id

    @property
    def minimum_order_quantity(self) -> Optional[Decimal]:
        return self._minimum_order_quantity

    @property
    def effective_from(self) -> datetime:
        return self._effective_from

    @property
    def effective_to(self) -> Optional[datetime]:
        return self._effective_to

    @property
    def quantity_tiers(self) -> List[PricingTier]:
        return self._quantity_tiers.copy()

    @property
    def status(self) -> SupplierPriceAgreementStatus:
        return self._status

    @property
    def notes(self) -> Optional[str]:
        return self._notes

    # ── Mutable properties ──

    @notes.setter
    def notes(self, value: Optional[str]) -> None:
        """Update notes (only in DRAFT/PENDING states)."""
        if self._status not in {SupplierPriceAgreementStatus.DRAFT, SupplierPriceAgreementStatus.PENDING}:
            raise DomainException(f"Cannot update notes in {self._status} state")
        self._notes = value
        self._touch()

    # ── Business logic methods ──

    def submit_for_approval(self) -> None:
        """Transition DRAFT → PENDING (submit for review)."""
        self._transition_to(SupplierPriceAgreementStatus.PENDING)

    def approve(self) -> None:
        """Transition PENDING → APPROVED (approved by procurement)."""
        self._transition_to(SupplierPriceAgreementStatus.APPROVED)

    def activate(self) -> None:
        """Transition APPROVED → ACTIVE (ready to use)."""
        self._transition_to(SupplierPriceAgreementStatus.ACTIVE)

    def expire(self) -> None:
        """Transition ACTIVE → EXPIRED (end of validity)."""
        self._transition_to(SupplierPriceAgreementStatus.EXPIRED)

    def cancel(self) -> None:
        """Cancel agreement from any state (except terminal states)."""
        if self._status in {SupplierPriceAgreementStatus.EXPIRED, SupplierPriceAgreementStatus.CANCELLED}:
            raise InvalidAgreementStateTransitionError(self._status.value, SupplierPriceAgreementStatus.CANCELLED.value)
        self._status = SupplierPriceAgreementStatus.CANCELLED
        self._touch()

    def is_valid_for_date(self, check_date: datetime) -> bool:
        """Check if agreement is valid (active and within date range)."""
        if self._status != SupplierPriceAgreementStatus.ACTIVE:
            return False
        if check_date < self._effective_from:
            return False
        if self._effective_to and check_date > self._effective_to:
            return False
        return True

    def get_price_for_quantity(self, quantity: Decimal) -> Decimal:
        """Get price for a given quantity (applies tiered discount if applicable)."""
        if not self._quantity_tiers:
            return self._base_price

        # Find applicable tier
        for tier in sorted(self._quantity_tiers, key=lambda t: t.min_quantity):
            if quantity >= tier.min_quantity:
                if tier.max_quantity is None or quantity <= tier.max_quantity:
                    return tier.get_price_after_discount(self._base_price)

        # If no tier matches, return base price
        return self._base_price

    # ── Private methods ──

    def _transition_to(self, new_status: SupplierPriceAgreementStatus) -> None:
        """Enforce state machine transitions."""
        allowed = _SUPPLIER_AGREEMENT_TRANSITIONS.get(self._status, set())
        if new_status not in allowed:
            raise InvalidAgreementStateTransitionError(self._status.value, new_status.value)
        self._status = new_status
        self._touch()

    def _validate_pricing(self) -> None:
        """Validate pricing fields."""
        if self._base_price < Decimal("0"):
            raise ValueError("base_price must be non-negative")
        if not self._currency_code or len(self._currency_code) != 3:
            raise ValueError("currency_code must be 3-letter ISO code")
        if (
            self._minimum_order_quantity is not None
            and self._minimum_order_quantity < Decimal("0")
        ):
            raise ValueError("minimum_order_quantity must be non-negative")
        if self._effective_to and self._effective_to < self._effective_from:
            raise ValueError("effective_to must be >= effective_from")


# ── MaterialCostHistory: Immutable Audit Log ──


class MaterialCostHistory(BaseEntity):
    """
    Immutable record of a material cost change (insert-only, never updated).

    Represents a single cost change event: GRN receipt, approval, reversal, etc.
    Used for audit trail and cost variance analysis.
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        material_id: uuid.UUID,
        old_cost: Optional[Decimal],
        new_cost: Decimal,
        change_type: str,  # GRN_RECEIPT, GRN_REVERSAL, COST_REVISION_APPROVED, etc.
        source_type: str,  # GRN, SUPPLIER_AGREEMENT, MANUAL, etc.
        source_id: Optional[str] = None,
        approved_by: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        """Initialize cost history record (immutable)."""
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=created_at,  # Immutable: updated_at = created_at
            is_deleted=False,  # Never deleted
            deleted_at=None,
        )

        self._material_id = material_id
        self._old_cost = Decimal(str(old_cost)) if old_cost is not None else None
        self._new_cost = Decimal(str(new_cost))
        self._change_type = change_type
        self._source_type = source_type
        self._source_id = source_id
        self._approved_by = approved_by
        self._notes = notes

    # ── Properties (all read-only, immutable) ──

    @property
    def material_id(self) -> uuid.UUID:
        return self._material_id

    @property
    def old_cost(self) -> Optional[Decimal]:
        return self._old_cost

    @property
    def new_cost(self) -> Decimal:
        return self._new_cost

    @property
    def change_type(self) -> str:
        return self._change_type

    @property
    def source_type(self) -> str:
        return self._source_type

    @property
    def source_id(self) -> Optional[str]:
        return self._source_id

    @property
    def approved_by(self) -> Optional[uuid.UUID]:
        return self._approved_by

    @property
    def notes(self) -> Optional[str]:
        return self._notes

    def get_variance_percent(self) -> Optional[Decimal]:
        """Calculate variance % between old and new cost."""
        if self._old_cost is None or self._old_cost == Decimal("0"):
            return None
        variance = ((self._new_cost - self._old_cost) / self._old_cost * Decimal("100"))
        return variance.quantize(Decimal("0.01"))

    def __repr__(self) -> str:
        return (
            f"<MaterialCostHistory(id={self.id}, material_id={self.material_id}, "
            f"change_type={self.change_type}, old={self.old_cost}, new={self.new_cost})>"
        )


# ── State Machine: StandardCostRevision ──


class StandardCostRevision(BaseEntity):
    """
    Domain entity for cost revision approval workflow.

    Represents a request to change a material's standard cost,
    with approval required from Finance/Costing Manager (segregation of duties).

    State Machine:
        PENDING → APPROVED / REJECTED
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        material_id: uuid.UUID,
        requested_by: uuid.UUID,
        requested_cost: Decimal,
        current_cost: Decimal,
        reason: str,
        notes: Optional[str] = None,
        status: StandardCostRevisionStatus = StandardCostRevisionStatus.PENDING,
        approved_by: Optional[uuid.UUID] = None,
        approved_at: Optional[datetime] = None,
        rejection_reason: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        """Initialize cost revision request."""
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )

        self._material_id = material_id
        self._requested_by = requested_by
        self._requested_cost = Decimal(str(requested_cost))
        self._current_cost = Decimal(str(current_cost))
        self._reason = reason
        self._notes = notes
        self._status = status
        self._approved_by = approved_by
        self._approved_at = approved_at
        self._rejection_reason = rejection_reason

        self._validate_costs()

    # ── Properties (read-only) ──

    @property
    def material_id(self) -> uuid.UUID:
        return self._material_id

    @property
    def requested_by(self) -> uuid.UUID:
        return self._requested_by

    @property
    def requested_cost(self) -> Decimal:
        return self._requested_cost

    @property
    def current_cost(self) -> Decimal:
        return self._current_cost

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def notes(self) -> Optional[str]:
        return self._notes

    @property
    def status(self) -> StandardCostRevisionStatus:
        return self._status

    @property
    def approved_by(self) -> Optional[uuid.UUID]:
        return self._approved_by

    @property
    def approved_at(self) -> Optional[datetime]:
        return self._approved_at

    @property
    def rejection_reason(self) -> Optional[str]:
        return self._rejection_reason

    # ── Business logic methods ──

    def approve(self, approver_id: uuid.UUID) -> None:
        """Approve cost revision (PENDING → APPROVED)."""
        if self._status != StandardCostRevisionStatus.PENDING:
            raise CostRevisionAlreadyReviewedError(self.id, self._status.value)

        # Segregation of duties: approver must not be requester
        if approver_id == self._requested_by:
            raise RequesterCannotApproveOwnRevisionError(self.id)

        self._status = StandardCostRevisionStatus.APPROVED
        self._approved_by = approver_id
        self._approved_at = datetime.now(timezone.utc)
        self._touch()

    def reject(self, rejection_reason: str) -> None:
        """Reject cost revision (PENDING → REJECTED)."""
        if self._status != StandardCostRevisionStatus.PENDING:
            raise CostRevisionAlreadyReviewedError(self.id, self._status.value)

        self._status = StandardCostRevisionStatus.REJECTED
        self._rejection_reason = rejection_reason
        self._touch()

    def get_variance_percent(self) -> Optional[Decimal]:
        """Calculate variance % between current and requested cost."""
        if self._current_cost == Decimal("0"):
            # Handle zero cost (initialization case)
            return None
        variance = ((self._requested_cost - self._current_cost) / self._current_cost * Decimal("100"))
        return variance.quantize(Decimal("0.01"))

    # ── Private methods ──

    def _validate_costs(self) -> None:
        """Validate cost fields."""
        if self._requested_cost < Decimal("0"):
            raise ValueError("requested_cost must be non-negative")
        if self._current_cost < Decimal("0"):
            raise ValueError("current_cost must be non-negative")


# ── PriceOverrideRecord ──


class PriceOverrideRecord(BaseEntity):
    """
    Record of a manual price override decision (for analytics and audit).

    Captures when a buyer overrides the system-suggested price for a GRN,
    used for tracking behavior and cost variance analysis.
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        material_id: uuid.UUID,
        grn_id: Optional[uuid.UUID] = None,
        suggested_price: Decimal,
        override_price: Decimal,
        override_reason: str,
        override_by: uuid.UUID,
        notes: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        """Initialize price override record."""
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )

        self._material_id = material_id
        self._grn_id = grn_id
        self._suggested_price = Decimal(str(suggested_price))
        self._override_price = Decimal(str(override_price))
        self._override_reason = override_reason
        self._override_by = override_by
        self._notes = notes

    # ── Properties (read-only) ──

    @property
    def material_id(self) -> uuid.UUID:
        return self._material_id

    @property
    def grn_id(self) -> Optional[uuid.UUID]:
        return self._grn_id

    @property
    def suggested_price(self) -> Decimal:
        return self._suggested_price

    @property
    def override_price(self) -> Decimal:
        return self._override_price

    @property
    def override_reason(self) -> str:
        return self._override_reason

    @property
    def override_by(self) -> uuid.UUID:
        return self._override_by

    @property
    def notes(self) -> Optional[str]:
        return self._notes

    def get_variance_percent(self) -> Decimal:
        """Calculate variance % between suggested and override price."""
        if self._suggested_price == Decimal("0"):
            return Decimal("0")
        variance = ((self._override_price - self._suggested_price) / self._suggested_price * Decimal("100"))
        return variance.quantize(Decimal("0.01"))

    def __repr__(self) -> str:
        return (
            f"<PriceOverrideRecord(id={self.id}, material_id={self.material_id}, "
            f"suggested={self.suggested_price}, override={self.override_price})>"
        )
