import pytest
import uuid
from decimal import Decimal
from datetime import date
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_sales_to_manufacturing_e2e(client: AsyncClient, get_token, db_session, test_tenant_id):
    """
    Test the E2E flow from:
    1. Create Client
    2. Create Product/BOM/Stock/PriceList
    3. Create Sales Order
    4. Confirm Sales Order -> Should auto-trigger Work Order
    """
    token = await get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Setup Product
    from backend.app.infrastructure.persistence.models import ItemVariantModel, BOMModel, SettingsModel, MaterialModel
    item_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    uom_id = uuid.uuid4()
    bom_id = uuid.uuid4()
    material_id = uuid.uuid4()

    db_session.add(SettingsModel(tenant_id=test_tenant_id, company_name="Test Company", timezone="UTC"))
    
    db_session.add(ItemVariantModel(
        id=variant_id, 
        tenant_id=test_tenant_id, 
        item_id=item_id, 
        name="Test FG", 
        sku="FG-001", 
        base_unit_id=uom_id
    ))
    db_session.add(MaterialModel(
        id=variant_id, # Link FG variant to material
        tenant_id=test_tenant_id,
        name="Test FG",
        code="FG-001",
        type="FINISHED_GOOD",
        unit_id=uom_id
    ))
    db_session.add(BOMModel(
        id=bom_id, 
        tenant_id=test_tenant_id, 
        item_variant_id=variant_id, 
        quantity=1.0, 
        is_active=True
    ))
    await db_session.commit()

    # 1. Create client
    client_res = await client.post(
        "/api/v1/sales/clients",
        json={
            "code": "CUST-001",
            "name": "Acme Corp",
            "email": "test@acme.com",
            "phone": "555-0100",
            "credit_limit": 5000.0,
            "payment_terms_days": 30
        },
        headers=headers
    )
    assert client_res.status_code == 201
    client_id = client_res.json()["id"]

    # 2. Create Price List
    pl_res = await client.post(
        "/api/v1/sales/price-lists",
        json={
            "name": "Default List",
            "is_default": True
        },
        headers=headers
    )
    assert pl_res.status_code == 201
    pl_id = pl_res.json()["id"]

    # 3. Add price list line
    from backend.app.infrastructure.persistence.models.pricing_model import PriceListLineModel
    db_session.add(PriceListLineModel(
        price_list_id=uuid.UUID(pl_id),
        product_id=variant_id,
        product_type="variant",
        price=150.0
    ))
    await db_session.commit()

    # 4. Create Sales Order
    so_res = await client.post(
        "/api/v1/sales/orders",
        json={
            "client_id": client_id,
            "order_date": date.today().isoformat(),
            "delivery_date": "2030-12-31"
        },
        headers=headers
    )
    assert so_res.status_code == 201
    order_id = so_res.json()["id"]

    # 5. Add Line Item -> Will fetch price 150.0
    line_res = await client.post(
        f"/api/v1/sales/orders/{order_id}/lines",
        json={
            "product_id": str(variant_id),
            "product_type": "variant",
            "uom_id": str(uom_id),
            "quantity": 20,
            "tax_rate": 0
        },
        headers=headers
    )
    assert line_res.status_code == 201

    # 6. Confirm Order -> No stock -> Shortage of 20 -> Create Work Order!
    conf_res = await client.post(
        f"/api/v1/sales/orders/{order_id}/confirm",
        json={"confirmed_by": "test-user"},
        headers=headers
    )
    assert conf_res.status_code == 200
    conf_data = conf_res.json()
    assert conf_data["status"] == "CONFIRMED"

    # Verify a Work Order was generated
    wo_res = await client.get("/api/v1/manufacturing/work-orders", headers=headers)
    assert wo_res.status_code == 200
    work_orders = wo_res.json()["items"]
    assert len(work_orders) == 1
    assert work_orders[0]["planned_quantity"] == 20.0
    assert work_orders[0]["sales_order_id"] is not None
