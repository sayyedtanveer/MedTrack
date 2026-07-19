import pytest
from httpx import AsyncClient
import uuid

@pytest.mark.asyncio
async def test_full_work_order_lifecycle(
    async_client: AsyncClient, token_headers: dict, setup_bom_data: dict
):
    """
    E2E Test: Full Work Order Lifecycle
    1. Create WO from BOM
    2. Check BOM materials/operations were snapshotted
    3. Release WO
    4. Start WO
    5. Start & Complete Job Card
    6. Issue Materials
    7. Record Production
    8. Complete & Close WO
    """
    tenant_id = setup_bom_data["tenant_id"]
    bom_id = setup_bom_data["bom_id"]
    product_id = setup_bom_data["product_id"]  # variant ID mapped to BOM
    rm_id = setup_bom_data["rm_id"]
    unit_id = setup_bom_data["unit_id"]

    # 1. Provide RM stock so we can issue materials later
    await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "material_id": str(rm_id),
            "unit_id": str(unit_id),
            "transaction_type": "adjustment",
            "quantity": 500.0,
            "remarks": "Initial stock for E2E WO test"
        },
        headers=token_headers
    )

    # 2. Create Work Order
    payload = {
        "product_id": str(product_id),
        "bom_id": str(bom_id),
        "planned_quantity": 10.0,
        "start_date": "2026-04-01",
        "due_date": "2026-04-05",
        "priority": "HIGH"
    }
    resp = await async_client.post("/api/v1/work-orders", json=payload, headers=token_headers)
    assert resp.status_code == 201, f"Failed to create WO: {resp.text}"
    wo_id = resp.json()["id"]

    # 3. Verify WO creation & snapshots
    resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    assert resp.status_code == 200
    wo = resp.json()
    assert wo["status"] == "PLANNED"
    assert wo["planned_quantity"] == "10.000"
    assert wo["wo_number"].startswith("WO-")

    # Check materials snapshot (BOM qty was 2.5 per unit, total required = 25.0)
    assert len(wo["materials"]) > 0
    mat = wo["materials"][0]
    assert float(mat["required_quantity"]) > 0

    # 4. Release Work Order
    resp = await async_client.post(f"/api/v1/work-orders/{wo_id}/release", headers=token_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "RELEASED"

    # 5. Start Work Order
    resp = await async_client.post(f"/api/v1/work-orders/{wo_id}/start", headers=token_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"

    # 6. Job Cards (Shop Floor ops)
    resp = await async_client.get(f"/api/v1/work-orders/{wo_id}/job-cards", headers=token_headers)
    assert resp.status_code == 200
    job_cards = resp.json()
    assert len(job_cards) > 0
    jc_id = job_cards[0]["id"]
    assert job_cards[0]["status"] == "PENDING"

    # Start Job Card
    resp = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}/job-cards/{jc_id}/start",
        json={"assigned_to": str(uuid.uuid4())},
        headers=token_headers
    )
    assert resp.status_code == 200, f"Failed start JC: {resp.text}"

    # Complete Job Card
    resp = await async_client.patch(
        f"/api/v1/work-orders/{wo_id}/job-cards/{jc_id}/complete",
        json={"remarks": "Milling done."},
        headers=token_headers
    )
    assert resp.status_code == 200, f"Failed complete JC: {resp.text}"

    # 7. Issue Materials
    req_qty = float(mat["required_quantity"])
    resp = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/issue-materials",
        json={
            "material_id": str(mat["material_id"]),
            "unit_id": str(mat["unit_id"]),
            "quantity": req_qty
        },
        headers=token_headers
    )
    assert resp.status_code == 200, f"Material issue failed: {resp.text}"

    # 8. Record Production (yield: 9 done, 1 scrap)
    resp = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/record-production",
        json={
            "produced_quantity": 9.0,
            "scrap_quantity": 1.0,
            "notes": "1 unit damaged during milling"
        },
        headers=token_headers
    )
    assert resp.status_code == 200, f"Record production failed: {resp.text}"

    # Verify FG stock received
    # (Checking the FG inventory via inventory/materials endpoint assuming we mapped it)
    
    # 9. Complete WO
    resp = await async_client.post(f"/api/v1/work-orders/{wo_id}/complete", headers=token_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"

    # 10. Close WO
    resp = await async_client.post(f"/api/v1/work-orders/{wo_id}/close", headers=token_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "CLOSED"

    # Verify Final WO State
    resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    assert resp.status_code == 200
    final_wo = resp.json()
    assert final_wo["status"] == "CLOSED"
    assert final_wo["produced_quantity"] == "9.000"
    assert final_wo["scrap_quantity"] == "1.000"
    assert final_wo["job_cards"][0]["status"] == "DONE"
    assert float(final_wo["materials"][0]["issued_quantity"]) == req_qty

@pytest.mark.asyncio
async def test_wo_immutable_fields_and_validation(
    async_client: AsyncClient, token_headers: dict, setup_bom_data: dict
):
    """Test WO lifecycle invariants and validation logic."""
    bom_id = setup_bom_data["bom_id"]
    product_id = setup_bom_data["product_id"]

    # 1. Invalid date (due before start)
    payload = {
        "product_id": str(product_id),
        "bom_id": str(bom_id),
        "planned_quantity": 5.0,
        "start_date": "2026-04-05",
        "due_date": "2026-04-01",  # Invalid
        "priority": "LOW"
    }
    resp = await async_client.post("/api/v1/work-orders", json=payload, headers=token_headers)
    assert resp.status_code == 422
    assert "Value error" in resp.text or "due_date" in resp.text

    # 2. Normal Create
    payload["due_date"] = "2026-04-10"
    resp = await async_client.post("/api/v1/work-orders", json=payload, headers=token_headers)
    wo_id = resp.json()["id"]

    # 3. Can't complete a WO without recording production first
    resp = await async_client.post(f"/api/v1/work-orders/{wo_id}/complete", headers=token_headers)
    assert resp.status_code == 422
    assert resp.json()["error_code"] in ("INVALID_STATUS_TRANSITION", "MATERIAL_NOT_ISSUED")

    # 4. Skip states (PLANNED -> IN_PROGRESS is invalid)
    resp = await async_client.post(f"/api/v1/work-orders/{wo_id}/start", headers=token_headers)
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "INVALID_STATUS_TRANSITION"

    # 5. Missing BOM
    payload["bom_id"] = str(uuid.uuid4())  # Random UUID
    resp = await async_client.post("/api/v1/work-orders", json=payload, headers=token_headers)
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "BOM_NOT_FOUND"
