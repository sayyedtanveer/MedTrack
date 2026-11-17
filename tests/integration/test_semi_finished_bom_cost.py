"""Phase C: real repository/provider costing against a disposable database."""
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable

from backend.app.application.bom.handlers.bom_advanced_handlers import BOMAdvancedHandlers
from backend.app.application.bom.queries.bom_advanced_queries import GetBOMCostQuery, GetBOMTreeQuery
from backend.app.infrastructure.persistence.models.bom_model import BOMModel, BOMLineModel
from backend.app.infrastructure.persistence.models.bom_operation_model import BOMOperationModel
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.procurement_pricing_models import StandardCostRevisionModel, MaterialCostHistoryModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.models.operation_model import OperationModel
from backend.app.infrastructure.persistence.models.workstation_model import WorkstationModel
from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository
from backend.app.interfaces.api.v1.schemas.bom_schemas import BOMCostResponse


@compiles(JSONB, "sqlite")
def compile_jsonb_for_fixture(element, compiler, **kwargs):
    return "JSON"


@pytest_asyncio.fixture
async def case():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    models = [TenantModel, UnitOfMeasureModel, MaterialModel, ItemTemplateModel, ItemVariantModel,
              BOMModel, BOMLineModel, BOMOperationModel, StandardCostRevisionModel, MaterialCostHistoryModel,
              OperationModel, WorkstationModel]
    async with engine.begin() as connection:
        # Existing pricing model metadata has duplicate index declarations.
        # Only table/constraint DDL is needed for this isolated fixture.
        for model in models:
            await connection.execute(CreateTable(model.__table__))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    tenant, user, unit, other_unit = uuid4(), uuid4(), uuid4(), uuid4()
    now = datetime.now(timezone.utc)
    async with factory() as session:
        session.add(TenantModel(id=tenant, name="Cost test", slug=str(tenant), currency_code="INR", currency_symbol="₹"))
        session.add_all([UnitOfMeasureModel(id=unit, tenant_id=tenant, code="PCS", name="Piece", precision=0,
                            created_at=now, updated_at=now, is_active=True, is_deleted=False),
                         UnitOfMeasureModel(id=other_unit, tenant_id=tenant, code="KG", name="Kilogram", precision=4,
                            created_at=now, updated_at=now, is_active=True, is_deleted=False)])
        materials = []
        for name, cost, kind in [("A", "100", "raw"), ("B", "10", "raw"), ("C", "10", "raw"),
                                 ("Extra", "12", "raw"), ("Semi", "90", "semi_finished")]:
            material = MaterialModel(id=uuid4(), tenant_id=tenant, code=name, name=name,
                material_type=kind, base_unit_id=unit, current_cost=Decimal(cost), is_active=True, is_deleted=False)
            materials.append(material)
            session.add(material)
            session.add(StandardCostRevisionModel(id=uuid4(), tenant_id=tenant, material_id=material.id,
                requested_by=user, requested_cost=Decimal(cost), current_cost=0, reason="INITIAL_SETUP",
                status="APPROVED", approved_at=now, is_deleted=False))
            session.add(MaterialCostHistoryModel(id=uuid4(), tenant_id=tenant, material_id=material.id,
                old_cost=None, new_cost=Decimal(cost), change_type="INITIAL_SETUP", source_type="MANUAL", created_at=now))
        parent_template = ItemTemplateModel(id=uuid4(), tenant_id=tenant, code="PT", name="Parent", base_unit_id=unit)
        child_template = ItemTemplateModel(id=uuid4(), tenant_id=tenant, code="CT", name="Child", base_unit_id=unit)
        session.add_all([parent_template, child_template])
        parent_variant = ItemVariantModel(id=uuid4(), tenant_id=tenant, template_id=parent_template.id,
            code="PV", name="Parent variant", variant_key="P", base_unit_id=unit)
        child_variant = ItemVariantModel(id=uuid4(), tenant_id=tenant, template_id=child_template.id,
            code="CV", name="Child assembly", variant_key="C", base_unit_id=unit, material_id=materials[4].id)
        session.add_all([parent_variant, child_variant])
        parent = BOMModel(id=uuid4(), tenant_id=tenant, variant_id=parent_variant.id, version="1",
            valid_from=now, created_by=user, is_active=True)
        child = BOMModel(id=uuid4(), tenant_id=tenant, variant_id=child_variant.id, version="1",
            valid_from=now, created_by=user, is_active=True, making_charge=30, making_charge_basis="PER_PIECE")
        session.add_all([parent, child])
        lines = [BOMLineModel(id=uuid4(), tenant_id=tenant, bom_id=child.id, material_id=m.id, quantity=1, unit_id=unit)
                 for m in materials[:3]]
        semi_line = BOMLineModel(id=uuid4(), tenant_id=tenant, bom_id=parent.id, material_id=materials[4].id, quantity=2, unit_id=unit)
        extra_line = BOMLineModel(id=uuid4(), tenant_id=tenant, bom_id=parent.id, material_id=materials[3].id, quantity=1, unit_id=unit)
        session.add_all([*lines, semi_line, extra_line])
        await session.commit()
    yield SimpleNamespace(factory=factory, tenant=tenant, user=user, unit=unit, other_unit=other_unit,
        parent=parent, child=child, parent_variant=parent_variant, child_variant=child_variant,
        child_template=child_template, materials=materials, semi_line=semi_line, extra_line=extra_line, raw_lines=lines)
    await engine.dispose()


