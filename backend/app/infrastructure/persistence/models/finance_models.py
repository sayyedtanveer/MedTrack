"""Finance ORM models: invoices, payments, journals, and tenant finance settings."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.infrastructure.persistence.database import Base


class InvoiceModel(Base):
    """Customer invoice (accounts receivable)."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_invoice_tenant_number"),
        Index("ix_invoices_tenant_id", "tenant_id"),
        Index("ix_invoices_client_id", "client_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_due_date", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    sales_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="RESTRICT"), nullable=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sales_clients.id", ondelete="RESTRICT"), nullable=False
    )

    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_gst_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    grand_total: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    paid_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
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

    lines: Mapped[List["InvoiceLineModel"]] = relationship(
        "InvoiceLineModel",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payments: Mapped[List["PaymentModel"]] = relationship(
        "PaymentModel",
        back_populates="invoice",
        lazy="selectin",
    )

    @property
    def balance_due(self) -> float:
        return float(self.grand_total) - float(self.paid_amount)


class InvoiceLineModel(Base):
    """Invoice line snapshot from a sales order or manual entry."""

    __tablename__ = "invoice_lines"
    __table_args__ = (
        Index("ix_invoice_lines_invoice_id", "invoice_id"),
        Index("ix_invoice_lines_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    invoice: Mapped["InvoiceModel"] = relationship("InvoiceModel", back_populates="lines")


class SupplierInvoiceModel(Base):
    """Supplier invoice (accounts payable)."""

    __tablename__ = "supplier_invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_supplier_invoice_tenant_number"),
        Index("ix_supplier_invoices_tenant", "tenant_id"),
        Index("ix_supplier_invoices_supplier", "supplier_id"),
        Index("ix_supplier_invoices_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    supplier_invoice_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    purchase_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=True
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    grand_total: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    paid_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
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

    supplier_payments: Mapped[List["SupplierPaymentModel"]] = relationship(
        "SupplierPaymentModel",
        back_populates="supplier_invoice",
        lazy="selectin",
    )

    @property
    def balance_due(self) -> float:
        return float(self.grand_total) - float(self.paid_amount)


class PaymentModel(Base):
    """Customer payment (AR)."""

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "payment_number", name="uq_payment_tenant_number"),
        Index("ix_payments_tenant", "tenant_id"),
        Index("ix_payments_invoice", "invoice_id"),
        Index("ix_payments_client", "client_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    payment_number: Mapped[str] = mapped_column(String(50), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sales_clients.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False, default="BANK_TRANSFER")
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    invoice: Mapped["InvoiceModel"] = relationship("InvoiceModel", back_populates="payments")


class SupplierPaymentModel(Base):
    """Supplier payment (AP)."""

    __tablename__ = "supplier_payments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "payment_number", name="uq_supplier_payment_tenant_number"),
        Index("ix_supplier_payments_tenant", "tenant_id"),
        Index("ix_supplier_payments_supplier", "supplier_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    payment_number: Mapped[str] = mapped_column(String(50), nullable=False)
    supplier_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_invoices.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False, default="BANK_TRANSFER")
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    supplier_invoice: Mapped["SupplierInvoiceModel"] = relationship(
        "SupplierInvoiceModel",
        back_populates="supplier_payments",
    )


class ChartOfAccountModel(Base):
    """Tenant-scoped chart of accounts used by the accounting engine."""

    __tablename__ = "chart_of_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_coa_tenant_code"),
        UniqueConstraint("tenant_id", "name", name="uq_coa_tenant_name"),
        Index("ix_coa_tenant", "tenant_id"),
        Index("ix_coa_type", "tenant_id", "account_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    normal_balance: Mapped[str] = mapped_column(String(10), nullable=False, default="DEBIT")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    journal_lines: Mapped[List["JournalLineModel"]] = relationship(
        "JournalLineModel",
        back_populates="account",
        lazy="selectin",
    )


class JournalEntryModel(Base):
    """Journal entry header for balanced double-entry postings."""

    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entry_number", name="uq_journal_entry_tenant_number"),
        Index("ix_journal_entries_tenant", "tenant_id"),
        Index("ix_journal_entries_reference", "tenant_id", "reference_type", "reference_id"),
        Index("ix_journal_entries_date", "tenant_id", "entry_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    entry_number: Mapped[str] = mapped_column(String(50), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="POSTED")
    reverses_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True
    )
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    lines: Mapped[List["JournalLineModel"]] = relationship(
        "JournalLineModel",
        back_populates="journal_entry",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class JournalLineModel(Base):
    """Journal entry line."""

    __tablename__ = "journal_lines"
    __table_args__ = (
        Index("ix_journal_lines_entry", "journal_entry_id"),
        Index("ix_journal_lines_account", "account_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    debit: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    credit: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    journal_entry: Mapped["JournalEntryModel"] = relationship("JournalEntryModel", back_populates="lines")
    account: Mapped["ChartOfAccountModel"] = relationship("ChartOfAccountModel", back_populates="journal_lines")


class TenantFinanceSettingsModel(Base):
    """Tenant-level finance customization such as numbering, branding, and tax defaults."""

    __tablename__ = "tenant_finance_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_finance_settings_tenant"),
        Index("ix_tenant_finance_settings_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    invoice_prefix: Mapped[str] = mapped_column(String(20), nullable=False, default="INV")
    supplier_invoice_prefix: Mapped[str] = mapped_column(String(20), nullable=False, default="SINV")
    payment_prefix: Mapped[str] = mapped_column(String(20), nullable=False, default="PAY")
    supplier_payment_prefix: Mapped[str] = mapped_column(String(20), nullable=False, default="SPAY")
    invoice_template: Mapped[str] = mapped_column(String(50), nullable=False, default="standard")
    default_tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    default_payment_terms_days: Mapped[int] = mapped_column(nullable=False, default=30)
    gst_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    custom_template: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    ar_account_code: Mapped[str] = mapped_column(String(20), nullable=False, default="1100")
    bank_account_code: Mapped[str] = mapped_column(String(20), nullable=False, default="1000")
    ap_account_code: Mapped[str] = mapped_column(String(20), nullable=False, default="2000")
    revenue_account_code: Mapped[str] = mapped_column(String(20), nullable=False, default="4000")
    expense_account_code: Mapped[str] = mapped_column(String(20), nullable=False, default="5000")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class FinancialTransactionModel(Base):
    """Legacy ledger rows retained for backward-compatible screens and analytics."""

    __tablename__ = "financial_transactions"
    __table_args__ = (
        Index("ix_financial_transactions_reference", "reference_type", "reference_id"),
        Index("ix_financial_transactions_tenant", "tenant_id"),
        Index("ix_financial_transactions_date", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    reference_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), nullable=False, default="RECEIVABLE")
    debit: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    credit: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class NotificationModel(Base):
    """In-app notification model."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user", "user_id", "is_read"),
        Index("ix_notifications_tenant", "tenant_id"),
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class BackgroundJobModel(Base):
    """Background job tracking."""

    __tablename__ = "background_jobs"
    __table_args__ = (
        Index("ix_background_jobs_status", "status"),
        Index("ix_background_jobs_type", "job_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
