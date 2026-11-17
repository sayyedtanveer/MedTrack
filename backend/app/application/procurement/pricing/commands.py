"""
Procurement pricing commands (Phase 2 application layer).

All commands are frozen dataclasses (immutable).
Commands represent intentions to mutate state (CQRS write operations).
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


# ── Supplier Price Agreement Commands ──


@dataclass(frozen=True)
class CreateSupplierPriceAgreementCommand:
    """Create a new supplier price agreement (DRAFT state)."""
    tenant_id: uuid.UUID
    supplier_id: uuid.UUID
    material_id: uuid.UUID
    base_price: Decimal
    currency_code: str
    effective_from: datetime
    effective_to: Optional[datetime] = None
    purchase_uom_id: Optional[uuid.UUID] = None
    minimum_order_quantity: Optional[Decimal] = None
    quantity_tiers: Optional[List[dict]] = None  # [{"min_qty": 0, "max_qty": 100, "discount_percent": 5}, ...]
    notes: Optional[str] = None
    created_by: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class SubmitSupplierPriceAgreementForApprovalCommand:
    """Submit agreement for approval (DRAFT → PENDING)."""
    tenant_id: uuid.UUID
    agreement_id: uuid.UUID
    submitted_by: uuid.UUID


@dataclass(frozen=True)
class ApproveSupplierPriceAgreementCommand:
    """Approve agreement (PENDING → APPROVED)."""
    tenant_id: uuid.UUID
    agreement_id: uuid.UUID
    approved_by: uuid.UUID  # Procurement Manager


@dataclass(frozen=True)
class RejectSupplierPriceAgreementCommand:
    """Reject agreement back to DRAFT (PENDING → DRAFT)."""
    tenant_id: uuid.UUID
    agreement_id: uuid.UUID
    rejection_reason: str
    rejected_by: uuid.UUID


@dataclass(frozen=True)
class ActivateSupplierPriceAgreementCommand:
    """Activate agreement (APPROVED → ACTIVE)."""
    tenant_id: uuid.UUID
    agreement_id: uuid.UUID
    activated_by: uuid.UUID


@dataclass(frozen=True)
class CancelSupplierPriceAgreementCommand:
    """Cancel agreement from any non-terminal state."""
    tenant_id: uuid.UUID
    agreement_id: uuid.UUID
    cancellation_reason: str
    cancelled_by: uuid.UUID


# ── Standard Cost Revision Commands ──


@dataclass(frozen=True)
class InitializeStandardCostCommand:
    """Initialize material standard cost (first time, always requires approval)."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    initial_cost: Decimal
    reason: str = "INITIAL_SETUP"
    notes: Optional[str] = None
    requested_by: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class CreateStandardCostRevisionCommand:
    """Request approval to change material standard cost."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    requested_cost: Decimal
    reason: str  # GRN_VARIANCE, SUPPLIER_AGREEMENT, MANUAL_ADJUSTMENT, etc.
    notes: Optional[str] = None
    requested_by: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class ApproveStandardCostRevisionCommand:
    """Approve cost revision (PENDING → APPROVED)."""
    tenant_id: uuid.UUID
    revision_id: uuid.UUID
    approved_by: uuid.UUID  # Finance/Costing Manager


@dataclass(frozen=True)
class RejectStandardCostRevisionCommand:
    """Reject cost revision (PENDING → REJECTED)."""
    tenant_id: uuid.UUID
    revision_id: uuid.UUID
    rejection_reason: str
    rejected_by: uuid.UUID


# ── Price History Commands ──


@dataclass(frozen=True)
class RecordMaterialCostChangeCommand:
    """Record a material cost change to immutable history (append-only)."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    old_cost: Optional[Decimal]
    new_cost: Decimal
    change_type: str  # GRN_RECEIPT, COST_REVISION_APPROVED, MANUAL_OVERRIDE, etc.
    source_type: str  # GRN, SUPPLIER_AGREEMENT, MANUAL
    source_id: Optional[str] = None  # GRN ID, revision ID, etc.
    approved_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    recorded_by: uuid.UUID = field(default_factory=uuid.uuid4)


# ── Price Override Commands ──


@dataclass(frozen=True)
class RecordPriceOverrideCommand:
    """Record manual price override for analytics."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    grn_id: Optional[uuid.UUID]
    suggested_price: Decimal
    override_price: Decimal
    override_reason: str  # QUALITY_ISSUE, RUSH_ORDER, BULK_DISCOUNT, VENDOR_PREFERENCE, OTHER
    notes: Optional[str] = None
    override_by: uuid.UUID = field(default_factory=uuid.uuid4)