async def change(case, model, identity, **values):
    async with case.factory() as session:
        item = (await session.execute(select(model).where(model.id == identity, model.tenant_id == case.tenant))).scalar_one()
        for key, value in values.items():
            setattr(item, key, value)
        await session.commit()


async def calculate(case, *, max_depth=20):
    async with case.factory() as session:
        handlers = BOMAdvancedHandlers(SimpleNamespace(_session=session), BOMRepository(session))
        return await handlers.handle_get_cost(GetBOMCostQuery(tenant_id=case.tenant, bom_id=case.parent.id, max_depth=max_depth))


@pytest.mark.asyncio
async def test_linked_material_312_and_stored_90_history_untouched(case):
    result = await calculate(case)
    assert result["is_complete"] and result["total_cost"] == Decimal("312"), result
    assert result["material_cost"] == Decimal("312") and result["making_cost"] == 0
    assert sum(Decimal(str(node["cost"])) for node in result["tree"]["children"]) == result["material_cost"]
    branch = result["tree"]["children"][0]
    assert branch["cost"] == 300 and branch["making_cost"] == 60
    assert sum(node["cost"] for node in branch["children"]) == 240
    async with case.factory() as session:
        material = await session.get(MaterialModel, case.materials[4].id)
        assert material.current_cost == 90
        assert (await session.execute(select(func.count()).select_from(MaterialCostHistoryModel))).scalar_one() == 5
        assert (await session.execute(select(func.count()).select_from(StandardCostRevisionModel))).scalar_one() == 5
        handler = BOMAdvancedHandlers(SimpleNamespace(_session=session), BOMRepository(session))
        tree = await handler.handle_get_tree(GetBOMTreeQuery(tenant_id=case.tenant, bom_id=case.parent.id))
        assert tree == result["tree"] and tree["currency_symbol"] == "₹"


@pytest.mark.asyncio
@pytest.mark.parametrize("charge", [None, Decimal("0"), Decimal("40")])
async def test_bom_details_return_saved_outside_processing_charge(case, charge):
    from backend.app.interfaces.api.v1.routes.boms import get_bom

    basis = None if charge is None else "PER_PIECE"
    await change(case, BOMModel, case.parent.id, making_charge=charge, making_charge_basis=basis)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        container=SimpleNamespace(session_factory=case.factory, event_dispatcher=None),
    )))
    response = await get_bom(case.parent.id, request, case.tenant)
    assert response.making_charge == charge
    assert response.making_charge_basis == basis


@pytest.mark.asyncio
@pytest.mark.parametrize("reference", ["variant", "template"])
async def test_direct_nested_targets_remain_312(case, reference):
    if reference == "variant":
        await change(case, BOMLineModel, case.semi_line.id, material_id=None, variant_id=case.child_variant.id)
    else:
        await change(case, BOMModel, case.child.id, variant_id=None, template_id=case.child_template.id)
        await change(case, BOMLineModel, case.semi_line.id, material_id=None, template_id=case.child_template.id)
    assert (await calculate(case))["total_cost"] == Decimal("312")


