"""Phase 5 E2E tests: Delivery lifecycle flows.

Tests cover:
- Delivery creation from sales order with line-item allocation
- Delivery shipment (carrier + tracking assignment)
- Delivery completion (mark as delivered)
- Delivery cancellation (with reason)
- Partial delivery handling
- Auto-invoice on delivery completion
- Permission enforcement for delivery operations

Requirements: 33–36, Gap #5 (dispatch → delivery)
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel, SalesOrderLineModel
from backend.app.infrastructure.persistence.models.delivery_model import (
    DeliveryOrderModel,
    DeliveryLineModel,
)
from backend.app.infrastructure.persistence.models.finance_models import InvoiceModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.domain.sales.value_objects.order_status import OrderStatus




# ─────────────────────────────────────────────────────────────────────────────
# Helper: Create a complete sales order with ready inventory
# ─────────────────────────────────────────────────────────────────────────────

async def _create_test_so_with_inventory(
    session: AsyncSession,
    test_tenant: TenantModel,
    admin_user_id: uuid.UUID,
) -> tuple[uuid.UUID, list[dict]]:
    """
    Create a complete SO ready for delivery:
    1. Create material, variant
    2. Create opening inventory stock
    3. Create SO with line items
    4. Return (so_id, [line_ids])
    """
    now_str = date.today().isoformat()

    # Create test material
    material = MaterialModel(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="Test Material",
        code=f"MAT-{uuid.uuid4().hex[:6].upper()}",
        description="Test material for Phase 5",
        purchase_uom="PCS",
        is_active=True,
        created_by=admin_user_id,
    )
    session.add(material)

    # Create variant
    variant = ItemVariantModel(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        template_id=uuid.uuid4(),  # Simplified; normally refs ItemTemplateModel
        code=f"VAR-{uuid.uuid4().hex[:6].upper()}",
        name="Test Variant",
        variant_key="V1",
        attribute_values={},
        is_active=True,
    )
    session.add(variant)
    await session.flush()  # Flush to get IDs before referencing

    # Create opening inventory stock
    stock = StockLevelModel(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        variant_id=variant.id,
        warehouse_id=None,  # Default warehouse
        quantity_on_hand=Decimal("100"),
        quantity_reserved=Decimal("0"),
        quantity_available=Decimal("100"),
        created_at=None,
    )
    session.add(stock)

    # Create sales order
    so = SalesOrderModel(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        sales_order_number=f"SO-{uuid.uuid4().hex[:6].upper()}",
        client_id=None,  # Simplify for test
        status=OrderStatus.CONFIRMED.value,  # Pre-confirm so it's ready for delivery
        order_date=date.today(),
        requested_delivery_date=date.today(),
        delivery_address="Test Address",
        currency="USD",
        subtotal=Decimal("1000"),
        tax_amount=Decimal("100"),
        grand_total=Decimal("1100"),
        notes="Test SO for Phase 5",
        created_by=admin_user_id,
        client_name="Test Client",
        client_address="Client Address",
        client_gst_number="GST123",
    )
    session.add(so)

    # Create SO line item
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

    return so.id, [
        {
            "sales_order_line_id": so_line.id,
            "quantity": Decimal("10"),
        }
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delivery_creation_from_sales_order(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Create delivery from confirmed sales order."""
    so_id, lines = await _create_test_so_with_inventory(
        e2e_db_session, test_tenant, admin_user["id"]
    )
    await e2e_db_session.commit()

    # Create delivery with SO lines
    response = await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "lines": [
                {"sales_order_line_id": str(line["sales_order_line_id"]), "quantity": str(line["quantity"])}
                for line in lines
            ],
            "carrier": "FedEx",
            "tracking_number": "1234567890",
            "notes": "Test delivery",
        },
        headers=admin_user["headers"],
    )

    assert response.status_code == 201, f"Failed: {response.text}"
    data = response.json()
    assert data["sales_order_id"] == str(so_id)
    assert data["status"] in ("DRAFT", "PACKING", "READY_TO_SHIP")
    assert "delivery_number" in data
    delivery_id = data["id"]

    # Verify delivery lines match
    assert len(data["lines"]) == len(lines)


