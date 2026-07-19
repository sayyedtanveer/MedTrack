from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.infrastructure.persistence.models.finance_models import (
    ChartOfAccountModel,
    InvoiceModel,
    JournalEntryModel,
    JournalLineModel,
    SupplierInvoiceModel,
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


def _headers(container, tenant_id: uuid.UUID, user_id: uuid.UUID, role: str, **extra_claims: str) -> dict[str, str]:
    token = container.jwt_handler.create_access_token(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        role=role,
        extra_claims=extra_claims or None,
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
    }


async def _seed_finance_context(db_session, test_container):
    tenant_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    client_id = uuid.uuid4()
    other_client_id = uuid.uuid4()
    client_user_id = uuid.uuid4()
    other_client_user_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    other_supplier_id = uuid.uuid4()
    supplier_user_id = uuid.uuid4()
    other_supplier_user_id = uuid.uuid4()
    sales_order_id = uuid.uuid4()
    sales_order_line_id = uuid.uuid4()
    po_id = uuid.uuid4()

    db_session.add(
        TenantModel(
            id=tenant_id,
            name="Finance Tenant",
            slug=f"finance-{uuid.uuid4().hex[:8]}",
            plan="growth",
            is_active=True,
            is_deleted=False,
            currency_code="INR",
            currency_symbol="₹",
        )
    )
    db_session.add_all(
        [
            ClientModel(
                id=client_id,
                tenant_id=tenant_id,
                code=f"CL-{uuid.uuid4().hex[:6]}",
                name="Acme Client",
                email="acme.client@example.com",
                address="Mumbai",
                gst_number="27ABCDE1234F1Z5",
                payment_terms_days=30,
                is_active=True,
                is_deleted=False,
            ),
            ClientModel(
                id=other_client_id,
                tenant_id=tenant_id,
                code=f"CL-{uuid.uuid4().hex[:6]}",
                name="Other Client",
                email="other.client@example.com",
                address="Pune",
                payment_terms_days=15,
                is_active=True,
                is_deleted=False,
            ),
            SupplierModel(
                id=supplier_id,
                tenant_id=tenant_id,
                code=f"SUP-{uuid.uuid4().hex[:6]}",
                name="Prime Supplier",
                email="prime.supplier@example.com",
                is_active=True,
                is_deleted=False,
                created_by=admin_id,
            ),
            SupplierModel(
                id=other_supplier_id,
                tenant_id=tenant_id,
                code=f"SUP-{uuid.uuid4().hex[:6]}",
                name="Other Supplier",
                email="other.supplier@example.com",
                is_active=True,
                is_deleted=False,
                created_by=admin_id,
            ),
        ]
    )
    db_session.add_all(
        [
            UserModel(
                id=admin_id,
                tenant_id=tenant_id,
                email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
                hashed_password=test_container.password_hasher.hash("TempPass123!"),
                first_name="Admin",
                last_name="Finance",
                role="admin",
                is_active=True,
                is_deleted=False,
            ),
            UserModel(
                id=client_user_id,
                tenant_id=tenant_id,
                email=f"client-{uuid.uuid4().hex[:8]}@example.com",
                hashed_password=test_container.password_hasher.hash("TempPass123!"),
                first_name="Client",
                last_name="Owner",
                role="client",
                client_id=client_id,
                is_active=True,
                is_deleted=False,
            ),
            UserModel(
                id=other_client_user_id,
                tenant_id=tenant_id,
                email=f"other-client-{uuid.uuid4().hex[:8]}@example.com",
                hashed_password=test_container.password_hasher.hash("TempPass123!"),
                first_name="Other",
                last_name="Client",
                role="client",
                client_id=other_client_id,
                is_active=True,
                is_deleted=False,
            ),
            UserModel(
                id=supplier_user_id,
                tenant_id=tenant_id,
                email=f"supplier-{uuid.uuid4().hex[:8]}@example.com",
                hashed_password=test_container.password_hasher.hash("TempPass123!"),
                first_name="Supplier",
                last_name="Owner",
                role="supplier",
                supplier_id=supplier_id,
                is_active=True,
                is_deleted=False,
            ),
            UserModel(
                id=other_supplier_user_id,
                tenant_id=tenant_id,
                email=f"other-supplier-{uuid.uuid4().hex[:8]}@example.com",
                hashed_password=test_container.password_hasher.hash("TempPass123!"),
                first_name="Other",
                last_name="Supplier",
                role="supplier",
                supplier_id=other_supplier_id,
                is_active=True,
                is_deleted=False,
            ),
        ]
    )
    db_session.add(
        SalesOrderModel(
            id=sales_order_id,
            tenant_id=tenant_id,
            order_number=f"SO-{uuid.uuid4().hex[:8]}",
            client_id=client_id,
            order_date=date.today().isoformat(),
            delivery_date=(date.today() + timedelta(days=5)).isoformat(),
            status="DELIVERED",
            payment_status="PENDING",
            subtotal=1000,
            discount_amount=0,
            tax_amount=180,
            grand_total=1180,
            created_by=str(admin_id),
            is_active=True,
            is_deleted=False,
        )
    )
    db_session.add(
        SalesOrderLineModel(
            id=sales_order_line_id,
            sales_order_id=sales_order_id,
            product_id=uuid.uuid4(),
            product_type="variant",
            uom_id=uuid.uuid4(),
            quantity=1,
            unit_price=1000,
            tax_rate=18,
            tax_amount=180,
            line_total=1180,
            allocated_quantity=1,
            shipped_quantity=1,
            backorder_quantity=0,
            status="DELIVERED",
        )
    )
    db_session.add(
        PurchaseOrderModel(
            id=po_id,
            tenant_id=tenant_id,
            po_number=f"PO-{uuid.uuid4().hex[:8]}",
            supplier_id=supplier_id,
            order_date=date.today(),
            expected_delivery=date.today() + timedelta(days=10),
            status="sent",
            total_amount=590,
            notes="Finance AP test PO",
            created_by=admin_id,
            is_deleted=False,
        )
    )
    await db_session.commit()
    return {
        "tenant_id": tenant_id,
        "admin_id": admin_id,
        "client_id": client_id,
        "other_client_id": other_client_id,
        "supplier_id": supplier_id,
        "other_supplier_id": other_supplier_id,
        "sales_order_id": sales_order_id,
        "sales_order_line_id": sales_order_line_id,
        "po_id": po_id,
        "admin_headers": _headers(test_container, tenant_id, admin_id, "admin"),
        "client_headers": _headers(test_container, tenant_id, client_user_id, "client", cid=str(client_id)),
        "other_client_headers": _headers(
            test_container,
            tenant_id,
            other_client_user_id,
            "client",
            cid=str(other_client_id),
        ),
        "supplier_headers": _headers(
            test_container,
            tenant_id,
            supplier_user_id,
            "supplier",
            sid=str(supplier_id),
        ),
        "other_supplier_headers": _headers(
            test_container,
            tenant_id,
            other_supplier_user_id,
            "supplier",
            sid=str(other_supplier_id),
        ),
    }


async def _journal_lines(db_session, entry_id: uuid.UUID) -> dict[str, tuple[Decimal, Decimal]]:
    result = await db_session.execute(
        select(
            ChartOfAccountModel.code,
            JournalLineModel.debit,
            JournalLineModel.credit,
        )
        .join(ChartOfAccountModel, ChartOfAccountModel.id == JournalLineModel.account_id)
        .where(JournalLineModel.journal_entry_id == entry_id)
    )
    return {
        code: (Decimal(str(debit or 0)), Decimal(str(credit or 0)))
        for code, debit, credit in result.all()
    }


@pytest.mark.asyncio
async def test_customer_invoice_payment_posts_journals_reports_and_client_scope(
    async_client,
    db_session,
    test_container,
):
    ctx = await _seed_finance_context(db_session, test_container)

    create_resp = await async_client.post(
        "/api/v1/finance/invoices/from-so",
        headers=ctx["admin_headers"],
        json={"sales_order_id": str(ctx["sales_order_id"]), "notes": "Auto invoice from SO"},
    )
    assert create_resp.status_code == 201, create_resp.text
    invoice = create_resp.json()
    invoice_id = invoice["id"]
    assert invoice["status"] == "DRAFT"
    assert invoice["sales_order_id"] == str(ctx["sales_order_id"])
    assert len(invoice["lines"]) == 1

    send_resp = await async_client.post(
        f"/api/v1/finance/invoices/{invoice_id}/send",
        headers=ctx["admin_headers"],
    )
    assert send_resp.status_code == 200
    assert send_resp.json()["status"] == "SENT"

    first_payment_resp = await async_client.post(
        "/api/v1/finance/payments",
        headers=ctx["admin_headers"],
        json={
            "invoice_id": invoice_id,
            "amount": 500,
            "payment_date": date.today().isoformat(),
            "payment_method": "BANK_TRANSFER",
            "reference_number": "AR-001",
        },
    )
    assert first_payment_resp.status_code == 201, first_payment_resp.text
    first_payment = first_payment_resp.json()

    second_payment_resp = await async_client.post(
        "/api/v1/finance/payments",
        headers=ctx["admin_headers"],
        json={
            "invoice_id": invoice_id,
            "amount": 680,
            "payment_date": date.today().isoformat(),
            "payment_method": "UPI",
            "reference_number": "AR-002",
        },
    )
    assert second_payment_resp.status_code == 201, second_payment_resp.text

    invoice_get = await async_client.get(
        f"/api/v1/finance/invoices/{invoice_id}",
        headers=ctx["admin_headers"],
    )
    assert invoice_get.status_code == 200
    assert invoice_get.json()["status"] == "PAID"
    assert invoice_get.json()["paid_amount"] == pytest.approx(1180.0)

    invoice_pdf = await async_client.get(
        f"/api/v1/finance/invoices/{invoice_id}/pdf",
        headers=ctx["admin_headers"],
    )
    assert invoice_pdf.status_code == 200
    assert invoice_pdf.headers["content-type"].startswith("application/pdf")
    assert invoice_pdf.content.startswith(b"%PDF")

    receipt_pdf = await async_client.get(
        f"/api/v1/finance/payments/{first_payment['id']}/receipt-pdf",
        headers=ctx["admin_headers"],
    )
    assert receipt_pdf.status_code == 200
    assert receipt_pdf.content.startswith(b"%PDF")

    invoice_entry = await db_session.scalar(
        select(JournalEntryModel).where(
            JournalEntryModel.tenant_id == ctx["tenant_id"],
            JournalEntryModel.reference_type == "invoice",
            JournalEntryModel.reference_id == uuid.UUID(invoice_id),
        )
    )
    assert invoice_entry is not None
    invoice_lines = await _journal_lines(db_session, invoice_entry.id)
    assert invoice_lines["1100"] == (Decimal("1180.00"), Decimal("0"))
    assert invoice_lines["4000"] == (Decimal("0"), Decimal("1180.00"))

    payment_entries = (
        await db_session.execute(
            select(JournalEntryModel).where(
                JournalEntryModel.tenant_id == ctx["tenant_id"],
                JournalEntryModel.reference_type == "payment",
            )
        )
    ).scalars().all()
    assert len(payment_entries) == 2

    trial_balance = await async_client.get(
        "/api/v1/finance/trial-balance",
        headers=ctx["admin_headers"],
    )
    assert trial_balance.status_code == 200
    tb = trial_balance.json()
    assert tb["totals"]["is_balanced"] is True
    assert tb["totals"]["debit"] == pytest.approx(tb["totals"]["credit"])

    pnl = await async_client.get("/api/v1/finance/profit-loss", headers=ctx["admin_headers"])
    assert pnl.status_code == 200
    assert pnl.json()["totals"]["income"] == pytest.approx(1180.0)
    assert pnl.json()["totals"]["net_profit"] == pytest.approx(1180.0)

    balance_sheet = await async_client.get("/api/v1/finance/balance-sheet", headers=ctx["admin_headers"])
    assert balance_sheet.status_code == 200
    assert balance_sheet.json()["totals"]["is_balanced"] is True

    cash_flow = await async_client.get("/api/v1/finance/cash-flow?months=6", headers=ctx["admin_headers"])
    assert cash_flow.status_code == 200
    assert cash_flow.json()["totals"]["cash_in"] == pytest.approx(1180.0)

    client_list = await async_client.get("/api/v1/client/invoices", headers=ctx["client_headers"])
    assert client_list.status_code == 200
    assert [item["id"] for item in client_list.json()["items"]] == [invoice_id]

    other_client_list = await async_client.get("/api/v1/client/invoices", headers=ctx["other_client_headers"])
    assert other_client_list.status_code == 200
    assert other_client_list.json()["items"] == []

    other_client_get = await async_client.get(
        f"/api/v1/client/invoices/{invoice_id}",
        headers=ctx["other_client_headers"],
    )
    assert other_client_get.status_code == 404

    client_pdf = await async_client.get(
        f"/api/v1/client/invoices/{invoice_id}/pdf",
        headers=ctx["client_headers"],
    )
    assert client_pdf.status_code == 200
    assert client_pdf.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_supplier_invoice_payment_ap_aging_and_supplier_scope(async_client, db_session, test_container):
    ctx = await _seed_finance_context(db_session, test_container)

    supplier_invoice_resp = await async_client.post(
        "/api/v1/finance/supplier-invoices",
        headers=ctx["supplier_headers"],
        json={
            "supplier_id": str(ctx["supplier_id"]),
            "purchase_order_id": str(ctx["po_id"]),
            "supplier_invoice_ref": "SUP-INV-001",
            "invoice_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=15)).isoformat(),
            "subtotal": 500,
            "tax_amount": 90,
            "grand_total": 590,
            "notes": "Submitted by supplier portal",
        },
    )
    assert supplier_invoice_resp.status_code == 201, supplier_invoice_resp.text
    supplier_invoice = supplier_invoice_resp.json()

    duplicate_resp = await async_client.post(
        "/api/v1/finance/supplier-invoices",
        headers=ctx["supplier_headers"],
        json={
            "supplier_id": str(ctx["supplier_id"]),
            "purchase_order_id": str(ctx["po_id"]),
            "supplier_invoice_ref": "SUP-INV-001",
            "invoice_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=15)).isoformat(),
            "subtotal": 500,
            "tax_amount": 90,
            "grand_total": 590,
        },
    )
    assert duplicate_resp.status_code == 201
    assert duplicate_resp.json()["id"] == supplier_invoice["id"]

    forbidden_create = await async_client.post(
        "/api/v1/finance/supplier-invoices",
        headers=ctx["other_supplier_headers"],
        json={
            "supplier_id": str(ctx["supplier_id"]),
            "purchase_order_id": str(ctx["po_id"]),
            "supplier_invoice_ref": "SUP-INV-002",
            "invoice_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=15)).isoformat(),
            "subtotal": 100,
            "tax_amount": 18,
            "grand_total": 118,
        },
    )
    assert forbidden_create.status_code == 403

    ap_aging_before_payment = await async_client.get("/api/v1/finance/ap-aging", headers=ctx["admin_headers"])
    assert ap_aging_before_payment.status_code == 200
    assert ap_aging_before_payment.json()[0]["supplier_id"] == str(ctx["supplier_id"])
    assert ap_aging_before_payment.json()[0]["total_outstanding"] == pytest.approx(590.0)

    payment_resp = await async_client.post(
        "/api/v1/finance/supplier-payments",
        headers=ctx["admin_headers"],
        json={
            "supplier_invoice_id": supplier_invoice["id"],
            "amount": 590,
            "payment_date": date.today().isoformat(),
            "payment_method": "BANK_TRANSFER",
            "reference_number": "AP-001",
        },
    )
    assert payment_resp.status_code == 201, payment_resp.text

    stored_supplier_invoice = await db_session.scalar(
        select(SupplierInvoiceModel).where(SupplierInvoiceModel.id == uuid.UUID(supplier_invoice["id"]))
    )
    assert stored_supplier_invoice is not None
    assert Decimal(str(stored_supplier_invoice.paid_amount)) == Decimal("590.00")
    assert stored_supplier_invoice.status == "PAID"

    supplier_invoice_entry = await db_session.scalar(
        select(JournalEntryModel).where(
            JournalEntryModel.tenant_id == ctx["tenant_id"],
            JournalEntryModel.reference_type == "supplier_invoice",
            JournalEntryModel.reference_id == uuid.UUID(supplier_invoice["id"]),
        )
    )
    assert supplier_invoice_entry is not None
    supplier_invoice_lines = await _journal_lines(db_session, supplier_invoice_entry.id)
    assert supplier_invoice_lines["5000"] == (Decimal("590.00"), Decimal("0"))
    assert supplier_invoice_lines["2000"] == (Decimal("0"), Decimal("590.00"))

    supplier_payment_entry = await db_session.scalar(
        select(JournalEntryModel).where(
            JournalEntryModel.tenant_id == ctx["tenant_id"],
            JournalEntryModel.reference_type == "supplier_payment",
        )
    )
    assert supplier_payment_entry is not None
    supplier_payment_lines = await _journal_lines(db_session, supplier_payment_entry.id)
    assert supplier_payment_lines["2000"] == (Decimal("590.00"), Decimal("0"))
    assert supplier_payment_lines["1000"] == (Decimal("0"), Decimal("590.00"))

    supplier_list = await async_client.get("/api/v1/supplier/invoices", headers=ctx["supplier_headers"])
    assert supplier_list.status_code == 200
    assert [item["id"] for item in supplier_list.json()["items"]] == [supplier_invoice["id"]]

    other_supplier_list = await async_client.get(
        "/api/v1/supplier/invoices",
        headers=ctx["other_supplier_headers"],
    )
    assert other_supplier_list.status_code == 200
    assert other_supplier_list.json()["items"] == []


@pytest.mark.asyncio
async def test_finance_settings_chart_of_accounts_and_tenant_isolation(async_client, db_session, test_container):
    first = await _seed_finance_context(db_session, test_container)
    second = await _seed_finance_context(db_session, test_container)

    settings_resp = await async_client.get("/api/v1/finance/settings", headers=first["admin_headers"])
    assert settings_resp.status_code == 200
    assert settings_resp.json()["invoice_prefix"] == "INV"

    update_resp = await async_client.put(
        "/api/v1/finance/settings",
        headers=first["admin_headers"],
        json={
            "invoice_prefix": "BILL",
            "supplier_invoice_prefix": "VBILL",
            "payment_prefix": "RCPT",
            "supplier_payment_prefix": "VPAY",
            "invoice_template": "gst-modern",
            "default_tax_rate": 18,
            "default_payment_terms_days": 21,
            "gst_number": "27ABCDE1234F1Z5",
            "logo_url": "https://cdn.example.com/logo.png",
            "custom_template": {"accent": "#2563eb", "footer": "Thanks"},
        },
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["invoice_prefix"] == "BILL"
    assert update_resp.json()["custom_template"]["accent"] == "#2563eb"

    chart_resp = await async_client.get("/api/v1/finance/chart-of-accounts", headers=first["admin_headers"])
    assert chart_resp.status_code == 200
    codes = {row["code"] for row in chart_resp.json()}
    assert {"1000", "1100", "2000", "4000", "5000"}.issubset(codes)

    first_invoice_resp = await async_client.post(
        "/api/v1/finance/invoices",
        headers=first["admin_headers"],
        json={
            "client_id": str(first["client_id"]),
            "invoice_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=21)).isoformat(),
            "lines": [
                {
                    "product_id": str(uuid.uuid4()),
                    "product_type": "finished",
                    "description": "Tenant 1 invoice",
                    "quantity": 1,
                    "unit_price": 250,
                    "discount_amount": 0,
                    "tax_rate": 18,
                    "tax_amount": 45,
                    "total": 295,
                }
            ],
        },
    )
    assert first_invoice_resp.status_code == 201, first_invoice_resp.text
    first_invoice = first_invoice_resp.json()
    assert first_invoice["invoice_number"].startswith("BILL-")

    second_invoice_resp = await async_client.post(
        "/api/v1/finance/invoices",
        headers=second["admin_headers"],
        json={
            "client_id": str(second["client_id"]),
            "invoice_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "lines": [
                {
                    "product_id": str(uuid.uuid4()),
                    "product_type": "finished",
                    "description": "Tenant 2 invoice",
                    "quantity": 1,
                    "unit_price": 100,
                    "discount_amount": 0,
                    "tax_rate": 0,
                    "tax_amount": 0,
                    "total": 100,
                }
            ],
        },
    )
    assert second_invoice_resp.status_code == 201, second_invoice_resp.text
    assert second_invoice_resp.json()["invoice_number"].startswith("INV-")

    first_list = await async_client.get("/api/v1/finance/invoices", headers=first["admin_headers"])
    assert first_list.status_code == 200
    first_ids = {item["id"] for item in first_list.json()["items"]}
    assert first_invoice["id"] in first_ids
    assert second_invoice_resp.json()["id"] not in first_ids

    second_list = await async_client.get("/api/v1/finance/invoices", headers=second["admin_headers"])
    assert second_list.status_code == 200
    second_ids = {item["id"] for item in second_list.json()["items"]}
    assert second_invoice_resp.json()["id"] in second_ids
    assert first_invoice["id"] not in second_ids

    stored_settings = await db_session.scalar(
        select(TenantFinanceSettingsModel).where(TenantFinanceSettingsModel.tenant_id == first["tenant_id"])
    )
    assert stored_settings is not None
    assert stored_settings.invoice_template == "gst-modern"

    tenant_one_invoice = await db_session.scalar(
        select(InvoiceModel).where(InvoiceModel.id == uuid.UUID(first_invoice["id"]))
    )
    assert tenant_one_invoice is not None
    assert tenant_one_invoice.tenant_id == first["tenant_id"]