@pytest.mark.asyncio
async def test_raw_leaf_approved_cost_and_unmapped_semi_leaf(case):
    await change(case, ItemVariantModel, case.child_variant.id, material_id=None)
    result = await calculate(case)
    assert result["is_complete"] and result["total_cost"] == Decimal("192")
    await change(case, BOMLineModel, case.semi_line.id, material_id=case.materials[0].id)
    assert (await calculate(case))["total_cost"] == Decimal("212")


@pytest.mark.asyncio
@pytest.mark.parametrize("model_name,changes,reason", [
    ("child", {"is_active": False}, "BOM_MISSING"),
    ("child", {"is_deleted": True}, "BOM_MISSING"),
    ("variant", {"is_active": False}, "MAPPING_INVALID"),
    ("variant", {"is_deleted": True}, "MAPPING_INVALID"),
    ("material", {"is_active": False}, "COMPONENT_INVALID"),
    ("material", {"is_deleted": True}, "COMPONENT_INVALID"),
    ("template", {"is_active": False}, "TARGET_INVALID"),
    ("template", {"is_deleted": True}, "TARGET_INVALID"),
])
async def test_invalid_manufacturing_links_never_fall_back_to_90(case, model_name, changes, reason):
    model, identity = {"child": (BOMModel, case.child.id), "variant": (ItemVariantModel, case.child_variant.id),
                       "material": (MaterialModel, case.materials[4].id),
                       "template": (ItemTemplateModel, case.child_template.id)}[model_name]
    await change(case, model, identity, **changes)
    result = await calculate(case)
    assert not result["is_complete"] and result["total_cost"] == 0, result
    assert result["missing_costs"][0]["reason"] == reason
    assert result["tree"]["children"][0]["cost"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("duplicate", ["variant", "bom"])
async def test_ambiguous_active_links_are_incomplete(case, duplicate):
    async with case.factory() as session:
        if duplicate == "variant":
            session.add(ItemVariantModel(id=uuid4(), tenant_id=case.tenant, template_id=case.child_template.id,
                code="Duplicate", name="Duplicate", variant_key="D", base_unit_id=case.unit, material_id=case.materials[4].id))
        else:
            session.add(BOMModel(id=uuid4(), tenant_id=case.tenant, variant_id=case.child_variant.id,
                version="2", valid_from=datetime.now(timezone.utc), created_by=case.user, is_active=True))
        await session.commit()
    result = await calculate(case)
    assert not result["is_complete"]
    assert result["missing_costs"][0]["reason"] in {"BOM_AMBIGUOUS", "MAPPING_AMBIGUOUS"}


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["output_mismatch", "line_mismatch", "line_missing", "output_missing", "foreign_unit"])
async def test_child_output_uom_is_required_and_exact(case, failure):
    if failure == "output_mismatch":
        await change(case, ItemVariantModel, case.child_variant.id, base_unit_id=case.other_unit)
    elif failure == "output_missing":
        await change(case, ItemVariantModel, case.child_variant.id, base_unit_id=None)
    elif failure == "foreign_unit":
        await change(case, ItemVariantModel, case.child_variant.id, base_unit_id=uuid4())
    else:
        await change(case, BOMLineModel, case.semi_line.id, unit_id=case.other_unit if failure == "line_mismatch" else None)
    result = await calculate(case)
    assert not result["is_complete"] and result["total_cost"] == 0
    assert result["missing_costs"][0]["reason"] in {"OUTPUT_UOM_MISSING", "UOM_INCOMPATIBLE"}


