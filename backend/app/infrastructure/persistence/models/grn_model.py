from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.infrastructure.persistence.database import Base

if TYPE_CHECKING:
    from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel
    from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel


class GoodsReceiptNoteModel(Base):
    """
    Goods Receipt Note (GRN): Tracks delivery and receipt of goods from supplier.
    
    Flow: PO → GRN (delivery) → Inventory Update (received into warehouse)
    """
    __tablename__ = "goods_receipt_notes"
    __table_args__ = (
        Index("ix_grn_tenant_po", "tenant_id", "purchase_order_id"),
        Index("ix_grn_tenant_supplier", "tenant_id", "supplier_id"),
        Index("ix_grn_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    grn_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    
    # Receipt details
    scheduled_delivery_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_receipt_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    warehouse_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    
    # Status: pending_receipt, received, in_inspection, inspected, rejected
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_receipt")
    
    # Optional driver/transport details
    driver_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vehicle_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    transport_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Receiving notes
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Audit
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
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
    lines: Mapped[List["GRNLineModel"]] = relationship(
        "GRNLineModel", back_populates="grn", cascade="all, delete-orphan"
    )
    purchase_order: Mapped["PurchaseOrderModel"] = relationship("PurchaseOrderModel", lazy="joined")
    supplier: Mapped["SupplierModel"] = relationship("SupplierModel", lazy="joined")


class GRNLineModel(Base):
    """
    Individual line items in a GRN: tracks quantities received per PO line.
    Links GRN → PO lines → Inventory transactions
    """
    __tablename__ = "grn_lines"
    __table_args__ = (
        Index("ix_grn_line_grn", "grn_id"),
        Index("ix_grn_line_po_line", "po_line_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    grn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("goods_receipt_notes.id", ondelete="CASCADE"), nullable=False
    )
    po_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"), nullable=False
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False
    )
    
    # Quantities
    po_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)  # From PO line
    received_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)  # Actually received
    accepted_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)  # After inspection
    rejected_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)  # After inspection
    
    unit_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)  # From PO
    
    # Inventory transaction reference (once goods are accepted into inventory)
    inventory_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
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
    grn: Mapped["GoodsReceiptNoteModel"] = relationship("GoodsReceiptNoteModel", back_populates="lines")
