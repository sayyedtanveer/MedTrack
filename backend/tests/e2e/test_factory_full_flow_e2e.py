from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx
import pytest

from backend.app.main import app


BASE = "/api/v1"
TENANT_ID = "b5ef68c4-18be-4fa6-a439-a23c34877550"
ADMIN_EMAIL = "admin.e2e@medtrack-demo.com"
ADMIN_PASSWORD = "E2EAdmin@1234"


class ERPClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.token: str | None = None

    async def call(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        expected: set[int] | None = None,
    ) -> Any:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        response = await self.client.request(
            method,
            BASE + path,
            json=data,
            headers=headers,
            timeout=60,
        )
        payload: Any = None
        if response.content:
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
        if expected and response.status_code not in expected:
            raise AssertionError(
                f"{method} {path} expected {expected} got {response.status_code}: {payload}"
            )
        return payload


def _as_float(value: Any) -> float:
    return float(Decimal(str(value)))


async def _login_admin(client: ERPClient) -> None:
    login = await client.call(
        "POST",
        "/auth/login",
        {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "tenant_id": TENANT_ID},
        {200},
    )
    client.token = login["access_token"]


async def _unit_id(client: ERPClient, run_id: str) -> str:
    units = await client.call("GET", "/inventory/master-data/units", expected={200})
    if units:
        return units[0]["id"]
    unit = await client.call(
        "POST",
        "/inventory/master-data/units",
        {"code": f"EA{run_id[:6]}", "name": "Each", "precision": 2, "is_active": True},
        {201},
    )
    return unit["id"]


async def _warehouse_id(client: ERPClient, run_id: str) -> str:
    locations = await client.call(
        "GET",
        "/inventory/master-data/locations?type=warehouse",
        expected={200},
    )
    if locations:
        return locations[0]["id"]
    warehouse = await client.call(
        "POST",
        "/inventory/master-data/locations",
        {
            "code": f"WH-{run_id}",
            "name": f"E2E Warehouse {run_id}",
            "type": "warehouse",
            "is_active": True,
        },
        {201},
    )
    return warehouse["id"]


async def _create_product_with_bom(
    client: ERPClient,
    *,
    run_id: str,
    unit_id: str,
    warehouse_id: str,
    raw_material_id: str,
) -> tuple[str, str, str, str]:
    template = await client.call(
        "POST",
        "/products/templates",
        {
            "code": f"E2E-FG-{run_id}",
            "name": f"E2E Finished Product {run_id}",
            "description": "Full ERP factory-flow product",
            "base_unit_id": unit_id,
            "attributes": [{"key": "SIZE", "label": "Size", "values": ["STD"]}],
        },
        {201},
    )
    template_id = template["id"]

    variant = await client.call(
        "POST",
        f"/products/templates/{template_id}/variants",
        {
            "attribute_values": {"SIZE": "STD"},
            "base_unit_id": unit_id,
            "standard_cost": 50,
            "selling_price": 120,
        },
        {201},
    )
    variant_id = variant["id"]
    variant_code = variant["code"]

    finished_material = await client.call(
        "POST",
        "/inventory/materials",
        {
            "code": variant_code,
            "name": f"Finished Goods Stock {run_id}",
            "material_type": "finished",
            "description": "Stock item linked to product variant code",
            "base_unit_id": unit_id,
            "location_id": warehouse_id,
            "reorder_level": 0,
            "is_batch_tracked": False,
            "is_serialized": False,
        },
        {201},
    )

    bom = await client.call(
        "POST",
        f"/products/{template_id}/boms",
        {
            "version": f"v{run_id}",
            "valid_from": datetime.now(timezone.utc).isoformat(),
            "template_id": template_id,
            "lines": [
                {
                    "material_id": raw_material_id,
                    "quantity": 2,
                    "unit_id": unit_id,
                    "scrap_percentage": 0,
                }
            ],
        },
        {201},
    )
    activated = await client.call("POST", f"/boms/{bom['id']}/activate", expected={200})
    assert activated["is_active"] is True
    return template_id, variant_id, finished_material["id"], bom["id"]


