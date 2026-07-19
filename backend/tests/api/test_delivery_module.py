from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from backend.app.infrastructure.persistence.models.finance_models import InvoiceModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.sales_models import ClientModel, SalesOrderLineModel, SalesOrderModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher


async def test_delivery_document_ships_delivers_and_generates_invoice(
    async_client,
    db_session,
    token_headers,
    test_tenant_id,
    test_user_id,
):
    run_id = uuid.uuid4().hex[:8]
    unit_id = uuid.uuid4()
    client_id = uuid.uuid4()
    material_id = uuid.uuid4()
    order_id = uuid.uuid4()
    line_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    await db_session.merge(
        TenantModel(
            id=test_tenant_id,
            name=f"Delivery Tenant {run_id}",
            slug=f"delivery-{run_id}",
            plan="starter",
            is_active=True,
        )
    )
    await db_session.merge(
        UserModel(
            id=test_user_id,
            tenant_id=test_tenant_id,
            email=f"delivery-admin-{run_id}@example.com",
            hashed_password=BcryptPasswordHasher().hash("Password123!"),
            first_name="Delivery",
            last_name="Admin",
            role="admin",
            is_active=True,
            is_deleted=False,
        )
    )
    db_session.add(
        UnitOfMeasureModel(
            id=unit_id,
            tenant_id=test_tenant_id,
            code=f"EA{run_id[:6]}",
            name="Each",
            precision=2,
            is_active=True,
            created_at=now,
            updated_at=now,
            is_deleted=False,
        )
    )
    db_session.add(
        ClientModel(
            id=client_id,
            tenant_id=test_tenant_id,
            code=f"DEL-CLI-{run_id}",
            name="Delivery Client",
            email=f"delivery-client-{run_id}@example.com",
            credit_limit=Decimal("1000"),
            credit_used=Decimal("0"),
            payment_terms_days=30,
            is_active=True,
            is_deleted=False,
        )
    )
    db_session.add(
        MaterialModel(
            id=material_id,
            tenant_id=test_tenant_id,
            code=f"DEL-FG-{run_id}",
            name="Delivery Finished Good",
            material_type="finished",
            base_unit_id=unit_id,
            current_cost=Decimal("10"),
            current_stock=Decimal("2"),
            reserved_stock=Decimal("2"),
            reorder_level=Decimal("0"),
            is_active=True,
            is_deleted=False,
        )
    )
    db_session.add(
        SalesOrderModel(
            id=order_id,
            tenant_id=test_tenant_id,
            client_id=client_id,
            order_number=f"SO-DEL-{run_id}",
            order_date=date.today().isoformat(),
            delivery_date=(date.today() + timedelta(days=3)).isoformat(),
            status="READY",
            payment_status="PENDING",
            subtotal=200,
            discount_amount=0,
            tax_amount=0,
            grand_total=200,
            created_by=str(test_user_id),
            is_active=True,
            is_deleted=False,
        )
    )
    db_session.add(
        SalesOrderLineModel(
            id=line_id,
            sales_order_id=order_id,
            product_id=material_id,
            product_type="variant",
            uom_id=unit_id,
            quantity=2,
            unit_price=100,
            tax_rate=0,
            tax_amount=0,
            line_total=200,
            allocated_quantity=2,
            shipped_quantity=0,
            backorder_quantity=0,
            status="allocated",
        )
    )
    db_session.add(
        InventoryTransactionModel(
            id=uuid.uuid4(),
            tenant_id=test_tenant_id,
            material_id=material_id,
            transaction_type="reserve",
            quantity=2,
            unit_id=unit_id,
            reference_type="sales_order_line",
            reference_id=line_id,
            created_by=test_user_id,
        )
    )
    await db_session.commit()

    create_resp = await async_client.post(
        "/api/v1/deliveries",
        headers=token_headers,
        json={"sales_order_id": str(order_id)},
    )
    assert create_resp.status_code == 201, create_resp.text
    delivery = create_resp.json()
    assert delivery["status"] == "DRAFT"
    assert Decimal(str(delivery["lines"][0]["quantity"])) == Decimal("2.0000")

    ship_resp = await async_client.post(
        f"/api/v1/deliveries/{delivery['id']}/ship",
        headers=token_headers,
        json={"carrier": "BlueDart", "tracking_number": "TRACK-1"},
    )
    assert ship_resp.status_code == 200, ship_resp.text
    assert ship_resp.json()["status"] == "SHIPPED"

    deliver_resp = await async_client.post(
        f"/api/v1/deliveries/{delivery['id']}/deliver",
        headers=token_headers,
    )
    assert deliver_resp.status_code == 200, deliver_resp.text
    assert deliver_resp.json()["status"] == "DELIVERED"

    material = await db_session.get(MaterialModel, material_id)
    assert Decimal(str(material.current_stock)) == Decimal("0.0000")
    assert Decimal(str(material.reserved_stock)) == Decimal("0.0000")

    invoice = (
        await db_session.execute(
            InvoiceModel.__table__.select().where(InvoiceModel.sales_order_id == order_id)
        )
    ).first()
    assert invoice is not None



