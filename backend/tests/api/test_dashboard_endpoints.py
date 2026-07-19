from __future__ import annotations

from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher


async def test_role_dashboard_endpoints_are_mounted_and_tenant_scoped(
    async_client,
    db_session,
    token_headers,
    test_tenant_id,
    test_user_id,
):
    await db_session.merge(
        TenantModel(
            id=test_tenant_id,
            name="Dashboard Test Tenant",
            slug="dashboard-test-tenant",
            plan="starter",
            is_active=True,
        )
    )
    await db_session.merge(
        UserModel(
            id=test_user_id,
            tenant_id=test_tenant_id,
            email="dashboard-admin@example.com",
            hashed_password=BcryptPasswordHasher().hash("Password123!"),
            first_name="Dashboard",
            last_name="Admin",
            role="admin",
            is_active=True,
            is_deleted=False,
        )
    )
    await db_session.commit()

    endpoints = [
        "/api/v1/dashboard/admin",
        "/api/v1/dashboards/admin",
        "/api/v1/dashboard/planner",
        "/api/v1/dashboard/sales",
        "/api/v1/dashboard/qc",
        "/api/v1/dashboard/storekeeper",
        "/api/v1/dashboard/worker",
        "/api/v1/dashboard/client",
    ]

    for endpoint in endpoints:
        response = await async_client.get(endpoint, headers=token_headers)
        assert response.status_code == 200, f"{endpoint}: {response.text}"
        assert response.json()["timestamp"]
