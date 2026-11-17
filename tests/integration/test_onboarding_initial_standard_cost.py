"""Regression coverage for the active Excel importer and effective cost path.

Uses an isolated SQLite database, never the configured development database.
PostgreSQL lock SQL and concurrent handler ordering are checked separately.
"""
import asyncio
import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
import openpyxl
from fastapi import HTTPException, UploadFile
from sqlalchemy import event, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable

from backend.app.application.inventory.services.onboarding_pricing import (
    agreement_dates, import_date, parse_import_decimal, plan_initial_cost,
)
from backend.app.application.procurement.pricing.direct_standard_cost import (
    ConcurrentCostChangeError, DirectStandardCostHandler, normalize_standard_cost,
)
from backend.app.application.procurement.services.purchase_history_query_service import PurchaseHistoryQueryService
from backend.app.domain.bom.entities.bom import BillOfMaterial
from backend.app.domain.bom.entities.bom_line import BOMLine
from backend.app.domain.bom.services.cost_rollup_service import CostRollupService
from backend.app.infrastructure.persistence.database import Base
from backend.app.infrastructure.persistence.models.material_category_model import MaterialCategoryModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.procurement_pricing_models import (
    MaterialCostHistoryModel, StandardCostRevisionModel, SupplierPriceAgreementModel, PriceOverrideRecordModel,
)
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.models.grn_model import GoodsReceiptNoteModel, GRNLineModel
from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel
from backend.app.infrastructure.persistence.repositories.procurement_pricing_repository import StandardCostRevisionRepository
from backend.app.infrastructure.services.bom_providers import InfrastructureCostProvider, InfrastructureTenantProvider
from backend.app.interfaces.api.v1.routes import inventory, material_onboarding as routes
from backend.app.interfaces.api.v1.schemas.inventory_schemas import SetStandardCostRequest


@pytest_asyncio.fixture
async def env(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def explicit_sqlite_transactions(connection, _):
        connection.isolation_level = None

    @event.listens_for(engine.sync_engine, "begin")
    def begin(connection):
        connection.exec_driver_sql("BEGIN")

    tables = [TenantModel, UnitOfMeasureModel, MaterialCategoryModel, MaterialModel, LocationModel,
              SupplierModel, SupplierPriceAgreementModel, StandardCostRevisionModel, MaterialCostHistoryModel,
              PurchaseOrderModel, GoodsReceiptNoteModel, GRNLineModel, PriceOverrideRecordModel]
    async with engine.begin() as connection:
        # Existing pricing models declare some indexes twice. Avoid unrelated
        # index DDL in this disposable fixture; retain real columns/constraints.
        for model in tables:
            await connection.execute(CreateTable(model.__table__))
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    tenant, user, kg, ton = uuid4(), uuid4(), uuid4(), uuid4()
    now = datetime.now(timezone.utc)
    async with factory() as session:
        session.add(TenantModel(id=tenant, name="Test tenant", slug=str(tenant), currency_code="INR", currency_symbol="₹"))
        session.add_all([
            UnitOfMeasureModel(id=kg, tenant_id=tenant, code="kg", name="Kilogram", precision=4, is_active=True, is_deleted=False, created_at=now, updated_at=now),
            UnitOfMeasureModel(id=ton, tenant_id=tenant, code="TON", name="Tonne", precision=4, is_active=True, is_deleted=False, created_at=now, updated_at=now),
            MaterialCategoryModel(id=uuid4(), tenant_id=tenant, name="METAL", code_prefix="MET", is_active=True, is_deleted=False, created_at=now, updated_at=now),
        ])
        await session.commit()

    class Codes:
        def __init__(self, session):
            pass

        async def validate_manual_code_with_policy(self, **kwargs):
            return SimpleNamespace(code=kwargs["code"])

        async def generate_for_entity(self, **kwargs):
            return "RM-" + kwargs["entity_name"].replace(" ", "-").upper()

    async def permit(*args):
        return None

    monkeypatch.setattr(routes, "ItemCodeService", Codes)
    monkeypatch.setattr(routes, "require_permission", lambda permission: permit)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(container=SimpleNamespace(session_factory=factory))))
    yield SimpleNamespace(factory=factory, tenant=tenant, user=user, kg=kg, ton=ton, request=request)
    routes._sessions.clear()
    await engine.dispose()


