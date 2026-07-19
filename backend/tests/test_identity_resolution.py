import uuid

import pytest
from fastapi import Request

from backend.app.main import app
from backend.app.config import settings
from backend.app.infrastructure.security.jwt_handler import JWTHandler


@pytest.fixture
def jwt_handler() -> JWTHandler:
    return JWTHandler(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expiry_minutes=settings.jwt_expiry_minutes,
    )


@pytest.fixture
def test_route():
    """Register a lightweight test route that returns `request.state` values."""

    @app.get("/__test/request-state")
    async def _request_state(request: Request):
        return {
            "tenant_id_state": getattr(request.state, "tenant_id", None),
            "role_state": getattr(request.state, "role", None),
            "supplier_id_state": getattr(request.state, "supplier_id", None),
            "state_user_id": (getattr(request.state, "user", None) or {}).get("id"),
        }

    yield


@pytest.mark.asyncio
async def test_supplier_linked_user_sets_supplier_id(async_client, test_route, jwt_handler):
    tenant_id = uuid.UUID("b5ef68c4-18be-4fa6-a439-a23c34877550")
    user_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    supplier_id = uuid.UUID("11111111-1111-4111-8111-111111111111")

    token = jwt_handler.create_access_token(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        role="supplier",
        extra_claims={"sid": str(supplier_id)},
    )

    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}
    async_client.headers.update(headers)

    resp = await async_client.get("/__test/request-state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["supplier_id_state"] == str(supplier_id)
    assert data["role_state"] == "supplier"
    assert data["tenant_id_state"] == str(tenant_id)
    assert data["state_user_id"] == str(user_id)


@pytest.mark.asyncio
async def test_x_tenant_id_header_sets_tenant_state(async_client, test_route):
    tenant_id = uuid.UUID("22222222-2222-4222-8222-222222222222")
    # ensure no auth header
    async_client.headers.pop("Authorization", None)
    async_client.headers.update({"X-Tenant-ID": str(tenant_id)})

    resp = await async_client.get("/__test/request-state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id_state"] == str(tenant_id)
    # no user/supplier set
    assert data["supplier_id_state"] is None
    assert data["role_state"] is None


def test_verify_token_alias_matches_decode(jwt_handler):
    tenant_id = uuid.UUID("33333333-3333-4333-8333-333333333333")
    user_id = uuid.UUID("44444444-4444-4444-8444-444444444444")
    token = jwt_handler.create_access_token(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        role="supplier",
    )

    payload = jwt_handler.verify_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["tid"] == str(tenant_id)
    assert payload["role"] == "supplier"
