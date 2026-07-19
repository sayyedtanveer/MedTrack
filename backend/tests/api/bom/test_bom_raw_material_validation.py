from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel


@pytest.mark.asyncio
async def test_create_bom_rejects_finished_good_in_material_line(
    authenticated_async_client: AsyncClient,
    db_session,
    test_tenant_id,
):
    now = datetime.now(timezone.utc)
    template_id = uuid.uuid4()
    finished_material_id = uuid.uuid4()

    db_session.add(
        ItemTemplateModel(
            id=template_id,
            tenant_id=test_tenant_id,
            code="FG-GEAR-ROTAMETER",
            name="Gear Rotameter",
            attributes=[],
            status="ACTIVE",
            is_active=True,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        MaterialModel(
            id=finished_material_id,
            tenant_id=test_tenant_id,
            code="FG-READY-UNIT",
            name="Ready Assembly",
            material_type="finished",
            current_stock=0,
            reserved_stock=0,
            is_active=True,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.commit()

    response = await authenticated_async_client.post(
        f"/api/v1/products/{template_id}/boms",
        json={
            "version": "v1.0",
            "valid_from": now.isoformat(),
            "template_id": str(template_id),
            "lines": [
                {
                    "material_id": str(finished_material_id),
                    "quantity": 1,
                    "scrap_percentage": 0,
                }
            ],
        },
    )

    assert response.status_code == 400
    assert "Only raw materials can be added as BOM material lines" in response.json()["detail"]
