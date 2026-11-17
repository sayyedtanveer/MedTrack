import os
from decimal import Decimal
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable

from backend.app.infrastructure.persistence.models.batch_model import BatchModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel
from backend.app.infrastructure.persistence.models.subcontract_model import (
    SubcontractMaterialIssueModel, SubcontractOrderLineModel, SubcontractOrderModel,
)
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.interfaces.api.v1.routes import supply_chain as routes
from backend.app.interfaces.api.v1.schemas.supply_chain_schemas import (
    SubcontractIssueRequest, SubcontractReceiveRequest, SubcontractReturnMaterialRequest,
)

D = Decimal


@pytest_asyncio.fixture
async def case():
    target = os.getenv("MEDTRACK_SUBCONTRACT_TEST_URL", "sqlite+aiosqlite:///:memory:")
    if target.startswith("postgresql"):
        parsed = urlsplit(target)
        assert parsed.hostname in ("localhost", "127.0.0.1")
        assert parsed.port and parsed.port != 5432
        assert parsed.path == "/medtrack_subcontract_disposable"
    engine = create_async_engine(target)
    models = (TenantModel, LocationModel, MaterialModel, SupplierModel, BatchModel, StockLevelModel,
              SubcontractOrderModel, SubcontractOrderLineModel, SubcontractMaterialIssueModel,
              InventoryTransactionModel)
    if target.startswith("postgresql"):
        # Each test owns an independent schema in the disposable server.
        from sqlalchemy import text
        # Omit unrelated foreign keys in this test subset of the schema.
        schema = "sco_" + uuid4().hex
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA {schema}"))
        engine = engine.execution_options(schema_translate_map={None: schema})
    async with engine.begin() as conn:
        for model in models:
            await conn.execute(CreateTable(model.__table__, include_foreign_key_constraints=[]))
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    t, user, raw, output, warehouse, vendor, supplier, order, other = [uuid4() for _ in range(9)]
    async with factory() as session:
        session.add_all([
            LocationModel(id=warehouse, tenant_id=t, name="Warehouse", type="warehouse", is_active=True),
            LocationModel(id=vendor, tenant_id=t, name="Vendor", code=f"SUB-{supplier}", type="subcontractor", is_active=True),
            SupplierModel(id=supplier, tenant_id=t, code="SUP", name="Supplier", is_active=True),
            MaterialModel(id=raw, tenant_id=t, code="RAW", name="Raw", material_type="raw", current_stock=D("10")),
            MaterialModel(id=output, tenant_id=t, code="SF", name="Output", material_type="semi_finished"),
            StockLevelModel(tenant_id=t, material_id=raw, location_id=warehouse, stock_status="available", quantity=D("7")),
            StockLevelModel(tenant_id=t, material_id=raw, location_id=vendor, stock_status="available", quantity=D("3")),
            SubcontractOrderModel(id=order, tenant_id=t, order_number="TEST-1", supplier_id=supplier,
                                  product_id=output, product_type="material", quantity=D("3"), status="materials_issued"),
            SubcontractOrderModel(id=other, tenant_id=t, order_number="TEST-2", supplier_id=supplier,
                                  product_id=output, product_type="material", quantity=D("3"), status="materials_issued"),
            SubcontractOrderLineModel(tenant_id=t, subcontract_order_id=order, material_id=raw,
                                       required_quantity=D("1"), issued_quantity=D("1")),
            SubcontractOrderLineModel(tenant_id=t, subcontract_order_id=other, material_id=raw,
                                       required_quantity=D("2"), issued_quantity=D("2")),
            SubcontractMaterialIssueModel(tenant_id=t, subcontract_order_id=order, material_id=raw, quantity=D("1")),
            SubcontractMaterialIssueModel(tenant_id=t, subcontract_order_id=other, material_id=raw, quantity=D("2")),
        ])
        await session.commit()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(container=SimpleNamespace(session_factory=factory))))
    yield SimpleNamespace(factory=factory, request=request, tenant=t, user=user, raw=raw, output=output,
                          warehouse=warehouse, vendor=vendor, order=order, other=other, postgres=target.startswith("postgresql"))
    await engine.dispose()


