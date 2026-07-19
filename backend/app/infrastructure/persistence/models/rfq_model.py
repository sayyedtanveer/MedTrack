"""RFQ (Request for Quotation) and Invoice Dispute ORM models."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.infrastructure.persistence.database import Base


class RFQModel(Base):
    """Request For Quotation header — sent to one or more suppliers."""

    __tablename__ = "rfqs"
    __table_args__ = (Index("ix_rfq_tenant", "tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    rfq_number: Mapped[str] = mapped_column(String(40), nullable=False)
    material_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_requests.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # draft → sent → closed → awarded
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    awarded_supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    awarded_po_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    lines: Mapped[List["RFQLineModel"]] = relationship(
        "RFQLineModel", back_populates="rfq", cascade="all, delete-orphan"
    )
    supplier_invites: Mapped[List["RFQSupplierModel"]] = relationship(
        "RFQSupplierModel", back_populates="rfq", cascade="all, delete-orphan"
    )


class RFQLineModel(Base):
    """A material line within an RFQ."""

    __tablename__ = "rfq_lines"
    __table_args__ = (Index("ix_rfq_lines_rfq", "rfq_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    rfq: Mapped["RFQModel"] = relationship("RFQModel", back_populates="lines")


class RFQSupplierModel(Base):
    """Supplier invited to submit a quotation for an RFQ."""

    __tablename__ = "rfq_suppliers"
    __table_args__ = (Index("ix_rfq_supplier_rfq", "rfq_id", "supplier_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    # invited / responded / declined
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="invited")
    quotation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_quotations.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    rfq: Mapped["RFQModel"] = relationship("RFQModel", back_populates="supplier_invites")


class InvoiceDisputeModel(Base):
    """Audit-trailed record when a supplier disputes an invoice amount."""

    __tablename__ = "invoice_disputes"
    __table_args__ = (Index("ix_invoice_dispute_invoice", "supplier_invoice_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    supplier_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_invoices.id", ondelete="CASCADE"), nullable=False
    )
    # Amount the supplier claims should be payable
    disputed_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # open / approved / rejected
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raised_by_supplier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
