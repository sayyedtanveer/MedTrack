from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from backend.app.infrastructure.persistence.models.material_model import MaterialModel


@pytest.mark.asyncio
async def test_create_material_rejects_generic_raw_material_name(
    authenticated_async_client: AsyncClient,
):
    response = await authenticated_async_client.post(
        "/api/v1/inventory/materials",
        json={
            "code": "RM-GENERIC-01",
            "name": "Raw Material",
            "material_type": "raw",
        },
    )

    assert response.status_code == 400
    assert "specific raw material name" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_materials_can_filter_by_material_type(
    authenticated_async_client: AsyncClient,
    db_session,
    test_tenant_id,
):
    now = datetime.now(timezone.utc)
    raw_id = uuid.uuid4()
    finished_id = uuid.uuid4()

    db_session.add_all(
        [
            MaterialModel(
                id=raw_id,
                tenant_id=test_tenant_id,
                code="RM-BRASS-BODY",
                name="Brass Body",
                material_type="raw",
                current_stock=0,
                reserved_stock=0,
                is_active=True,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
            MaterialModel(
                id=finished_id,
                tenant_id=test_tenant_id,
                code="FG-GEAR-ROTAMETER",
                name="Gear Rotameter - Standard",
                material_type="finished",
                current_stock=0,
                reserved_stock=0,
                is_active=True,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await db_session.commit()

    response = await authenticated_async_client.get(
        "/api/v1/inventory/materials",
        params={"material_type": "raw", "page": 1, "page_size": 50},
    )

    assert response.status_code == 200
    payload = response.json()
    assert any(item["id"] == str(raw_id) for item in payload["items"])
    assert all(item["material_type"] == "raw" for item in payload["items"])