@pytest.mark.asyncio
async def test_delivery_ship_transitions_status(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Shipping delivery updates status and carrier info."""
    so_id, lines = await _create_test_so_with_inventory(
        e2e_db_session, test_tenant, admin_user["id"]
    )
    await e2e_db_session.commit()

    # Create delivery
    create_resp = await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "lines": [
                {"sales_order_line_id": str(line["sales_order_line_id"]), "quantity": str(line["quantity"])}
                for line in lines
            ],
        },
        headers=admin_user["headers"],
    )
    assert create_resp.status_code == 201
    delivery_id = create_resp.json()["id"]

    # Ship delivery
    ship_resp = await async_client.post(
        f"/api/v1/deliveries/{delivery_id}/ship",
        json={
            "carrier": "UPS",
            "tracking_number": "9999999999",
        },
        headers=admin_user["headers"],
    )
    assert ship_resp.status_code == 200
    data = ship_resp.json()
    assert data["status"] in ("SHIPPED", "IN_TRANSIT")
    assert data["carrier"] == "UPS"
    assert data["tracking_number"] == "9999999999"
    assert data["shipped_at"] is not None


@pytest.mark.asyncio
async def test_delivery_deliver_completes_lifecycle(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Delivering marks delivery as delivered and updates SO status."""
    so_id, lines = await _create_test_so_with_inventory(
        e2e_db_session, test_tenant, admin_user["id"]
    )
    await e2e_db_session.commit()

    # Create and ship delivery
    create_resp = await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "lines": [
                {"sales_order_line_id": str(line["sales_order_line_id"]), "quantity": str(line["quantity"])}
                for line in lines
            ],
        },
        headers=admin_user["headers"],
    )
    delivery_id = create_resp.json()["id"]

    ship_resp = await async_client.post(
        f"/api/v1/deliveries/{delivery_id}/ship",
        json={},
        headers=admin_user["headers"],
    )
    assert ship_resp.status_code == 200

    # Deliver
    deliver_resp = await async_client.post(
        f"/api/v1/deliveries/{delivery_id}/deliver",
        headers=admin_user["headers"],
    )
    assert deliver_resp.status_code == 200
    data = deliver_resp.json()
    assert data["status"] in ("DELIVERED", "COMPLETED")
    assert data["delivered_at"] is not None

    # Verify SO transitioned to DELIVERED or similar
    so = await e2e_db_session.get(SalesOrderModel, so_id)
    await e2e_db_session.refresh(so)
    assert so.status in (
        OrderStatus.DELIVERED.value,
        OrderStatus.INVOICED.value,
        OrderStatus.IN_TRANSIT.value,
    )


@pytest.mark.asyncio
async def test_partial_delivery_handling(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Partial delivery (qty < SO line total)."""
    so_id, lines = await _create_test_so_with_inventory(
        e2e_db_session, test_tenant, admin_user["id"]
    )
    await e2e_db_session.commit()

    # Create partial delivery (deliver 5 of 10)
    response = await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "lines": [
                {
                    "sales_order_line_id": str(lines[0]["sales_order_line_id"]),
                    "quantity": "5",  # Partial quantity
                }
            ],
        },
        headers=admin_user["headers"],
    )

    assert response.status_code == 201
    data = response.json()
    # Verify line quantity is 5 (not full 10)
    assert len(data["lines"]) == 1
    assert Decimal(str(data["lines"][0]["quantity"])) == Decimal("5")


@pytest.mark.asyncio
async def test_delivery_cancellation(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Cancel delivery in DRAFT status."""
    so_id, lines = await _create_test_so_with_inventory(
        e2e_db_session, test_tenant, admin_user["id"]
    )
    await e2e_db_session.commit()

    # Create delivery
    create_resp = await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "lines": [
                {"sales_order_line_id": str(line["sales_order_line_id"]), "quantity": str(line["quantity"])}
                for line in lines
            ],
        },
        headers=admin_user["headers"],
    )
    delivery_id = create_resp.json()["id"]

    # Cancel delivery
    cancel_resp = await async_client.post(
        f"/api/v1/deliveries/{delivery_id}/cancel",
        json={"reason": "Cancelled per customer request"},
        headers=admin_user["headers"],
    )
    assert cancel_resp.status_code == 200
    data = cancel_resp.json()
    assert data["status"] == "CANCELLED"
    assert data["cancelled_at"] is not None
    assert data["cancellation_reason"] == "Cancelled per customer request"


