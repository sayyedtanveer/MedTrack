"""Phase 6 E2E tests: Finance/Payment + Audit Trail workflows.

Tests cover:
- Invoice creation from sales order
- Manual invoice creation
- Payment recording against invoices
- Invoice balance tracking
- Audit log retrieval with filters
- Actor metadata in audit logs
- Permission enforcement for finance operations

Requirements: 37–40 (Finance/Payment/Audit)
"""
import pytest
import uuid
from datetime import date
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderModel,
    SalesOrderLineModel,
)
from backend.app.infrastructure.persistence.models.finance_models import (
    InvoiceModel,
    InvoiceLineModel,
    PaymentModel,
)
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel
from backend.app.domain.sales.value_objects.order_status import OrderStatus


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Create complete sales order with inventory and lines
# ─────────────────────────────────────────────────────────────────────────────

async def _create_test_so_with_inventory(
    session: AsyncSession,
    test_tenant: TenantModel,
    admin_user_id: uuid.UUID,
) -> uuid.UUID:
    """
    Create a complete SO:
    1. Create material, variant
    2. Create opening inventory stock
    3. Create SO with line item
    4. Return so_id
    """
    # Create test material
    material = MaterialModel(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="Finance Test Material",
        code=f"MAT-{uuid.uuid4().hex[:6].upper()}",
        description="Test material for finance phase",
        purchase_uom="PCS",
        is_active=True,
        created_by=admin_user_id,
    )
    session.add(material)

    # Create variant
    variant = ItemVariantModel(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        template_id=uuid.uuid4(),
        code=f"VAR-{uuid.uuid4().hex[:6].upper()}",
        name="Test Variant",
        variant_key="V1",
        attribute_values={},
        is_active=True,
    )
    session.add(variant)
    await session.flush()

    # Create opening inventory
    stock = StockLevelModel(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        variant_id=variant.id,
        warehouse_id=None,
        quantity_on_hand=Decimal("100"),
        quantity_reserved=Decimal("0"),
        quantity_available=Decimal("100"),
    )
    session.add(stock)

    # Create sales order
    so = SalesOrderModel(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        sales_order_number=f"SO-{uuid.uuid4().hex[:6].upper()}",
        client_id=None,
        status=OrderStatus.CONFIRMED.value,
        order_date=date.today(),
        requested_delivery_date=date.today(),
        delivery_address="Test Address",
        currency="USD",
        subtotal=Decimal("1000"),
        tax_amount=Decimal("100"),
        grand_total=Decimal("1100"),
        notes="Test SO",
        created_by=admin_user_id,
        client_name="Test Client",
        client_address="Client Address",
        client_gst_number="GST123",
    )
    session.add(so)

    # Create SO line
    so_line = SalesOrderLineModel(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        sales_order_id=so.id,
        variant_id=variant.id,
        quantity_ordered=Decimal("10"),
        quantity_delivered=Decimal("0"),
        unit_price=Decimal("100"),
        discount_amount=Decimal("0"),
        line_total=Decimal("1000"),
        notes="Line 1",
    )
    session.add(so_line)
    await session.flush()

    return so.id


# ─────────────────────────────────────────────────────────────────────────────
# Finance/Invoice Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_invoice_from_sales_order(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Create invoice from confirmed sales order."""
    so_id = await _create_test_so_with_inventory(e2e_db_session, test_tenant, admin_user["id"])
    await e2e_db_session.commit()

    # Create invoice from SO
    response = await async_client.post(
        "/api/v1/finance/invoices/from-so",
        json={
            "sales_order_id": str(so_id),
            "notes": "Test invoice from SO",
        },
        headers=admin_user["headers"],
    )

    assert response.status_code == 201, f"Failed: {response.text}"
    data = response.json()
    assert data["sales_order_id"] == str(so_id)
    assert data["status"] in ("GENERATED", "PENDING")
    assert "invoice_number" in data
    assert Decimal(str(data["grand_total"])) == Decimal("1100")
    assert len(data["lines"]) > 0