def row(name="Brass rod", **changes):
    data = dict(material_name=name, item_code="RM-BRASS", material_category="METAL", uom="Kg",
                supplier_name="Test Supplier", supplier_price="500", supplier_currency="INR",
                supplier_uom="KG", supplier_moq="", proposed_initial_cost="",
                effective_from_date="", effective_to_date="")
    data.update(changes)
    return dict(id=str(uuid4()), row_number=2, classification="new", status="ready",
                data=data, issues=[], protected_changes=[])


async def execute(env, rows, dry_run=False):
    session_id = str(uuid4())
    for number, entry in enumerate(rows, 2):
        entry["row_number"] = number
    routes._sessions[session_id] = dict(tenant_id=str(env.tenant), rows=rows, protected_confirmed=False, status="validated")
    return await routes.execute_session(session_id, routes.ExecuteRequest(dry_run=dry_run), env.request,
                                        env.tenant, env.user, "manager")


async def records(env, model):
    async with env.factory() as session:
        return (await session.execute(select(model))).scalars().all()


@pytest.mark.asyncio
@pytest.mark.parametrize("explicit,expected", [("400", "400.0000"), ("", "500.0000"), ("0", "0.0000"), ("400.12345", "400.1235")])
async def test_new_cost_revision_and_history_are_effective(env, explicit, expected):
    result = await execute(env, [row(proposed_initial_cost=explicit)])
    assert result["created"] == 1 and result["rejected"] == 0, result
    material = (await records(env, MaterialModel))[0]
    revision = (await records(env, StandardCostRevisionModel))[0]
    history = (await records(env, MaterialCostHistoryModel))[0]
    agreement = (await records(env, SupplierPriceAgreementModel))[0]
    assert material.current_cost == revision.requested_cost == history.new_cost == Decimal(expected)
    assert revision.status == "APPROVED" and revision.approved_by is None
    assert history.change_type == "INITIAL_SETUP" and history.old_cost is None
    assert agreement.base_price == Decimal("500") and agreement.status == "DRAFT"
    assert agreement.purchase_uom_id == env.kg


@pytest.mark.asyncio
async def test_repeated_rows_are_grouped_before_selecting_cost(env):
    result = await execute(env, [row(), row(supplier_name="Second Supplier", supplier_price="600")])
    assert result["created"] == 1 and result["rejected"] == 0, result
    assert len(await records(env, SupplierPriceAgreementModel)) == 2
    assert not await records(env, StandardCostRevisionModel)
    assert result["cost_outcomes"][0]["status"] == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_explicit_cost_without_supplier_and_explicit_precedence(env):
    explicit = row(supplier_name="", supplier_price="", supplier_currency="", supplier_uom="", proposed_initial_cost="400")
    result = await execute(env, [explicit])
    assert result["rejected"] == 0 and result["cost_outcomes"][0]["standard_cost"] == "400.0000", result
    assert not await records(env, SupplierPriceAgreementModel)


@pytest.mark.asyncio
async def test_explicit_cost_wins_over_conflicting_quotes(env):
    result = await execute(env, [row(proposed_initial_cost="400"), row(supplier_name="Second", supplier_price="600")])
    assert result["rejected"] == 0, result
    assert (await records(env, MaterialModel))[0].current_cost == Decimal("400")


@pytest.mark.asyncio
async def test_existing_unconfigured_material_is_not_initialized_on_reimport(env):
    await execute(env, [row(supplier_currency="USD")])
    result = await execute(env, [row(supplier_currency="USD", proposed_initial_cost="400")])
    assert result["rejected"] == 0, result
    assert (await records(env, MaterialModel))[0].current_cost == Decimal("0")
    assert not await records(env, StandardCostRevisionModel)