async def test_dispatch_queue_returns_ready_for_dispatch_orders(
    async_client,
    db_session,
    token_headers,
    test_tenant_id,
    test_user_id,
):
    """Test GET /delivery/dispatch-queue returns READY_FOR_DISPATCH orders with correct fields.
    
    Requirements: 33 — Gap #5
    - Returns sales orders with status = 'READY_FOR_DISPATCH'
    - Filters by tenant_id
    - Returns: id, order_number, customer_name, grand_total, ready_at timestamp
    - Requires delivery:dispatch:view permission (403 if absent)
    """
    run_id = uuid.uuid4().hex[:8]
    client_id = uuid.uuid4()
    order_1_id = uuid.uuid4()
    order_2_id = uuid.uuid4()
    order_3_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Setup tenant
    await db_session.merge(
        TenantModel(
            id=test_tenant_id,
            name=f"Dispatch Tenant {run_id}",
            slug=f"dispatch-{run_id}",
            plan="starter",
            is_active=True,
        )
    )
    await db_session.merge(
        UserModel(
            id=test_user_id,
            tenant_id=test_tenant_id,
            email=f"dispatch-admin-{run_id}@example.com",
            hashed_password=BcryptPasswordHasher().hash("Password123!"),
            first_name="Dispatch",
            last_name="Admin",
            role="admin",
            is_active=True,
            is_deleted=False,
        )
    )
    
    # Create client
    db_session.add(
        ClientModel(
            id=client_id,
            tenant_id=test_tenant_id,
            code=f"DISP-CLI-{run_id}",
            name="Dispatch Test Client",
            email=f"dispatch-client-{run_id}@example.com",
            credit_limit=Decimal("10000"),
            credit_used=Decimal("0"),
            payment_terms_days=30,
            is_active=True,
            is_deleted=False,
        )
    )
    
    # Create SO in READY_FOR_DISPATCH
    db_session.add(
        SalesOrderModel(
            id=order_1_id,
            tenant_id=test_tenant_id,
            client_id=client_id,
            order_number=f"SO-DISP-001-{run_id}",
            order_date=date.today().isoformat(),
            delivery_date=(date.today() + timedelta(days=2)).isoformat(),
            status="READY_FOR_DISPATCH",
            payment_status="PENDING",
            subtotal=1000,
            discount_amount=0,
            tax_amount=50,
            grand_total=1050,
            created_by=str(test_user_id),
            is_active=True,
            is_deleted=False,
            updated_at=now,
        )
    )
    
    # Create another SO in READY_FOR_DISPATCH
    db_session.add(
        SalesOrderModel(
            id=order_2_id,
            tenant_id=test_tenant_id,
            client_id=client_id,
            order_number=f"SO-DISP-002-{run_id}",
            order_date=date.today().isoformat(),
            delivery_date=(date.today() + timedelta(days=5)).isoformat(),
            status="READY_FOR_DISPATCH",
            payment_status="PENDING",
            subtotal=2000,
            discount_amount=0,
            tax_amount=100,
            grand_total=2100,
            created_by=str(test_user_id),
            is_active=True,
            is_deleted=False,
            updated_at=now - timedelta(minutes=5),
        )
    )
    
    # Create SO in CONFIRMED (should not appear in dispatch queue)
    db_session.add(
        SalesOrderModel(
            id=order_3_id,
            tenant_id=test_tenant_id,
            client_id=client_id,
            order_number=f"SO-DISP-003-{run_id}",
            order_date=date.today().isoformat(),
            delivery_date=(date.today() + timedelta(days=3)).isoformat(),
            status="CONFIRMED",
            payment_status="PENDING",
            subtotal=500,
            discount_amount=0,
            tax_amount=25,
            grand_total=525,
            created_by=str(test_user_id),
            is_active=True,
            is_deleted=False,
            updated_at=now,
        )
    )
    
    await db_session.commit()

    # Call the dispatch queue endpoint
    response = await async_client.get(
        "/api/v1/delivery/dispatch-queue",
        headers=token_headers,
    )
    
    assert response.status_code == 200, response.text
    queue_data = response.json()
    
    # Should have 2 orders (only READY_FOR_DISPATCH)
    assert len(queue_data) == 2
    
    # Check first order has required fields
    order_1 = next((o for o in queue_data if o["order_number"] == f"SO-DISP-001-{run_id}"), None)
    assert order_1 is not None
    assert order_1["id"] == str(order_1_id)
    assert order_1["order_number"] == f"SO-DISP-001-{run_id}"
    assert order_1["customer_name"] == "Dispatch Test Client"
    assert order_1["grand_total"] == 1050.0
    assert order_1["ready_at"] is not None  # Should have a timestamp
    
    # Check second order
    order_2 = next((o for o in queue_data if o["order_number"] == f"SO-DISP-002-{run_id}"), None)
    assert order_2 is not None
    assert order_2["id"] == str(order_2_id)
    assert order_2["grand_total"] == 2100.0
    
    # Verify CONFIRMED order is not in the queue
    order_3 = next((o for o in queue_data if o["order_number"] == f"SO-DISP-003-{run_id}"), None)
    assert order_3 is None
