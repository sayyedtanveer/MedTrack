from __future__ import annotations

import uuid

import pytest

from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.user_model import UserModel


def _headers(container, tenant_id: uuid.UUID, user_id: uuid.UUID, role: str) -> dict[str, str]:
    token = container.jwt_handler.create_access_token(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        role=role,
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
    }


@pytest.mark.asyncio
async def test_admin_can_manage_custom_role_and_permissions(async_client, db_session, test_container):
    tenant_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    password = "TempPassword123!"

    db_session.add(
        TenantModel(
            id=tenant_id,
            name="Dynamic RBAC Tenant",
            slug=f"dynamic-rbac-{uuid.uuid4().hex[:8]}",
            plan="starter",
            is_active=True,
            is_deleted=False,
        )
    )
    db_session.add(
        UserModel(
            id=admin_id,
            tenant_id=tenant_id,
            email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
            hashed_password=test_container.password_hasher.hash(password),
            first_name="Admin",
            last_name="User",
            role="admin",
            is_active=True,
            is_deleted=False,
        )
    )
    await db_session.commit()

    admin_headers = _headers(test_container, tenant_id, admin_id, "admin")

    roles_resp = await async_client.get("/api/v1/admin/rbac/roles", headers=admin_headers)
    assert roles_resp.status_code == 200
    roles = roles_resp.json()["roles"]
    assert "admin" in roles
    assert "*" in roles["admin"]["permissions"]

    create_role_resp = await async_client.post(
        "/api/v1/admin/rbac/roles",
        headers=admin_headers,
        json={
            "name": "sales_reviewer",
            "label": "Sales Reviewer",
            "description": "Can view sales orders only",
            "permissions": ["sales:view_orders"],
        },
    )
    assert create_role_resp.status_code == 201
    assert create_role_resp.json()["permissions"] == ["sales:view_orders"]

    email = f"sales-reviewer-{uuid.uuid4().hex[:8]}@example.com"
    user_resp = await async_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": email,
            "first_name": "Sales",
            "last_name": "Reviewer",
            "role": "sales_reviewer",
            "is_active": True,
        },
    )
    assert user_resp.status_code == 201
    user_body = user_resp.json()

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": user_body["temporary_password"],
            "tenant_id": str(tenant_id),
        },
    )
    assert login_resp.status_code == 200
    custom_headers = {
        "Authorization": f"Bearer {login_resp.json()['access_token']}",
        "X-Tenant-ID": str(tenant_id),
    }

    me_resp = await async_client.get("/api/v1/auth/me", headers=custom_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["user"]["role"] == "sales_reviewer"
    assert me_resp.json()["permissions"] == ["sales:view_orders"]

    denied_resp = await async_client.get("/api/v1/admin/rbac/roles", headers=custom_headers)
    assert denied_resp.status_code == 403

    update_role_resp = await async_client.put(
        "/api/v1/admin/rbac/roles/sales_reviewer/permissions",
        headers=admin_headers,
        json={"permissions": ["sales:view_orders", "rbac:read"]},
    )
    assert update_role_resp.status_code == 200
    assert update_role_resp.json()["permissions"] == ["rbac:read", "sales:view_orders"]

    allowed_resp = await async_client.get("/api/v1/admin/rbac/roles", headers=custom_headers)
    assert allowed_resp.status_code == 200

    bad_role_resp = await async_client.put(
        f"/api/v1/users/{user_body['id']}",
        headers=admin_headers,
        json={"role": "missing_role"},
    )
    assert bad_role_resp.status_code == 400
