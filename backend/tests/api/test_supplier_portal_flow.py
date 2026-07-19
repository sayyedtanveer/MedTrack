import uuid

from backend.app.config import settings
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.user_model import UserModel
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
        json={"code": f"SUP-{uuid.uuid4().hex[:8]}", "name": "Portal Supplier"},
        headers=admin_headers,
    )
    assert supplier_resp.status_code == 201
    supplier_id = supplier_resp.json()["id"]

    material_resp = await async_client.post(
        "/api/v1/inventory/materials",
        json={
            "code": f"MAT-{uuid.uuid4().hex[:8]}",
            "name": "Portal Material",
            "description": "Portal test material",
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
            "lines": [{"material_id": material_id, "quantity": 12, "unit_price": 8.5}],
        },
        headers=admin_headers,
    )
    assert po_resp.status_code == 201
    po_id = po_resp.json()["id"]

    send_resp = await async_client.put(
        f"/api/v1/purchase-orders/{po_id}/send",
        headers=admin_headers,
    )
    assert send_resp.status_code == 200

    return supplier_id, po_id


async def _create_supplier_user(async_client, admin_headers, supplier_id):
    user_resp = await async_client.post(
        "/api/v1/users",
        json={
            "email": f"supplier-{uuid.uuid4().hex[:8]}@example.com",
            "first_name": "Portal",
            "last_name": "Supplier",
            "role": "supplier",
            "is_active": True,
            "supplier_id": supplier_id,
        },
        headers=admin_headers,
    )
    assert user_resp.status_code == 201
    return user_resp.json()["id"]