async def receive(case, quantity, *, order=None, material=None, location=None, tenant=None, batch=None):
    return await routes.receive_subcontract(order or case.order, SubcontractReceiveRequest(
        material_id=material or case.output, quantity=D(quantity), warehouse_location_id=location or case.warehouse,
        output_batch_number=batch,
    ), case.request, tenant or case.tenant, case.user)


async def return_material(case, quantity, *, batch_id=None):
    return await routes.return_subcontract_material(case.order, SubcontractReturnMaterialRequest(
        material_id=case.raw, quantity=D(quantity), to_location_id=case.warehouse, batch_id=batch_id,
    ), case.request, case.tenant, case.user)


async def quantity_at(case, material, location):
    async with case.factory() as session:
        result = await session.scalar(select(StockLevelModel.quantity).where(
            StockLevelModel.tenant_id == case.tenant, StockLevelModel.material_id == material,
            StockLevelModel.location_id == location, StockLevelModel.stock_status == "available",
        ))
        return result if result is not None else D("0")


@pytest.mark.asyncio
async def test_valid_partials_use_cumulative_rounding_and_do_not_borrow(case):
    for expected in ("2.667", "2.333", "2.000"):
        await receive(case, "1")
        assert await quantity_at(case, case.raw, case.vendor) == D(expected)
    assert await quantity_at(case, case.output, case.warehouse) == D("3")
    async with case.factory() as session:
        order = await session.get(SubcontractOrderModel, case.order)
        assert order.status == "completed" and order.received_quantity == D("3")
        batch = await session.get(BatchModel, order.output_batch_id)
        assert batch.remaining_quantity == batch.original_quantity == D("3")
        consumed = await session.scalar(select(func.sum(InventoryTransactionModel.quantity)).where(
            InventoryTransactionModel.reference_id == case.order, InventoryTransactionModel.transaction_type == "out",
        ))
        assert consumed == D("1")


@pytest.mark.asyncio
async def test_excess_wrong_output_tenant_location_and_order_shortage_do_not_post(case):
    for qty, kwargs, code in (
        ("4", {}, 409), ("1", {"material": case.raw}, 422),
        ("1", {"location": case.vendor}, 422), ("1", {"tenant": uuid4()}, 404),
    ):
        with pytest.raises(HTTPException) as exc:
            await receive(case, qty, **kwargs)
        assert exc.value.status_code == code
    async with case.factory() as session:
        line = await session.scalar(select(SubcontractOrderLineModel).where(
            SubcontractOrderLineModel.subcontract_order_id == case.order,
        ))
        line.issued_quantity = D("0")
        await session.commit()
    with pytest.raises(HTTPException, match="Insufficient material issued"):
        await receive(case, "1")
    assert await quantity_at(case, case.raw, case.vendor) == D("3")
    assert await quantity_at(case, case.output, case.warehouse) == D("0")


@pytest.mark.asyncio
async def test_return_conserves_stock_and_rejects_replay_beyond_outstanding(case):
    with pytest.raises(HTTPException, match="outstanding"):
        await return_material(case, "2")
    with pytest.raises(HTTPException, match="Batch"):
        await return_material(case, "1", batch_id=uuid4())
    await return_material(case, "1")
    with pytest.raises(HTTPException, match="outstanding"):
        await return_material(case, "1")
    assert await quantity_at(case, case.raw, case.warehouse) == D("8")
    assert await quantity_at(case, case.raw, case.vendor) == D("2")


@pytest.mark.asyncio
async def test_vendor_bucket_shortage_leaves_return_and_receipt_unposted(case):
    async with case.factory() as session:
        bucket = await session.scalar(select(StockLevelModel).where(StockLevelModel.location_id == case.vendor))
        bucket.quantity = 0
        await session.commit()
    with pytest.raises(HTTPException) as ret:
        await return_material(case, "1")
    assert ret.value.status_code == 409
    with pytest.raises(HTTPException) as rec:
        await receive(case, "1")
    assert rec.value.status_code == 409
    assert await quantity_at(case, case.raw, case.warehouse) == D("7")
    assert await quantity_at(case, case.output, case.warehouse) == D("0")