@pytest.mark.asyncio
async def test_child_operations_and_making_are_counted_once(case):
    async with case.factory() as session:
        workstation = WorkstationModel(id=uuid4(), tenant_id=case.tenant, code="W", name="Work", hourly_rate=10)
        operation = OperationModel(id=uuid4(), tenant_id=case.tenant, operation_code="10", name="Assembly",
            workstation_id=workstation.id, setup_time=30, run_time=30, created_by=case.user)
        session.add_all([workstation, operation, BOMOperationModel(id=uuid4(), tenant_id=case.tenant,
            bom_id=case.child.id, operation_id=operation.id, sequence=1)])
        await session.commit()
    result = await calculate(case)
    assert result["total_cost"] == Decimal("332")
    branch = result["tree"]["children"][0]
    assert branch["cost"] == 320 and branch["operation_cost"] == 20 and branch["making_cost"] == 60
    assert result["operation_cost"] == 0 and result["making_cost"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["operation_deleted", "operation_inactive", "workstation_foreign", "workstation_deleted"])
async def test_invalid_operation_or_workstation_is_incomplete(case, invalid):
    async with case.factory() as session:
        workstation = WorkstationModel(id=uuid4(), tenant_id=uuid4() if invalid == "workstation_foreign" else case.tenant,
            code="W", name="Work", hourly_rate=10, is_deleted=invalid == "workstation_deleted")
        operation = OperationModel(id=uuid4(), tenant_id=case.tenant, operation_code="10", name="Assembly",
            workstation_id=workstation.id, setup_time=30, run_time=30, created_by=case.user,
            is_deleted=invalid == "operation_deleted", is_active=invalid != "operation_inactive")
        session.add_all([workstation, operation, BOMOperationModel(id=uuid4(), tenant_id=case.tenant,
            bom_id=case.child.id, operation_id=operation.id, sequence=1)])
        await session.commit()
    result = await calculate(case)
    assert not result["is_complete"] and result["total_cost"] == 0
    assert any(issue["reason"] == "OPERATION_COST_MISSING" for issue in result["missing_costs"])


@pytest.mark.asyncio
async def test_deleted_component_lines_are_not_costed(case):
    await change(case, BOMLineModel, case.raw_lines[0].id, is_deleted=True)
    assert (await calculate(case))["total_cost"] == Decimal("112")


@pytest.mark.asyncio
async def test_real_provider_uses_shared_resolution_with_existing_constructor(case):
    from backend.app.domain.bom.services.cost_rollup_service import CostRollupService
    from backend.app.infrastructure.services.bom_providers import InfrastructureBOMProvider, InfrastructureCostProvider, InfrastructureTenantProvider
    async with case.factory() as session:
        repository = BOMRepository(session)
        parent = await repository.get_by_id(case.parent.id, case.tenant)
        service = CostRollupService(InfrastructureBOMProvider(repository), InfrastructureCostProvider(session), InfrastructureTenantProvider(session))
        assert (await service.calculate_standard_cost(case.tenant, parent))["total_cost"] == Decimal("312")


@pytest.mark.asyncio
async def test_repeated_child_branches_are_valid_and_scrap_is_applied_once(case):
    async with case.factory() as session:
        session.add(BOMLineModel(id=uuid4(), tenant_id=case.tenant, bom_id=case.parent.id,
            material_id=case.materials[4].id, quantity=3, unit_id=case.unit))
        await session.commit()
    assert (await calculate(case))["total_cost"] == Decimal("762")
    await change(case, BOMLineModel, case.semi_line.id, scrap_percentage=10)
    await change(case, BOMLineModel, case.raw_lines[0].id, scrap_percentage=10)
    # Child = 110+10+10+30=160; effective parent qty = 2.2+3 = 5.2.
    assert (await calculate(case))["total_cost"] == Decimal("844")


