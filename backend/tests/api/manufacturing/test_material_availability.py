from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from backend.app.domain.product.value_objects.product_status import ProductStatus
from backend.app.infrastructure.persistence.models.bom_model import BOMLineModel, BOMModel
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel


async def test_material_availability_preview_highlights_shortage(
    async_client,
    db_session,
    token_headers,
    test_tenant_id,
    test_user_id,
):
    now = datetime.now(timezone.utc)
    run_id = uuid.uuid4().hex[:8]

    unit_id = uuid.uuid4()
    template_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    bom_id = uuid.uuid4()
    material_ok_id = uuid.uuid4()
    material_short_id = uuid.uuid4()

    db_session.add_all(
        [
            UnitOfMeasureModel(
                id=unit_id,
                tenant_id=test_tenant_id,
                code=f"EA{run_id[:4]}",
                name="Each",
                precision=2,
                is_active=True,
                created_at=now,
                updated_at=now,
                is_deleted=False,
            ),
            ItemTemplateModel(
                id=template_id,
                tenant_id=test_tenant_id,
                code=f"FG-TPL-{run_id}",
                name="Availability Test Template",
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
                code=f"FG-{run_id}",
                name="Availability Test Variant",
                variant_key=f"BASE={run_id}",
                attribute_values={},
                base_unit_id=unit_id,
                standard_cost=Decimal("25"),
                is_active=True,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
            MaterialModel(
                id=material_ok_id,
                tenant_id=test_tenant_id,
                code=f"RM-OK-{run_id}",
                name="Available Material",
                material_type="raw",
                base_unit_id=unit_id,
                current_cost=Decimal("5"),
                current_stock=Decimal("20"),
                reserved_stock=Decimal("0"),
                reorder_level=Decimal("0"),
                is_active=True,
                is_deleted=False,
            ),
            MaterialModel(
                id=material_short_id,
                tenant_id=test_tenant_id,
                code=f"RM-SHORT-{run_id}",
                name="Short Material",
                material_type="raw",
                base_unit_id=unit_id,
                current_cost=Decimal("8"),
                current_stock=Decimal("1"),
                reserved_stock=Decimal("0"),
                reorder_level=Decimal("0"),
                is_active=True,
                is_deleted=False,
            ),
            BOMModel(
                id=bom_id,
                tenant_id=test_tenant_id,
                variant_id=variant_id,
                version="v1.0",
                is_active=True,
                valid_from=now,
                created_by=test_user_id,
                approved_by=test_user_id,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
            BOMLineModel(
                id=uuid.uuid4(),
                tenant_id=test_tenant_id,
                bom_id=bom_id,
                material_id=material_ok_id,
                quantity=Decimal("2"),
                scrap_percentage=Decimal("0"),
                unit_id=unit_id,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
            BOMLineModel(
                id=uuid.uuid4(),
                tenant_id=test_tenant_id,
                bom_id=bom_id,
                material_id=material_short_id,
                quantity=Decimal("3"),
                scrap_percentage=Decimal("0"),
                unit_id=unit_id,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/work-orders/material-availability",
        headers=token_headers,
        params={
            "product_id": str(variant_id),
            "bom_id": str(bom_id),
            "quantity": "2",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["bom_id"] == str(bom_id)
    assert payload["has_shortage"] is True
    assert payload["shortage_count"] == 1
    assert len(payload["lines"]) == 2

    lines_by_code = {line["material_code"]: line for line in payload["lines"]}
    assert Decimal(lines_by_code[f"RM-OK-{run_id}"]["required_quantity"]) == Decimal("4")
    assert Decimal(lines_by_code[f"RM-OK-{run_id}"]["shortage_quantity"]) == Decimal("0")
    assert lines_by_code[f"RM-OK-{run_id}"]["status"] == "ok"

    assert Decimal(lines_by_code[f"RM-SHORT-{run_id}"]["required_quantity"]) == Decimal("6")
    assert Decimal(lines_by_code[f"RM-SHORT-{run_id}"]["available_quantity"]) == Decimal("1")
    assert Decimal(lines_by_code[f"RM-SHORT-{run_id}"]["shortage_quantity"]) == Decimal("5")
    assert lines_by_code[f"RM-SHORT-{run_id}"]["status"] == "low"


async def test_material_availability_preview_falls_back_to_template_bom(
    async_client,
    db_session,
    token_headers,
    test_tenant_id,
    test_user_id,
):
    now = datetime.now(timezone.utc)
    run_id = uuid.uuid4().hex[:8]

    unit_id = uuid.uuid4()
    template_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    bom_id = uuid.uuid4()
    material_id = uuid.uuid4()

    db_session.add_all(
        [
            UnitOfMeasureModel(
                id=unit_id,
                tenant_id=test_tenant_id,
                code=f"EA{run_id[:4]}",
                name="Each",
                precision=2,
                is_active=True,
                created_at=now,
                updated_at=now,
                is_deleted=False,
            ),
            ItemTemplateModel(
                id=template_id,
                tenant_id=test_tenant_id,
                code=f"FG-TPL-{run_id}",
                name="Template BOM Fallback",
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
                code=f"FG-{run_id}",
                name="Variant With Inherited BOM",
                variant_key=f"BASE={run_id}",
                attribute_values={},
                base_unit_id=unit_id,
                standard_cost=Decimal("25"),
                is_active=True,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
            MaterialModel(
                id=material_id,
                tenant_id=test_tenant_id,
                code=f"RM-{run_id}",
                name="Template Material",
                material_type="raw",
                base_unit_id=unit_id,
                current_cost=Decimal("5"),
                current_stock=Decimal("20"),
                reserved_stock=Decimal("0"),
                reorder_level=Decimal("0"),
                is_active=True,
                is_deleted=False,
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
            BOMLineModel(
                id=uuid.uuid4(),
                tenant_id=test_tenant_id,
                bom_id=bom_id,
                material_id=material_id,
                quantity=Decimal("2"),
                scrap_percentage=Decimal("0"),
                unit_id=unit_id,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/work-orders/material-availability",
        headers=token_headers,
        params={
            "product_id": str(variant_id),
            "quantity": "3",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["bom_id"] == str(bom_id)
    assert payload["has_shortage"] is False
    assert len(payload["lines"]) == 1
    assert payload["lines"][0]["material_id"] == str(material_id)
    assert Decimal(payload["lines"][0]["required_quantity"]) == Decimal("6")