@pytest.mark.asyncio
async def test_batch_conflict_rolls_back_preceding_consumption(case):
    await receive(case, "1", order=case.other, batch="OTHER-ORDER")
    before = await quantity_at(case, case.raw, case.vendor)
    with pytest.raises(HTTPException, match="not created for this subcontract order"):
        await receive(case, "1", batch="OTHER-ORDER")
    assert await quantity_at(case, case.raw, case.vendor) == before
    assert await quantity_at(case, case.output, case.warehouse) == D("1")


@pytest.mark.asyncio
async def test_manual_orders_and_existing_completed_orders_can_return(case):
    async with case.factory() as session:
        from sqlalchemy import delete
        await session.execute(delete(SubcontractOrderLineModel).where(
            SubcontractOrderLineModel.subcontract_order_id == case.order,
        ))
        await session.commit()
    await receive(case, "3")
    assert await quantity_at(case, case.raw, case.vendor) == D("3")
    await return_material(case, "1")
    assert await quantity_at(case, case.raw, case.vendor) == D("2")


def test_schema_rejects_zero_negative_and_excess_precision():
    for value in ("0", "-1", "0.0001", "1000000000000"):
        with pytest.raises(ValidationError):
            SubcontractIssueRequest(material_id=uuid4(), from_location_id=uuid4(), quantity=value)


@pytest.mark.asyncio
async def test_postgresql_concurrent_receipts_cannot_both_exceed_order(case):
    import asyncio
    if not case.postgres:
        pytest.skip("Requires the dedicated disposable PostgreSQL server")
    results = await asyncio.gather(receive(case, "2"), receive(case, "2"), return_exceptions=True)
    assert sorted(result.status_code if isinstance(result, HTTPException) else 200 for result in results) == [200, 409]
    assert await quantity_at(case, case.output, case.warehouse) == D("2")

async def issue(case, quantity, *, order=None, batch_id=None):
    return await routes.issue_subcontract_material(order or case.order, SubcontractIssueRequest(
        material_id=case.raw, quantity=D(quantity), from_location_id=case.warehouse, batch_id=batch_id,
    ), case.request, case.tenant, case.user)


@pytest.mark.asyncio
async def test_shared_vendor_shortfall_does_not_consume_another_orders_stock(case):
    async with case.factory() as session:
        bucket = await session.scalar(select(StockLevelModel).where(StockLevelModel.location_id == case.vendor))
        bucket.quantity = D("2")  # all two units are attributable to the other order
        await session.commit()
    with pytest.raises(HTTPException, match="other orders"):
        await receive(case, "1")
    with pytest.raises(HTTPException, match="other orders"):
        await return_material(case, "1")
    assert await quantity_at(case, case.raw, case.vendor) == D("2")
    assert await quantity_at(case, case.output, case.warehouse) == D("0")


@pytest.mark.asyncio
async def test_issue_checks_stock_batch_and_status_before_cancellation(case):
    with pytest.raises(HTTPException, match="Batch"):
        await issue(case, "1", batch_id=uuid4())
    with pytest.raises(HTTPException, match="Insufficient"):
        await issue(case, "8")
    assert await quantity_at(case, case.raw, case.warehouse) == D("7")
    await issue(case, "2")
    with pytest.raises(HTTPException, match="Cannot cancel"):
        await routes.cancel_subcontract_order(case.order, case.request, case.tenant)
    assert await quantity_at(case, case.raw, case.warehouse) == D("5")
    assert await quantity_at(case, case.raw, case.vendor) == D("5")


@pytest.mark.asyncio
async def test_postgresql_concurrent_issues_cannot_overdraw_shared_warehouse(case):
    import asyncio
    if not case.postgres:
        pytest.skip("Requires the dedicated disposable PostgreSQL server")
    results = await asyncio.gather(issue(case, "5"), issue(case, "5", order=case.other), return_exceptions=True)
    assert sorted(result.status_code if isinstance(result, HTTPException) else 200 for result in results) == [200, 409]
    assert await quantity_at(case, case.raw, case.warehouse) == D("2")
    assert await quantity_at(case, case.raw, case.vendor) == D("8")