@pytest.mark.asyncio
async def test_multiple_semi_finished_levels(case):
    async with case.factory() as session:
        middle = MaterialModel(id=uuid4(), tenant_id=case.tenant, code="MID", name="Middle",
            material_type="semi_finished", base_unit_id=case.unit, current_cost=999)
        variant = ItemVariantModel(id=uuid4(), tenant_id=case.tenant, template_id=case.child_template.id,
            code="MID", name="Middle", variant_key="MID", material_id=middle.id, base_unit_id=case.unit)
        bom = BOMModel(id=uuid4(), tenant_id=case.tenant, variant_id=variant.id, version="1", is_active=True,
            created_by=case.user, valid_from=datetime.now(timezone.utc), making_charge=5, making_charge_basis="PER_PIECE")
        session.add_all([middle, variant, bom, BOMLineModel(id=uuid4(), tenant_id=case.tenant,
            bom_id=bom.id, material_id=case.materials[4].id, quantity=3, unit_id=case.unit)])
        await session.commit()
    await change(case, BOMLineModel, case.semi_line.id, material_id=middle.id)
    result = await calculate(case)
    assert result["total_cost"] == Decimal("922")
    nested = result["tree"]["children"][0]["children"][0]
    assert {row["line_id"] for row in nested["children"]} == {str(line.id) for line in case.raw_lines}

    await change(case, BOMLineModel, case.semi_line.id, unit_id=None)
    result = await calculate(case)
    branch = result["tree"]["children"][0]
    assert result["is_complete"] is False and result["total_cost"] == 0
    assert branch["reason"] == "OUTPUT_UOM_MISSING" and branch["cost"] is None
    raw_rows = branch["children"][0]["children"]
    assert {row["line_id"] for row in raw_rows} == {str(line.id) for line in case.raw_lines}
    assert all(row["cost"] is None for row in raw_rows)


@pytest.mark.asyncio
async def test_cycle_and_depth_limits_report_incomplete(case):
    result = await calculate(case, max_depth=1)
    assert not result["is_complete"] and result["missing_costs"][0]["reason"] == "MAX_DEPTH"
    async with case.factory() as session:
        session.add(BOMLineModel(id=uuid4(), tenant_id=case.tenant, bom_id=case.child.id,
            variant_id=case.parent_variant.id, quantity=1, unit_id=case.unit))
        await session.commit()
    result = await calculate(case)
    assert not result["is_complete"] and result["total_cost"] == 0
    assert any(issue["reason"] == "CYCLE_DETECTED" for issue in result["missing_costs"])


@pytest.mark.asyncio
async def test_missing_raw_cost_propagates_and_configured_zero_remains_valid(case):
    async with case.factory() as session:
        revision = (await session.execute(select(StandardCostRevisionModel).where(
            StandardCostRevisionModel.tenant_id == case.tenant,
            StandardCostRevisionModel.material_id == case.materials[0].id))).scalar_one()
        revision.is_deleted = True
        await session.commit()
    result = await calculate(case)
    assert not result["is_complete"] and result["total_cost"] == 0
    assert any(issue["reason"] == "STANDARD_COST_MISSING" for issue in result["missing_costs"])
    async with case.factory() as session:
        revision = (await session.execute(select(StandardCostRevisionModel).where(
            StandardCostRevisionModel.tenant_id == case.tenant,
            StandardCostRevisionModel.material_id == case.materials[0].id))).scalar_one()
        revision.is_deleted = False
        material = await session.get(MaterialModel, case.materials[0].id)
        material.current_cost = 0
        await session.commit()
    result = await calculate(case)
    assert result["is_complete"] and result["total_cost"] == Decimal("112")


@pytest.mark.asyncio
@pytest.mark.parametrize("foreign", ["variant", "bom", "line", "material"])
async def test_tenant_boundaries_do_not_resolve_foreign_components(case, foreign):
    if foreign == "variant":
        await change(case, BOMLineModel, case.semi_line.id, material_id=None, variant_id=uuid4())
    elif foreign == "bom":
        await change(case, BOMModel, case.child.id, tenant_id=uuid4())
    elif foreign == "line":
        await change(case, BOMLineModel, case.raw_lines[0].id, tenant_id=uuid4())
        # A corrupt cross-tenant relationship cannot yield a healthy low total.
        result = await calculate(case)
        assert not result["is_complete"]
        assert any(issue["reason"] == "TENANT_MISMATCH" for issue in result["missing_costs"])
        return
    else:
        await change(case, MaterialModel, case.materials[4].id, tenant_id=uuid4())
    assert not (await calculate(case))["is_complete"]


def test_missing_bom_reason_survives_api_contract():
    response = BOMCostResponse(bom_id=uuid4(), material_cost=0, operation_cost=0, making_cost=0,
        total_cost=0, is_complete=False, missing_costs=[dict(component_type="bom", component_id=uuid4(),
        name="Child", reason="CYCLE_DETECTED", message="Cyclic reference")])
    assert response.missing_costs[0].reason == "CYCLE_DETECTED"