async def run() -> None:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as raw_client:
            admin = ERPClient(raw_client)
            await _login_admin(admin)

            run_id = uuid.uuid4().hex[:8].upper()
            today = date.today()
            unit_id = await _unit_id(admin, run_id)
            warehouse_id = await _warehouse_id(admin, run_id)

            raw_material = await admin.call(
                "POST",
                "/inventory/materials",
                {
                    "code": f"E2E-RAW-{run_id}",
                    "name": f"E2E Raw Material {run_id}",
                    "material_type": "raw",
                    "description": "Full ERP raw material shortage target",
                    "base_unit_id": unit_id,
                    "location_id": warehouse_id,
                    "reorder_level": 10,
                    "is_batch_tracked": False,
                    "is_serialized": False,
                },
                {201},
            )
            raw_material_id = raw_material["id"]

            template_id, variant_id, finished_material_id, bom_id = await _create_product_with_bom(
                admin,
                run_id=run_id,
                unit_id=unit_id,
                warehouse_id=warehouse_id,
                raw_material_id=raw_material_id,
            )

            raw_stock_before = await admin.call(
                "GET",
                f"/inventory/materials/{raw_material_id}/stock",
                expected={200},
            )
            assert _as_float(raw_stock_before["available_stock"]) == 0

            mrp = await admin.call("POST", "/material-requests/run-mrp", expected={200})
            assert mrp["created"] >= 1
            material_requests = await admin.call(
                "GET",
                "/material-requests?status=open&skip=0&limit=100",
                expected={200},
            )
            request_items = material_requests.get("items", material_requests)
            material_request = next(
                item for item in request_items if item["item_id"] == raw_material_id
            )

            supplier = await admin.call(
                "POST",
                "/suppliers",
                {
                    "code": f"E2E-SUP-{run_id}",
                    "name": f"E2E Supplier {run_id}",
                    "contact_person": "Supplier Portal User",
                    "email": f"supplier-{run_id.lower()}@example.com",
                    "phone": "+10000000000",
                    "address": "Factory procurement lane",
                    "payment_terms": "Net 15",
                },
                {201},
            )
            supplier_id = supplier["id"]

            rfq = await admin.call(
                "POST",
                "/rfq",
                {
                    "title": f"E2E RFQ {run_id}",
                    "material_request_id": material_request["id"],
                    "deadline": (today + timedelta(days=3)).isoformat(),
                    "notes": "Generated by full ERP E2E",
                    "lines": [
                        {
                            "material_id": raw_material_id,
                            "quantity": 10,
                            "description": "Raw shortage replenishment",
                        }
                    ],
                    "supplier_ids": [supplier_id],
                },
                {201},
            )
            rfq_id = rfq["id"]
            assert (await admin.call("POST", f"/rfq/{rfq_id}/send", expected={200}))["status"] == "sent"

            supplier_user = await admin.call(
                "POST",
                "/users",
                {
                    "email": f"supplier-user-{run_id.lower()}@example.com",
                    "first_name": "E2E",
                    "last_name": "Supplier",
                    "role": "supplier",
                    "is_active": True,
                    "supplier_id": supplier_id,
                },
                {201},
            )

            supplier_portal = ERPClient(raw_client)
            supplier_login = await supplier_portal.call(
                "POST",
                "/auth/login",
                {
                    "email": supplier_user["email"],
                    "password": supplier_user["temporary_password"],
                    "tenant_id": TENANT_ID,
                },
                {200},
            )
            supplier_portal.token = supplier_login["access_token"]

            supplier_rfqs = await supplier_portal.call("GET", "/supplier/rfq", expected={200})
            assert any(item["id"] == rfq_id for item in supplier_rfqs)
            quote = await supplier_portal.call(
                "POST",
                f"/supplier/rfq/{rfq_id}/quote",
                {
                    "material_id": raw_material_id,
                    "quantity": 10,
                    "unit_price": 7.5,
                    "valid_until": (today + timedelta(days=10)).isoformat(),
                    "rfq_id": rfq_id,
                },
                {201},
            )
            assert quote["id"]

            rfq_detail = await admin.call("GET", f"/rfq/{rfq_id}", expected={200})
            assert rfq_detail["quotation_details"][supplier_id]["status"] == "submitted"

            awarded = await admin.call(
                "POST",
                f"/rfq/{rfq_id}/award",
                {
                    "supplier_id": supplier_id,
                    "expected_delivery": (today + timedelta(days=5)).isoformat(),
                    "notes": "Awarded by full ERP E2E",
                    "lines": [
                        {"material_id": raw_material_id, "quantity": 10, "unit_price": 7.5}
                    ],
                },
                {200},
            )
            po_id = awarded["po_id"]
            assert await admin.call("PUT", f"/purchase-orders/{po_id}/send", expected={200})

            supplier_pos = await supplier_portal.call(
                "GET",
                "/supplier/purchase-orders",
                expected={200},
            )
            supplier_po_items = supplier_pos["items"] if isinstance(supplier_pos, dict) else supplier_pos
            assert any(item["id"] == po_id for item in supplier_po_items)
            ack = await supplier_portal.call(
                "PUT",
                f"/supplier/purchase-orders/{po_id}/acknowledge",
                expected={200},
            )
            assert ack
            po_acknowledged = await admin.call("GET", f"/purchase-orders/{po_id}", expected={200})
            assert po_acknowledged["status"] == "acknowledged"

            po_line_id = po_acknowledged["lines"][0]["id"]
            grn = await admin.call(
                "POST",
                "/grns",
                {
                    "purchase_order_id": po_id,
                    "warehouse_location_id": warehouse_id,
                    "lines": [{"po_line_id": po_line_id, "received_quantity": 10}],
                    "driver_name": "E2E Driver",
                    "vehicle_number": f"E2E-{run_id}",
                    "remarks": "Full ERP E2E goods receipt",
                },
                {201},
            )
            grn_received = await admin.call(
                "PUT",
                f"/grns/{grn['id']}/receive-in-inventory",
                expected={200},
            )
            assert grn_received["status"] == "received"
            po_after_receipt = await admin.call("GET", f"/purchase-orders/{po_id}", expected={200})
            assert po_after_receipt["status"] == "received"
            po_receipts = await admin.call("GET", f"/purchase-orders/{po_id}/receipts", expected={200})
            assert any(
                receipt["material_id"] == raw_material_id and _as_float(receipt["quantity"]) == 10
                for receipt in po_receipts
            )
            fulfilled_request = await admin.call(
                "GET",
                f"/material-requests/{material_request['id']}",
                expected={200},
            )
            assert fulfilled_request["status"] == "fulfilled"
            assert _as_float(fulfilled_request["fulfilled_quantity"]) >= 10

            raw_stock_after = await admin.call(
                "GET",
                f"/inventory/materials/{raw_material_id}/stock",
                expected={200},
            )
            assert _as_float(raw_stock_after["available_stock"]) >= 10

            work_order = await admin.call(
                "POST",
                "/work-orders",
                {
                    "product_id": variant_id,
                    "bom_id": bom_id,
                    "planned_quantity": 1,
                    "start_date": today.isoformat(),
                    "due_date": (today + timedelta(days=7)).isoformat(),
                    "priority": "NORMAL",
                    "notes": "Full ERP E2E work order",
                },
                {201},
            )
            work_order_id = work_order["id"]
            assert (await admin.call("POST", f"/work-orders/{work_order_id}/release", {}, {200}))["status"] == "RELEASED"
            assert (await admin.call("POST", f"/work-orders/{work_order_id}/start", {}, {200}))["status"] == "IN_PROGRESS"
            issued = await admin.call(
                "POST",
                f"/work-orders/{work_order_id}/issue-materials",
                {"material_id": raw_material_id, "quantity": 2, "unit_id": unit_id},
                {200},
            )
            assert issued["message"]
            material_consumption = await admin.call(
                "GET",
                f"/work-orders/{work_order_id}/material-consumption",
                expected={200},
            )
            assert any(
                item["material_id"] == raw_material_id and _as_float(item["quantity"]) == 2
                for item in material_consumption
            )
            raw_stock_after_issue = await admin.call(
                "GET",
                f"/inventory/materials/{raw_material_id}/stock",
                expected={200},
            )
            assert _as_float(raw_stock_after_issue["available_stock"]) == 8
            produced = await admin.call(
                "POST",
                f"/work-orders/{work_order_id}/record-production",
                {"produced_quantity": 1, "scrap_quantity": 0, "notes": "Full ERP E2E output"},
                {200},
            )
            assert produced["message"]
            assert (await admin.call("POST", f"/work-orders/{work_order_id}/complete", {}, {200}))["status"] == "COMPLETED"
            assert (await admin.call("POST", f"/work-orders/{work_order_id}/close", {}, {200}))["status"] == "CLOSED"

            fg_stock_after_production = await admin.call(
                "GET",
                f"/inventory/materials/{finished_material_id}/stock",
                expected={200},
            )
            assert _as_float(fg_stock_after_production["available_stock"]) >= 1

            client = await admin.call(
                "POST",
                "/sales/clients",
                {
                    "code": f"E2E-CLI-{run_id}",
                    "name": f"E2E Client {run_id}",
                    "email": f"client-{run_id.lower()}@example.com",
                    "phone": "+10000000001",
                    "address": "Client delivery address",
                    "credit_limit": "10000",
                    "payment_terms_days": 30,
                },
                {201},
            )
            price_list = await admin.call(
                "POST",
                "/sales/price-lists",
                {
                    "name": f"E2E Price List {run_id}",
                    "is_default": True,
                    "valid_from": today.isoformat(),
                    "valid_to": (today + timedelta(days=90)).isoformat(),
                },
                {201},
            )
            await admin.call(
                "POST",
                f"/sales/price-lists/{price_list['id']}/lines",
                {"product_id": variant_id, "product_type": "variant", "unit_price": "120"},
                {201},
            )
            sales_order = await admin.call(
                "POST",
                "/sales/orders",
                {
                    "client_id": client["id"],
                    "order_date": today.isoformat(),
                    "delivery_date": (today + timedelta(days=7)).isoformat(),
                    "notes": "Full ERP E2E sales order",
                },
                {201},
            )
            order_with_line = await admin.call(
                "POST",
                f"/sales/orders/{sales_order['id']}/lines",
                {
                    "product_id": variant_id,
                    "product_type": "variant",
                    "uom_id": unit_id,
                    "quantity": 1,
                    "tax_rate": 0,
                },
                {201},
            )
            sales_line_id = order_with_line["lines"][0]["id"]
            confirmed = await admin.call(
                "POST",
                f"/sales/orders/{sales_order['id']}/confirm",
                {"confirmed_by": "Full ERP E2E"},
                {200},
            )
            assert confirmed["status"] == "READY"
            assert _as_float(confirmed["lines"][0]["allocated_quantity"]) == 1

            shipped = await admin.call(
                "POST",
                f"/sales/orders/{sales_order['id']}/ship",
                {"line_shipments": {sales_line_id: 1}, "shipped_by": "Full ERP E2E"},
                {200},
            )
            assert shipped["status"] == "SHIPPED"
            delivered = await admin.call(
                "POST",
                f"/sales/orders/{sales_order['id']}/deliver",
                expected={200},
            )
            assert delivered["status"] == "DELIVERED"

            invoice = await admin.call(
                "POST",
                "/finance/invoices/from-so",
                {
                    "sales_order_id": sales_order["id"],
                    "notes": "Full ERP E2E invoice from delivered order",
                    "terms": "Net 30",
                },
                {201},
            )
            assert invoice["sales_order_id"] == sales_order["id"]
            assert invoice["client_id"] == client["id"]
            assert len(invoice["lines"]) == 1

            fg_stock_after_ship = await admin.call(
                "GET",
                f"/inventory/materials/{finished_material_id}/stock",
                expected={200},
            )
            assert _as_float(fg_stock_after_ship["available_stock"]) == 0

            audit = await admin.call("GET", "/audit-logs?limit=200", expected={200})
            audit_actions = {item["action"] for item in audit["items"]}
            expected_audit_actions = {
                "SUPPLIER_CREATED",
                "SUPPLIER_USER_CREATED",
                "MRP_RUN",
                "RFQ_CREATED",
                "RFQ_SENT",
                "QUOTE_SUBMITTED",
                "RFQ_AWARDED",
                "GRN_CREATED",
                "GRN_RECEIVED",
            }
            missing_audit_actions = expected_audit_actions - audit_actions
            assert not missing_audit_actions, f"Missing audit actions: {missing_audit_actions}"

            print("FULL_FACTORY_ERP_FLOW_ASGI_E2E_PASSED")
            print(f"template_id={template_id}")
            print(f"variant_id={variant_id}")
            print(f"raw_material_id={raw_material_id}")
            print(f"finished_material_id={finished_material_id}")
            print(f"bom_id={bom_id}")
            print(f"material_request_id={material_request['id']}")
            print(f"rfq_id={rfq_id}")
            print(f"supplier_id={supplier_id}")
            print(f"po_id={po_id}")
            print(f"grn_id={grn['id']}")
            print(f"work_order_id={work_order_id}")
            print(f"sales_order_id={sales_order['id']}")
            print(f"invoice_id={invoice['id']}")
            print(f"supplier_login_email={supplier_user['email']}")
            print(f"supplier_login_password={supplier_user['temporary_password']}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_factory_erp_flow_asgi_e2e() -> None:
    await run()


if __name__ == "__main__":
    asyncio.run(run())
