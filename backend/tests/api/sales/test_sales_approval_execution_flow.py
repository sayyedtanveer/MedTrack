from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.config import settings
from backend.app.infrastructure.persistence.models.bom_model import BOMLineModel, BOMModel
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.finance_models import NotificationModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderLineModel, PurchaseOrderModel
from backend.app.infrastructure.persistence.models.sales_models import ClientModel, PriceListLineModel, PriceListModel, SalesOrderModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel, SupplierPriceHistoryModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderMaterialModel, WorkOrderModel
from backend.app.infrastructure.security.jwt_handler import JWTHandler
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher


_jwt = JWTHandler(
    secret_key=settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
    expiry_minutes=settings.jwt_expiry_minutes,
)
_hasher = BcryptPasswordHasher()


def _headers(user_id: uuid.UUID, tenant_id: uuid.UUID, role: str, *, client_id: uuid.UUID | None = None) -> dict[str, str]:
    extra_claims = {"cid": str(client_id)} if client_id else None
    token = _jwt.create_access_token(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        role=role,
        extra_claims=extra_claims,
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}


async def _seed_tenant_user_unit_material(db_session, tenant_id: uuid.UUID, admin_id: uuid.UUID):
    now = datetime.now(timezone.utc)
    run_id = uuid.uuid4().hex[:8]
    manager_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    product_id = uuid.uuid4()

    db_session.add(
        UserModel(
            id=manager_id,
            tenant_id=tenant_id,
            email=f"manager-{run_id}@example.com",
            hashed_password=_hasher.hash("Password123!"),
            first_name="Manager",
            last_name="Approver",
            role="manager",
            is_active=True,
            is_deleted=False,
        )
    )
    db_session.add(
        UnitOfMeasureModel(
            id=unit_id,
            tenant_id=tenant_id,
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
        MaterialModel(
            id=product_id,
            tenant_id=tenant_id,
            code=f"FG-{run_id}",
            name="Finished approval test item",
            material_type="finished",
            base_unit_id=unit_id,
            current_cost=Decimal("10"),
            current_stock=Decimal("5"),
            reserved_stock=Decimal("0"),
            reorder_level=Decimal("0"),
            is_active=True,
            is_deleted=False,
        )
    )
    await db_session.commit()
    return run_id, manager_id, unit_id, product_id


async def _seed_price_list(db_session, tenant_id: uuid.UUID, product_id: uuid.UUID, run_id: str, unit_price: Decimal = Decimal("25")):
    price_list = PriceListModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=f"Portal Catalog {run_id}",
        is_default=True,
        valid_from=date.today(),
        valid_to=date.today() + timedelta(days=30),
        is_active=True,
        is_deleted=False,
    )
    db_session.add(price_list)
    await db_session.flush()
    db_session.add(
        PriceListLineModel(
            id=uuid.uuid4(),
            price_list_id=price_list.id,
            product_id=product_id,
            product_type="variant",
            unit_price=unit_price,
        )
    )
    await db_session.commit()
    return price_list.id


