from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from backend.app.domain.product.value_objects.product_status import ProductStatus
from backend.app.infrastructure.persistence.models.bom_model import BOMModel
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel


@pytest.mark.asyncio
async def test_list_variant_boms_falls_back_to_template_bom(
    async_client,
    db_session,
    token_headers,
    test_tenant_id,
    test_user_id,
):
    now = datetime.now(timezone.utc)
    template_id = uuid4()
    variant_id = uuid4()
    bom_id = uuid4()

    db_session.add_all(
        [
            ItemTemplateModel(
                id=template_id,
                tenant_id=test_tenant_id,
                code=f"FG-TPL-{str(template_id)[:8]}",
                name="Fallback Template",
                attributes=[],
                status=ProductStatus.ACTIVE.value,
                is_active=True,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
            ItemVariantModel(
                id=variant_id,
                tenant_id=test_tenant_id,
                template_id=template_id,
                code=f"FG-VAR-{str(variant_id)[:8]}",
                name="Fallback Variant",
                variant_key="BASE",
                attribute_values={},
                standard_cost=Decimal("10"),
                is_active=True,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
            BOMModel(
                id=bom_id,
                tenant_id=test_tenant_id,
                template_id=template_id,
                version="v1.0",
                is_active=True,
                valid_from=now,
                created_by=test_user_id,
                approved_by=test_user_id,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/products/{variant_id}/boms",
        headers=token_headers,
        params={"is_template": "false"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == str(bom_id)
    assert payload["items"][0]["template_id"] == str(template_id)
    assert payload["items"][0]["variant_id"] is None
