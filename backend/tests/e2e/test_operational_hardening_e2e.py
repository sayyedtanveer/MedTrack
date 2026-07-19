"""
E2E operational hardening flow (release → reserve → issue → produce → consume → QC).

Requires a running API with test tenant fixtures (see test_operational_flow_e2e.py).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_operational_hardening_endpoints_exist(authenticated_async_client):
    """Smoke test new operational endpoints respond without 404."""
    client = authenticated_async_client

    response = await client.get("/api/v1/work-orders", params={"active": True})
    assert response.status_code == 200, response.text
    wo_list = response.json()
    assert isinstance(wo_list, list)

    response = await client.get("/api/v1/work-orders/planner/shortage-queue")
    assert response.status_code == 200, response.text
    planner = response.json()
    assert isinstance(planner, list)

    response = await client.get("/api/v1/storekeeper/issue-queue")
    assert response.status_code == 200, response.text
    issue_q = response.json()
    assert isinstance(issue_q, list)
    if issue_q:
        row = issue_q[0]
        assert "wo_number" in row
        assert "material_code" in row
        assert "material_name" in row
        assert "returned_quantity" in row

    response = await client.get("/api/v1/storekeeper/pending-reservations")
    assert response.status_code == 200, response.text
    pending_reservations = response.json()
    assert isinstance(pending_reservations, list)

    response = await client.get("/api/v1/storekeeper/pending-returns")
    assert response.status_code == 200, response.text
    pending_returns = response.json()
    assert isinstance(pending_returns, list)

    response = await client.get("/api/v1/storekeeper/inventory-alerts")
    assert response.status_code == 200, response.text
    inventory_alerts = response.json()
    assert isinstance(inventory_alerts, list)

    response = await client.post("/api/v1/inventory/scan/resolve", json={"payload": "RM-TEST"})
    assert response.status_code in {200, 422}, response.text
    scan = response.json()
    assert "type" in scan

    response = await client.get("/api/v1/reports/inventory/near-empty-batches", params={"threshold_pct": 15})
    assert response.status_code == 200, response.text
    near_empty = response.json()
    assert isinstance(near_empty, list)

    response = await client.get("/api/v1/reports/inventory/consumption-variance")
    assert response.status_code == 200, response.text
    variance = response.json()
    assert isinstance(variance, list)