@pytest.mark.asyncio
async def test_delivery_auto_invoice_on_complete(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test Gap #7: Delivery completion auto-generates invoice."""
    so_id, lines = await _create_test_so_with_inventory(
        e2e_db_session, test_tenant, admin_user["id"]
    )
    await e2e_db_session.commit()

    # Create and complete delivery
    create_resp = await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "lines": [
                {"sales_order_line_id": str(line["sales_order_line_id"]), "quantity": str(line["quantity"])}
                for line in lines
            ],
        },
        headers=admin_user["headers"],
    )
    delivery_id = create_resp.json()["id"]

    # Ship
    await async_client.post(
        f"/api/v1/deliveries/{delivery_id}/ship",
        json={},
        headers=admin_user["headers"],
    )

    # Deliver (should trigger auto-invoice)
    deliver_resp = await async_client.post(
        f"/api/v1/deliveries/{delivery_id}/deliver",
        headers=admin_user["headers"],
    )
    assert deliver_resp.status_code == 200

    # Verify invoice was auto-created
    invoice_stmt = select(InvoiceModel).where(
        and_(
            InvoiceModel.tenant_id == test_tenant.id,
            InvoiceModel.sales_order_id == so_id,
        )
    )
    invoices = (await e2e_db_session.execute(invoice_stmt)).scalars().all()
    assert len(invoices) > 0, f"Expected auto-invoice on delivery completion (Gap #7)"

    invoice = invoices[0]
    assert invoice.status in ("GENERATED", "PENDING")
    # Verify amount matches SO grand_total
    so = await e2e_db_session.get(SalesOrderModel, so_id)
    await e2e_db_session.refresh(so)
    assert Decimal(str(invoice.total_amount or 0)) == Decimal(str(so.grand_total))


@pytest.mark.asyncio
async def test_delivery_permission_required(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: Non-admin user cannot create delivery without permission."""
    so_id, lines = await _create_test_so_with_inventory(
        e2e_db_session, test_tenant, admin_user["id"]
    )
    await e2e_db_session.commit()

    # Create non-admin user
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

    # Generate token for viewer
    from tests.e2e.fixtures.conftest import _make_jwt
    viewer_token = _make_jwt(user_id=user.id, tenant_id=test_tenant.id, role="viewer")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": str(test_tenant.id),
    }

    # Try to create delivery
    response = await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "lines": [
                {"sales_order_line_id": str(line["sales_order_line_id"]), "quantity": str(line["quantity"])}
                for line in lines
            ],
        },
        headers=viewer_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_deliveries_by_sales_order(
    async_client: AsyncClient,
    e2e_db_session: AsyncSession,
    test_tenant: TenantModel,
    admin_user: dict,
):
    """Test: List deliveries filtered by sales_order_id."""
    so_id, lines = await _create_test_so_with_inventory(
        e2e_db_session, test_tenant, admin_user["id"]
    )
    await e2e_db_session.commit()

    # Create delivery
    await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "lines": [
                {"sales_order_line_id": str(line["sales_order_line_id"]), "quantity": str(line["quantity"])}
                for line in lines
            ],
        },
        headers=admin_user["headers"],
    )

    # List deliveries for that SO
    list_resp = await async_client.get(
        f"/api/v1/deliveries?sales_order_id={so_id}",
        headers=admin_user["headers"],
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(d["sales_order_id"] == str(so_id) for d in data)

