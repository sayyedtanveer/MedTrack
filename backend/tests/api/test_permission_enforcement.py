from __future__ import annotations

import uuid

import pytest

from backend.app.config import settings
from backend.app.infrastructure.security.jwt_handler import JWTHandler


_jwt = JWTHandler(
    secret_key=settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
    expiry_minutes=settings.jwt_expiry_minutes,
)


def _headers(user_id: uuid.UUID, tenant_id: uuid.UUID, role: str) -> dict[str, str]:
    token = _jwt.create_access_token(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        role=role,
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}


@pytest.mark.asyncio
async def test_worker_cannot_read_sales_orders(async_client, test_tenant_id):
    response = await async_client.get(
        "/api/v1/sales/orders",
        headers=_headers(uuid.uuid4(), test_tenant_id, "worker"),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_write_inventory_transactions(async_client, token_headers, test_tenant_id):
    location_resp = await async_client.post(
        "/api/v1/inventory/master-data/locations",
        json={
            "name": "Permission Warehouse",
            "code": "WH-PERM",
            "type": "warehouse",
            "is_active": True,
        },
        headers=token_headers,
    )
    assert location_resp.status_code == 201, location_resp.text
    location_id = location_resp.json()["id"]

    material_resp = await async_client.post(
        "/api/v1/inventory/materials",
        json={
            "code": "RM-PERM-01",
            "name": "Permission Test Material",
            "material_type": "raw",
        },
        headers=token_headers,
    )
    assert material_resp.status_code == 201, material_resp.text
    material_id = material_resp.json()["id"]

    response = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "material_id": material_id,
            "transaction_type": "in",
            "quantity": "2",
            "to_location_id": location_id,
        },
        headers=_headers(uuid.uuid4(), test_tenant_id, "viewer"),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_client_cannot_list_work_orders(async_client, test_tenant_id):
    response = await async_client.get(
        "/api/v1/work-orders",
        headers=_headers(uuid.uuid4(), test_tenant_id, "client"),
    )
    assert response.status_code == 403