async def test_auth_me_returns_persisted_user_profile(async_client, db_session, token_headers, test_tenant_id, test_user_id):
    supplier_id = uuid.uuid4()
    db_session.add(
        TenantModel(
            id=test_tenant_id,
            name="Auth Profile Tenant",
            slug=f"auth-profile-{uuid.uuid4().hex[:8]}",
            plan="starter",
            is_active=True,
        )
    )
    db_session.add(
        SupplierModel(
            id=supplier_id,
            tenant_id=test_tenant_id,
            code=f"SUP-{uuid.uuid4().hex[:8]}",
            name="Auth Supplier",
        )
    )
    db_session.add(
        UserModel(
            id=test_user_id,
            tenant_id=test_tenant_id,
            email="supplier.profile@example.com",
            hashed_password="not-used-for-auth-me",
            first_name="Supplier",
            last_name="Profile",
            role="admin",
            supplier_id=supplier_id,
            is_active=True,
        )
    )
    await db_session.commit()

    response = await async_client.get("/api/v1/auth/me", headers=token_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "supplier.profile@example.com"
    assert body["user"]["first_name"] == "Supplier"
    assert body["user"]["last_name"] == "Profile"
    assert body["user"]["supplier_id"] == str(supplier_id)
    assert body["tenant"]["id"] == str(test_tenant_id)
    assert body["tenant"]["name"] == "Auth Profile Tenant"


async def test_supplier_portal_flow_lists_and_acknowledges_pos(async_client, token_headers):
    admin_headers = _build_admin_headers(token_headers)
    supplier_id, po_id = await _create_supplier_and_material_and_po(async_client, admin_headers)
    supplier_user_id = await _create_supplier_user(async_client, admin_headers, supplier_id)

    supplier_token = jwt_handler.create_access_token(
        user_id=str(supplier_user_id),
        tenant_id=token_headers["X-Tenant-ID"],
        role="supplier",
        extra_claims={"sid": supplier_id},
    )
    supplier_headers = {
        "Authorization": f"Bearer {supplier_token}",
        "X-Tenant-ID": token_headers["X-Tenant-ID"],
    }

    list_response = await async_client.get("/api/v1/supplier/purchase-orders", headers=supplier_headers)
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == po_id
    assert items[0]["status"] == "sent"

    detail_response = await async_client.get(f"/api/v1/supplier/purchase-orders/{po_id}", headers=supplier_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "sent"

    acknowledge_response = await async_client.put(
        f"/api/v1/supplier/purchase-orders/{po_id}/acknowledge",
        headers=supplier_headers,
    )
    assert acknowledge_response.status_code == 200

    refreshed_detail_response = await async_client.get(
        f"/api/v1/supplier/purchase-orders/{po_id}",
        headers=supplier_headers,
    )
    assert refreshed_detail_response.status_code == 200
    assert refreshed_detail_response.json()["status"] == "acknowledged"


async def test_admin_can_regenerate_supplier_user_temporary_password(async_client, token_headers):
    admin_headers = _build_admin_headers(token_headers)
    supplier_resp = await async_client.post(
        "/api/v1/suppliers",
        json={"code": f"SUP-{uuid.uuid4().hex[:8]}", "name": "Password Reset Supplier"},
        headers=admin_headers,
    )
    assert supplier_resp.status_code == 201
    supplier_id = supplier_resp.json()["id"]
    email = f"supplier-reset-{uuid.uuid4().hex[:8]}@example.com"

    user_resp = await async_client.post(
        "/api/v1/users",
        json={
            "email": email,
            "first_name": "Reset",
            "last_name": "Supplier",
            "role": "supplier",
            "is_active": True,
            "supplier_id": supplier_id,
        },
        headers=admin_headers,
    )
    assert user_resp.status_code == 201
    user_body = user_resp.json()

    reset_resp = await async_client.post(
        f"/api/v1/users/{user_body['id']}/temporary-password",
        headers=admin_headers,
    )
    assert reset_resp.status_code == 200
    reset_body = reset_resp.json()
    assert reset_body["email"] == email
    assert reset_body["supplier_id"] == supplier_id
    assert reset_body["temporary_password"]
    assert reset_body["temporary_password"] != user_body["temporary_password"]

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": reset_body["temporary_password"],
            "tenant_id": token_headers["X-Tenant-ID"],
        },
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["role"] == "supplier"


async def test_supplier_user_can_reset_password_from_main_login_flow(async_client, token_headers):
    admin_headers = _build_admin_headers(token_headers)
    supplier_resp = await async_client.post(
        "/api/v1/suppliers",
        json={"code": f"SUP-{uuid.uuid4().hex[:8]}", "name": "Forgot Password Supplier"},
        headers=admin_headers,
    )
    assert supplier_resp.status_code == 201
    supplier_id = supplier_resp.json()["id"]
    email = f"supplier-forgot-{uuid.uuid4().hex[:8]}@example.com"

    user_resp = await async_client.post(
        "/api/v1/users",
        json={
            "email": email,
            "first_name": "Forgot",
            "last_name": "Supplier",
            "role": "supplier",
            "is_active": True,
            "supplier_id": supplier_id,
        },
        headers=admin_headers,
    )
    assert user_resp.status_code == 201

    request_resp = await async_client.post(
        "/api/v1/forgot-password/request",
        json={"email": email},
    )
    assert request_resp.status_code == 200
    reset_token = request_resp.json()["reset_token"]
    assert reset_token

    new_password = "SupplierReset123!"
    reset_resp = await async_client.post(
        "/api/v1/forgot-password/reset",
        json={"token": reset_token, "new_password": new_password},
    )
    assert reset_resp.status_code == 200

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": new_password,
            "tenant_id": token_headers["X-Tenant-ID"],
        },
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["role"] == "supplier"