async def _seed_variant_bom_shortage_flow(db_session, tenant_id: uuid.UUID):
    now = datetime.now(timezone.utc)
    run_id = uuid.uuid4().hex[:8]
    manager_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    raw_material_id = uuid.uuid4()
    finished_material_id = uuid.uuid4()
    template_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    bom_id = uuid.uuid4()
    supplier_id = uuid.uuid4()

    db_session.add_all(
        [
            UserModel(
                id=manager_id,
                tenant_id=tenant_id,
                email=f"manager-shortage-{run_id}@example.com",
                hashed_password=_hasher.hash("Password123!"),
                first_name="Manager",
                last_name="Planner",
                role="manager",
                is_active=True,
                is_deleted=False,
            ),
            UnitOfMeasureModel(
                id=unit_id,
                tenant_id=tenant_id,
                code=f"EA{run_id[:6]}",
                name="Each",
                precision=2,
                is_active=True,
                created_at=now,
                updated_at=now,
                is_deleted=False,
            ),
            MaterialModel(
                id=raw_material_id,
                tenant_id=tenant_id,
                code=f"RAW-{run_id}",
                name="Shortage Raw Material",
                material_type="raw",
                base_unit_id=unit_id,
                current_cost=Decimal("7.5"),
                current_stock=Decimal("1"),
                reserved_stock=Decimal("0"),
                reorder_level=Decimal("0"),
                is_active=True,
                is_deleted=False,
            ),
            MaterialModel(
                id=finished_material_id,
                tenant_id=tenant_id,
                code=f"FG-{run_id}",
                name="Shortage Finished Good",
                material_type="finished",
                base_unit_id=unit_id,
                current_cost=Decimal("25"),
                current_stock=Decimal("0"),
                reserved_stock=Decimal("0"),
                reorder_level=Decimal("0"),
                is_active=True,
                is_deleted=False,
            ),
            ItemTemplateModel(
                id=template_id,
                tenant_id=tenant_id,
                code=f"TPL-{run_id}",
                name="Shortage Template",
                description="Template for shortage flow",
                base_unit_id=unit_id,
                attributes=[],
                status="ACTIVE",
                is_active=True,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
            ItemVariantModel(
                id=variant_id,
                tenant_id=tenant_id,
                template_id=template_id,
                code=f"VAR-{run_id}",
                name="Shortage Variant",
                variant_key=f"DEFAULT-{run_id}",
                attribute_values={},
                base_unit_id=unit_id,
                material_id=finished_material_id,
                standard_cost=Decimal("25"),
                selling_price=Decimal("40"),
                is_active=True,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
            BOMModel(
                id=bom_id,
                tenant_id=tenant_id,
                variant_id=variant_id,
                template_id=None,
                version="v1",
                is_active=True,
                valid_from=now,
                valid_to=None,
                created_by=manager_id,
                approved_by=manager_id,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
            BOMLineModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                bom_id=bom_id,
                material_id=raw_material_id,
                template_id=None,
                variant_id=None,
                quantity=Decimal("2"),
                scrap_percentage=Decimal("0"),
                unit_id=unit_id,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
            SupplierModel(
                id=supplier_id,
                tenant_id=tenant_id,
                code=f"SUP-{run_id}",
                name="Preferred Supplier",
                is_active=True,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
            SupplierPriceHistoryModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                supplier_id=supplier_id,
                material_id=raw_material_id,
                unit_price=Decimal("7.5"),
                effective_from=date.today(),
                created_at=now,
            ),
        ]
    )
    await db_session.commit()
    return {
        "run_id": run_id,
        "manager_id": manager_id,
        "unit_id": unit_id,
        "raw_material_id": raw_material_id,
        "finished_material_id": finished_material_id,
        "variant_id": variant_id,
        "bom_id": bom_id,
        "supplier_id": supplier_id,
    }


@pytest.mark.asyncio
async def test_admin_order_requires_approval_then_allocates_inventory(
    async_client,
    db_session,
    token_headers,
    test_tenant_id,
    test_user_id,
):
    run_id, manager_id, unit_id, product_id = await _seed_tenant_user_unit_material(
        db_session,
        test_tenant_id,
        test_user_id,
    )

    client_resp = await async_client.post(
        "/api/v1/sales/clients",
        headers=token_headers,
        json={
            "code": f"CLI-{run_id}",
            "name": "Approval Flow Client",
            "email": f"client-{run_id}@example.com",
            "credit_limit": "1000",
            "payment_terms_days": 30,
        },
    )
    assert client_resp.status_code == 201, client_resp.text
    client_id = client_resp.json()["id"]

    price_list_resp = await async_client.post(
        "/api/v1/sales/price-lists",
        headers=token_headers,
        json={
            "name": f"Approval Price List {run_id}",
            "is_default": True,
            "valid_from": date.today().isoformat(),
            "valid_to": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert price_list_resp.status_code == 201, price_list_resp.text
    price_list_id = price_list_resp.json()["id"]

    price_line_resp = await async_client.post(
        f"/api/v1/sales/price-lists/{price_list_id}/lines",
        headers=token_headers,
        json={"product_id": str(product_id), "product_type": "variant", "unit_price": "25"},
    )
    assert price_line_resp.status_code == 201, price_line_resp.text

    order_resp = await async_client.post(
        "/api/v1/sales/orders",
        headers=token_headers,
        json={
            "client_id": client_id,
            "order_date": date.today().isoformat(),
            "delivery_date": (date.today() + timedelta(days=7)).isoformat(),
            "notes": "Approval flow order",
        },
    )
    assert order_resp.status_code == 201, order_resp.text
    order = order_resp.json()
    assert order["status"] == "DRAFT"
    assert order["approver_id"]

    line_resp = await async_client.post(
        f"/api/v1/sales/orders/{order['id']}/lines",
        headers=token_headers,
        json={
            "product_id": str(product_id),
            "product_type": "variant",
            "uom_id": str(unit_id),
            "quantity": "2",
            "tax_rate": "0",
        },
    )
    assert line_resp.status_code == 201, line_resp.text

    submitted_resp = await async_client.post(
        f"/api/v1/sales/orders/{order['id']}/submit-approval",
        headers=token_headers,
        json={"notes": "Please approve"},
    )
    assert submitted_resp.status_code == 200, submitted_resp.text
    assert submitted_resp.json()["status"] == "PENDING_APPROVAL"

    worker_resp = await async_client.post(
        f"/api/v1/sales/orders/{order['id']}/approve",
        headers=_headers(uuid.uuid4(), test_tenant_id, "worker"),
        json={},
    )
    assert worker_resp.status_code == 403

    approved_resp = await async_client.post(
        f"/api/v1/sales/orders/{order['id']}/approve",
        headers=_headers(manager_id, test_tenant_id, "manager"),
        json={"notes": "Approved"},
    )
    assert approved_resp.status_code == 200, approved_resp.text
    approved = approved_resp.json()
    assert approved["status"] == "READY"
    assert approved["approved_at"]
    assert Decimal(str(approved["lines"][0]["allocated_quantity"])) == Decimal("2")

    material = await db_session.get(MaterialModel, product_id)
    assert Decimal(str(material.reserved_stock)) == Decimal("2.0000")


@pytest.mark.asyncio
async def test_client_order_creation_is_tenant_client_scoped(
    async_client,
    db_session,
    test_tenant_id,
    test_user_id,
):
    run_id, manager_id, unit_id, product_id = await _seed_tenant_user_unit_material(
        db_session,
        test_tenant_id,
        test_user_id,
    )
    client_id = uuid.uuid4()
    other_client_id = uuid.uuid4()
    client_user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    db_session.add_all(
        [
            ClientModel(
                id=client_id,
                tenant_id=test_tenant_id,
                code=f"PORTAL-{run_id}",
                name="Portal Client",
                email=f"portal-{run_id}@example.com",
                credit_limit=Decimal("1000"),
                credit_used=Decimal("0"),
                payment_terms_days=30,
                is_active=True,
                is_deleted=False,
            ),
            ClientModel(
                id=other_client_id,
                tenant_id=test_tenant_id,
                code=f"OTHER-{run_id}",
                name="Other Client",
                credit_limit=Decimal("1000"),
                credit_used=Decimal("0"),
                payment_terms_days=30,
                is_active=True,
                is_deleted=False,
            ),
            UserModel(
                id=client_user_id,
                tenant_id=test_tenant_id,
                email=f"portal-user-{run_id}@example.com",
                hashed_password=_hasher.hash("Password123!"),
                first_name="Portal",
                last_name="User",
                role="client",
                client_id=client_id,
                is_active=True,
                is_deleted=False,
            ),
            SalesOrderModel(
                id=uuid.uuid4(),
                tenant_id=test_tenant_id,
                client_id=other_client_id,
                order_number=f"SO-{run_id}-OTHER",
                order_date=date.today().isoformat(),
                delivery_date=(date.today() + timedelta(days=5)).isoformat(),
                status="DRAFT",
                payment_status="PENDING",
                subtotal=0,
                discount_amount=0,
                tax_amount=0,
                grand_total=0,
                created_by="test",
                is_active=True,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await db_session.commit()
    await _seed_price_list(db_session, test_tenant_id, product_id, run_id)

    client_headers = _headers(client_user_id, test_tenant_id, "client", client_id=client_id)
    catalog_resp = await async_client.get("/api/v1/client/catalog", headers=client_headers)
    assert catalog_resp.status_code == 200, catalog_resp.text
    catalog = catalog_resp.json()
    assert catalog[0]["product_id"] == str(product_id)
    assert catalog[0]["uom_id"] == str(unit_id)
    assert catalog[0]["unit_price"] == 25.0

    create_resp = await async_client.post(
        "/api/v1/client/orders",
        headers=client_headers,
        json={
            "delivery_date": (date.today() + timedelta(days=7)).isoformat(),
            "notes": "Client portal order",
            "lines": [
                {
                    "product_id": str(product_id),
                    "product_type": "variant",
                    "uom_id": str(unit_id),
                    "quantity": "1",
                    "unit_price": "25",
                    "tax_rate": "0",
                }
            ],
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["status"] == "PENDING_APPROVAL"
    assert created["client_id"] == str(client_id)
    assert created["approver_id"]

    list_resp = await async_client.get("/api/v1/client/orders", headers=client_headers)
    assert list_resp.status_code == 200, list_resp.text
    visible_client_ids = {item["client_id"] for item in list_resp.json()["items"]}
    assert visible_client_ids == {str(client_id)}

    admin_headers = _headers(test_user_id, test_tenant_id, "admin")
    sales_list_resp = await async_client.get(
        f"/api/v1/sales/orders?client_id={client_id}",
        headers=admin_headers,
    )
    assert sales_list_resp.status_code == 200, sales_list_resp.text
    listed_order = sales_list_resp.json()["items"][0]
    assert listed_order["client_name"] == "Portal Client"
    assert listed_order["item_summary"].startswith("Finished approval test item x1")

    detail_resp = await async_client.get(
        f"/api/v1/sales/orders/{created['id']}",
        headers=admin_headers,
    )
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()
    assert detail["client_name"] == "Portal Client"
    assert detail["lines"][0]["product_name"] == "Finished approval test item"
    assert detail["lines"][0]["uom_code"] == f"EA{run_id[:6]}"

    notifications = (
        await db_session.execute(
            select(NotificationModel).where(
                NotificationModel.tenant_id == test_tenant_id,
                NotificationModel.reference_type == "sales_order",
                NotificationModel.reference_id == uuid.UUID(created["id"]),
                NotificationModel.type == "CLIENT_ORDER_PENDING_APPROVAL",
            )
        )
    ).scalars().all()
    assert notifications
    assert any("Portal Client" in notification.message for notification in notifications)
    assert any("Finished approval test item x1" in notification.message for notification in notifications)


@pytest.mark.asyncio
async def test_sales_shortage_uses_variant_material_mapping_and_creates_linked_work_order(
    async_client,
    db_session,
    token_headers,
    test_tenant_id,
):
    seeded = await _seed_variant_bom_shortage_flow(db_session, test_tenant_id)
    run_id = seeded["run_id"]

    client_resp = await async_client.post(
        "/api/v1/sales/clients",
        headers=token_headers,
        json={
            "code": f"CLI-SHORT-{run_id}",
            "name": "Shortage Flow Client",
            "email": f"shortage-{run_id}@example.com",
            "credit_limit": "5000",
            "payment_terms_days": 30,
        },
    )
    assert client_resp.status_code == 201, client_resp.text
    client_id = client_resp.json()["id"]

    price_list_resp = await async_client.post(
        "/api/v1/sales/price-lists",
        headers=token_headers,
        json={
            "name": f"Shortage Price List {run_id}",
            "is_default": True,
            "valid_from": date.today().isoformat(),
            "valid_to": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert price_list_resp.status_code == 201, price_list_resp.text
    price_list_id = price_list_resp.json()["id"]

    price_line_resp = await async_client.post(
        f"/api/v1/sales/price-lists/{price_list_id}/lines",
        headers=token_headers,
        json={
            "product_id": str(seeded["variant_id"]),
            "product_type": "variant",
            "unit_price": "40",
        },
    )
    assert price_line_resp.status_code == 201, price_line_resp.text

    order_resp = await async_client.post(
        "/api/v1/sales/orders",
        headers=token_headers,
        json={
            "client_id": client_id,
            "order_date": date.today().isoformat(),
            "delivery_date": (date.today() + timedelta(days=10)).isoformat(),
            "notes": "Trigger shortage production",
        },
    )
    assert order_resp.status_code == 201, order_resp.text
    order = order_resp.json()

    line_resp = await async_client.post(
        f"/api/v1/sales/orders/{order['id']}/lines",
        headers=token_headers,
        json={
            "product_id": str(seeded["variant_id"]),
            "product_type": "variant",
            "uom_id": str(seeded["unit_id"]),
            "quantity": "3",
            "tax_rate": "0",
        },
    )
    assert line_resp.status_code == 201, line_resp.text
    order_line_id = line_resp.json()["lines"][0]["id"]

    submit_resp = await async_client.post(
        f"/api/v1/sales/orders/{order['id']}/submit-approval",
        headers=token_headers,
        json={"notes": "Route to approval"},
    )
    assert submit_resp.status_code == 200, submit_resp.text

    approve_resp = await async_client.post(
        f"/api/v1/sales/orders/{order['id']}/approve",
        headers=_headers(seeded["manager_id"], test_tenant_id, "manager"),
        json={"notes": "Approve shortage order"},
    )
    assert approve_resp.status_code == 200, approve_resp.text
    approved = approve_resp.json()
    assert approved["status"] == "PRODUCTION"
    approved_line = approved["lines"][0]
    assert approved_line["work_order_id"]
    assert Decimal(str(approved_line["allocated_quantity"])) == Decimal("0")
    assert Decimal(str(approved_line["backorder_quantity"])) == Decimal("3")
    assert Decimal(str(approved_line["shortfall_quantity"])) == Decimal("3")
    assert approved_line["production_required"] is True

    work_order = await db_session.get(WorkOrderModel, uuid.UUID(approved_line["work_order_id"]))
    assert work_order is not None
    assert work_order.sales_order_id == uuid.UUID(order["id"])
    assert work_order.sales_order_line_id == uuid.UUID(order_line_id)
    assert work_order.product_id == seeded["variant_id"]

    material_rows = (
        await db_session.execute(
            select(WorkOrderMaterialModel).where(WorkOrderMaterialModel.work_order_id == work_order.id)
        )
    ).scalars().all()
    assert len(material_rows) == 1
    assert material_rows[0].material_id == seeded["raw_material_id"]
    assert Decimal(str(material_rows[0].required_quantity)) == Decimal("6")

    po = (
        await db_session.execute(
            select(PurchaseOrderModel).where(
                PurchaseOrderModel.tenant_id == test_tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
            )
        )
    ).scalars().first()
    assert po is not None
    assert po.supplier_id == seeded["supplier_id"]

    po_line = (
        await db_session.execute(
            select(PurchaseOrderLineModel).where(PurchaseOrderLineModel.purchase_order_id == po.id)
        )
    ).scalars().one()
    assert po_line.material_id == seeded["raw_material_id"]
    assert Decimal(str(po_line.quantity)) == Decimal("5")