@pytest.mark.asyncio
async def test_manual_supplier_item_code_is_saved_updated_and_preserved_when_blank(env):
    first = await execute(env, [row(supplier_item_code="CAT-BRASS-01", proposed_initial_cost="400")])
    assert first["rejected"] == 0, first
    assert (await records(env, MaterialModel))[0].supplier_item_code == "CAT-BRASS-01"
    update = await execute(env, [row(supplier_item_code="CAT-BRASS-02")])
    assert update["rejected"] == 0, update
    await execute(env, [row(supplier_item_code="")])
    material = (await records(env, MaterialModel))[0]
    assert material.supplier_item_code == "CAT-BRASS-02"
    assert material.current_cost == Decimal("400")
    assert len(await records(env, SupplierPriceAgreementModel)) == 1


@pytest.mark.asyncio
async def test_oversized_supplier_item_code_rejected_before_write(env):
    result = await execute(env, [row(supplier_item_code="x" * 121)])
    assert result["rejected"] == 1, result
    assert not await records(env, MaterialModel)


@pytest.mark.asyncio
async def test_existing_material_override_endpoint_uses_real_command_and_repository(env):
    from backend.app.interfaces.api.v1.routes import procurement_pricing
    from backend.app.interfaces.api.v1.schemas.procurement_pricing_schemas import RecordMaterialPriceOverrideRequest

    await execute(env, [row(proposed_initial_cost="400")])
    material = (await records(env, MaterialModel))[0]
    async with env.factory() as session:
        result = await procurement_pricing.record_price_override(
            RecordMaterialPriceOverrideRequest(material_id=material.id, suggested_price=500,
                                               override_price=450, override_reason="BULK_DISCOUNT"),
            session, str(env.tenant), str(env.user),
        )
        history = await procurement_pricing.list_price_overrides(session, str(env.tenant), str(material.id))
    assert len(history) == 1
    assert history[0]["id"] == result["override_id"]
    assert history[0]["suggested_price"] == Decimal("500")
    assert history[0]["override_price"] == Decimal("450")
    assert history[0]["variance_percent"] == Decimal("-10.00")
    assert history[0]["override_by"] == env.user
    assert (await records(env, MaterialModel))[0].current_cost == Decimal("400")


@pytest.mark.asyncio
async def test_material_override_cannot_reference_other_tenant_material(env):
    from backend.app.interfaces.api.v1.routes import procurement_pricing
    from backend.app.interfaces.api.v1.schemas.procurement_pricing_schemas import RecordMaterialPriceOverrideRequest

    await execute(env, [row()])
    material = (await records(env, MaterialModel))[0]
    async with env.factory() as session:
        with pytest.raises(HTTPException) as error:
            await procurement_pricing.record_price_override(
                RecordMaterialPriceOverrideRequest(material_id=material.id, suggested_price=500,
                                                   override_price=450, override_reason="OTHER"),
                session, str(uuid4()), str(env.user),
            )
        assert error.value.status_code == 400
    assert not await records(env, PriceOverrideRecordModel)