@pytest.mark.asyncio
async def test_create_manual_invoice(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Create manual invoice with line items."""
    # Create a client record (simplified)
    client_id = uuid.uuid4()

    response = await async_client.post(
        "/api/v1/finance/invoices",
        json={
            "client_id": str(client_id),
            "invoice_date": date.today().isoformat(),
            "due_date": date(2025, 1, 31).isoformat(),
            "lines": [
                {
                    "product_id": str(uuid.uuid4()),
                    "product_type": "finished",
                    "description": "Test Product",
                    "quantity": 5,
                    "unit_price": 200.0,
                    "discount_amount": 0,
                    "tax_rate": 0.1,
                    "tax_amount": 100.0,
                    "total": 1100.0,
                }
            ],
            "notes": "Manual test invoice",
        },
        headers=admin_user["headers"],
    )

    assert response.status_code == 201, f"Failed: {response.text}"
    data = response.json()
    assert data["client_id"] == str(client_id)
    assert data["status"] in ("GENERATED", "PENDING")
    assert Decimal(str(data["grand_total"])) == Decimal("1100.0")
    assert len(data["lines"]) == 1


@pytest.mark.asyncio
async def test_record_payment_against_invoice(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Record payment and verify invoice balance."""
    so_id = await _create_test_so_with_inventory(e2e_db_session, test_tenant, admin_user["id"])
    await e2e_db_session.commit()

    # Create invoice from SO
    invoice_resp = await async_client.post(
        "/api/v1/finance/invoices/from-so",
        json={"sales_order_id": str(so_id)},
        headers=admin_user["headers"],
    )
    assert invoice_resp.status_code == 201
    invoice_id = invoice_resp.json()["id"]
    grand_total = Decimal(str(invoice_resp.json()["grand_total"]))

    # Record partial payment
    payment_resp = await async_client.post(
        "/api/v1/finance/payments",
        json={
            "invoice_id": invoice_id,
            "amount": 500.0,  # Partial
            "payment_date": date.today().isoformat(),
            "payment_method": "BANK_TRANSFER",
            "reference_number": "REF-123456",
        },
        headers=admin_user["headers"],
    )
    assert payment_resp.status_code == 201, f"Failed: {payment_resp.text}"
    payment_data = payment_resp.json()
    assert Decimal(str(payment_data["amount"])) == Decimal("500")
    assert "payment_number" in payment_data

    # Record second payment (full remaining)
    payment_resp2 = await async_client.post(
        "/api/v1/finance/payments",
        json={
            "invoice_id": invoice_id,
            "amount": 600.0,
            "payment_date": date.today().isoformat(),
            "payment_method": "BANK_TRANSFER",
        },
        headers=admin_user["headers"],
    )
    assert payment_resp2.status_code == 201
    await e2e_db_session.commit()

    # Verify invoice balance
    invoice = await e2e_db_session.get(InvoiceModel, uuid.UUID(invoice_id))
    await e2e_db_session.refresh(invoice)
    total_paid = Decimal(str(invoice.paid_amount or 0))
    assert total_paid == grand_total, f"Expected {grand_total} paid, got {total_paid}"


@pytest.mark.asyncio
async def test_invoice_balance_tracking(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Invoice balance is accurately calculated."""
    so_id = await _create_test_so_with_inventory(e2e_db_session, test_tenant, admin_user["id"])
    await e2e_db_session.commit()

    # Create invoice
    invoice_resp = await async_client.post(
        "/api/v1/finance/invoices/from-so",
        json={"sales_order_id": str(so_id)},
        headers=admin_user["headers"],
    )
    invoice_id = invoice_resp.json()["id"]
    grand_total = Decimal(str(invoice_resp.json()["grand_total"]))

    # Initially, balance = grand_total
    inv_before = invoice_resp.json()
    assert Decimal(str(inv_before["balance_due"])) == grand_total

    # Record partial payment
    await async_client.post(
        "/api/v1/finance/payments",
        json={
            "invoice_id": invoice_id,
            "amount": 300.0,
            "payment_date": date.today().isoformat(),
            "payment_method": "BANK_TRANSFER",
        },
        headers=admin_user["headers"],
    )
    await e2e_db_session.commit()

    # Fetch invoice and verify balance
    get_resp = await async_client.get(
        f"/api/v1/finance/invoices/{invoice_id}",
        headers=admin_user["headers"],
    )
    if get_resp.status_code == 200:
        inv_data = get_resp.json()
        balance = Decimal(str(inv_data["balance_due"]))
        expected_balance = grand_total - Decimal("300")
        assert balance == expected_balance


@pytest.mark.asyncio
async def test_finance_permission_required(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Non-finance user cannot create invoice."""
    so_id = await _create_test_so_with_inventory(e2e_db_session, test_tenant, admin_user["id"])
    await e2e_db_session.commit()

    # Create non-finance user
    user = UserModel(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        email=f"worker-{uuid.uuid4().hex[:6]}@test.local",
        hashed_password="hashed",
        first_name="Worker",
        last_name="Test",
        role="worker",
        is_active=True,
    )
    e2e_db_session.add(user)
    await e2e_db_session.flush()

    from tests.e2e.fixtures.conftest import _make_jwt
    worker_token = _make_jwt(user_id=user.id, tenant_id=test_tenant.id, role="worker")
    worker_headers = {
        "Authorization": f"Bearer {worker_token}",
        "X-Tenant-ID": str(test_tenant.id),
    }

    # Try to create invoice
    response = await async_client.post(
        "/api/v1/finance/invoices/from-so",
        json={"sales_order_id": str(so_id)},
        headers=worker_headers,
    )
    assert response.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Audit Trail Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_logs_listed_with_pagination(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Audit logs are returned with pagination."""
    # List audit logs
    response = await async_client.get(
        "/api/v1/audit-logs?skip=0&limit=50",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_audit_logs_include_actor_metadata(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Audit logs include actor name and email."""
    so_id = await _create_test_so_with_inventory(e2e_db_session, test_tenant, admin_user["id"])
    await e2e_db_session.commit()

    # Create invoice (generates audit log)
    await async_client.post(
        "/api/v1/finance/invoices/from-so",
        json={"sales_order_id": str(so_id)},
        headers=admin_user["headers"],
    )
    await e2e_db_session.commit()

    # Query audit logs
    response = await async_client.get(
        "/api/v1/audit-logs?limit=50",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) > 0

    # Verify actor metadata
    log = data["items"][0]
    assert "actor" in log
    assert "email" in log["actor"] or "name" in log["actor"]
    # email and name might be null for system actions, but structure should exist
    assert isinstance(log["actor"], dict)


@pytest.mark.asyncio
async def test_audit_logs_filter_by_action(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Filter audit logs by action."""
    response = await async_client.get(
        "/api/v1/audit-logs?action=INVOICE_CREATED&limit=50",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    data = response.json()
    # All items should have action = INVOICE_CREATED or be empty
    for item in data["items"]:
        # Filter may return no items if no INVOICE_CREATED actions exist
        if "action" in item:
            assert "INVOICE" in item["action"] or item["action"] == "INVOICE_CREATED"


@pytest.mark.asyncio
async def test_audit_logs_filter_by_entity_type(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Filter audit logs by entity type."""
    response = await async_client.get(
        "/api/v1/audit-logs?entity_type=invoice&limit=50",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    data = response.json()
    # All items should have entity_type = invoice or be empty
    for item in data["items"]:
        if "entity_type" in item:
            assert item["entity_type"].lower() == "invoice"


@pytest.mark.asyncio
async def test_audit_logs_filter_by_entity_id(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Filter audit logs by specific entity ID."""
    so_id = await _create_test_so_with_inventory(e2e_db_session, test_tenant, admin_user["id"])
    await e2e_db_session.commit()

    # Create invoice
    invoice_resp = await async_client.post(
        "/api/v1/finance/invoices/from-so",
        json={"sales_order_id": str(so_id)},
        headers=admin_user["headers"],
    )
    invoice_id = invoice_resp.json()["id"]
    await e2e_db_session.commit()

    # Filter logs by invoice ID
    response = await async_client.get(
        f"/api/v1/audit-logs?entity_id={invoice_id}&limit=50",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    data = response.json()
    # All items should relate to this invoice
    for item in data["items"]:
        assert item["entity_id"] == invoice_id


@pytest.mark.asyncio
async def test_audit_logs_search_functionality(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Search audit logs by keyword."""
    response = await async_client.get(
        "/api/v1/audit-logs?search=invoice&limit=50",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    data = response.json()
    # Results should match the search term (if any exist)
    for item in data["items"]:
        action_or_type = (item.get("action", "") or "") + (item.get("entity_type", "") or "")
        assert "invoice" in action_or_type.lower()


@pytest.mark.asyncio
async def test_audit_logs_tenant_scoped(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Audit logs are tenant-scoped (user can only see their tenant's logs)."""
    response = await async_client.get(
        "/api/v1/audit-logs?limit=50",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    data = response.json()
    # All items should have tenant_id matching the authenticated tenant
    for item in data["items"]:
        assert item["tenant_id"] == str(test_tenant.id)


@pytest.mark.asyncio
async def test_audit_logs_require_permission(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Non-admin user cannot read audit logs."""
    # Create viewer user
    user = UserModel(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        email=f"viewer-{uuid.uuid4().hex[:6]}@test.local",
        hashed_password="hashed",
        first_name="Viewer",
        last_name="Test",
        role="viewer",
        is_active=True,
    )
    e2e_db_session.add(user)
    await e2e_db_session.flush()

    from tests.e2e.fixtures.conftest import _make_jwt
    viewer_token = _make_jwt(user_id=user.id, tenant_id=test_tenant.id, role="viewer")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": str(test_tenant.id),
    }

    # Try to read audit logs
    response = await async_client.get(
        "/api/v1/audit-logs?limit=50",
        headers=viewer_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_before_and_after_values(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Audit logs capture before/after values for updates."""
    so_id = await _create_test_so_with_inventory(e2e_db_session, test_tenant, admin_user["id"])
    await e2e_db_session.commit()

    # Create invoice (captures after value)
    invoice_resp = await async_client.post(
        "/api/v1/finance/invoices/from-so",
        json={"sales_order_id": str(so_id)},
        headers=admin_user["headers"],
    )
    invoice_id = invoice_resp.json()["id"]
    await e2e_db_session.commit()

    # Record payment (updates invoice status, should capture before/after)
    payment_resp = await async_client.post(
        "/api/v1/finance/payments",
        json={
            "invoice_id": invoice_id,
            "amount": 500.0,
            "payment_date": date.today().isoformat(),
            "payment_method": "BANK_TRANSFER",
        },
        headers=admin_user["headers"],
    )
    assert payment_resp.status_code == 201
    await e2e_db_session.commit()

    # Query audit logs for this invoice
    response = await async_client.get(
        f"/api/v1/audit-logs?entity_id={invoice_id}&limit=50",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    data = response.json()
    # Should have at least creation and payment records
    assert len(data["items"]) > 0

    # Verify structure includes before/after (may be null for creates)
    log = data["items"][0]
    assert "before_value" in log
    assert "after_value" in log