@pytest.mark.asyncio
async def test_postgresql_concurrent_return_and_receipt_cannot_both_use_same_allocation(case):
    import asyncio
    if not case.postgres:
        pytest.skip("Requires the dedicated disposable PostgreSQL server")
    results = await asyncio.gather(receive(case, "3"), return_material(case, "1"), return_exceptions=True)
    assert sorted(result.status_code if isinstance(result, HTTPException) else 200 for result in results) == [200, 409]
    assert await quantity_at(case, case.raw, case.vendor) == D("2")

@pytest.mark.asyncio
async def test_approval_preserves_manual_order_and_rejects_wrong_bom(case):
    if not case.postgres:
        pytest.skip("BOM fixtures use PostgreSQL JSONB models")
    from datetime import datetime, timezone

    from backend.app.infrastructure.persistence.models.bom_model import BOMLineModel, BOMModel
    from backend.app.infrastructure.persistence.models.bom_operation_model import BOMOperationModel
    from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
    from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
    from backend.app.infrastructure.persistence.models.operation_model import OperationModel
    from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
    from backend.app.infrastructure.persistence.models.workstation_model import WorkstationModel

    unit, template, variant, wrong_template, bom, wrong_bom, manual, production = [uuid4() for _ in range(8)]
    now = datetime.now(timezone.utc)
    async with case.factory() as session:
        for model in (UnitOfMeasureModel, ItemTemplateModel, ItemVariantModel, BOMModel, BOMLineModel, BOMOperationModel, OperationModel, WorkstationModel):
            await session.execute(CreateTable(model.__table__, include_foreign_key_constraints=[]))
        supplier_id = await session.scalar(select(SubcontractOrderModel.supplier_id).where(SubcontractOrderModel.id == case.order))
        for material_id in (case.raw, case.output):
            material = await session.get(MaterialModel, material_id)
            material.base_unit_id = unit
        session.add_all([
            UnitOfMeasureModel(id=unit, tenant_id=case.tenant, code="KG", name="Kilogram", created_at=now, updated_at=now),
            ItemTemplateModel(id=template, tenant_id=case.tenant, code="T1", name="Correct", base_unit_id=unit),
            ItemTemplateModel(id=wrong_template, tenant_id=case.tenant, code="T2", name="Wrong", base_unit_id=unit),
            ItemVariantModel(id=variant, tenant_id=case.tenant, code="V1", name="Output", variant_key="one",
                             base_unit_id=unit, material_id=case.output, template_id=template),
            BOMModel(id=bom, tenant_id=case.tenant, template_id=template, is_active=True,
                     version="1", valid_from=now, created_by=case.user),
            BOMModel(id=wrong_bom, tenant_id=case.tenant, template_id=wrong_template, is_active=True,
                     version="1", valid_from=now, created_by=case.user),
            BOMLineModel(tenant_id=case.tenant, bom_id=bom, material_id=case.raw, unit_id=unit, quantity=D("0.333333")),
            SubcontractOrderModel(id=manual, tenant_id=case.tenant, order_number="MANUAL", supplier_id=supplier_id,
                                  product_id=case.output, product_type="material", quantity=D("3"), status="draft"),
            SubcontractOrderModel(id=production, tenant_id=case.tenant, order_number="BOM", supplier_id=supplier_id,
                                  product_id=case.output, product_type="material", quantity=D("3"), status="draft",
                                  bom_id=wrong_bom),
        ])
        await session.commit()

    await routes.approve_subcontract_order(manual, case.request, case.tenant, case.user)
    with pytest.raises(HTTPException, match="explicit variant"):
        await routes.approve_subcontract_order(production, case.request, case.tenant, case.user)

    async with case.factory() as session:
        order = await session.get(SubcontractOrderModel, production)
        assert order.status == "draft"
        order.bom_id = bom
        nested = BOMLineModel(id=uuid4(), tenant_id=case.tenant, bom_id=bom, variant_id=variant, unit_id=unit, quantity=D("1"))
        session.add(nested)
        await session.commit()
        nested_id = nested.id
    with pytest.raises(HTTPException, match="nested BOM"):
        await routes.approve_subcontract_order(production, case.request, case.tenant, case.user)
    async with case.factory() as session:
        (await session.get(BOMLineModel, nested_id)).is_deleted = True
        await session.commit()

    await routes.approve_subcontract_order(production, case.request, case.tenant, case.user)
    async with case.factory() as session:
        snapshot = await session.scalar(select(SubcontractOrderLineModel).where(
            SubcontractOrderLineModel.subcontract_order_id == production,
        ))
        assert snapshot.material_id == case.raw and snapshot.required_quantity == D("1.000")
        assert await session.scalar(select(func.count()).select_from(SubcontractOrderLineModel).where(
            SubcontractOrderLineModel.subcontract_order_id == manual,
        )) == 0
        approved_bom = await session.get(BOMModel, bom)
        approved_bom.is_active = False
        await session.commit()

    await issue(case, "1", order=production)
    await receive(case, "3", order=production)