@pytest.mark.asyncio
async def test_generated_supplier_dropdown_values_upload_to_existing_supplier(env):
    supplier_id = uuid4()
    async with env.factory() as session:
        session.add(SupplierModel(id=supplier_id, tenant_id=env.tenant, code="SUP-EXISTING",
                                  name='Existing, "Supplier"', is_active=True, is_deleted=False))
        await session.commit()
    response = await routes.get_template(format="xlsx", request=env.request, tenant_id=env.tenant)
    content = b"".join([chunk async for chunk in response.body_iterator])
    workbook = openpyxl.load_workbook(io.BytesIO(content))
    worksheet = workbook["Raw Materials"]
    worksheet.delete_rows(2)

    def first_option(name):
        sheet, bounds = next(workbook.defined_names[name].destinations)
        return workbook[sheet][bounds][0][0].value

    data = {"Item Code": "RM-BRASS", "Material Name": "Brass rod", "Category": "METAL",
            "Base Unit": first_option("BaseUnitOptions"),
            "Supplier Name": first_option("SupplierNameOptions"),
            "Supplier Currency": first_option("SupplierCurrencyOptions"),
            "Supplier UOM": first_option("SupplierUOMOptions"),
            "Supplier Item Code": "CAT-ROD", "Supplier Price": 500, "Proposed Initial Cost": 400}
    worksheet.append([data.get(cell.value, "") for cell in worksheet[1]])
    output = io.BytesIO()
    workbook.save(output)
    upload = await routes.create_session(UploadFile(filename="template.xlsx", file=io.BytesIO(output.getvalue())), env.tenant, env.user)
    mapping = routes._suggest_mapping(upload["headers"])
    await routes.validate_session(upload["session_id"], routes.ValidateRequest(mapping=mapping), env.request, env.tenant)
    preview = await routes.get_preview(upload["session_id"], env.request, env.tenant, env.user, "manager")
    assert preview["cost_outcomes"][0]["standard_cost"] == "400.0000", preview
    assert not await records(env, MaterialModel)
    result = await routes.execute_session(upload["session_id"], routes.ExecuteRequest(dry_run=False), env.request,
                                          env.tenant, env.user, "manager")
    assert result["rejected"] == 0, result
    assert len(await records(env, SupplierModel)) == 1
    agreement = (await records(env, SupplierPriceAgreementModel))[0]
    assert agreement.supplier_id == supplier_id
    assert agreement.base_price == Decimal("500")
    material = (await records(env, MaterialModel))[0]
    assert material.current_cost == Decimal("400")
    assert material.supplier_item_code == "CAT-ROD"


@pytest.mark.asyncio
async def test_excel_upload_mapping_preview_and_execution_share_the_same_outcome(env):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Raw Materials"
    worksheet.append(["Item Code", "Material Name", "Category", "Base Unit", "Supplier Name", "Supplier Price",
                      "Supplier Currency", "Supplier UOM", "Effective From", "Proposed Initial Cost"])
    worksheet.append(["RM-BRASS", "Brass rod", "METAL", "Kg", "Test Supplier", 500, "INR", "kg",
                      datetime.now().replace(hour=0, minute=0, second=0, microsecond=0), 400])
    buffer = io.BytesIO()
    workbook.save(buffer)
    upload = await routes.create_session(UploadFile(filename="onboarding.xlsx", file=io.BytesIO(buffer.getvalue())), env.tenant, env.user)
    mapping = routes._suggest_mapping(upload["headers"])
    await routes.validate_session(upload["session_id"], routes.ValidateRequest(mapping=mapping), env.request, env.tenant)
    preview = await routes.get_preview(upload["session_id"], env.request, env.tenant, env.user, "manager")
    assert preview["cost_outcomes"][0]["standard_cost"] == "400.0000", preview
    assert preview["summary"]["supplier_pricing"]["supplier_agreements_draft"] == 1
    assert not await records(env, MaterialModel)
    result = await routes.execute_session(upload["session_id"], routes.ExecuteRequest(dry_run=False), env.request, env.tenant, env.user, "manager")
    assert result["created"] == 1 and result["rejected"] == 0, result
    assert (await records(env, MaterialModel))[0].current_cost == Decimal("400")


@pytest.mark.asyncio
async def test_identical_repeated_rows_and_reimport_are_idempotent(env):
    first = await execute(env, [row(), row()])
    assert first["created"] == 1 and first["rejected"] == 0, first
    second = await execute(env, [row(proposed_initial_cost="900")])
    assert second["rejected"] == 0, second
    assert len(await records(env, SupplierPriceAgreementModel)) == 1
    assert len(await records(env, StandardCostRevisionModel)) == 1
    assert len(await records(env, MaterialCostHistoryModel)) == 1
    assert (await records(env, MaterialModel))[0].current_cost == Decimal("500")
    assert second["skip_details"] and second["warnings"]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [dict(supplier_price="600"), dict(supplier_moq="5"), dict(supplier_uom="TON"),
                                    dict(effective_from_date="2020-01-01"), dict(effective_to_date="2099-01-01")])
