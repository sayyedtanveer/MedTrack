"""Exercise the template HTTP route and persisted Excel validations in isolation."""
import io
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import httpx
import openpyxl
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable

from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.interfaces.api.v1.dependencies.auth import get_current_user_payload
from backend.app.interfaces.api.v1.routes import material_onboarding as routes


@pytest_asyncio.fixture
async def template_env():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        for model in (LocationModel, UnitOfMeasureModel, TenantModel, SupplierModel):
            await connection.execute(CreateTable(model.__table__))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    tenant, other = uuid4(), uuid4()
    now = datetime.now(timezone.utc)
    locations = ['raw-01', 'Rack, "North"'] + [f"STORAGE-{i:03}" for i in range(40)]
    async with factory() as session:
        session.add(TenantModel(id=tenant, name="Template tenant", slug=str(tenant), currency_code="NZD"))
        for tid, name, active, deleted in [
            (tenant, 'Supplier, "North"', True, False), (tenant, "Test Supplier", True, False),
            (tenant, "Inactive Supplier", False, False), (tenant, "Deleted Supplier", True, True),
            (other, "Private Supplier", True, False),
        ]:
            session.add(SupplierModel(id=uuid4(), tenant_id=tid, name=name, code=str(uuid4()),
                                      is_active=active, is_deleted=deleted))
        for tid, code, active, deleted in [(tenant, v, True, False) for v in locations] + [
            (tenant, "INACTIVE", False, False), (tenant, "DELETED", True, True),
            (other, "OTHER-TENANT", True, False),
        ]:
            session.add(LocationModel(id=uuid4(), tenant_id=tid, name=code, code=code,
                                      type="warehouse", is_active=active, is_deleted=deleted,
                                      is_default=code == "raw-01"))
        for tid, code, active, deleted in [
            (tenant, "KG", True, False), (tenant, "PCS", True, False),
            (tenant, "OLD", False, False), (tenant, "GONE", True, True),
            (other, "PRIVATE", True, False),
        ]:
            session.add(UnitOfMeasureModel(id=uuid4(), tenant_id=tid, name=code, code=code,
                                          precision=2, is_active=active, is_deleted=deleted,
                                          created_at=now, updated_at=now))
        await session.commit()
    app = FastAPI()
    app.state.container = SimpleNamespace(session_factory=factory)
    app.include_router(routes.router)
    yield SimpleNamespace(app=app, tenant=tenant, locations=locations)
    await engine.dispose()


async def download(env, *, authenticated=True, format="xlsx"):
    if authenticated:
        env.app.dependency_overrides[get_current_user_payload] = lambda: {"tid": str(env.tenant)}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=env.app), base_url="http://test") as client:
        return await client.get(f"/inventory/material-onboarding/template?format={format}")


@pytest.mark.asyncio
async def test_authenticated_template_has_master_dropdowns_on_raw_materials(template_env):
    response = await download(template_env)
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]
    workbook = openpyxl.load_workbook(io.BytesIO(response.content), data_only=True)
    assert [s.title for s in workbook if s.sheet_state == "visible"] == ["Field Guide", "Quick Start", "Raw Materials"]
    assert workbook["_Master Data"].sheet_state == "hidden"
    sheet = workbook["Raw Materials"]
    headers = [c.value for c in sheet[1]]
    for heading, name, expected in (
        ("Storage Location", "StorageLocationOptions", set(template_env.locations)),
        ("Base Unit", "BaseUnitOptions", {"KG", "PCS"}),
        ("Supplier Name", "SupplierNameOptions", {'Supplier, "North"', "Test Supplier"}),
        ("Supplier Currency", "SupplierCurrencyOptions", {"INR", "USD", "EUR", "GBP", "AED", "SGD", "JPY", "AUD", "CAD", "NZD"}),
        ("Supplier UOM", "SupplierUOMOptions", {"KG", "PCS"}),
    ):
        cell = f"{openpyxl.utils.get_column_letter(headers.index(heading) + 1)}2"
        validation = next(d for d in sheet.data_validations.dataValidation if cell in d)
        assert validation.formula1 == f"={name}"
        assert validation.showDropDown is False  # True hides the arrow in Excel.
        assert validation.showErrorMessage is (heading not in ("Supplier Name", "Supplier Currency"))
        source, bounds = next(workbook.defined_names[name].destinations)
        values = {c.value for row in workbook[source][bounds] for c in row}
        assert values == expected
        assert not any(s.data_validations.count for s in (workbook["Field Guide"], workbook["Quick Start"]))
    assert sheet["F2"].value == "raw-01"
    # No guessed supplier, currency, UOM or item code is prefilled into a quote.
    for heading in ("Supplier Name", "Supplier Currency", "Supplier UOM", "Supplier Item Code"):
        cell = f"{openpyxl.utils.get_column_letter(headers.index(heading) + 1)}2"
        assert sheet[cell].value is None
        if heading == "Supplier Item Code":
            assert not any(cell in d for d in sheet.data_validations.dataValidation)
    # Long and punctuation-containing lists survive without inline formula corruption.
    assert len(",".join(template_env.locations)) > 255
    headers, rows = routes._parse_file(response.content, "template.xlsx")
    assert "Material Name" in headers
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_anonymous_template_is_rejected(template_env):
    response = await download(template_env, authenticated=False)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_failed_master_query_does_not_return_successful_empty_template(template_env, monkeypatch):
    async def fail(*args):
        raise RuntimeError("isolated database failure")
    monkeypatch.setattr(routes, "_get_unit_of_measures", fail)
    response = await download(template_env)
    assert response.status_code == 503
    assert response.json()["detail"] == "Could not load template master data. Please retry."


@pytest.mark.asyncio
async def test_csv_template_keeps_authenticated_default_location(template_env):
    response = await download(template_env, format="csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "raw-01" in response.content.decode("utf-8-sig")


@pytest.mark.asyncio
async def test_excel_failure_does_not_masquerade_as_csv(template_env, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("isolated workbook failure")
    monkeypatch.setattr(routes.openpyxl, "Workbook", fail)
    response = await download(template_env)
    assert response.status_code == 503
    assert "application/json" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_empty_tenant_does_not_receive_another_tenants_master_data(template_env):
    template_env.tenant = uuid4()
    response = await download(template_env)
    assert response.status_code == 200
    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    assert all(not d.formula1.startswith("=Storage") and not d.formula1.startswith("=Base")
               for d in workbook["Raw Materials"].data_validations.dataValidation)
    assert list(workbook["_Master Data"].values)[1][:3] == (None, None, None)
