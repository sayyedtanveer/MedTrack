"""Sales order ORM models for database persistence."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property
from sqlalchemy.sql import select

from backend.app.infrastructure.persistence.database import Base


class ClientModel(Base):
    """Client ORM model for database persistence."""

    __tablename__ = "sales_clients"

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_client_tenant_code"),
        Index("ix_client_tenant_id", "tenant_id"),
        Index("ix_client_is_active", "is_active"),
        Index("ix_client_is_deleted", "is_deleted"),
    )

    # Primary and tenant
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Business fields
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    gst_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Credit management
    credit_limit: Mapped[Optional[float]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    credit_used: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )

    # Payment terms (days)
    payment_terms_days: Mapped[int] = mapped_column(nullable=False, default=0)

    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Pricing: default price list assigned to this client
    default_price_list_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_price_lists.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    sales_orders: Mapped[List["SalesOrderModel"]] = relationship(
        "SalesOrderModel",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    addresses: Mapped[List["ClientAddressModel"]] = relationship(
        "ClientAddressModel",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ClientModel id={self.id} code={self.code} name={self.name}>"


class SalesOrderModel(Base):
    """Sales Order ORM model."""

    __tablename__ = "sales_orders"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "order_number", name="uq_sales_order_tenant_number"
        ),
        Index("ix_sales_order_tenant_id", "tenant_id"),
        Index("ix_sales_order_client_id", "client_id"),
        Index("ix_sales_order_status", "status"),
        Index("ix_sales_order_order_date", "order_date"),
        Index("ix_sales_order_delivery_date", "delivery_date"),
        Index("ix_sales_order_is_deleted", "is_deleted"),
    )

    # Primary and tenant
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Business identity
    order_number: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Foreign keys
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_clients.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Dates
    order_date: Mapped[str] = mapped_column(nullable=False)  # ISO date string
    delivery_date: Mapped[str] = mapped_column(nullable=False)

    # Status fields
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )

    # Financial totals (denormalized for efficiency)
    subtotal: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    discount_amount: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    tax_amount: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    grand_total: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )

    # Estimated dates for order tracking (Req 28.1)
    estimated_completion_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )
    expected_dispatch_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )
    expected_delivery_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approval_notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    client: Mapped["ClientModel"] = relationship(
        "ClientModel", back_populates="sales_orders", lazy="selectin"
    )
    lines: Mapped[List["SalesOrderLineModel"]] = relationship(
        "SalesOrderLineModel",
        back_populates="sales_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<SalesOrderModel id={self.id} order_number={self.order_number}>"


class SalesOrderLineModel(Base):
    """Sales Order Line ORM model."""

    __tablename__ = "sales_order_lines"

    __table_args__ = (
        Index("ix_sales_order_line_order_id", "sales_order_id"),
        Index("ix_sales_order_line_product_id", "product_id"),
        Index("ix_sales_order_line_status", "status"),
    )

    # Primary and foreign keys
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sales_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Product references
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_type: Mapped[str] = mapped_column(String(50), nullable=False)
    uom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Line quantities and pricing
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    tax_rate: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )

    # Calculated totals
    tax_amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    line_total: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )

    # Allocation tracking
    allocated_quantity: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    dispatched_quantity: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    shipped_quantity: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    backorder_quantity: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )

    # Work order linkage (if created for shortage)
    work_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Shortage tracking (Req 16 — Gap #2)
    # shortfall_quantity: the quantity that could not be reserved from existing FG stock
    shortfall_quantity: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    # production_required: True when FG stock was insufficient and a work order is needed
    production_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    # Extended line status for partial dispatch tracking (Req 19.3, 20.1)
    # Values: PENDING, ALLOCATED, PARTIAL, SHORT_CLOSED, BACKORDER, CANCELLED
    line_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    sales_order: Mapped["SalesOrderModel"] = relationship(
        "SalesOrderModel", back_populates="lines", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<SalesOrderLineModel id={self.id} "
            f"product={self.product_id} qty={self.quantity}>"
        )


class PriceListModel(Base):
    """Price List ORM model."""

    __tablename__ = "sales_price_lists"

    __table_args__ = (
        Index("ix_price_list_tenant_id", "tenant_id"),
        Index("ix_price_list_is_default", "is_default"),
        Index("ix_price_list_valid_from", "valid_from"),
        Index("ix_price_list_is_active", "is_active"),
        Index("ix_price_list_is_deleted", "is_deleted"),
    )

    # Primary and tenant
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Validity period
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    lines: Mapped[List["PriceListLineModel"]] = relationship(
        "PriceListLineModel",
        back_populates="price_list",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PriceListModel id={self.id} name={self.name}>"


class PriceListLineModel(Base):
    """Price List Line ORM model."""

    __tablename__ = "sales_price_list_lines"

    __table_args__ = (
        Index("ix_price_list_line_price_list_id", "price_list_id"),
        Index("ix_price_list_line_product", "price_list_id", "product_id", "product_type"),
    )

    # Primary and foreign keys
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    price_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_price_lists.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Product reference
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Pricing
    unit_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    price_list: Mapped["PriceListModel"] = relationship(
        "PriceListModel", back_populates="lines", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<PriceListLineModel id={self.id} "
            f"product={self.product_id} price={self.unit_price}>"
        )


class ClientAddressModel(Base):
    """Billing and shipping addresses for client portal self-service."""

    __tablename__ = "client_addresses"
    __table_args__ = (
        Index("ix_client_addresses_tenant", "tenant_id"),
        Index("ix_client_addresses_client", "client_id"),
        Index("ix_client_addresses_default", "client_id", "type", "is_default"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line1: Mapped[str] = mapped_column(Text, nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    client: Mapped["ClientModel"] = relationship("ClientModel", back_populates="addresses", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ClientAddressModel id={self.id} type={self.type} client={self.client_id}>"