async def test_supplier_portal_profile_shipment_invoice_and_payment_views(async_client, token_headers):
    admin_headers = _build_admin_headers(token_headers)
    supplier_id, po_id = await _create_supplier_and_material_and_po(async_client, admin_headers)
    supplier_user_id = await _create_supplier_user(async_client, admin_headers, supplier_id)

    supplier_token = jwt_handler.create_access_token(
        user_id=str(supplier_user_id),
        tenant_id=token_headers["X-Tenant-ID"],
        role="supplier",
        extra_claims={"sid": supplier_id},
    )
    supplier_headers = {
        "Authorization": f"Bearer {supplier_token}",
        "X-Tenant-ID": token_headers["X-Tenant-ID"],
    }

    dashboard_response = await async_client.get("/api/v1/supplier/dashboard", headers=supplier_headers)
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["purchase_orders"]["total"] == 1

    profile_response = await async_client.get("/api/v1/supplier/profile", headers=supplier_headers)
    assert profile_response.status_code == 200
    assert profile_response.json()["id"] == supplier_id

    update_profile_response = await async_client.put(
        "/api/v1/supplier/profile",
        json={
            "contact_person": "Supplier Portal Owner",
            "email": "portal-supplier@example.com",
            "phone": "9000000000",
            "address": "Dock 7, Supplier Industrial Area",
            "gst": "GSTPORTAL123",
            "payment_terms": "Net 30",
        },
        headers=supplier_headers,
    )
    assert update_profile_response.status_code == 200
    assert update_profile_response.json()["profile_completeness"] == 100

    detail_response = await async_client.get(
        f"/api/v1/supplier/purchase-orders/{po_id}",
        headers=supplier_headers,
    )
    assert detail_response.status_code == 200
    po_detail = detail_response.json()
    line = po_detail["lines"][0]

    acknowledge_response = await async_client.put(
        f"/api/v1/supplier/purchase-orders/{po_id}/acknowledge",
        headers=supplier_headers,
    )
    assert acknowledge_response.status_code == 200

    shipment_response = await async_client.post(
        f"/api/v1/supplier/purchase-orders/{po_id}/shipment-notices",
        json={
            "vehicle_number": "MH12AB1234",
            "tracking_number": "ASN-TRACK-1",
            "remarks": "Dispatching against portal E2E PO",
            "lines": [{"po_line_id": line["id"], "quantity": 5, "remarks": "First shipment"}],
        },
        headers=supplier_headers,
    )
    assert shipment_response.status_code == 201
    shipment_body = shipment_response.json()
    assert shipment_body["status"] == "pending_receipt"
    assert shipment_body["purchase_order_id"] == po_id
    assert shipment_body["lines"][0]["received_quantity"] == 5

    receipts_response = await async_client.get("/api/v1/supplier/receipts", headers=supplier_headers)
    assert receipts_response.status_code == 200
    assert receipts_response.json()["items"][0]["id"] == shipment_body["id"]

    invoice_response = await async_client.post(
        "/api/v1/supplier/invoices",
        json={
            "purchase_order_id": po_id,
            "supplier_invoice_ref": "SUP-INV-E2E-001",
            "invoice_date": "2026-05-01",
            "due_date": "2026-05-31",
            "subtotal": 102.0,
            "tax_amount": 18.36,
            "grand_total": 120.36,
            "notes": "Portal E2E supplier invoice",
        },
        headers=supplier_headers,
    )
    assert invoice_response.status_code == 201
    invoice_body = invoice_response.json()
    assert invoice_body["status"] == "PENDING"
    assert invoice_body["purchase_order_id"] == po_id
    assert invoice_body["balance_due"] == 120.36

    invoices_response = await async_client.get("/api/v1/supplier/invoices", headers=supplier_headers)
    assert invoices_response.status_code == 200
    assert invoices_response.json()["items"][0]["id"] == invoice_body["id"]

    invoice_detail_response = await async_client.get(
        f"/api/v1/supplier/invoices/{invoice_body['id']}",
        headers=supplier_headers,
    )
    assert invoice_detail_response.status_code == 200
    assert invoice_detail_response.json()["supplier_invoice_ref"] == "SUP-INV-E2E-001"

    payments_response = await async_client.get("/api/v1/supplier/payments", headers=supplier_headers)
    assert payments_response.status_code == 200
    assert payments_response.json()["items"] == []
