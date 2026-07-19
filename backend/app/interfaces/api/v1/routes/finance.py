"""Finance API routes for AR, AP, accounting, reports, PDFs, and tenant settings."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.finance.finance_service import FinanceService
from backend.app.application.finance.reporting_service import ReportingService
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_role,
    get_current_tenant_id,
    get_current_user_id,
    get_current_user_payload,
)
from backend.app.infrastructure.security.jwt_claim_validator import (
    parse_client_claim,
    parse_supplier_claim,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission

router = APIRouter(prefix="/finance", tags=["Finance"])


FINANCE_ROLES = {"ADMIN", "ACCOUNTANT", "MANAGER"}
INVOICE_CREATE_ROLES = FINANCE_ROLES | {"SALES"}


async def _get_db_session(request: Request):
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session


class InvoiceLineCreate(BaseModel):
    product_id: uuid.UUID
    product_type: str = "finished"
    description: Optional[str] = None
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)
    discount_amount: float = 0
    tax_rate: float = 0
    tax_amount: float = 0
    total: float


class InvoiceCreateFromSO(BaseModel):
    sales_order_id: uuid.UUID
    notes: Optional[str] = None
    terms: Optional[str] = None


class InvoiceCreateManual(BaseModel):
    client_id: uuid.UUID
    invoice_date: date
    due_date: date
    lines: List[InvoiceLineCreate]
    notes: Optional[str] = None
    terms: Optional[str] = None


class PaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    amount: float = Field(gt=0)
    payment_date: date
    payment_method: str = "BANK_TRANSFER"
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class SupplierInvoiceCreate(BaseModel):
    supplier_id: uuid.UUID
    purchase_order_id: Optional[uuid.UUID] = None
    supplier_invoice_ref: Optional[str] = None
    invoice_date: date
    due_date: date
    subtotal: float
    tax_amount: float = 0
    grand_total: float
    notes: Optional[str] = None


class SupplierPaymentCreate(BaseModel):
    supplier_invoice_id: uuid.UUID
    amount: float = Field(gt=0)
    payment_date: date
    payment_method: str = "BANK_TRANSFER"
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class FinanceSettingsUpdate(BaseModel):
    invoice_prefix: Optional[str] = None
    supplier_invoice_prefix: Optional[str] = None
    payment_prefix: Optional[str] = None
    supplier_payment_prefix: Optional[str] = None
    invoice_template: Optional[str] = None
    default_tax_rate: Optional[float] = None
    default_payment_terms_days: Optional[int] = None
    gst_number: Optional[str] = None
    logo_url: Optional[str] = None
    custom_template: Optional[dict[str, Any]] = None
    ar_account_code: Optional[str] = None
    bank_account_code: Optional[str] = None
    ap_account_code: Optional[str] = None
    revenue_account_code: Optional[str] = None
    expense_account_code: Optional[str] = None


def _serialize_line(line) -> dict:
    return {
        "id": str(line.id),
        "product_id": str(line.product_id),
        "product_type": line.product_type,
        "description": line.description,
        "quantity": line.quantity,
        "unit_price": float(line.unit_price),
        "discount_amount": float(line.discount_amount),
        "tax_rate": float(line.tax_rate),
        "tax_amount": float(line.tax_amount),
        "total": float(line.total),
    }


def _serialize_payment_brief(payment) -> dict:
    return {
        "id": str(payment.id),
        "payment_number": payment.payment_number,
        "amount": float(payment.amount),
        "payment_date": str(payment.payment_date),
        "payment_method": payment.payment_method,
    }


def _serialize_invoice(invoice) -> dict:
    return {
        "id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "sales_order_id": str(invoice.sales_order_id) if invoice.sales_order_id else None,
        "client_id": str(invoice.client_id),
        "client_name": invoice.client_name,
        "client_address": invoice.client_address,
        "client_gst_number": invoice.client_gst_number,
        "status": invoice.status,
        "invoice_date": str(invoice.invoice_date),
        "due_date": str(invoice.due_date),
        "subtotal": float(invoice.subtotal),
        "discount_amount": float(invoice.discount_amount),
        "tax_amount": float(invoice.tax_amount),
        "grand_total": float(invoice.grand_total),
        "paid_amount": float(invoice.paid_amount),
        "balance_due": float(invoice.grand_total) - float(invoice.paid_amount),
        "notes": invoice.notes,
        "terms": invoice.terms,
        "created_at": invoice.created_at.isoformat(),
        "lines": [_serialize_line(line) for line in (invoice.lines or [])],
        "payments": [_serialize_payment_brief(payment) for payment in (invoice.payments or [])],
    }


def _serialize_payment(payment) -> dict:
    return {
        "id": str(payment.id),
        "payment_number": payment.payment_number,
        "invoice_id": str(payment.invoice_id),
        "client_id": str(payment.client_id),
        "amount": float(payment.amount),
        "payment_date": str(payment.payment_date),
        "payment_method": payment.payment_method,
        "reference_number": payment.reference_number,
        "notes": payment.notes,
        "created_at": payment.created_at.isoformat(),
    }


def _serialize_supplier_invoice(invoice) -> dict:
    return {
        "id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "supplier_invoice_ref": invoice.supplier_invoice_ref,
        "purchase_order_id": str(invoice.purchase_order_id) if invoice.purchase_order_id else None,
        "supplier_id": str(invoice.supplier_id),
        "supplier_name": invoice.supplier_name,
        "status": invoice.status,
        "invoice_date": str(invoice.invoice_date),
        "due_date": str(invoice.due_date),
        "subtotal": float(invoice.subtotal),
        "tax_amount": float(invoice.tax_amount),
        "grand_total": float(invoice.grand_total),
        "paid_amount": float(invoice.paid_amount),
        "balance_due": float(invoice.grand_total) - float(invoice.paid_amount),
        "notes": invoice.notes,
        "created_at": invoice.created_at.isoformat(),
    }


def _serialize_supplier_payment(payment) -> dict:
    return {
        "id": str(payment.id),
        "payment_number": payment.payment_number,
        "supplier_invoice_id": str(payment.supplier_invoice_id),
        "supplier_id": str(payment.supplier_id),
        "amount": float(payment.amount),
        "payment_date": str(payment.payment_date),
        "payment_method": payment.payment_method,
        "reference_number": payment.reference_number,
        "notes": payment.notes,
        "created_at": payment.created_at.isoformat(),
    }


def _client_id_from_payload(payload: dict) -> Optional[uuid.UUID]:
    """Safely parse client_id from JWT payload using centralized validator."""
    return parse_client_claim(payload)


def _supplier_id_from_payload(payload: dict) -> Optional[uuid.UUID]:
    """Safely parse supplier_id from JWT payload using centralized validator."""
    return parse_supplier_claim(payload)


@router.post(
    "/invoices/from-so",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("invoice.create"))],
)
async def create_invoice_from_so(
    body: InvoiceCreateFromSO,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in INVOICE_CREATE_ROLES:
        raise HTTPException(status_code=403, detail="Invoice creation access required")
    try:
        invoice = await FinanceService(session).create_invoice_from_sales_order(
            tenant_id=tenant_id,
            sales_order_id=body.sales_order_id,
            created_by=user_id,
            notes=body.notes,
            terms=body.terms,
        )
        return _serialize_invoice(invoice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/invoices",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("invoice.create"))],
)
async def create_invoice_manual(
    body: InvoiceCreateManual,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    try:
        invoice = await FinanceService(session).create_invoice_manual(
            tenant_id=tenant_id,
            client_id=body.client_id,
            invoice_date=body.invoice_date,
            due_date=body.due_date,
            lines_data=[line.model_dump() for line in body.lines],
            created_by=user_id,
            notes=body.notes,
            terms=body.terms,
        )
        return _serialize_invoice(invoice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/invoices", dependencies=[Depends(require_permission("invoice.view"))])
async def list_invoices(
    status: Optional[str] = Query(None),
    client_id: Optional[uuid.UUID] = Query(None),
    overdue_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(_get_db_session),
):
    role_upper = role.upper()
    effective_client_id = client_id
    if role_upper == "CLIENT":
        effective_client_id = _client_id_from_payload(payload)
        if effective_client_id is None:
            raise HTTPException(status_code=403, detail="Client access requires a linked client account")
    elif role_upper not in INVOICE_CREATE_ROLES and role_upper not in {"VIEWER", "ACCOUNTANT", "MANAGER", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await FinanceService(session).list_invoices(
        tenant_id=tenant_id,
        status=status,
        client_id=effective_client_id,
        overdue_only=overdue_only,
        page=page,
        page_size=page_size,
    )
    return {**result, "items": [_serialize_invoice(item) for item in result["items"]]}


@router.get("/invoices/{invoice_id}", dependencies=[Depends(require_permission("invoice.view"))])
async def get_invoice(
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        invoice = await FinanceService(session).get_invoice(tenant_id, invoice_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if role.upper() == "CLIENT":
        client_id = _client_id_from_payload(payload)
        if client_id is None or invoice.client_id != client_id:
            raise HTTPException(status_code=403, detail="Clients can only access their own invoices")
    elif role.upper() not in INVOICE_CREATE_ROLES and role.upper() not in {"VIEWER", "ACCOUNTANT", "MANAGER", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Access denied")
    return _serialize_invoice(invoice)


@router.post(
    "/invoices/{invoice_id}/send",
    dependencies=[Depends(require_permission("invoice.approve"))],
)
async def send_invoice(
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance approval access required")
    try:
        invoice = await FinanceService(session).send_invoice(tenant_id, invoice_id)
        return _serialize_invoice(invoice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/invoices/{invoice_id}/void",
    dependencies=[Depends(require_permission("invoice.approve"))],
)
async def void_invoice(
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in {"ADMIN", "ACCOUNTANT"}:
        raise HTTPException(status_code=403, detail="Admin or Accountant access required")
    try:
        invoice = await FinanceService(session).void_invoice(tenant_id, invoice_id, created_by=user_id)
        return _serialize_invoice(invoice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/invoices/{invoice_id}/pdf", dependencies=[Depends(require_permission("invoice.view"))])
async def invoice_pdf(
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        invoice = await FinanceService(session).get_invoice(tenant_id, invoice_id)
        if role.upper() == "CLIENT":
            client_id = _client_id_from_payload(payload)
            if client_id is None or invoice.client_id != client_id:
                raise HTTPException(status_code=403, detail="Clients can only access their own invoices")
        elif role.upper() not in INVOICE_CREATE_ROLES and role.upper() not in {"VIEWER", "ACCOUNTANT", "MANAGER", "ADMIN"}:
            raise HTTPException(status_code=403, detail="Access denied")

        invoice_number, pdf_bytes = await FinanceService(session).build_invoice_pdf(tenant_id, invoice_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{invoice_number}.pdf"'},
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/payments",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("payment.record"))],
)
async def record_payment(
    body: PaymentCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    try:
        payment = await FinanceService(session).record_payment(
            tenant_id=tenant_id,
            invoice_id=body.invoice_id,
            amount=body.amount,
            payment_date=body.payment_date,
            payment_method=body.payment_method,
            created_by=user_id,
            reference_number=body.reference_number,
            notes=body.notes,
        )
        return _serialize_payment(payment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/payments", dependencies=[Depends(require_permission("invoice.view"))])
async def list_payments(
    invoice_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    result = await FinanceService(session).list_payments(tenant_id, invoice_id, page, page_size)
    return {**result, "items": [_serialize_payment(item) for item in result["items"]]}


@router.get("/payments/{payment_id}/receipt-pdf", dependencies=[Depends(require_permission("invoice.view"))])
async def receipt_pdf(
    payment_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    try:
        payment_number, pdf_bytes = await FinanceService(session).build_receipt_pdf(tenant_id, payment_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{payment_number}.pdf"'},
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/supplier-invoices",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("supplier_invoice.create"))],
)
async def create_supplier_invoice(
    body: SupplierInvoiceCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
    payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(_get_db_session),
):
    supplier_role_id = _supplier_id_from_payload(payload)
    if role.upper() == "SUPPLIER":
        if supplier_role_id is None or supplier_role_id != body.supplier_id:
            raise HTTPException(status_code=403, detail="Suppliers can only submit their own invoices")
    elif role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance or Supplier access required")

    try:
        invoice = await FinanceService(session).create_supplier_invoice(
            tenant_id=tenant_id,
            supplier_id=body.supplier_id,
            purchase_order_id=body.purchase_order_id,
            supplier_invoice_ref=body.supplier_invoice_ref,
            invoice_date=body.invoice_date,
            due_date=body.due_date,
            subtotal=body.subtotal,
            tax_amount=body.tax_amount,
            grand_total=body.grand_total,
            created_by=user_id,
            notes=body.notes,
        )
        return _serialize_supplier_invoice(invoice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/supplier-invoices", dependencies=[Depends(require_permission("supplier_invoice.view"))])
async def list_supplier_invoices(
    status: Optional[str] = Query(None),
    supplier_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(_get_db_session),
):
    effective_supplier_id = supplier_id
    if role.upper() == "SUPPLIER":
        effective_supplier_id = _supplier_id_from_payload(payload)
        if effective_supplier_id is None:
            raise HTTPException(status_code=403, detail="Supplier access requires a linked supplier account")
    elif role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance or Supplier access required")

    result = await FinanceService(session).list_supplier_invoices(
        tenant_id=tenant_id,
        status=status,
        supplier_id=effective_supplier_id,
        page=page,
        page_size=page_size,
    )
    return {**result, "items": [_serialize_supplier_invoice(item) for item in result["items"]]}


@router.post(
    "/supplier-payments",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("supplier_payment.record"))],
)
async def record_supplier_payment(
    body: SupplierPaymentCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    try:
        payment = await FinanceService(session).record_supplier_payment(
            tenant_id=tenant_id,
            supplier_invoice_id=body.supplier_invoice_id,
            amount=body.amount,
            payment_date=body.payment_date,
            payment_method=body.payment_method,
            created_by=user_id,
            reference_number=body.reference_number,
            notes=body.notes,
        )
        return _serialize_supplier_payment(payment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/supplier-payments", dependencies=[Depends(require_permission("supplier_invoice.view"))])
async def list_supplier_payments(
    supplier_invoice_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    result = await FinanceService(session).list_supplier_payments(
        tenant_id=tenant_id,
        supplier_invoice_id=supplier_invoice_id,
        page=page,
        page_size=page_size,
    )
    return {**result, "items": [_serialize_supplier_payment(item) for item in result["items"]]}


@router.get("/dashboard", dependencies=[Depends(require_permission("report.view_financial"))])
async def finance_dashboard(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Finance access required")
    svc = FinanceService(session)
    return {
        "ar": await svc.get_ar_summary(tenant_id),
        "ap": await svc.get_ap_summary(tenant_id),
        "revenue_trend": await svc.get_revenue_by_month(tenant_id, months=6),
        "cash_flow": await svc.get_cash_flow_statement(tenant_id, months=6),
    }


@router.get("/ar-aging", dependencies=[Depends(require_permission("report.view_financial"))])
async def ar_aging_report(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await ReportingService(session).ar_aging(tenant_id, role.upper())
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/ap-aging", dependencies=[Depends(require_permission("report.view_financial"))])
async def ap_aging_report(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await ReportingService(session).ap_aging(tenant_id, role.upper())
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/trial-balance", dependencies=[Depends(require_permission("report.view_financial"))])
async def trial_balance(
    as_of: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await ReportingService(session).trial_balance(tenant_id, role.upper(), as_of=as_of)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/profit-loss", dependencies=[Depends(require_permission("report.view_financial"))])
async def profit_and_loss(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await ReportingService(session).profit_and_loss(
            tenant_id,
            role.upper(),
            from_date=from_date,
            to_date=to_date,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/balance-sheet", dependencies=[Depends(require_permission("report.view_financial"))])
async def balance_sheet(
    as_of: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await ReportingService(session).balance_sheet(tenant_id, role.upper(), as_of=as_of)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/cash-flow", dependencies=[Depends(require_permission("report.view_financial"))])
async def cash_flow_statement(
    months: int = Query(6, ge=1, le=24),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await ReportingService(session).cash_flow(tenant_id, role.upper(), months=months)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/ledger", dependencies=[Depends(require_permission("ledger.view"))])
async def get_ledger(
    reference_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in {"ADMIN", "ACCOUNTANT", "MANAGER"}:
        raise HTTPException(status_code=403, detail="Finance ledger access required")
    result = await FinanceService(session).get_ledger(tenant_id, reference_type, page, page_size)
    return {
        **result,
        "items": [
            {
                "id": str(item.id),
                "reference_type": item.reference_type,
                "reference_id": str(item.reference_id),
                "account_type": item.account_type,
                "debit": float(item.debit),
                "credit": float(item.credit),
                "description": item.description,
                "created_at": item.created_at.isoformat(),
                "meta": item.meta or {},
            }
            for item in result["items"]
        ],
    }


@router.get("/settings", dependencies=[Depends(require_permission("finance_settings.view"))])
async def get_finance_settings(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in {"ADMIN", "ACCOUNTANT", "MANAGER"}:
        raise HTTPException(status_code=403, detail="Finance settings access required")
    return await FinanceService(session).get_settings(tenant_id)


@router.put("/settings", dependencies=[Depends(require_permission("finance_settings.write"))])
async def update_finance_settings(
    body: FinanceSettingsUpdate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in {"ADMIN", "ACCOUNTANT"}:
        raise HTTPException(status_code=403, detail="Admin or Accountant access required")
    return await FinanceService(session).update_settings(tenant_id, body.model_dump(exclude_none=True))


@router.get("/chart-of-accounts", dependencies=[Depends(require_permission("ledger.view"))])
async def chart_of_accounts(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    if role.upper() not in {"ADMIN", "ACCOUNTANT", "MANAGER"}:
        raise HTTPException(status_code=403, detail="Ledger access required")
    return await FinanceService(session).list_chart_of_accounts(tenant_id)
