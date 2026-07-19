import uuid
from backend.app.config import settings
from backend.app.infrastructure.security.jwt_handler import JWTHandler

jwt_handler = JWTHandler(
    secret_key=settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
    expiry_minutes=settings.jwt_expiry_minutes,
)


def _build_admin_headers(token_headers: dict) -> dict:
    return {
        "Authorization": token_headers["Authorization"],
        "X-Tenant-ID": token_headers["X-Tenant-ID"],
    }


async def _create_supplier_and_material_and_po(async_client, admin_headers):
    supplier_resp = await async_client.post(
        "/api/v1/suppliers",
        json={"code": f"SUP-{uuid.uuid4().hex[:8]}", "name": "Test Supplier"},
        headers=admin_headers,
    )
    assert supplier_resp.status_code == 201
    supplier_id = supplier_resp.json()["id"]

    material_resp = await async_client.post(
        "/api/v1/inventory/materials",
        json={
            "code": f"MAT-{uuid.uuid4().hex[:8]}",
            "name": "Test Material",
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
            "lines": [{"material_id": material_id, "quantity": 10, "unit_price": 5.5}],
        },
        headers=admin_headers,
    )
    assert po_resp.status_code == 201
    po_id = po_resp.json()["id"]

    return supplier_id, material_id, po_id


async def _create_supplier_user(async_client, admin_headers, supplier_id):
    user_email = f"supplier-{uuid.uuid4().hex[:8]}@example.com"
    user_resp = await async_client.post(
        "/api/v1/users",
        json={
            "email": user_email,
            "first_name": "Supplier",
            "last_name": "User",
            "role": "supplier",
            "is_active": True,
            "supplier_id": supplier_id,
        },
        headers=admin_headers,
    )
    assert user_resp.status_code == 201
    return user_resp.json()["id"]


async def test_supplier_can_submit_quotation_for_their_po(async_client, token_headers):
    admin_headers = _build_admin_headers(token_headers)
    supplier_id, material_id, po_id = await _create_supplier_and_material_and_po(async_client, admin_headers)

    supplier_user_id = await _create_supplier_user(async_client, admin_headers, supplier_id)
    supplier_token = jwt_handler.create_access_token(
        user_id=str(supplier_user_id),
        tenant_id=token_headers["X-Tenant-ID"],
        role="supplier",
        extra_claims={"sid": supplier_id},
    )
    headers = {"Authorization": f"Bearer {supplier_token}", "X-Tenant-ID": token_headers["X-Tenant-ID"]}

    body = {
        "material_id": material_id,
        "quantity": 10,
        "unit_price": 5.5,
        "purchase_order_id": po_id,
    }
    resp = await async_client.post("/api/v1/supplier/quotations", json=body, headers=headers)

    assert resp.status_code == 201
    assert "id" in resp.json()


async def test_supplier_cannot_submit_for_other_supplier_po(async_client, token_headers):
    admin_headers = _build_admin_headers(token_headers)
    supplier_a_resp = await async_client.post(
        "/api/v1/suppliers",
        json={"code": f"SUP-A-{uuid.uuid4().hex[:8]}", "name": "Supplier A"},
        headers=admin_headers,
    )
    supplier_b_resp = await async_client.post(
        "/api/v1/suppliers",
        json={"code": f"SUP-B-{uuid.uuid4().hex[:8]}", "name": "Supplier B"},
        headers=admin_headers,
    )
    assert supplier_a_resp.status_code == 201
    assert supplier_b_resp.status_code == 201
    supplier_a = supplier_a_resp.json()["id"]
    supplier_b = supplier_b_resp.json()["id"]

    material_resp = await async_client.post(
        "/api/v1/inventory/materials",
        json={
            "code": f"MAT-{uuid.uuid4().hex[:8]}",
            "name": "Test Material",
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
            "supplier_id": supplier_b,
            "lines": [{"material_id": material_id, "quantity": 5, "unit_price": 4.0}],
        },
        headers=admin_headers,
    )
    assert po_resp.status_code == 201
    po_b = po_resp.json()["id"]

    supplier_a_user_id = await _create_supplier_user(async_client, admin_headers, supplier_a)
    supplier_token = jwt_handler.create_access_token(
        user_id=str(supplier_a_user_id),
        tenant_id=token_headers["X-Tenant-ID"],
        role="supplier",
        extra_claims={"sid": supplier_a},
    )
    headers = {"Authorization": f"Bearer {supplier_token}", "X-Tenant-ID": token_headers["X-Tenant-ID"]}

    body = {
        "material_id": material_id,
        "quantity": 5,
        "unit_price": 4.0,
        "purchase_order_id": po_b,
    }
    resp = await async_client.post("/api/v1/supplier/quotations", json=body, headers=headers)

    assert resp.status_code == 404


async def test_supplier_invalid_po_id_returns_400(async_client, token_headers):
    admin_headers = _build_admin_headers(token_headers)
    supplier_resp = await async_client.post(
        "/api/v1/suppliers",
        json={"code": f"SUP-{uuid.uuid4().hex[:8]}", "name": "Test Supplier"},
        headers=admin_headers,
    )
    assert supplier_resp.status_code == 201
    supplier_id = supplier_resp.json()["id"]

    material_resp = await async_client.post(
        "/api/v1/inventory/materials",
        json={
            "code": f"MAT-{uuid.uuid4().hex[:8]}",
            "name": "Test Material",
            "description": "Test material",
            "material_type": "raw",
        },
        headers=admin_headers,
    )
    assert material_resp.status_code == 201
    material_id = material_resp.json()["id"]

    supplier_user_id = await _create_supplier_user(async_client, admin_headers, supplier_id)
    supplier_token = jwt_handler.create_access_token(
        user_id=str(supplier_user_id),
        tenant_id=token_headers["X-Tenant-ID"],
        role="supplier",
        extra_claims={"sid": supplier_id},
    )
    headers = {"Authorization": f"Bearer {supplier_token}", "X-Tenant-ID": token_headers["X-Tenant-ID"]}

    body = {
        "material_id": material_id,
        "quantity": 1,
        "unit_price": 1.0,
        "purchase_order_id": "not-a-uuid",
    }
    resp = await async_client.post("/api/v1/supplier/quotations", json=body, headers=headers)

    assert resp.status_code == 400
