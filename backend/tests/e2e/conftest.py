"""E2E test fixtures for full system workflow testing."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.infrastructure.persistence.models.bom_model import BOMModel, BOMLineModel
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.models.bom_operation_model import BOMOperationModel
from backend.app.infrastructure.persistence.models.batch_model import BatchModel
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel


def _placeholder_bom_id(*, product_id: uuid.UUID, tenant_id: uuid.UUID) -> uuid.UUID:
    # Must match CreateWorkOrderCommand placeholder logic in:
    # backend/app/application/manufacturing/commands/work_order_commands.py
    return uuid.uuid5(
        uuid.NAMESPACE_DNS,
        f"placeholder:bom:{product_id}:{tenant_id}",
    )


@pytest.fixture
def e2e_test_context(test_tenant_id, test_user_id):
    """Provide context for E2E tests including tenant and user IDs."""
    return {
        "tenant_id": test_tenant_id,
        "user_id": test_user_id,
        "product_template_id": None,
        "variant_ids": [],
        "bom_ids": [],
        "material_ids": [],
        "operation_ids": [],
    }


@pytest.fixture
def test_product_id(sample_product_template) -> uuid.UUID:
    """Stable product/work-product identifier for E2E tests."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"product:{sample_product_template.get('code')}")


@pytest.fixture
def test_material_id(sample_material_data) -> uuid.UUID:
    """Stable inventory material identifier for E2E traceability tests."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, sample_material_data.get("code", "MAT"))


@pytest.fixture
def test_customer_id(test_tenant_id) -> uuid.UUID:
    """Stable customer id for delivery/invoice-related E2E tests."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"customer:{test_tenant_id}")


