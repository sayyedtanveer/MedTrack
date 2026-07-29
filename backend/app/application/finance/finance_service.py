"""Finance application service for AR, AP, journals, settings, and statements."""

from __future__ import annotations

import io
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable, List, Optional

from sqlalchemy import and_, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.finance_models import (
    ChartOfAccountModel,
    FinancialTransactionModel,
    InvoiceLineModel,
    InvoiceModel,
    JournalEntryModel,
    JournalLineModel,
    PaymentModel,
    SupplierInvoiceModel,
    SupplierPaymentModel,
    TenantFinanceSettingsModel,
)
from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel
from backend.app.infrastructure.persistence.models.sales_models import (
    ClientModel,
    SalesOrderLineModel,
    SalesOrderModel,
)
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.user_model import UserModel

logger = logging.getLogger(__name__)


def _as_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def _as_float(value: Any) -> float:
    return float(_as_decimal(value))


def _json_safe_uuid(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray)) and len(value) == 16:
        return str(uuid.UUID(bytes=bytes(value)))
    return str(value)


def _pdf_escape(text_value: str) -> str:
    return str(text_value or "").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_minimal_pdf(lines: list[str]) -> bytes:
    buffer = io.StringIO()
    offsets: list[int] = []

    def write(chunk: str) -> None:
        buffer.write(chunk)

    write("%PDF-1.4\n")
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    ]

    content_lines = ["BT", "/F1 12 Tf", "50 760 Td", "14 TL"]
    for idx, line in enumerate(lines):
        if idx == 0:
            content_lines.append(f"({_pdf_escape(line)}) Tj")
        else:
            content_lines.append(f"T* ({_pdf_escape(line)}) Tj")
    content_lines.append("ET")
    content_stream = "\n".join(content_lines)
    objects.append(f"<< /Length {len(content_stream.encode('utf-8'))} >>\nstream\n{content_stream}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(buffer.getvalue().encode("utf-8")))
        write(f"{index} 0 obj\n{obj}\nendobj\n")

    xref_offset = len(buffer.getvalue().encode("utf-8"))
    write(f"xref\n0 {len(objects) + 1}\n")
    write("0000000000 65535 f \n")
    for offset in offsets:
        write(f"{offset:010d} 00000 n \n")
    write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF")
    return buffer.getvalue().encode("utf-8")


DEFAULT_CHART_OF_ACCOUNTS = (
    {
        "code": "1000",
        "name": "Bank",
        "account_type": "ASSET",
        "category": "CURRENT_ASSET",
        "normal_balance": "DEBIT",
        "legacy_label": "CASH",
    },
    {
        "code": "1100",
        "name": "Accounts Receivable",
        "account_type": "ASSET",
        "category": "CURRENT_ASSET",
        "normal_balance": "DEBIT",
        "legacy_label": "RECEIVABLE",
    },
    {
        "code": "2000",
        "name": "Accounts Payable",
        "account_type": "LIABILITY",
        "category": "CURRENT_LIABILITY",
        "normal_balance": "CREDIT",
        "legacy_label": "PAYABLE",
    },
    {
        "code": "3000",
        "name": "Retained Earnings",
        "account_type": "EQUITY",
        "category": "EQUITY",
        "normal_balance": "CREDIT",
        "legacy_label": "EQUITY",
    },
    {
        "code": "4000",
        "name": "Sales Revenue",
        "account_type": "INCOME",
        "category": "OPERATING_REVENUE",
        "normal_balance": "CREDIT",
        "legacy_label": "REVENUE",
    },
    {
        "code": "5000",
        "name": "Procurement Expense",
        "account_type": "EXPENSE",
        "category": "COST_OF_GOODS_SOLD",
        "normal_balance": "DEBIT",
        "legacy_label": "EXPENSE",
    },
)


class FinanceService:
    """
    Finance application service.

    Extends the existing invoice and payment flows with:
    - tenant finance settings and numbering
    - chart of accounts
    - balanced journal entries
    - backward-compatible legacy ledger rows
    - AR/AP aging and financial statements
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._schema_checked = False

    # ------------------------------------------------------------------ #
    #  Finance Setup / Numbering
    # ------------------------------------------------------------------ #
    async def ensure_finance_setup(self, tenant_id: uuid.UUID) -> TenantFinanceSettingsModel:
        await self._ensure_finance_schema()
        settings = await self._get_or_create_settings(tenant_id)
        await self._ensure_default_chart_of_accounts(tenant_id)
        return settings

    async def _ensure_finance_schema(self) -> None:
        if self._schema_checked:
            return
        connection = await self.session.connection()

        def _create_tables(sync_connection) -> None:
            for table in (
                TenantFinanceSettingsModel.__table__,
                ChartOfAccountModel.__table__,
                JournalEntryModel.__table__,
                JournalLineModel.__table__,
            ):
                table.create(bind=sync_connection, checkfirst=True)

        await connection.run_sync(_create_tables)
        self._schema_checked = True

    async def _get_or_create_settings(self, tenant_id: uuid.UUID) -> TenantFinanceSettingsModel:
        settings = await self.session.scalar(
            select(TenantFinanceSettingsModel).where(TenantFinanceSettingsModel.tenant_id == tenant_id)
        )
        if settings is not None:
            return settings

        settings = TenantFinanceSettingsModel(
            tenant_id=tenant_id,
            invoice_prefix="INV",
            supplier_invoice_prefix="SINV",
            payment_prefix="PAY",
            supplier_payment_prefix="SPAY",
            invoice_template="standard",
            default_tax_rate=0,
            default_payment_terms_days=30,
            ar_account_code="1100",
            bank_account_code="1000",
            ap_account_code="2000",
            revenue_account_code="4000",
            expense_account_code="5000",
        )
        self.session.add(settings)
        await self.session.flush()
        return settings

    async def _ensure_default_chart_of_accounts(self, tenant_id: uuid.UUID) -> None:
        existing_rows = await self.session.execute(
            select(ChartOfAccountModel.code).where(ChartOfAccountModel.tenant_id == tenant_id)
        )
        existing_codes = {row[0] for row in existing_rows.all()}
        for account in DEFAULT_CHART_OF_ACCOUNTS:
            if account["code"] in existing_codes:
                continue
            self.session.add(
                ChartOfAccountModel(
                    tenant_id=tenant_id,
                    code=account["code"],
                    name=account["name"],
                    account_type=account["account_type"],
                    category=account["category"],
                    normal_balance=account["normal_balance"],
                    is_system=True,
                    is_active=True,
                )
            )
        await self.session.flush()

    async def _next_invoice_number(self, tenant_id: uuid.UUID) -> str:
        settings = await self.ensure_finance_setup(tenant_id)
        return await self._next_document_number(InvoiceModel, "invoice_number", tenant_id, settings.invoice_prefix)

    async def _next_supplier_invoice_number(self, tenant_id: uuid.UUID) -> str:
        settings = await self.ensure_finance_setup(tenant_id)
        return await self._next_document_number(
            SupplierInvoiceModel,
            "invoice_number",
            tenant_id,
            settings.supplier_invoice_prefix,
        )

    async def _next_payment_number(self, tenant_id: uuid.UUID) -> str:
        settings = await self.ensure_finance_setup(tenant_id)
        return await self._next_document_number(PaymentModel, "payment_number", tenant_id, settings.payment_prefix)

    async def _next_supplier_payment_number(self, tenant_id: uuid.UUID) -> str:
        settings = await self.ensure_finance_setup(tenant_id)
        return await self._next_document_number(
            SupplierPaymentModel,
            "payment_number",
            tenant_id,
            settings.supplier_payment_prefix,
        )

    async def _next_journal_number(self, tenant_id: uuid.UUID) -> str:
        return await self._next_document_number(JournalEntryModel, "entry_number", tenant_id, "JE")

    async def _next_document_number(self, model, field_name: str, tenant_id: uuid.UUID, prefix: str) -> str:
        field = getattr(model, field_name)
        latest = await self.session.scalar(
            select(field)
            .where(model.tenant_id == tenant_id, field.like(f"{prefix}-%"))
            .order_by(field.desc())
            .limit(1)
        )
        next_seq = 1
        if latest:
            try:
                next_seq = int(str(latest).split("-")[-1]) + 1
            except (ValueError, IndexError):
                next_seq = 1
        return f"{prefix}-{next_seq:06d}"

    async def get_settings(self, tenant_id: uuid.UUID) -> dict:
        settings = await self.ensure_finance_setup(tenant_id)
        return self._serialize_settings(settings)

    async def update_settings(self, tenant_id: uuid.UUID, payload: dict[str, Any]) -> dict:
        settings = await self.ensure_finance_setup(tenant_id)
        allowed_fields = {
            "invoice_prefix",
            "supplier_invoice_prefix",
            "payment_prefix",
            "supplier_payment_prefix",
            "invoice_template",
            "default_tax_rate",
            "default_payment_terms_days",
            "gst_number",
            "logo_url",
            "custom_template",
            "ar_account_code",
            "bank_account_code",
            "ap_account_code",
            "revenue_account_code",
            "expense_account_code",
        }
        for key, value in payload.items():
            if key in allowed_fields:
                setattr(settings, key, value)

        await self._ensure_default_chart_of_accounts(tenant_id)
        await self.session.commit()
        await self.session.refresh(settings)
        return self._serialize_settings(settings)

    def _serialize_settings(self, settings: TenantFinanceSettingsModel) -> dict:
        return {
            "tenant_id": str(settings.tenant_id),
            "invoice_prefix": settings.invoice_prefix,
            "supplier_invoice_prefix": settings.supplier_invoice_prefix,
            "payment_prefix": settings.payment_prefix,
            "supplier_payment_prefix": settings.supplier_payment_prefix,
            "invoice_template": settings.invoice_template,
            "default_tax_rate": _as_float(settings.default_tax_rate),
            "default_payment_terms_days": settings.default_payment_terms_days,
            "gst_number": settings.gst_number,
            "logo_url": settings.logo_url,
            "custom_template": settings.custom_template or {},
            "ar_account_code": settings.ar_account_code,
            "bank_account_code": settings.bank_account_code,
            "ap_account_code": settings.ap_account_code,
            "revenue_account_code": settings.revenue_account_code,
            "expense_account_code": settings.expense_account_code,
            "updated_at": settings.updated_at.isoformat(),
        }

    async def list_chart_of_accounts(self, tenant_id: uuid.UUID) -> list[dict]:
        await self.ensure_finance_setup(tenant_id)
        rows = (
            await self.session.execute(
                select(ChartOfAccountModel)
                .where(ChartOfAccountModel.tenant_id == tenant_id)
                .order_by(ChartOfAccountModel.code.asc())
            )
        ).scalars().all()
        return [
            {
                "id": str(row.id),
                "code": row.code,
                "name": row.name,
                "account_type": row.account_type,
                "category": row.category,
                "normal_balance": row.normal_balance,
                "is_system": row.is_system,
                "is_active": row.is_active,
            }
            for row in rows
        ]

    # ------------------------------------------------------------------ #
    #  Invoice CRUD
    # ------------------------------------------------------------------ #
    async def create_invoice_from_sales_order(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        created_by: uuid.UUID,
        notes: Optional[str] = None,
        terms: Optional[str] = None,
    ) -> InvoiceModel:
        settings = await self.ensure_finance_setup(tenant_id)
        invoice_number = await self._next_invoice_number(tenant_id)

        so = await self.session.scalar(
            select(SalesOrderModel).where(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted == False,
            )
        )
        if so is None:
            raise ValueError("Sales order not found")
        if so.status != "DELIVERED":
            raise ValueError(f"Invoice can only be created for DELIVERED orders (current: {so.status})")

        existing_invoice = await self.session.scalar(
            select(InvoiceModel).where(
                InvoiceModel.sales_order_id == sales_order_id,
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.is_deleted == False,
            )
        )
        if existing_invoice:
            if so.status == "DELIVERED":
                so.status = "INVOICED"
                await self.session.commit()
            return existing_invoice

        client = await self.session.scalar(select(ClientModel).where(ClientModel.id == so.client_id))
        if client is None:
            raise ValueError("Client not found for sales order")

        today = date.today()
        due_date = today + timedelta(days=client.payment_terms_days or settings.default_payment_terms_days or 30)

        invoice = InvoiceModel(
            tenant_id=tenant_id,
            invoice_number=invoice_number,
            sales_order_id=sales_order_id,
            client_id=so.client_id,
            client_name=client.name,
            client_address=client.address,
            client_gst_number=client.gst_number,
            status="DRAFT",
            invoice_date=today,
            due_date=due_date,
            subtotal=_as_float(so.subtotal),
            discount_amount=_as_float(so.discount_amount),
            tax_amount=_as_float(so.tax_amount),
            grand_total=_as_float(so.grand_total),
            paid_amount=0.0,
            notes=notes,
            terms=terms or f"Net {client.payment_terms_days or settings.default_payment_terms_days or 30}",
            created_by=created_by,
        )
        self.session.add(invoice)
        await self.session.flush()

        so_lines = (
            await self.session.execute(
                select(SalesOrderLineModel).where(SalesOrderLineModel.sales_order_id == sales_order_id)
            )
        ).scalars().all()
        for sol in so_lines:
            self.session.add(
                InvoiceLineModel(
                    tenant_id=tenant_id,
                    invoice_id=invoice.id,
                    product_id=sol.product_id,
                    product_type=sol.product_type,
                    description=f"Product {sol.product_id}",
                    quantity=int(_as_float(sol.quantity)),
                    unit_price=_as_float(sol.unit_price),
                    discount_amount=0.0,
                    tax_rate=_as_float(sol.tax_rate),
                    tax_amount=_as_float(sol.tax_amount),
                    total=_as_float(sol.line_total),
                )
            )

        await self._post_customer_invoice_entries(
            tenant_id=tenant_id,
            invoice=invoice,
            memo=f"Invoice {invoice_number} created for SO {so.order_number}",
            created_by=created_by,
        )

        if so.status == "DELIVERED":
            so.status = "INVOICED"

        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice

    async def create_invoice_manual(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        invoice_date: date,
        due_date: date,
        lines_data: List[dict],
        created_by: uuid.UUID,
        notes: Optional[str] = None,
        terms: Optional[str] = None,
    ) -> InvoiceModel:
        if not lines_data:
            raise ValueError("Invoice requires at least one line")

        await self.ensure_finance_setup(tenant_id)
        invoice_number = await self._next_invoice_number(tenant_id)

        client = await self.session.scalar(
            select(ClientModel).where(ClientModel.id == client_id, ClientModel.tenant_id == tenant_id)
        )
        if client is None:
            raise ValueError("Client not found")

        subtotal = sum(
            _as_decimal(d["quantity"]) * _as_decimal(d["unit_price"]) - _as_decimal(d.get("discount_amount", 0))
            for d in lines_data
        )
        tax_amount = sum(_as_decimal(d.get("tax_amount", 0)) for d in lines_data)
        grand_total = subtotal + tax_amount
        if grand_total <= 0:
            raise ValueError("Invoice total must be greater than zero")

        invoice = InvoiceModel(
            tenant_id=tenant_id,
            invoice_number=invoice_number,
            client_id=client_id,
            client_name=client.name,
            client_address=client.address,
            client_gst_number=client.gst_number,
            status="DRAFT",
            invoice_date=invoice_date,
            due_date=due_date,
            subtotal=_as_float(subtotal),
            discount_amount=_as_float(sum(_as_decimal(d.get("discount_amount", 0)) for d in lines_data)),
            tax_amount=_as_float(tax_amount),
            grand_total=_as_float(grand_total),
            paid_amount=0.0,
            notes=notes,
            terms=terms,
            created_by=created_by,
        )
        self.session.add(invoice)
        await self.session.flush()

        for ld in lines_data:
            product_id = ld["product_id"]
            if not isinstance(product_id, uuid.UUID):
                product_id = uuid.UUID(str(product_id))
            self.session.add(
                InvoiceLineModel(
                    tenant_id=tenant_id,
                    invoice_id=invoice.id,
                    product_id=product_id,
                    product_type=ld.get("product_type", "finished"),
                    description=ld.get("description"),
                    quantity=int(ld["quantity"]),
                    unit_price=_as_float(ld["unit_price"]),
                    discount_amount=_as_float(ld.get("discount_amount", 0)),
                    tax_rate=_as_float(ld.get("tax_rate", 0)),
                    tax_amount=_as_float(ld.get("tax_amount", 0)),
                    total=_as_float(ld["total"]),
                )
            )

        await self._post_customer_invoice_entries(
            tenant_id=tenant_id,
            invoice=invoice,
            memo=f"Manual invoice {invoice_number} created",
            created_by=created_by,
        )

        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice

    async def send_invoice(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> InvoiceModel:
        invoice = await self._get_invoice(tenant_id, invoice_id)
        if invoice.status != "DRAFT":
            raise ValueError("Only DRAFT invoices can be sent")
        invoice.status = "SENT"
        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice

    async def void_invoice(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID, created_by: Optional[uuid.UUID] = None) -> InvoiceModel:
        invoice = await self._get_invoice(tenant_id, invoice_id)
        if invoice.status == "PAID":
            raise ValueError("Cannot void a fully paid invoice")
        if invoice.status == "VOID":
            return invoice

        original_entry = await self.session.scalar(
            select(JournalEntryModel).where(
                JournalEntryModel.tenant_id == tenant_id,
                JournalEntryModel.reference_type == "invoice",
                JournalEntryModel.reference_id == invoice.id,
                JournalEntryModel.status == "POSTED",
            )
        )
        if original_entry is not None:
            await self._reverse_journal_entry(
                tenant_id=tenant_id,
                original_entry=original_entry,
                reference_type="invoice_void",
                reference_id=invoice.id,
                memo=f"Void invoice {invoice.invoice_number}",
                created_by=created_by,
            )

        invoice.status = "VOID"
        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice

    async def list_invoices(
        self,
        tenant_id: uuid.UUID,
        status: Optional[str] = None,
        client_id: Optional[uuid.UUID] = None,
        overdue_only: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        q = select(InvoiceModel).where(
            InvoiceModel.tenant_id == tenant_id,
            InvoiceModel.is_deleted == False,
        )
        if status:
            q = q.where(InvoiceModel.status == status)
        if client_id:
            q = q.where(InvoiceModel.client_id == client_id)
        if overdue_only:
            q = q.where(InvoiceModel.due_date < date.today(), InvoiceModel.status.in_(["SENT", "PARTIAL", "OVERDUE"]))

        total = await self.session.scalar(select(func.count()).select_from(q.subquery()))
        result = await self.session.execute(
            q.order_by(InvoiceModel.invoice_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        invoices = result.scalars().all()
        return {
            "items": invoices,
            "total": int(total or 0),
            "page": page,
            "page_size": page_size,
            "pages": ((int(total or 0) + page_size - 1) // page_size) if total else 0,
        }

    async def get_invoice(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> InvoiceModel:
        return await self._get_invoice(tenant_id, invoice_id)

    async def _get_invoice(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> InvoiceModel:
        invoice = await self.session.scalar(
            select(InvoiceModel).where(
                InvoiceModel.id == invoice_id,
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.is_deleted == False,
            )
        )
        if invoice is None:
            raise ValueError("Invoice not found")
        return invoice

    # ------------------------------------------------------------------ #
    #  Payments (AR)
    # ------------------------------------------------------------------ #
    async def record_payment(
        self,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        amount: float,
        payment_date: date,
        payment_method: str,
        created_by: uuid.UUID,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PaymentModel:
        if amount <= 0:
            raise ValueError("Payment amount must be positive")

        await self.ensure_finance_setup(tenant_id)
        payment_number = await self._next_payment_number(tenant_id)
        invoice = await self._get_invoice(tenant_id, invoice_id)
        balance = _as_float(invoice.grand_total) - _as_float(invoice.paid_amount)
        if amount > balance + 0.001:
            raise ValueError(f"Payment amount ({amount}) exceeds balance due ({balance:.2f})")

        payment = PaymentModel(
            tenant_id=tenant_id,
            payment_number=payment_number,
            invoice_id=invoice_id,
            client_id=invoice.client_id,
            amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
            created_by=created_by,
        )
        self.session.add(payment)

        new_paid = _as_float(invoice.paid_amount) + amount
        invoice.paid_amount = new_paid
        new_balance = _as_float(invoice.grand_total) - new_paid
        if new_balance <= 0.001:
            invoice.status = "PAID"
        elif new_paid > 0:
            invoice.status = "PARTIAL"

        await self.session.flush()

        if getattr(invoice, "sales_order_id", None):
            try:
                from backend.app.application.manufacturing.services.workflow_orchestration_service import (
                    WorkflowOrchestrationService,
                )

                workflow_service = WorkflowOrchestrationService(self.session)
                await workflow_service.on_payment_received(
                    tenant_id=tenant_id,
                    sales_order_id=invoice.sales_order_id,
                    payment_amount=Decimal(str(amount)),
                )
            except Exception as exc:
                logger.warning(
                    "Failed to trigger sales-order workflow after payment recording",
                    extra={
                        "tenant_id": str(tenant_id),
                        "invoice_id": str(invoice_id),
                        "sales_order_id": str(invoice.sales_order_id),
                        "error": str(exc),
                    },
                )

        await self._post_customer_payment_entries(
            tenant_id=tenant_id,
            payment=payment,
            invoice=invoice,
            memo=f"Payment {payment_number} received for invoice {invoice.invoice_number}",
            created_by=created_by,
        )

        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def list_payments(
        self,
        tenant_id: uuid.UUID,
        invoice_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        q = select(PaymentModel).where(PaymentModel.tenant_id == tenant_id)
        if invoice_id:
            q = q.where(PaymentModel.invoice_id == invoice_id)

        total = await self.session.scalar(select(func.count()).select_from(q.subquery()))
        result = await self.session.execute(
            q.order_by(PaymentModel.payment_date.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return {
            "items": result.scalars().all(),
            "total": int(total or 0),
            "page": page,
            "pages": ((int(total or 0) + page_size - 1) // page_size) if total else 0,
        }

    # ------------------------------------------------------------------ #
    #  Supplier Invoices / Payments (AP)
    # ------------------------------------------------------------------ #
    async def create_supplier_invoice(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        purchase_order_id: Optional[uuid.UUID],
        supplier_invoice_ref: Optional[str],
        invoice_date: date,
        due_date: date,
        subtotal: float,
        tax_amount: float,
        grand_total: float,
        created_by: uuid.UUID,
        notes: Optional[str] = None,
    ) -> SupplierInvoiceModel:
        if grand_total <= 0:
            raise ValueError("Supplier invoice total must be greater than zero")

        await self.ensure_finance_setup(tenant_id)
        invoice_number = await self._next_supplier_invoice_number(tenant_id)

        supplier = await self.session.scalar(
            select(SupplierModel).where(SupplierModel.id == supplier_id, SupplierModel.tenant_id == tenant_id)
        )
        if supplier is None:
            raise ValueError("Supplier not found")

        if purchase_order_id is not None:
            po = await self.session.scalar(
                select(PurchaseOrderModel).where(
                    PurchaseOrderModel.id == purchase_order_id,
                    PurchaseOrderModel.tenant_id == tenant_id,
                    PurchaseOrderModel.is_deleted == False,
                )
            )
            if po is None:
                raise ValueError("Purchase order not found")
            if po.supplier_id != supplier_id:
                raise ValueError("Purchase order does not belong to the selected supplier")

        if supplier_invoice_ref:
            duplicate = await self.session.scalar(
                select(SupplierInvoiceModel).where(
                    SupplierInvoiceModel.tenant_id == tenant_id,
                    SupplierInvoiceModel.supplier_id == supplier_id,
                    SupplierInvoiceModel.supplier_invoice_ref == supplier_invoice_ref,
                    SupplierInvoiceModel.is_deleted == False,
                )
            )
            if duplicate is not None:
                return duplicate

        supplier_invoice = SupplierInvoiceModel(
            tenant_id=tenant_id,
            invoice_number=invoice_number,
            supplier_invoice_ref=supplier_invoice_ref,
            purchase_order_id=purchase_order_id,
            supplier_id=supplier_id,
            supplier_name=supplier.name,
            status="PENDING",
            invoice_date=invoice_date,
            due_date=due_date,
            subtotal=subtotal,
            tax_amount=tax_amount,
            grand_total=grand_total,
            paid_amount=0.0,
            notes=notes,
            created_by=created_by,
        )
        self.session.add(supplier_invoice)
        await self.session.flush()

        await self._post_supplier_invoice_entries(
            tenant_id=tenant_id,
            supplier_invoice=supplier_invoice,
            memo=f"Supplier invoice {invoice_number} from {supplier.name}",
            created_by=created_by,
        )

        await self.session.commit()
        await self.session.refresh(supplier_invoice)
        return supplier_invoice

    async def record_supplier_payment(
        self,
        tenant_id: uuid.UUID,
        supplier_invoice_id: uuid.UUID,
        amount: float,
        payment_date: date,
        payment_method: str,
        created_by: uuid.UUID,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> SupplierPaymentModel:
        if amount <= 0:
            raise ValueError("Payment amount must be positive")

        await self.ensure_finance_setup(tenant_id)
        payment_number = await self._next_supplier_payment_number(tenant_id)
        supplier_invoice = await self.session.scalar(
            select(SupplierInvoiceModel).where(
                SupplierInvoiceModel.id == supplier_invoice_id,
                SupplierInvoiceModel.tenant_id == tenant_id,
                SupplierInvoiceModel.is_deleted == False,
            )
        )
        if supplier_invoice is None:
            raise ValueError("Supplier invoice not found")

        balance = _as_float(supplier_invoice.grand_total) - _as_float(supplier_invoice.paid_amount)
        if amount > balance + 0.001:
            raise ValueError(f"Payment ({amount}) exceeds balance ({balance:.2f})")

        payment = SupplierPaymentModel(
            tenant_id=tenant_id,
            payment_number=payment_number,
            supplier_invoice_id=supplier_invoice_id,
            supplier_id=supplier_invoice.supplier_id,
            amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
            created_by=created_by,
        )
        self.session.add(payment)

        new_paid = _as_float(supplier_invoice.paid_amount) + amount
        supplier_invoice.paid_amount = new_paid
        if _as_float(supplier_invoice.grand_total) - new_paid <= 0.001:
            supplier_invoice.status = "PAID"
        elif new_paid > 0:
            supplier_invoice.status = "PARTIAL"

        await self.session.flush()
        await self._post_supplier_payment_entries(
            tenant_id=tenant_id,
            payment=payment,
            supplier_invoice=supplier_invoice,
            memo=f"Supplier payment {payment_number} for invoice {supplier_invoice.invoice_number}",
            created_by=created_by,
        )

        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def list_supplier_invoices(
        self,
        tenant_id: uuid.UUID,
        status: Optional[str] = None,
        supplier_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        q = select(SupplierInvoiceModel).where(
            SupplierInvoiceModel.tenant_id == tenant_id,
            SupplierInvoiceModel.is_deleted == False,
        )
        if status:
            q = q.where(SupplierInvoiceModel.status == status)
        if supplier_id:
            q = q.where(SupplierInvoiceModel.supplier_id == supplier_id)

        total = await self.session.scalar(select(func.count()).select_from(q.subquery()))
        result = await self.session.execute(
            q.order_by(SupplierInvoiceModel.invoice_date.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return {
            "items": result.scalars().all(),
            "total": int(total or 0),
            "page": page,
            "pages": ((int(total or 0) + page_size - 1) // page_size) if total else 0,
        }

    async def list_supplier_payments(
        self,
        tenant_id: uuid.UUID,
        supplier_invoice_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        q = select(SupplierPaymentModel).where(SupplierPaymentModel.tenant_id == tenant_id)
        if supplier_invoice_id:
            q = q.where(SupplierPaymentModel.supplier_invoice_id == supplier_invoice_id)

        total = await self.session.scalar(select(func.count()).select_from(q.subquery()))
        result = await self.session.execute(
            q.order_by(SupplierPaymentModel.payment_date.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return {
            "items": result.scalars().all(),
            "total": int(total or 0),
            "page": page,
            "pages": ((int(total or 0) + page_size - 1) // page_size) if total else 0,
        }

    # ------------------------------------------------------------------ #
    #  Dashboard / Aging / Financial Statements
    # ------------------------------------------------------------------ #
    async def get_ar_summary(self, tenant_id: uuid.UUID) -> dict:
        result = await self.session.execute(
            select(
                func.sum(InvoiceModel.grand_total).label("total_billed"),
                func.sum(InvoiceModel.paid_amount).label("total_collected"),
                func.sum(InvoiceModel.grand_total - InvoiceModel.paid_amount).label("total_outstanding"),
                func.count(InvoiceModel.id).filter(InvoiceModel.status.in_(["SENT", "PARTIAL", "OVERDUE"])).label("open_count"),
            ).where(InvoiceModel.tenant_id == tenant_id, InvoiceModel.is_deleted == False)
        )
        row = result.one()
        return {
            "total_billed": _as_float(row.total_billed),
            "total_collected": _as_float(row.total_collected),
            "total_outstanding": _as_float(row.total_outstanding),
            "open_count": row.open_count or 0,
        }

    async def get_ap_summary(self, tenant_id: uuid.UUID) -> dict:
        result = await self.session.execute(
            select(
                func.sum(SupplierInvoiceModel.grand_total).label("total_payable"),
                func.sum(SupplierInvoiceModel.paid_amount).label("total_paid"),
                func.sum(SupplierInvoiceModel.grand_total - SupplierInvoiceModel.paid_amount).label("outstanding"),
                func.count(SupplierInvoiceModel.id).filter(SupplierInvoiceModel.status.in_(["PENDING", "PARTIAL", "OVERDUE"])).label("open_count"),
            ).where(SupplierInvoiceModel.tenant_id == tenant_id, SupplierInvoiceModel.is_deleted == False)
        )
        row = result.one()
        return {
            "total_payable": _as_float(row.total_payable),
            "total_paid": _as_float(row.total_paid),
            "outstanding": _as_float(row.outstanding),
            "open_count": row.open_count or 0,
        }

    async def get_cash_flow(self, tenant_id: uuid.UUID, months: int = 6) -> List[dict]:
        settings = await self.ensure_finance_setup(tenant_id)
        cutoff = date.today() - timedelta(days=months * 31)
        result = await self.session.execute(
            select(
                JournalEntryModel.entry_date,
                JournalLineModel.debit,
                JournalLineModel.credit,
            )
            .join(JournalLineModel, JournalLineModel.journal_entry_id == JournalEntryModel.id)
            .join(ChartOfAccountModel, ChartOfAccountModel.id == JournalLineModel.account_id)
            .where(
                JournalEntryModel.tenant_id == tenant_id,
                JournalEntryModel.entry_date >= cutoff,
                ChartOfAccountModel.code == settings.bank_account_code,
            )
            .order_by(JournalEntryModel.entry_date.asc())
        )
        by_month: dict[str, dict[str, float]] = {}
        for row in result:
            month = row.entry_date.strftime("%Y-%m")
            bucket = by_month.setdefault(month, {"month": month, "cash_in": 0.0, "cash_out": 0.0})
            bucket["cash_in"] += _as_float(row.debit)
            bucket["cash_out"] += _as_float(row.credit)
        return list(by_month.values())

    async def get_revenue_by_month(self, tenant_id: uuid.UUID, months: int = 6) -> List[dict]:
        cutoff = date.today() - timedelta(days=months * 31)
        result = await self.session.execute(
            select(
                InvoiceModel.invoice_date,
                InvoiceModel.grand_total,
                InvoiceModel.paid_amount,
            ).where(
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.is_deleted == False,
                InvoiceModel.invoice_date >= cutoff,
            ).order_by(InvoiceModel.invoice_date.asc())
        )
        by_month: dict[str, dict[str, float | int | str]] = {}
        for row in result:
            month = row.invoice_date.strftime("%Y-%m")
            bucket = by_month.setdefault(
                month,
                {"month": month, "invoice_count": 0, "revenue": 0.0, "collected": 0.0},
            )
            bucket["invoice_count"] = int(bucket["invoice_count"]) + 1
            bucket["revenue"] = float(bucket["revenue"]) + _as_float(row.grand_total)
            bucket["collected"] = float(bucket["collected"]) + _as_float(row.paid_amount)
        return list(by_month.values())

    async def get_ar_aging(self, tenant_id: uuid.UUID) -> list[dict]:
        today = date.today()
        d30 = today - timedelta(days=30)
        d60 = today - timedelta(days=60)
        d90 = today - timedelta(days=90)
        result = await self.session.execute(
            select(
                InvoiceModel.client_id,
                InvoiceModel.client_name,
                InvoiceModel.due_date,
                InvoiceModel.grand_total,
                InvoiceModel.paid_amount,
            ).where(
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.is_deleted == False,
                InvoiceModel.status.notin_(["PAID", "CANCELLED", "VOID"]),
            )
        )
        buckets: dict[tuple[str, str], dict[str, Any]] = {}
        for client_id, client_name, due_date, grand_total, paid_amount in result.all():
            outstanding = _as_float(grand_total) - _as_float(paid_amount)
            if outstanding <= 0.001:
                continue
            key = (_json_safe_uuid(client_id) or "", client_name or "Unknown client")
            bucket = buckets.setdefault(
                key,
                {
                    "client_id": key[0],
                    "client_name": key[1],
                    "current_amount": 0.0,
                    "overdue_1_30": 0.0,
                    "overdue_31_60": 0.0,
                    "overdue_61_90": 0.0,
                    "overdue_90_plus": 0.0,
                    "total_outstanding": 0.0,
                },
            )
            if due_date >= today:
                bucket["current_amount"] += outstanding
            elif due_date >= d30:
                bucket["overdue_1_30"] += outstanding
            elif due_date >= d60:
                bucket["overdue_31_60"] += outstanding
            elif due_date >= d90:
                bucket["overdue_61_90"] += outstanding
            else:
                bucket["overdue_90_plus"] += outstanding
            bucket["total_outstanding"] += outstanding
        return sorted(buckets.values(), key=lambda item: item["total_outstanding"], reverse=True)

    async def get_ap_aging(self, tenant_id: uuid.UUID) -> list[dict]:
        today = date.today()
        d30 = today - timedelta(days=30)
        d60 = today - timedelta(days=60)
        d90 = today - timedelta(days=90)
        result = await self.session.execute(
            select(
                SupplierInvoiceModel.supplier_id,
                SupplierInvoiceModel.supplier_name,
                SupplierInvoiceModel.due_date,
                SupplierInvoiceModel.grand_total,
                SupplierInvoiceModel.paid_amount,
            ).where(
                SupplierInvoiceModel.tenant_id == tenant_id,
                SupplierInvoiceModel.is_deleted == False,
                SupplierInvoiceModel.status.notin_(["PAID", "CANCELLED", "VOID"]),
            )
        )
        buckets: dict[tuple[str, str], dict[str, Any]] = {}
        for supplier_id, supplier_name, due_date, grand_total, paid_amount in result.all():
            outstanding = _as_float(grand_total) - _as_float(paid_amount)
            if outstanding <= 0.001:
                continue
            key = (_json_safe_uuid(supplier_id) or "", supplier_name or "Unknown supplier")
            bucket = buckets.setdefault(
                key,
                {
                    "supplier_id": key[0],
                    "supplier_name": key[1],
                    "current_amount": 0.0,
                    "overdue_1_30": 0.0,
                    "overdue_31_60": 0.0,
                    "overdue_61_90": 0.0,
                    "overdue_90_plus": 0.0,
                    "total_outstanding": 0.0,
                },
            )
            if due_date >= today:
                bucket["current_amount"] += outstanding
            elif due_date >= d30:
                bucket["overdue_1_30"] += outstanding
            elif due_date >= d60:
                bucket["overdue_31_60"] += outstanding
            elif due_date >= d90:
                bucket["overdue_61_90"] += outstanding
            else:
                bucket["overdue_90_plus"] += outstanding
            bucket["total_outstanding"] += outstanding
        return sorted(buckets.values(), key=lambda item: item["total_outstanding"], reverse=True)

    async def get_trial_balance(self, tenant_id: uuid.UUID, as_of: Optional[date] = None) -> dict:
        await self.ensure_finance_setup(tenant_id)
        filters = [JournalEntryModel.tenant_id == tenant_id, JournalEntryModel.status == "POSTED"]
        if as_of:
            filters.append(JournalEntryModel.entry_date <= as_of)

        result = await self.session.execute(
            select(
                ChartOfAccountModel.code,
                ChartOfAccountModel.name,
                ChartOfAccountModel.account_type,
                func.sum(JournalLineModel.debit).label("debit"),
                func.sum(JournalLineModel.credit).label("credit"),
            )
            .join(JournalLineModel, JournalLineModel.account_id == ChartOfAccountModel.id)
            .join(JournalEntryModel, JournalEntryModel.id == JournalLineModel.journal_entry_id)
            .where(*filters)
            .group_by(ChartOfAccountModel.code, ChartOfAccountModel.name, ChartOfAccountModel.account_type)
            .order_by(ChartOfAccountModel.code.asc())
        )
        items = []
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for row in result:
            debit = _as_decimal(row.debit)
            credit = _as_decimal(row.credit)
            total_debit += debit
            total_credit += credit
            items.append(
                {
                    "code": row.code,
                    "name": row.name,
                    "account_type": row.account_type,
                    "debit": _as_float(debit),
                    "credit": _as_float(credit),
                    "balance": _as_float(debit - credit),
                }
            )
        return {
            "as_of": str(as_of or date.today()),
            "items": items,
            "totals": {
                "debit": _as_float(total_debit),
                "credit": _as_float(total_credit),
                "is_balanced": total_debit == total_credit,
            },
        }

    async def get_profit_and_loss(self, tenant_id: uuid.UUID, from_date: Optional[date] = None, to_date: Optional[date] = None) -> dict:
        await self.ensure_finance_setup(tenant_id)
        filters = [JournalEntryModel.tenant_id == tenant_id, JournalEntryModel.status == "POSTED"]
        if from_date:
            filters.append(JournalEntryModel.entry_date >= from_date)
        if to_date:
            filters.append(JournalEntryModel.entry_date <= to_date)

        result = await self.session.execute(
            select(
                ChartOfAccountModel.code,
                ChartOfAccountModel.name,
                ChartOfAccountModel.account_type,
                func.sum(JournalLineModel.debit).label("debit"),
                func.sum(JournalLineModel.credit).label("credit"),
            )
            .join(JournalLineModel, JournalLineModel.account_id == ChartOfAccountModel.id)
            .join(JournalEntryModel, JournalEntryModel.id == JournalLineModel.journal_entry_id)
            .where(*filters, ChartOfAccountModel.account_type.in_(["INCOME", "EXPENSE"]))
            .group_by(ChartOfAccountModel.code, ChartOfAccountModel.name, ChartOfAccountModel.account_type)
            .order_by(ChartOfAccountModel.code.asc())
        )
        income_items: list[dict] = []
        expense_items: list[dict] = []
        total_income = Decimal("0")
        total_expense = Decimal("0")
        for row in result:
            debit = _as_decimal(row.debit)
            credit = _as_decimal(row.credit)
            if row.account_type == "INCOME":
                amount = credit - debit
                total_income += amount
                income_items.append({"code": row.code, "name": row.name, "amount": _as_float(amount)})
            else:
                amount = debit - credit
                total_expense += amount
                expense_items.append({"code": row.code, "name": row.name, "amount": _as_float(amount)})
        return {
            "period": {"from": str(from_date or ""), "to": str(to_date or date.today())},
            "income": income_items,
            "expenses": expense_items,
            "totals": {
                "income": _as_float(total_income),
                "expense": _as_float(total_expense),
                "net_profit": _as_float(total_income - total_expense),
            },
        }

    async def get_balance_sheet(self, tenant_id: uuid.UUID, as_of: Optional[date] = None) -> dict:
        await self.ensure_finance_setup(tenant_id)
        filters = [JournalEntryModel.tenant_id == tenant_id, JournalEntryModel.status == "POSTED"]
        if as_of:
            filters.append(JournalEntryModel.entry_date <= as_of)

        result = await self.session.execute(
            select(
                ChartOfAccountModel.code,
                ChartOfAccountModel.name,
                ChartOfAccountModel.account_type,
                func.sum(JournalLineModel.debit).label("debit"),
                func.sum(JournalLineModel.credit).label("credit"),
            )
            .join(JournalLineModel, JournalLineModel.account_id == ChartOfAccountModel.id)
            .join(JournalEntryModel, JournalEntryModel.id == JournalLineModel.journal_entry_id)
            .where(*filters, ChartOfAccountModel.account_type.in_(["ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE"]))
            .group_by(ChartOfAccountModel.code, ChartOfAccountModel.name, ChartOfAccountModel.account_type)
            .order_by(ChartOfAccountModel.code.asc())
        )

        assets: list[dict] = []
        liabilities: list[dict] = []
        equity: list[dict] = []
        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        total_equity = Decimal("0")
        current_earnings = Decimal("0")

        for row in result:
            debit = _as_decimal(row.debit)
            credit = _as_decimal(row.credit)
            if row.account_type == "ASSET":
                amount = debit - credit
                total_assets += amount
                assets.append({"code": row.code, "name": row.name, "amount": _as_float(amount)})
            elif row.account_type == "LIABILITY":
                amount = credit - debit
                total_liabilities += amount
                liabilities.append({"code": row.code, "name": row.name, "amount": _as_float(amount)})
            elif row.account_type == "EQUITY":
                amount = credit - debit
                total_equity += amount
                equity.append({"code": row.code, "name": row.name, "amount": _as_float(amount)})
            elif row.account_type == "INCOME":
                current_earnings += credit - debit
            elif row.account_type == "EXPENSE":
                current_earnings -= debit - credit

        if current_earnings != 0:
            total_equity += current_earnings
            equity.append({"code": "CURRENT", "name": "Current Earnings", "amount": _as_float(current_earnings)})

        return {
            "as_of": str(as_of or date.today()),
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "totals": {
                "assets": _as_float(total_assets),
                "liabilities": _as_float(total_liabilities),
                "equity": _as_float(total_equity),
                "liabilities_and_equity": _as_float(total_liabilities + total_equity),
                "is_balanced": abs(_as_float(total_assets - (total_liabilities + total_equity))) < 0.01,
            },
        }

    async def get_cash_flow_statement(self, tenant_id: uuid.UUID, months: int = 6) -> dict:
        rows = await self.get_cash_flow(tenant_id, months=months)
        total_in = sum(row["cash_in"] for row in rows)
        total_out = sum(row["cash_out"] for row in rows)
        return {
            "months": months,
            "items": rows,
            "totals": {
                "cash_in": total_in,
                "cash_out": total_out,
                "net_cash_flow": total_in - total_out,
            },
        }

    async def mark_overdue_invoices(self, tenant_id: Optional[uuid.UUID] = None) -> int:
        from sqlalchemy import update

        q = (
            update(InvoiceModel)
            .where(
                InvoiceModel.due_date < date.today(),
                InvoiceModel.status.in_(["SENT", "PARTIAL"]),
                InvoiceModel.is_deleted == False,
            )
            .values(status="OVERDUE")
        )
        if tenant_id:
            q = q.where(InvoiceModel.tenant_id == tenant_id)
        result = await self.session.execute(q)
        await self.session.commit()
        return result.rowcount

    # ------------------------------------------------------------------ #
    #  Journal / Legacy Ledger
    # ------------------------------------------------------------------ #
    async def _get_account_by_code(self, tenant_id: uuid.UUID, code: str) -> ChartOfAccountModel:
        await self.ensure_finance_setup(tenant_id)
        account = await self.session.scalar(
            select(ChartOfAccountModel).where(
                ChartOfAccountModel.tenant_id == tenant_id,
                ChartOfAccountModel.code == code,
                ChartOfAccountModel.is_active == True,
            )
        )
        if account is None:
            raise ValueError(f"Account code '{code}' not found")
        return account

    def _legacy_label_for_account(self, code: str) -> str:
        for account in DEFAULT_CHART_OF_ACCOUNTS:
            if account["code"] == code:
                return str(account["legacy_label"])
        return code

    async def _post_journal_entry(
        self,
        tenant_id: uuid.UUID,
        *,
        reference_type: str,
        reference_id: uuid.UUID,
        entry_date: date,
        memo: str,
        lines: Iterable[dict[str, Any]],
        created_by: Optional[uuid.UUID] = None,
        meta: Optional[dict[str, Any]] = None,
        reverses_entry_id: Optional[uuid.UUID] = None,
    ) -> JournalEntryModel:
        journal_lines = list(lines)
        total_debit = sum(_as_decimal(line.get("debit", 0)) for line in journal_lines)
        total_credit = sum(_as_decimal(line.get("credit", 0)) for line in journal_lines)
        if total_debit != total_credit:
            raise ValueError("Journal entry must balance")

        entry_number = await self._next_journal_number(tenant_id)
        entry = JournalEntryModel(
            tenant_id=tenant_id,
            entry_number=entry_number,
            entry_date=entry_date,
            reference_type=reference_type,
            reference_id=reference_id,
            memo=memo,
            status="POSTED",
            reverses_entry_id=reverses_entry_id,
            meta=meta or {},
            created_by=created_by,
        )
        self.session.add(entry)
        await self.session.flush()

        for line in journal_lines:
            account = await self._get_account_by_code(tenant_id, str(line["account_code"]))
            description = line.get("description") or memo
            debit = _as_float(line.get("debit", 0))
            credit = _as_float(line.get("credit", 0))
            self.session.add(
                JournalLineModel(
                    journal_entry_id=entry.id,
                    account_id=account.id,
                    description=description,
                    debit=debit,
                    credit=credit,
                )
            )
            await self._create_legacy_ledger_entry(
                tenant_id=tenant_id,
                reference_type=reference_type,
                reference_id=reference_id,
                account_type=self._legacy_label_for_account(account.code),
                debit=debit,
                credit=credit,
                description=description,
                created_by=created_by,
                meta={
                    "account_code": account.code,
                    "account_name": account.name,
                    "journal_entry_id": str(entry.id),
                },
            )
        return entry

    async def _reverse_journal_entry(
        self,
        tenant_id: uuid.UUID,
        *,
        original_entry: JournalEntryModel,
        reference_type: str,
        reference_id: uuid.UUID,
        memo: str,
        created_by: Optional[uuid.UUID] = None,
    ) -> JournalEntryModel:
        reversal_lines = []
        for line in original_entry.lines:
            account = line.account
            reversal_lines.append(
                {
                    "account_code": account.code,
                    "debit": _as_float(line.credit),
                    "credit": _as_float(line.debit),
                    "description": f"Reversal of {original_entry.entry_number}",
                }
            )
        reversal = await self._post_journal_entry(
            tenant_id=tenant_id,
            reference_type=reference_type,
            reference_id=reference_id,
            entry_date=date.today(),
            memo=memo,
            lines=reversal_lines,
            created_by=created_by,
            meta={"reversed_entry_id": str(original_entry.id)},
            reverses_entry_id=original_entry.id,
        )
        original_entry.status = "REVERSED"
        return reversal

    async def _post_customer_invoice_entries(
        self,
        tenant_id: uuid.UUID,
        *,
        invoice: InvoiceModel,
        memo: str,
        created_by: Optional[uuid.UUID],
    ) -> JournalEntryModel:
        settings = await self.ensure_finance_setup(tenant_id)
        return await self._post_journal_entry(
            tenant_id=tenant_id,
            reference_type="invoice",
            reference_id=invoice.id,
            entry_date=invoice.invoice_date,
            memo=memo,
            created_by=created_by,
            lines=[
                {
                    "account_code": settings.ar_account_code,
                    "debit": _as_float(invoice.grand_total),
                    "credit": 0.0,
                    "description": f"Accounts receivable for {invoice.invoice_number}",
                },
                {
                    "account_code": settings.revenue_account_code,
                    "debit": 0.0,
                    "credit": _as_float(invoice.grand_total),
                    "description": f"Revenue for {invoice.invoice_number}",
                },
            ],
            meta={"invoice_number": invoice.invoice_number},
        )

    async def _post_customer_payment_entries(
        self,
        tenant_id: uuid.UUID,
        *,
        payment: PaymentModel,
        invoice: InvoiceModel,
        memo: str,
        created_by: Optional[uuid.UUID],
    ) -> JournalEntryModel:
        settings = await self.ensure_finance_setup(tenant_id)
        return await self._post_journal_entry(
            tenant_id=tenant_id,
            reference_type="payment",
            reference_id=payment.id,
            entry_date=payment.payment_date,
            memo=memo,
            created_by=created_by,
            lines=[
                {
                    "account_code": settings.bank_account_code,
                    "debit": _as_float(payment.amount),
                    "credit": 0.0,
                    "description": f"Cash received for {invoice.invoice_number}",
                },
                {
                    "account_code": settings.ar_account_code,
                    "debit": 0.0,
                    "credit": _as_float(payment.amount),
                    "description": f"Receivable cleared for {invoice.invoice_number}",
                },
            ],
            meta={"payment_number": payment.payment_number, "invoice_number": invoice.invoice_number},
        )

    async def _post_supplier_invoice_entries(
        self,
        tenant_id: uuid.UUID,
        *,
        supplier_invoice: SupplierInvoiceModel,
        memo: str,
        created_by: Optional[uuid.UUID],
    ) -> JournalEntryModel:
        settings = await self.ensure_finance_setup(tenant_id)
        return await self._post_journal_entry(
            tenant_id=tenant_id,
            reference_type="supplier_invoice",
            reference_id=supplier_invoice.id,
            entry_date=supplier_invoice.invoice_date,
            memo=memo,
            created_by=created_by,
            lines=[
                {
                    "account_code": settings.expense_account_code,
                    "debit": _as_float(supplier_invoice.grand_total),
                    "credit": 0.0,
                    "description": f"Expense for {supplier_invoice.invoice_number}",
                },
                {
                    "account_code": settings.ap_account_code,
                    "debit": 0.0,
                    "credit": _as_float(supplier_invoice.grand_total),
                    "description": f"Accounts payable for {supplier_invoice.invoice_number}",
                },
            ],
            meta={"supplier_invoice_number": supplier_invoice.invoice_number},
        )

    async def _post_supplier_payment_entries(
        self,
        tenant_id: uuid.UUID,
        *,
        payment: SupplierPaymentModel,
        supplier_invoice: SupplierInvoiceModel,
        memo: str,
        created_by: Optional[uuid.UUID],
    ) -> JournalEntryModel:
        settings = await self.ensure_finance_setup(tenant_id)
        return await self._post_journal_entry(
            tenant_id=tenant_id,
            reference_type="supplier_payment",
            reference_id=payment.id,
            entry_date=payment.payment_date,
            memo=memo,
            created_by=created_by,
            lines=[
                {
                    "account_code": settings.ap_account_code,
                    "debit": _as_float(payment.amount),
                    "credit": 0.0,
                    "description": f"Accounts payable cleared for {supplier_invoice.invoice_number}",
                },
                {
                    "account_code": settings.bank_account_code,
                    "debit": 0.0,
                    "credit": _as_float(payment.amount),
                    "description": f"Cash paid for {supplier_invoice.invoice_number}",
                },
            ],
            meta={"payment_number": payment.payment_number, "supplier_invoice_number": supplier_invoice.invoice_number},
        )

    async def _create_legacy_ledger_entry(
        self,
        tenant_id: uuid.UUID,
        reference_type: str,
        reference_id: uuid.UUID,
        account_type: str,
        debit: float,
        credit: float,
        description: str,
        created_by: Optional[uuid.UUID] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> FinancialTransactionModel:
        entry = FinancialTransactionModel(
            tenant_id=tenant_id,
            reference_type=reference_type,
            reference_id=reference_id,
            account_type=account_type,
            debit=debit,
            credit=credit,
            description=description,
            created_by=created_by,
            meta=meta or {},
        )
        self.session.add(entry)
        return entry

    async def get_ledger(
        self,
        tenant_id: uuid.UUID,
        reference_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        q = select(FinancialTransactionModel).where(FinancialTransactionModel.tenant_id == tenant_id)
        if reference_type:
            q = q.where(FinancialTransactionModel.reference_type == reference_type)

        total = await self.session.scalar(select(func.count()).select_from(q.subquery()))
        result = await self.session.execute(
            q.order_by(FinancialTransactionModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return {
            "items": result.scalars().all(),
            "total": int(total or 0),
            "page": page,
            "pages": ((int(total or 0) + page_size - 1) // page_size) if total else 0,
        }

    # ------------------------------------------------------------------ #
    #  PDF Documents
    # ------------------------------------------------------------------ #
    async def build_invoice_pdf(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> tuple[str, bytes]:
        invoice = await self._get_invoice(tenant_id, invoice_id)
        settings = await self.ensure_finance_setup(tenant_id)
        tenant = await self.session.scalar(select(TenantModel).where(TenantModel.id == tenant_id))
        tenant_name = tenant.name if tenant else "Tenant"
        lines = [
            tenant_name,
            f"Invoice {invoice.invoice_number}",
            f"Client: {invoice.client_name}",
            f"Invoice Date: {invoice.invoice_date}",
            f"Due Date: {invoice.due_date}",
            f"Status: {invoice.status}",
        ]
        if settings.gst_number:
            lines.append(f"GST: {settings.gst_number}")
        if settings.logo_url:
            lines.append(f"Logo: {settings.logo_url}")
        lines.extend(
            [
                f"Subtotal: {_as_float(invoice.subtotal):.2f}",
                f"Tax: {_as_float(invoice.tax_amount):.2f}",
                f"Grand Total: {_as_float(invoice.grand_total):.2f}",
                "",
            ]
        )
        for idx, line in enumerate(invoice.lines or [], start=1):
            lines.append(
                f"{idx}. {line.description or line.product_type} x {line.quantity} @ {_as_float(line.unit_price):.2f} = {_as_float(line.total):.2f}"
            )
        lines.extend(
            [
                "",
                f"Paid: {_as_float(invoice.paid_amount):.2f}",
                f"Balance Due: {_as_float(invoice.grand_total) - _as_float(invoice.paid_amount):.2f}",
                f"Template: {settings.invoice_template}",
            ]
        )
        return invoice.invoice_number, _build_minimal_pdf(lines)

    async def build_receipt_pdf(self, tenant_id: uuid.UUID, payment_id: uuid.UUID) -> tuple[str, bytes]:
        payment = await self.session.scalar(
            select(PaymentModel).where(PaymentModel.id == payment_id, PaymentModel.tenant_id == tenant_id)
        )
        if payment is None:
            raise ValueError("Payment not found")
        invoice = await self._get_invoice(tenant_id, payment.invoice_id)
        tenant = await self.session.scalar(select(TenantModel).where(TenantModel.id == tenant_id))
        tenant_name = tenant.name if tenant else "Tenant"
        lines = [
            tenant_name,
            f"Receipt {payment.payment_number}",
            f"Invoice: {invoice.invoice_number}",
            f"Client: {invoice.client_name}",
            f"Payment Date: {payment.payment_date}",
            f"Method: {payment.payment_method}",
            f"Amount Received: {_as_float(payment.amount):.2f}",
            f"Reference: {payment.reference_number or '-'}",
            f"Remaining Balance: {_as_float(invoice.grand_total) - _as_float(invoice.paid_amount):.2f}",
        ]
        return payment.payment_number, _build_minimal_pdf(lines)
