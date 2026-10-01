"""Subcontracting / Outside Processing domain models.

Lifecycle:
  draft → approved → materials_issued → partially_received → completed
                  ↘                                          ↗
                   cancelled
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.infrastructure.persistence.database import Base


class SubcontractOrderModel(Base):
    """One Subcontract Order = one external processing event at one vendor."""

    __tablename__ = "subcontract_orders"
    __table_args__ = (
        UniqueConstraint("tenant_id", "order_number", name="uq_subco_tenant_number"),
        Index("ix_subco_supplier", "supplier_id"),
        Index("ix_subco_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    order_number: Mapped[str] = mapped_column(String(40), nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )

    # Output product: the semi-finished / processed material that will be returned
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), nullable=False, default="variant")
    quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)

    # Optional BOM reference used to auto-load required components
    bom_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("boms.id", ondelete="SET NULL"), nullable=True
    )

    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status: draft | approved | materials_issued | partially_received | completed | cancelled
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")

    # Output batch created when processed material is received back
    output_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batches.id", ondelete="SET NULL"), nullable=True
    )
    received_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)

    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    lines: Mapped[list["SubcontractOrderLineModel"]] = relationship(
        "SubcontractOrderLineModel",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    issues: Mapped[list["SubcontractMaterialIssueModel"]] = relationship(
        "SubcontractMaterialIssueModel",
        back_populates="order",
        cascade="all, delete-orphan",
    )


class SubcontractOrderLineModel(Base):
    """Required component snapshot — one row per raw material component.

    Copied from BOM at order approval time (like WorkOrderMaterialModel).
    Tracks required / issued / returned quantities per component.
    """

    __tablename__ = "subcontract_order_lines"
    __table_args__ = (
        Index("ix_sco_line_order", "subcontract_order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    subcontract_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subcontract_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False
    )

    required_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    issued_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    consumed_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    returned_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)

    # Derived status per line
    @property
    def line_status(self) -> str:
        if self.returned_quantity >= self.issued_quantity > 0:
            return "returned"
        if self.issued_quantity >= self.required_quantity:
            return "issued"
        if self.issued_quantity > 0:
            return "partial"
        return "pending"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    order: Mapped["SubcontractOrderModel"] = relationship("SubcontractOrderModel", back_populates="lines")


class SubcontractMaterialIssueModel(Base):
    """One row per material issue transaction — supports multiple batches per material.

    batch_id is a FK to BatchModel (UUID) for proper traceability.
    batch_number is kept for display / backward compat.
    """

    __tablename__ = "subcontract_material_issues"
    __table_args__ = (
        Index("ix_sco_issue_order", "subcontract_order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    subcontract_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subcontract_orders.id", ondelete="CASCADE"), nullable=False
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False
    )
    # Proper batch reference (UUID FK) — replaces the old free-text string
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batches.id", ondelete="SET NULL"), nullable=True
    )
    # Kept for display and backward compat with legacy rows
    batch_number: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    returned_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)

    from_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    issued_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    order: Mapped["SubcontractOrderModel"] = relationship("SubcontractOrderModel", back_populates="issues")
