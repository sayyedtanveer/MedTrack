import uuid
from decimal import Decimal


def _build_admin_headers(token_headers: dict) -> dict:
    return {
        "Authorization": token_headers["Authorization"],
        "X-Tenant-ID": token_headers["X-Tenant-ID"],
    }


async def _create_supplier_material_po_and_warehouse(async_client, admin_headers):
    run_id = uuid.uuid4().hex[:8]
    supplier_resp = await async_client.post(
        "/api/v1/suppliers",
        json={"code": f"SUP-{uuid.uuid4().hex[:8]}", "name": "Test Supplier"},
        headers=admin_headers,
    )
    assert supplier_resp.status_code == 201
    supplier_id = supplier_resp.json()["id"]

    location_resp = await async_client.post(
        "/api/v1/inventory/master-data/locations",
        json={
            "name": f"Default Warehouse {run_id}",
            "code": f"WH-{uuid.uuid4().hex[:8]}",
            "type": "warehouse",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert location_resp.status_code == 201
    warehouse_location_id = location_resp.json()["id"]

    material_resp = await async_client.post(
        "/api/v1/inventory/materials",
        json={
            "code": f"MAT-{uuid.uuid4().hex[:8]}",
            "name": f"Test Material {run_id}",
            "description": "Test material",
            "material_type": "raw",
        },
        headers=admin_headers,
    )
    assert material_resp.status_code == 201
    material_id = material_resp.json()["id"]

    po_resp = await async_client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "lines": [{"material_id": material_id, "quantity": 10, "unit_price": 2.5}],
        },
        headers=admin_headers,
    )
    assert po_resp.status_code == 201
    po_id = po_resp.json()["id"]

    return supplier_id, material_id, po_id, warehouse_location_id


async def test_po_receive_creates_grn_and_updates_inventory(async_client, token_headers):
    admin_headers = _build_admin_headers(token_headers)
    supplier_id, material_id, po_id, warehouse_location_id = await _create_supplier_material_po_and_warehouse(async_client, admin_headers)

    send_resp = await async_client.put(f"/api/v1/purchase-orders/{po_id}/send", headers=admin_headers)
    assert send_resp.status_code == 200

    # Receive 5 units for the PO
    receive_resp = await async_client.put(
        f"/api/v1/purchase-orders/{po_id}/receive",
        json={"lines": [{"line_id": await _get_first_po_line_id(async_client, admin_headers, po_id), "quantity": 5}], "warehouse_location_id": warehouse_location_id},
        headers=admin_headers,
    )
    assert receive_resp.status_code == 200

    # Check receipts endpoint returns at least one transaction
    receipts_resp = await async_client.get(f"/api/v1/purchase-orders/{po_id}/receipts", headers=admin_headers)
    assert receipts_resp.status_code == 200
    items = receipts_resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1

    # Verify material current stock increased via stock query
    stock_resp = await async_client.get(f"/api/v1/inventory/materials/{material_id}/stock", headers=admin_headers)
    assert stock_resp.status_code == 200
    current_stock = Decimal(str(stock_resp.json()["current_stock"]))
    assert current_stock >= Decimal("5")


async def test_legacy_grn_reverse_reverses_document_stock(async_client, token_headers):
    admin_headers = _build_admin_headers(token_headers)
    _, material_id, po_id, warehouse_location_id = await _create_supplier_material_po_and_warehouse(
        async_client,
        admin_headers,
    )

    send_resp = await async_client.put(f"/api/v1/purchase-orders/{po_id}/send", headers=admin_headers)
    assert send_resp.status_code == 200

    receive_resp = await async_client.put(
        f"/api/v1/purchase-orders/{po_id}/receive",
        json={
            "lines": [
                {
                    "line_id": await _get_first_po_line_id(async_client, admin_headers, po_id),
                    "quantity": 5,
                }
            ],
            "warehouse_location_id": warehouse_location_id,
        },
        headers=admin_headers,
    )
    assert receive_resp.status_code == 200
    grn_id = receive_resp.json()["grn_id"]

    before_reverse_resp = await async_client.get(
        f"/api/v1/inventory/materials/{material_id}/stock",
        headers=admin_headers,
    )
    assert before_reverse_resp.status_code == 200
    assert Decimal(str(before_reverse_resp.json()["current_stock"])) >= Decimal("5")

    reverse_resp = await async_client.post(f"/api/v1/grn/{grn_id}/reverse", headers=admin_headers)
    assert reverse_resp.status_code == 200, reverse_resp.text
    assert reverse_resp.json()["status"] == "reversed"

    receipts_resp = await async_client.get(
        f"/api/v1/purchase-orders/{po_id}/receipts",
        headers=admin_headers,
    )
    assert receipts_resp.status_code == 200
    assert any(item["id"] == grn_id and item["status"] == "reversed" for item in receipts_resp.json())

    after_reverse_resp = await async_client.get(
        f"/api/v1/inventory/materials/{material_id}/stock",
        headers=admin_headers,
    )
    assert after_reverse_resp.status_code == 200
    assert Decimal(str(after_reverse_resp.json()["current_stock"])) == Decimal("0")


async def _get_first_po_line_id(async_client, admin_headers, po_id):
    po_resp = await async_client.get(f"/api/v1/purchase-orders/{po_id}", headers=admin_headers)
    assert po_resp.status_code == 200
    po_data = po_resp.json()
    return po_data["lines"][0]["id"]
