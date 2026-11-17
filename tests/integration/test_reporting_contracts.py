import uuid

import httpx
import pytest
from fastapi import FastAPI

from backend.app.interfaces.api.v1.dependencies.auth import get_current_role, get_current_tenant_id
from backend.app.interfaces.api.v1.routes import reports


@pytest.mark.asyncio
async def test_report_permissions_and_manufacturing_contract(monkeypatch):
    app = FastAPI()
    app.include_router(reports.router)
    tenant_id = uuid.uuid4()
    role = "supplier"
    app.dependency_overrides[get_current_role] = lambda: role
    app.dependency_overrides[get_current_tenant_id] = lambda: tenant_id
    app.dependency_overrides[reports._get_db_session] = lambda: None
    from backend.app.services.kpi_query_service import ManufacturingKPIs

    async def kpis(self, tenant, dates):
        assert tenant == tenant_id
        assert dates.start_date.isoformat() == "2026-01-01"
        return ManufacturingKPIs(oee=0, yield_rate=75, scrap_rate=25, rework_rate=0,
                                 inventory_turnover=0, total_produced=4, total_scrap=1,
                                 total_completed=1, total_rework=0)

    monkeypatch.setattr(reports.KPIQueryService, "get_manufacturing_kpis", kpis)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for path in ("inventory/summary", "sales/fulfillment", "manufacturing-kpis", "finance/trial-balance",
                     f"bom-cost/{tenant_id}", f"bom-cost/{tenant_id}/export/xlsx"):
            assert (await client.get(f"/reports/{path}")).status_code == 403
        role = "admin"
        response = await client.get("/reports/manufacturing-kpis", params={
            "date_from": "2026-01-01", "date_to": "2026-01-31",
        })
        assert response.status_code == 200
        assert response.json()["yield_rate"] == 75
        assert response.json()["rework_rate"] == 0