@pytest.fixture
def test_work_order_id() -> uuid.UUID:
    """Stable work order id used for notification event tests."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, "work-order-e2e")


@pytest.fixture(autouse=True)
async def ensure_placeholder_bom_ready(
    session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
    test_product_id: uuid.UUID,
    test_material_id: uuid.UUID,
) -> AsyncGenerator[None, None]:
    """
    Make the E2E operational flow pass by ensuring:
    - BOM referenced by CreateWorkOrderCommand placeholder bom_id exists and is active
    - Seed enough AVAILABLE batch stock so WO release can create reservations
    """
    placeholder_bom_id = _placeholder_bom_id(product_id=test_product_id, tenant_id=test_tenant_id)
    now = datetime.now(timezone.utc)

    # Unit
    unit_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"uom:e2e:{test_tenant_id}")
    unit = await session.scalar(select(UnitOfMeasureModel).where(UnitOfMeasureModel.id == unit_id))
    if unit is None:
        unit = UnitOfMeasureModel(
            id=unit_id,
            tenant_id=test_tenant_id,
            code="EA-E2E",
            name="Each (E2E)",
            precision=2,
            is_active=True,
            created_at=now,
            updated_at=now,
            is_deleted=False,
            deleted_at=None,
        )
        session.add(unit)

    # Raw material
    raw_material = await session.scalar(
        select(MaterialModel).where(
            MaterialModel.id == test_material_id,
            MaterialModel.tenant_id == test_tenant_id,
        )
    )
    if raw_material is None:
        raw_material = MaterialModel(
            id=test_material_id,
            tenant_id=test_tenant_id,
            code="E2E-RM",
            item_code="E2E-RM",
            code_locked=False,
            name="E2E Raw Material",
            description="Seeded for E2E BOM placeholder",
            category_id=None,
            base_unit_id=unit_id,
            material_type="raw",
            current_cost=Decimal("0"),
            current_stock=Decimal("0"),
            reserved_stock=Decimal("0"),
            reorder_level=Decimal("0"),
            location_id=None,
            is_batch_tracked=False,
            is_serialized=False,
            inspection_required=False,
            inspection_template_id=None,
            safety_stock=None,
            lead_time_days=None,
            is_active=True,
            length_uom=None,
            length_per_unit=None,
            weight_per_unit=None,
            dimension_spec=None,
            preferred_supplier_id=None,
            hazardous_flag=False,
            qc_required_flag=False,
            is_deleted=False,
            deleted_at=None,
            created_by=test_user_id,
            updated_by=None,
            created_at=now,
            updated_at=now,
        )
        session.add(raw_material)

    # Finished-good material expected by WorkflowOrchestrationService after QC approval.
    # It resolves finished-good by:
    # 1) MaterialModel.id == work_order.product_id (unlikely here)
    # 2) ItemVariantModel.id == work_order.product_id, then variant.material_id
    finished_material_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"fg:e2e:{test_tenant_id}:{test_product_id}")
    finished_material = await session.scalar(
        select(MaterialModel).where(
            MaterialModel.id == finished_material_id,
            MaterialModel.tenant_id == test_tenant_id,
        )
    )
    if finished_material is None:
        # Match variant.code so any fallback by code works too.
        finished_material = MaterialModel(
            id=finished_material_id,
            tenant_id=test_tenant_id,
            code="E2E-VAR",
            item_code="E2E-VAR",
            code_locked=False,
            name="E2E Finished Goods",
            description="Seeded for E2E QC->FG_RECEIPT flow",
            category_id=None,
            base_unit_id=unit_id,
            material_type="finished",
            current_cost=Decimal("0"),
            current_stock=Decimal("0"),
            reserved_stock=Decimal("0"),
            reorder_level=Decimal("0"),
            location_id=None,
            is_batch_tracked=False,
            is_serialized=False,
            inspection_required=False,
            inspection_template_id=None,
            safety_stock=None,
            lead_time_days=None,
            is_active=True,
            length_uom=None,
            length_per_unit=None,
            weight_per_unit=None,
            dimension_spec=None,
            preferred_supplier_id=None,
            hazardous_flag=False,
            qc_required_flag=False,
            is_deleted=False,
            deleted_at=None,
            created_by=test_user_id,
            updated_by=None,
            created_at=now,
            updated_at=now,
        )
        session.add(finished_material)

    # Seed an internal warehouse location + stock bucket so reserve_for_work_order()
    # finds AVAILABLE stock (reserve_for_work_order uses StockLevelModel, not BatchModel).
    location_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"loc:e2e:{test_tenant_id}:{test_material_id}")
    location = await session.scalar(select(LocationModel).where(LocationModel.id == location_id))
    if location is None:
        location = LocationModel(
            id=location_id,
            tenant_id=test_tenant_id,
            name="E2E Warehouse",
            code="WH-E2E",
            type="warehouse",
            parent_location_id=None,
            is_active=True,
            is_deleted=False,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(location)

    stock_level = await session.scalar(
        select(StockLevelModel).where(
            StockLevelModel.tenant_id == test_tenant_id,
            StockLevelModel.material_id == test_material_id,
            StockLevelModel.location_id == location_id,
            StockLevelModel.stock_status == "available",
        )
    )
    if stock_level is None:
        stock_level = StockLevelModel(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"sl:e2e:{test_tenant_id}:{test_material_id}:{location_id}"),
            tenant_id=test_tenant_id,
            material_id=test_material_id,
            location_id=location_id,
            stock_status="available",
            quantity=Decimal("1000"),
            is_deleted=False,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(stock_level)
    else:
        stock_level.quantity = float(Decimal("1000"))
        stock_level.updated_at = now

    await session.flush()

    # Seed a batch as well (some flows use batch-level cards/visuals, but WO reservation
    # in this codebase relies on StockLevelModel buckets).
    batch_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"batch:e2e:{test_tenant_id}:{test_material_id}")
    batch = await session.scalar(select(BatchModel).where(BatchModel.id == batch_id))
    if batch is None:
        batch = BatchModel(
            id=batch_id,
            tenant_id=test_tenant_id,
            material_id=test_material_id,
            batch_number="E2E-BATCH-1",
            quantity=Decimal("1000"),
            remaining_quantity=Decimal("1000"),
            expiry_date=None,
            location_id=None,
            status="in_stock",
            original_quantity=Decimal("1000"),
            reserved_quantity=Decimal("0"),
            consumed_quantity=Decimal("0"),
            returned_quantity=Decimal("0"),
            is_deleted=False,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(batch)
    else:
        # Ensure availability for retries.
        batch.status = batch.status or "in_stock"

        # BatchModel maps these columns as float/Numeric -> float in the ORM typing.
        remaining_qty: float = float(batch.remaining_quantity) if batch.remaining_quantity is not None else 0.0
        batch.remaining_quantity = remaining_qty

        if remaining_qty <= 0:
            seed_qty = 1000.0
            batch.quantity = seed_qty
            batch.remaining_quantity = seed_qty
            batch.original_quantity = seed_qty
            batch.status = "in_stock"
            batch.reserved_quantity = 0.0
            batch.consumed_quantity = 0.0
            batch.returned_quantity = 0.0

    # Fast path: if BOM exists + active, still ensure stock batch exists (we do above), then yield.
    existing = await session.scalar(
        select(BOMModel).where(BOMModel.id == placeholder_bom_id, BOMModel.tenant_id == test_tenant_id)
    )
    if existing is not None and existing.is_active:
        await session.commit()
        yield
        return

    # Finished goods template + variant
    template_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"tmpl:e2e:{test_tenant_id}:{test_product_id}")
    template = await session.scalar(
        select(ItemTemplateModel).where(ItemTemplateModel.id == template_id, ItemTemplateModel.tenant_id == test_tenant_id)
    )
    if template is None:
        template = ItemTemplateModel(
            id=template_id,
            tenant_id=test_tenant_id,
            code="E2E-TEMPLATE",
            code_locked=True,
            name="E2E Template",
            description=None,
            category_id=None,
            base_unit_id=unit_id,
            attributes=[{"key": "SIZE", "label": "Size"}],
            status="ACTIVE",
            is_active=True,
            is_deleted=False,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(template)

    # WorkOrderModel.product_id is FK to item_variants.id.
    # The E2E CreateWorkOrderCommand passes `test_product_id`, so ensure an ItemVariantModel exists
    # with id == test_product_id (not some derived variant id).
    variant = await session.scalar(
        select(ItemVariantModel).where(
            ItemVariantModel.id == test_product_id,
            ItemVariantModel.tenant_id == test_tenant_id,
            ItemVariantModel.is_deleted.is_(False),
        )
    )
    if variant is None:
        variant = ItemVariantModel(
            id=test_product_id,
            tenant_id=test_tenant_id,
            template_id=template_id,
            code="E2E-VAR",
            code_locked=True,
            name="E2E Variant",
            variant_key="SIZE=STD",
            attribute_values={"SIZE": "STD"},
            base_unit_id=unit_id,
            material_id=finished_material.id,  # crucial for QC->FG receipt
            standard_cost=Decimal("0"),
            selling_price=Decimal("0"),
            is_active=True,
            is_deleted=False,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(variant)

    # Operation seed for BOMOperationModel (BOMOperationModel references operations.id)
    operation_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"op:e2e:{test_tenant_id}:{placeholder_bom_id}")

    bom = await session.scalar(select(BOMModel).where(BOMModel.id == placeholder_bom_id, BOMModel.tenant_id == test_tenant_id))
    if bom is None:
        bom = BOMModel(
            id=placeholder_bom_id,
            tenant_id=test_tenant_id,
            template_id=template_id,
            variant_id=None,
            version="v1.0-e2e",
            is_active=True,
            valid_from=now,
            valid_to=None,
            created_by=test_user_id,
            approved_by=None,
            is_deleted=False,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(bom)
        await session.flush()

        bom_line = BOMLineModel(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"bomline:e2e:{placeholder_bom_id}:{raw_material.id}"),
            tenant_id=test_tenant_id,
            bom_id=bom.id,
            material_id=raw_material.id,
            template_id=None,
            variant_id=None,
            quantity=Decimal("1"),
            scrap_percentage=Decimal("0"),
            unit_id=unit_id,
            is_deleted=False,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(bom_line)

        # BOM operation best-effort: create OperationModel if it exists in this slice.
        try:
            from backend.app.infrastructure.persistence.models.operation_model import OperationModel  # type: ignore

            op = await session.scalar(select(OperationModel).where(OperationModel.id == operation_id))
            if op is None:
                op = OperationModel(
                    id=operation_id,
                    tenant_id=test_tenant_id,
                    code="OP-E2E",
                    name="E2E Operation",
                    description=None,
                    process_type="assembly",
                    estimated_time_hours=Decimal("1"),
                    estimated_labor_cost=Decimal("0"),
                    is_active=True,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                )
                session.add(op)
                await session.flush()
        except Exception:
            pass

        bom_op = BOMOperationModel(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"bomop:e2e:{placeholder_bom_id}:{operation_id}"),
            tenant_id=test_tenant_id,
            bom_id=bom.id,
            operation_id=operation_id,
            sequence=1,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        session.add(bom_op)

    await session.commit()
    yield