async def test_changed_overlapping_agreement_terms_are_rejected(env, change):
    await execute(env, [row()])
    result = await execute(env, [row(**change)])
    assert result["rejected"] == 1 and "overlap" in result["error_messages"][0].lower(), result
    assert len(await records(env, SupplierPriceAgreementModel)) == 1
    assert len(await records(env, MaterialCostHistoryModel)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("change,warning", [(dict(supplier_uom="TON"), "UOM"), (dict(supplier_currency="USD"), "currency")])
async def test_incompatible_quote_is_saved_without_initializing_cost(env, change, warning):
    result = await execute(env, [row(**change)])
    assert result["rejected"] == 0, result
    assert len(await records(env, SupplierPriceAgreementModel)) == 1
    assert not await records(env, StandardCostRevisionModel)
    assert warning in result["warnings"][0]


@pytest.mark.asyncio
async def test_no_cost_permission_preserves_import_and_reports_outcome(env, monkeypatch):
    async def denied(*args):
        raise HTTPException(status_code=403)
    monkeypatch.setattr(routes, "require_permission", lambda permission: denied)
    result = await execute(env, [row(proposed_initial_cost="400")])
    assert result["created"] == 1 and result["rejected"] == 0, result
    assert "permission" in result["warnings"][0]
    assert not await records(env, StandardCostRevisionModel)
    assert not await records(env, MaterialCostHistoryModel)


@pytest.mark.asyncio
async def test_pending_revision_is_preserved_without_reimport_duplication(env):
    await execute(env, [row()])
    material = (await records(env, MaterialModel))[0]
    async with env.factory() as session:
        session.add(StandardCostRevisionModel(id=uuid4(), tenant_id=env.tenant, material_id=material.id,
                    requested_by=env.user, requested_cost=Decimal("600"), current_cost=Decimal("500"),
                    reason="MANUAL_ADJUSTMENT", status="PENDING", is_deleted=False))
        await session.commit()
    await execute(env, [row(proposed_initial_cost="600")])
    assert len(await records(env, StandardCostRevisionModel)) == 2


@pytest.mark.asyncio
async def test_partial_success_and_dry_run_use_the_same_checks(env):
    rows = [row(), row("Bad supplier", item_code="RM-BAD", supplier_uom="UNKNOWN")]
    dry = await execute(env, rows, dry_run=True)
    assert dry["created"] == 1 and dry["rejected"] == 1, dry
    assert not await records(env, MaterialModel)
    result = await execute(env, rows)
    assert result["created"] == dry["created"] and result["rejected"] == dry["rejected"], result
    assert len(await records(env, MaterialModel)) == 1
    assert len(await records(env, MaterialCostHistoryModel)) == 1


@pytest.mark.asyncio
async def test_identity_conflicts_do_not_create_materials(env):
    result = await execute(env, [row(), row("Different name")])
    assert result["rejected"] == 2, result
    assert not await records(env, MaterialModel)


@pytest.mark.asyncio
async def test_direct_action_refreshes_bom_and_preserves_history(env):
    await execute(env, [row(proposed_initial_cost="400")])
    material = (await records(env, MaterialModel))[0]
    bom_id = uuid4()
    bom = BillOfMaterial(id=bom_id, tenant_id=env.tenant, variant_id=uuid4(), version="1",
        valid_from=datetime.now(timezone.utc), created_by=env.user,
        lines=[BOMLine(id=uuid4(), tenant_id=env.tenant, bom_id=bom_id, material_id=material.id,
                       quantity=Decimal("5"), scrap_percentage=Decimal("0"), unit_id=env.kg)])
    async with env.factory() as session:
        rollup = CostRollupService(AsyncMock(), InfrastructureCostProvider(session), InfrastructureTenantProvider(session))
        before = await rollup.calculate_standard_cost(env.tenant, bom)
    assert before["is_complete"] and before["total_cost"] == Decimal("2000")
    result = await inventory.set_standard_cost(material.id, SetStandardCostRequest(new_cost="450", reason="Annual review", expected_current_cost="400"), env.request, env.tenant, env.user)
    assert result.new_cost == Decimal("450")
    async with env.factory() as session:
        rollup = CostRollupService(AsyncMock(), InfrastructureCostProvider(session), InfrastructureTenantProvider(session))
        assert (await rollup.calculate_standard_cost(env.tenant, bom))["total_cost"] == Decimal("2250")
        assert await InfrastructureCostProvider(session).get_material_cost(uuid4(), material.id) is None
    history = await records(env, MaterialCostHistoryModel)
    assert len(history) == 2 and sorted(h.new_cost for h in history) == [Decimal("400"), Decimal("450")]


@pytest.mark.asyncio
async def test_missing_cost_is_incomplete_and_explicit_zero_is_complete(env):
    await execute(env, [row(supplier_currency="USD")])
    material = (await records(env, MaterialModel))[0]
    async with env.factory() as session:
        assert await InfrastructureCostProvider(session).get_material_cost(env.tenant, material.id) is None
    await inventory.set_standard_cost(material.id, SetStandardCostRequest(new_cost="0", expected_current_cost="0"), env.request, env.tenant, env.user)
    async with env.factory() as session:
        assert await InfrastructureCostProvider(session).get_material_cost(env.tenant, material.id) == Decimal("0")


@pytest.mark.asyncio
async def test_completed_grns_update_purchase_summary_without_changing_standard_cost(env):
    await execute(env, [row(proposed_initial_cost="400")])
    material = (await records(env, MaterialModel))[0]
    supplier = (await records(env, SupplierModel))[0]
    now = datetime.now(timezone.utc)
    async with env.factory() as session:
        summary = await PurchaseHistoryQueryService(session).get_purchasing_summary(material.id, env.tenant)
        assert summary["latest_purchase_price"] is None and summary["purchase_count"] == 0
        po = PurchaseOrderModel(id=uuid4(), tenant_id=env.tenant, supplier_id=supplier.id,
                po_number="PO-TEST", order_date=now.date(), created_by=env.user)
        session.add(po)
        for index, (status, price) in enumerate([("received", "550"), ("reversed", "999"), ("pending_receipt", "999")]):
            grn = GoodsReceiptNoteModel(id=uuid4(), tenant_id=env.tenant, grn_number=f"GRN-{index}",
                    purchase_order_id=po.id, supplier_id=supplier.id, actual_receipt_date=now + timedelta(days=index),
                    status=status, created_by=env.user)
            session.add(grn)
            session.add(GRNLineModel(id=uuid4(), tenant_id=env.tenant, grn_id=grn.id, po_line_id=uuid4(),
                    material_id=material.id, po_quantity=5, received_quantity=5, unit_price=Decimal(price)))
        await session.commit()
    async with env.factory() as session:
        summary = await PurchaseHistoryQueryService(session).get_purchasing_summary(material.id, env.tenant)
        assert summary["latest_purchase_price"] == Decimal("550") and summary["purchase_count"] == 1
        assert summary["last_supplier_name"] == supplier.name
        other = await PurchaseHistoryQueryService(session).get_purchasing_summary(material.id, uuid4())
        assert other["latest_purchase_price"] is None
    assert (await records(env, MaterialModel))[0].current_cost == Decimal("400")
    assert len(await records(env, MaterialCostHistoryModel)) == 1


@pytest.mark.asyncio
async def test_direct_endpoint_conflict_reason_and_tenant_boundaries(env):
    await execute(env, [row(proposed_initial_cost="400")])
    material = (await records(env, MaterialModel))[0]
    for body, tenant, expected_status in [
        (SetStandardCostRequest(new_cost="450", expected_current_cost="399", reason="Review"), env.tenant, 409),
        (SetStandardCostRequest(new_cost="450", expected_current_cost="400"), env.tenant, 422),
        (SetStandardCostRequest(new_cost="450", reason="Review"), uuid4(), 404),
    ]:
        with pytest.raises(HTTPException) as error:
            await inventory.set_standard_cost(material.id, body, env.request, tenant, env.user)
        assert error.value.status_code == expected_status
    assert len(await records(env, MaterialCostHistoryModel)) == 1


@pytest.mark.asyncio
async def test_failed_history_write_rolls_back_effective_cost(env):
    await execute(env, [row(proposed_initial_cost="400")])
    material = (await records(env, MaterialModel))[0]
    with pytest.raises(RuntimeError, match="history failure"):
        async with env.factory() as session:
            @event.listens_for(session.sync_session, "before_flush")
            def fail_history(db, *_):
                if any(isinstance(item, MaterialCostHistoryModel) for item in db.new):
                    raise RuntimeError("history failure")
            await DirectStandardCostHandler(session).handle(tenant_id=env.tenant, material_id=material.id,
                user_id=env.user, new_cost=Decimal("800"), reason="Change")
            await session.commit()
    assert (await records(env, MaterialModel))[0].current_cost == Decimal("400")
    assert len(await records(env, StandardCostRevisionModel)) == 1
    assert len(await records(env, MaterialCostHistoryModel)) == 1


@pytest.mark.asyncio
async def test_concurrent_writers_compare_under_lock():
    lock = asyncio.Lock()
    state = {"cost": Decimal("400"), "history": []}

    class Session:
        def add_all(self, entries):
            state["history"].extend(item for item in entries if isinstance(item, MaterialCostHistoryModel))
        async def flush(self):
            pass

    class Repo:
        async def get_material_current_cost(self, *args, lock=False):
            assert lock
            await globals_lock.acquire()
            return state["cost"]
        async def get_approved_cost(self, *args):
            return object()
        async def update_material_current_cost(self, tenant, material, cost, user):
            state["cost"] = cost
            return True

    globals_lock = lock
    async def writer(value):
        handler = DirectStandardCostHandler(Session())
        handler.revisions = Repo()
        try:
            return await handler.handle(tenant_id=uuid4(), material_id=uuid4(), user_id=uuid4(),
                new_cost=Decimal(value), expected_current_cost=Decimal("400"), reason="Review")
        finally:
            lock.release()
    results = await asyncio.gather(writer("450"), writer("500"), return_exceptions=True)
    assert sum(isinstance(result, ConcurrentCostChangeError) for result in results) == 1
    assert len(state["history"]) == 1 and state["history"][0].old_cost == Decimal("400")


@pytest.mark.asyncio
async def test_repository_emits_tenant_scoped_for_update():
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: Decimal("400"))))
    tenant, material = uuid4(), uuid4()
    await StandardCostRevisionRepository(session).get_material_current_cost(tenant, material, lock=True)
    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql and "tenant_id" in sql and "is_deleted" in sql


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1000000000"])
def test_invalid_import_numbers_are_rejected(value):
    with pytest.raises(ValueError):
        parse_import_decimal(value)


@pytest.mark.parametrize("changes", [dict(supplier_price="NaN"), dict(supplier_price="0"), dict(supplier_moq="Infinity"),
                                     dict(opening_stock="NaN"), dict(supplier_currency="A1B"),
                                     dict(effective_from_date="not-a-date"), dict(supplier_uom="")])
def test_active_row_validator_rejects_invalid_prices_units_currency_and_dates(changes):
    _, status, issues, _ = routes._validate_row(row(**changes)["data"], 2, {})
    assert status == "error" and any(issue["severity"] == "error" for issue in issues)


def test_excel_dates_and_cost_precision():
    assert import_date(datetime(2026, 11, 16)) == "2026-11-16"
    assert agreement_dates({"effective_from_date": "2026-11-16 00:00:00"}, datetime.now().date())[0].day == 16
    assert normalize_standard_cost(Decimal("400.12345")) == Decimal("400.1235")
