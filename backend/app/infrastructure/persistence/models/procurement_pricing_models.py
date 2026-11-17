"""
ORM Models for Procurement Pricing (Phase 2).

This module contains SQLAlchemy models for:
- SupplierPriceAgreementModel: Supplier pricing contracts with versioning
- MaterialCostHistoryModel: Immutable cost audit log (insert-only)
- StandardCostRevisionModel: Cost approval workflow tracking
- PriceOverrideRecordModel: Manual price override analytics

Multi-tenancy: All models enforce tenant_id filter.
Soft deletes: All models use is_deleted + deleted_at pattern.
Audit trail: All models track created_by/updated_by timestamps.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class SupplierPriceAgreementModel(Base):
    """
    Supplier pricing agreement contract (e.g., volume discounts, effective dates).

    State Machine:
        DRAFT → PENDING → APPROVED → ACTIVE → EXPIRED/CANCELLED

    Fields:
    - supplier_id: FK to suppliers(id)
    - material_id: FK to materials(id)
    - status: State (DRAFT, PENDING, APPROVED, ACTIVE, EXPIRED, CANCELLED)
    - effective_from/to: Date range for agreement validity
    - base_price: Price per unit in supplier's currency
    - currency_code: ISO 4217 (USD, INR, EUR, etc.)
    - quantity_tier: JSON array of {min_qty, max_qty, discount_percent} for tiered pricing
    - notes: Terms, conditions, or special agreements
    """

    __tablename__ = "supplier_price_agreements"

    __table_args__ = (
        Index("ix_supplier_price_agreements_tenant_id", "tenant_id"),
        Index("ix_supplier_price_agreements_is_deleted", "is_deleted"),
        Index("ix_supplier_price_agreements_status", "status"),
        Index("ix_supplier_price_agreements_supplier_id", "supplier_id"),
        Index("ix_supplier_price_agreements_material_id", "material_id"),
        Index("ix_supplier_price_agreements_effective_from", "effective_from"),
    )

    # Primary identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Foreign keys
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Agreement status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="DRAFT",
        comment="DRAFT, PENDING, APPROVED, ACTIVE, EXPIRED, CANCELLED",
    )

    # Pricing details
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, comment="Price per unit in supplier's currency"
    )
    currency_code: Mapped[str] = mapped_column(
        String(3), nullable=False, comment="ISO 4217 currency code (USD, INR, EUR)"
    )
    purchase_uom_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units_of_measure.id", ondelete="RESTRICT"),
        nullable=True,
    )
    minimum_order_quantity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 6), nullable=True
    )
    quantity_tier: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="JSON array of tiered pricing {min_qty, max_qty, discount_percent}"
    )

    # Agreement validity
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="Agreement start date"
    )
    effective_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Agreement end date (null = ongoing)"
    )

    # Notes and conditions
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Terms, conditions, special agreements"
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Audit trail
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(datetime.now().astimezone().tzinfo),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(datetime.now().astimezone().tzinfo),
        onupdate=lambda: datetime.now(datetime.now().astimezone().tzinfo),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SupplierPriceAgreement(id={self.id}, supplier_id={self.supplier_id}, material_id={self.material_id}, status={self.status})>"


class MaterialCostHistoryModel(Base):
    """
    Immutable audit log of all material cost changes (insert-only, no updates).

    This is the source of truth for cost history and reversals.
    Every cost change (GRN receipt, GRN reversal, approval, rejection) creates a new record.

    Fields:
    - material_id: FK to materials(id)
    - old_cost: Previous cost (null if first initialization)
    - new_cost: New cost value
    - change_type: Type of change (GRN_RECEIPT, GRN_REVERSAL, COST_REVISION_APPROVED, COST_REVISION_REJECTED, MANUAL_OVERRIDE)
    - source_type: Source of change (GRN, PO_RECEIPT, SUPPLIER_AGREEMENT, MANUAL)
    - source_id: ID of the source transaction (grn_id, cost_revision_id, etc.)
    - approved_by: User who approved (if applicable)
    - notes: Change reason or context
    """

    __tablename__ = "material_cost_history"

    __table_args__ = (
        Index("ix_material_cost_history_tenant_id", "tenant_id"),
        Index("ix_material_cost_history_material_id", "material_id"),
        Index("ix_material_cost_history_change_type", "change_type"),
        Index("ix_material_cost_history_created_at", "created_at"),
    )

    # Primary identity (insert-only, no updates)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Foreign keys
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Cost change details
    old_cost: Mapped[Optional[float]] = mapped_column(
        Numeric(18, 6),
        nullable=True,
        comment="Previous cost (null = first initialization)",
    )
    new_cost: Mapped[float] = mapped_column(
        Numeric(18, 6), nullable=False, comment="New cost value"
    )

    # Change classification
    change_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="GRN_RECEIPT, GRN_REVERSAL, COST_REVISION_APPROVED, COST_REVISION_REJECTED, MANUAL_OVERRIDE",
    )
    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="GRN, PO_RECEIPT, SUPPLIER_AGREEMENT, MANUAL",
    )
    source_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="ID of the source transaction (grn_id, cost_revision_id)"
    )

    # Approval context
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        comment="User who approved the change"
    )

    # Reason and notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Change reason or context"
    )

    # Timestamp (insert-only, immutable)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(datetime.now().astimezone().tzinfo),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<MaterialCostHistory(id={self.id}, material_id={self.material_id}, change_type={self.change_type}, old_cost={self.old_cost}, new_cost={self.new_cost})>"


class StandardCostRevisionModel(Base):
    """
    Cost approval workflow tracking for standard material costs.

    State Machine:
        PENDING → APPROVED / REJECTED

    Fields:
    - material_id: FK to materials(id)
    - requested_by: User who initiated the cost revision request
    - requested_cost: Proposed new cost
    - current_cost: Cost at time of request (for reference)
    - reason: Reason for cost change (GRN_VARIANCE, SUPPLIER_AGREEMENT, VARIANCE_THRESHOLD, etc.)
    - variance_percent: % difference between requested and current (for variance tracking)
    - status: PENDING, APPROVED, REJECTED
    - approved_by: Finance/Costing Manager who approved
    - rejection_reason: If rejected, reason why
    - approved_at: Timestamp of approval decision
    """

    __tablename__ = "standard_cost_revisions"

    __table_args__ = (
        Index("ix_standard_cost_revisions_tenant_id", "tenant_id"),
        Index("ix_standard_cost_revisions_material_id", "material_id"),
        Index("ix_standard_cost_revisions_status", "status"),
        Index("ix_standard_cost_revisions_requested_by", "requested_by"),
        Index("ix_standard_cost_revisions_approved_by", "approved_by"),
        Index("ix_standard_cost_revisions_created_at", "created_at"),
    )

    # Primary identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Foreign keys
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    # Cost details
    requested_cost: Mapped[float] = mapped_column(
        Numeric(18, 6), nullable=False, comment="Proposed new cost"
    )
    current_cost: Mapped[float] = mapped_column(
        Numeric(18, 6),
        nullable=False,
        comment="Cost at time of request (for reference)",
    )
    variance_percent: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="% difference between requested and current",
    )

    # Request details
    reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="GRN_VARIANCE, SUPPLIER_AGREEMENT, VARIANCE_THRESHOLD, MANUAL_ADJUSTMENT",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Detailed reason or context"
    )

    # Approval workflow
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", comment="PENDING, APPROVED, REJECTED"
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Finance/Costing Manager who approved",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp of approval decision"
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="If rejected, reason why"
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Audit trail
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(datetime.now().astimezone().tzinfo),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(datetime.now().astimezone().tzinfo),
        onupdate=lambda: datetime.now(datetime.now().astimezone().tzinfo),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<StandardCostRevision(id={self.id}, material_id={self.material_id}, status={self.status}, requested_cost={self.requested_cost})>"


class PriceOverrideRecordModel(Base):
    """
    Analytics record for manual price overrides (when buyer overrides suggestion).

    Used for tracking, audit, and analytics on price override behavior.

    Fields:
    - material_id: FK to materials(id)
    - grn_id: FK to goods_receipts_notes(id) (the GRN where override occurred)
    - suggested_price: Price algorithm suggested (before override)
    - override_price: Price that was actually used
    - override_reason: Why the override was made (QUALITY_ISSUE, RUSH_ORDER, BULK_DISCOUNT, etc.)
    - override_by: User who made the override
    - variance_percent: % difference between suggested and override
    """

    __tablename__ = "price_override_records"

    __table_args__ = (
        Index("ix_price_override_records_tenant_id", "tenant_id"),
        Index("ix_price_override_records_material_id", "material_id"),
        Index("ix_price_override_records_grn_id", "grn_id"),
        Index("ix_price_override_records_override_by", "override_by"),
        Index("ix_price_override_records_created_at", "created_at"),
    )

    # Primary identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Foreign keys
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=True
    )
    purchase_order_line_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    grn_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_receipt_notes.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="GRN where override occurred",
    )

    # Override details
    suggested_price: Mapped[float] = mapped_column(
        Numeric(18, 6), nullable=False, comment="Price algorithm suggested"
    )
    override_price: Mapped[float] = mapped_column(
        Numeric(18, 6), nullable=False, comment="Price that was actually used"
    )
    variance_percent: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 2), nullable=True, comment="% difference between suggested and override"
    )

    # Override context
    override_reason: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="QUALITY_ISSUE, RUSH_ORDER, BULK_DISCOUNT, VENDOR_PREFERENCE, OTHER",
    )
    pricing_source: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    currency_code: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units_of_measure.id", ondelete="RESTRICT"),
        nullable=True,
    )
    override_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Additional context for override"
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Audit trail
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(datetime.now().astimezone().tzinfo),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(datetime.now().astimezone().tzinfo),
        onupdate=lambda: datetime.now(datetime.now().astimezone().tzinfo),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PriceOverrideRecord(id={self.id}, material_id={self.material_id}, suggested_price={self.suggested_price}, override_price={self.override_price})>"