@pytest.mark.asyncio
async def test_reporting_analysis_reconciles_exact_nested_costs_and_isolates_tenant(case):
    from backend.app.interfaces.api.v1.routes.reports import bom_cost_analysis

    await change(case, BOMModel, case.parent.id, making_charge=Decimal("40"), making_charge_basis="PER_PIECE")
    await change(case, ItemTemplateModel, case.parent_variant.template_id, is_active=False)
    async with case.factory() as session:
        result = await bom_cost_analysis(case.parent.id, case.tenant, session)
        assert Decimal(result["total_cost"]) == Decimal("352")
        assert Decimal(result["direct_material_cost"]) == Decimal("12")
        assert Decimal(result["nested_cost"]) == Decimal("300")
        assert Decimal(result["tree"]["children"][0]["stored_standard_cost"]) == Decimal("90")
        assert {key: Decimal(value) for key, value in result["composition"].items()} == {
            "material": Decimal("252"), "operations": Decimal("0"), "outside_processing": Decimal("100"),
        }
        with pytest.raises(Exception) as exc:
            await bom_cost_analysis(case.parent.id, uuid4(), session)
        assert exc.value.status_code == 404

    await change(case, BOMLineModel, case.semi_line.id, unit_id=None)
    async with case.factory() as session:
        result = await bom_cost_analysis(case.parent.id, case.tenant, session)
        assert not result["is_complete"] and result["total_cost"] is None and result["composition"] is None
        assert result["missing_costs"][0]["reason"] == "OUTPUT_UOM_MISSING"

@pytest.mark.asyncio
async def test_bom_xlsx_matches_web_and_preserves_decimal_text_and_formula_like_labels(case):
    from io import BytesIO

    from openpyxl import load_workbook

    from backend.app.interfaces.api.v1.routes.reports import bom_cost_analysis, bom_cost_analysis_xlsx

    quantity = Decimal("1.123456")
    await change(case, BOMLineModel, case.semi_line.id, quantity=quantity, scrap_percentage=Decimal("1.2345"))
    await change(case, MaterialModel, case.materials[0].id, name="=1+1")
    await change(case, BOMModel, case.parent.id, making_charge=Decimal("40"), making_charge_basis="PER_PIECE")
    async with case.factory() as session:
        web = await bom_cost_analysis(case.parent.id, case.tenant, session)
        response = await bom_cost_analysis_xlsx(case.parent.id, case.tenant, session)
    book = load_workbook(BytesIO(response.body))
    assert book.sheetnames == ["Summary", "Cost Breakdown", "BOM Hierarchy", "Exceptions"]
    for sheet in book:
        assert sheet.freeze_panes and sheet.auto_filter.ref
        assert all(cell.data_type != "f" for cells in sheet for cell in cells)
    summary = {row[0].value: row[1:] for row in list(book["Summary"].rows)[1:]}
    numerical, exact = summary["Calculated BOM cost per output unit"]
    assert numerical.data_type == "n" and Decimal(exact.value) == Decimal(web["total_cost"])
    assert summary["Calculated at (UTC)"][0].is_date
    breakdown = list(book["Cost Breakdown"].values)
    flattened = [Decimal(row[3]) for row in breakdown
                 if row[0] == "Flattened composition" and row[1] != "Reconciled total"]
    assert sum(flattened) == Decimal(web["total_cost"])
    hierarchy = list(book["BOM Hierarchy"].values)[1:]
    assert len(hierarchy) == 8  # root, five components and two processing entries
    assert [row[4] for row in hierarchy].count("=1+1") == 1
    assert sum(Decimal(row[12]) for row in hierarchy if row[5] == "Outside processing") == Decimal(web["composition"]["outside_processing"])

    await change(case, BOMLineModel, case.semi_line.id, unit_id=None)
    async with case.factory() as session:
        response = await bom_cost_analysis_xlsx(case.parent.id, case.tenant, session)
    incomplete = load_workbook(BytesIO(response.body))
    assert any(row[4] == "OUTPUT_UOM_MISSING" for row in incomplete["Exceptions"].values)
    assert any(row[0] == "Calculated BOM cost per output unit" and row[1] is None for row in incomplete["Summary"].values)