@pytest_asyncio.fixture
async def http_case(case):
    if not case.postgres:
        pytest.skip("Transactional HTTP tests require disposable PostgreSQL")
    from pathlib import Path
    from runpy import run_path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text

    from backend.app.infrastructure.security.jwt_handler import JWTHandler
    from backend.app.main import create_application

    migration = run_path(str(Path(__file__).resolve().parents[2] / "alembic/versions/20261117_subcontract_stock_ops.py"))
    foreign_tenant = uuid4()
    async with case.factory() as session:
        conn = await session.connection()
        schema = conn.sync_connection.get_execution_options()["schema_translate_map"][None]
        await conn.execute(text(f"SET LOCAL search_path TO {schema}"))
        await conn.execute(text("ALTER TABLE subcontract_orders DROP CONSTRAINT uq_subcontract_orders_tenant_id_id"))
        def upgrade(sync_connection):
            with Operations.context(MigrationContext.configure(sync_connection)):
                migration["upgrade"]()
        await conn.run_sync(upgrade)
        session.add_all([
            TenantModel(id=case.tenant, name="Writing tenant", slug="writer", status="active"),
            TenantModel(id=foreign_tenant, name="Other tenant", slug="other", status="active"),
        ])
        await session.commit()

    app = create_application()
    jwt = JWTHandler(uuid4().hex, "HS256", 10)
    app.state.container = SimpleNamespace(session_factory=case.factory, jwt_handler=jwt, task_service=None)

    def headers(key=None, *, tenant=case.tenant, role="admin"):
        values = {"Authorization": "Bearer " + jwt.create_access_token(str(case.user), str(tenant), role)}
        if key is not None:
            values["Idempotency-Key"] = str(key)
        return values

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield case, client, headers, foreign_tenant


@pytest.mark.asyncio
async def test_http_receipt_replay_conflict_concurrency_and_authorization(http_case):
    import asyncio
    case, client, headers, foreign_tenant = http_case
    path = f"/api/v1/subcontract/orders/{case.order}/receive"
    key = uuid4()
    payload = {"material_id": str(case.output), "warehouse_location_id": str(case.warehouse), "quantity": "1.000"}
    assert (await client.post(path, json=payload)).status_code == 401
    assert (await client.post(path, headers=headers(key, role="viewer"), json=payload)).status_code == 403
    assert (await client.post(path, headers=headers(key, tenant=foreign_tenant), json=payload)).status_code == 404
    responses = await asyncio.gather(*[
        client.post(path, headers=headers(key), json=payload) for _ in range(2)
    ])
    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    assert (await client.post(path, headers=headers(key, role="viewer"), json=payload)).status_code == 403
    assert await quantity_at(case, case.output, case.warehouse) == D("1")
    equivalent = {**payload, "quantity": 1, "output_batch_number": None}
    assert (await client.post(path, headers=headers(key), json=equivalent)).json() == responses[0].json()
    assert (await client.post(path, headers=headers(key), json={**payload, "quantity": 2})).status_code == 409
    assert (await client.post(path, headers=headers(uuid4()), json=payload)).status_code == 200
    final_key = uuid4()
    final = await client.post(path, headers=headers(final_key), json=payload)
    assert final.status_code == 200 and final.json()["status"] == "completed"
    assert (await client.post(path, headers=headers(final_key), json=payload)).json() == final.json()
    assert await quantity_at(case, case.output, case.warehouse) == D("3")


@pytest.mark.asyncio
async def test_http_manual_return_closes_fulfilled_order_and_preserves_historical_exception(http_case):
    case, client, headers, _ = http_case
    path = f"/api/v1/subcontract/orders/{case.order}"
    historical = f"/api/v1/subcontract/orders/{case.other}"
    async with case.factory() as session:
        for line in (await session.scalars(select(SubcontractOrderLineModel).where(
            SubcontractOrderLineModel.subcontract_order_id == case.order,
        ))).all():
            await session.delete(line)
        other = await session.get(SubcontractOrderModel, case.other)
        other.status = "completed"
        other.received_quantity = D("3")
        await session.commit()

    issue_key = uuid4()
    issue_body = {"material_id": str(case.raw), "from_location_id": str(case.warehouse), "quantity": 1}
    posted = await client.post(path + "/issue", headers=headers(issue_key), json=issue_body)
    assert posted.status_code == 200
    assert (await client.post(path + "/issue", headers=headers(issue_key), json=issue_body)).json() == posted.json()
    assert await quantity_at(case, case.raw, case.warehouse) == D("6")
    output = {"material_id": str(case.output), "warehouse_location_id": str(case.warehouse), "quantity": 3}
    receipt = await client.post(path + "/receive", headers=headers(uuid4()), json=output)
    assert receipt.status_code == 200 and receipt.json()["status"] == "partially_received"
    detail = (await client.get(path, headers=headers())).json()
    assert detail["output_fulfilled"] and not detail["materials_reconciled"]
    assert D(detail["reconciliation_exceptions"][0]["outstanding"]) == D("2")

    return_key = uuid4()
    returned = {"material_id": str(case.raw), "to_location_id": str(case.warehouse), "quantity": 2}
    posted_return = await client.post(path + "/return-material", headers=headers(return_key), json=returned)
    assert posted_return.status_code == 200
    assert (await client.post(path + "/return-material", headers=headers(return_key), json=returned)).json() == posted_return.json()
    assert (await client.post(path + "/return-material", headers=headers(return_key), json={**returned, "quantity": 1})).status_code == 409
    detail = (await client.get(path, headers=headers())).json()
    assert detail["status"] == "completed" and detail["materials_reconciled"]
    old_detail = (await client.get(historical, headers=headers())).json()
    assert old_detail["status"] == "completed" and not old_detail["materials_reconciled"]
    assert D(old_detail["reconciliation_exceptions"][0]["outstanding"]) == D("2")
    assert await quantity_at(case, case.raw, case.warehouse) == D("8")


@pytest.mark.asyncio
async def test_http_failed_posting_rolls_back_stock_and_operation(http_case):
    from backend.app.infrastructure.persistence.models.subcontract_model import SubcontractStockOperationModel

    case, client, headers, _ = http_case
    async with case.factory() as session:
        session.add(BatchModel(tenant_id=case.tenant, material_id=case.output, location_id=case.warehouse,
                               batch_number="collision", status="in_stock", quantity=D("1")))
        await session.commit()
    path = f"/api/v1/subcontract/orders/{case.order}/receive"
    body = {"material_id": str(case.output), "warehouse_location_id": str(case.warehouse), "quantity": 1}
    key = uuid4()
    assert (await client.post(path, headers=headers(key), json={**body, "output_batch_number": "collision"})).status_code == 422
    assert await quantity_at(case, case.raw, case.vendor) == D("3")
    async with case.factory() as session:
        assert await session.get(SubcontractStockOperationModel, (case.tenant, case.order, "receive", key)) is None
    assert (await client.post(path, headers=headers(key), json=body)).status_code == 200

