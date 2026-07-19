import pytest
import uuid
from httpx import AsyncClient

# Pytest fixture to run under anyio
pytestmark = pytest.mark.anyio

async def test_phase23_routing_and_advanced_bom(async_client: AsyncClient, token_headers: dict, test_tenant_id: uuid.UUID):
    # 1. Create a Workstation
    ws_payload = {
        "code": "WS-ASSEMBLY-01",
        "name": "Main Assembly Line",
        "capacity_hours_per_day": 8.0,
        "hourly_rate": 120.0 # $120 / hr
    }
    resp = await async_client.post("/api/v1/workstations", json=ws_payload, headers=token_headers)
    assert resp.status_code == 201
    workstation_id = resp.json()

    # 2. Create an Operation
    op_payload = {
        "name": "Final Assembly",
        "workstation_id": workstation_id,
        "setup_time": 30.0, # 30 mins setup
        "run_time": 15.0,   # 15 mins per unit
        "description": "Assemble components into final product"
    }
    resp = await async_client.post("/api/v1/operations", json=op_payload, headers=token_headers)
    assert resp.status_code == 201
    operation_id = resp.json()

    # 3. Create items: Raw Material ($10), SubAssembly (Variant 1), Final Product (Variant 2)
    cat_resp = await async_client.post("/api/v1/categories", json={"name": "P23 Component", "description": "Test"}, headers=token_headers)
    cat_id = cat_resp.json()
    
    unit_resp = await async_client.post("/api/v1/units", json={"name": "PCS", "abbreviation": "pcs"}, headers=token_headers)
    unit_id = unit_resp.json()

    # Raw Material (Cost = $10.00)
    mat_resp = await async_client.post("/api/v1/materials", json={
        "code": "RM-23-01", "name": "Metal Sheet", "category_id": cat_id, "base_unit_id": unit_id, "is_active": True
    }, headers=token_headers)
    assert mat_resp.status_code == 201
    mat_id = mat_resp.json()
    # Mocking cost is difficult via API until pricing is implemented in 2.4, so it defaults to 0. 
    # For now, CostRollup will just add operations if material cost is 0, or we can see if our DB triggers it.

    # Item Template
    tpl_resp = await async_client.post("/api/v1/products/templates", json={
        "code": "TPL-23", "name": "Bicycle Frame", "category_id": cat_id, "base_unit_id": unit_id, "is_active": True,
        "is_stockable": True, "is_purchasable": False, "is_manufacturable": True
    }, headers=token_headers)
    tpl_id = tpl_resp.json()

    # Sub-Assembly Variant
    v1_resp = await async_client.post(f"/api/v1/products/templates/{tpl_id}/variants", json={
        "attribute_values": {"type": "SubAssembly"}, "is_active": True, "standard_cost": 50.0
    }, headers=token_headers)
    sub_variant_id = v1_resp.json()

    # Final Product Variant
    v2_resp = await async_client.post(f"/api/v1/products/templates/{tpl_id}/variants", json={
        "attribute_values": {"type": "FinalBicycle"}, "is_active": True, "standard_cost": 250.0
    }, headers=token_headers)
    final_variant_id = v2_resp.json()

    # 4. Create Sub-Assembly BOM
    sub_bom_payload = {
        "version": "1.0",
        "valid_from": "2026-01-01T00:00:00Z",
        "lines": [
            {"material_id": mat_id, "quantity": 2.0, "unit_id": unit_id}
        ]
    }
    resp = await async_client.post(f"/api/v1/products/{sub_variant_id}/boms", json=sub_bom_payload, headers=token_headers)
    assert resp.status_code == 201
    sub_bom_id = resp.json()
    await async_client.post(f"/api/v1/boms/{sub_bom_id}/activate", headers=token_headers)

    # 5. Create Final Assembly BOM
    fin_bom_payload = {
        "version": "1.0",
        "valid_from": "2026-01-01T00:00:00Z",
        "lines": [
            {"variant_id": sub_variant_id, "quantity": 1.0, "unit_id": unit_id}
        ]
    }
    resp = await async_client.post(f"/api/v1/products/{final_variant_id}/boms", json=fin_bom_payload, headers=token_headers)
    assert resp.status_code == 201
    final_bom_id = resp.json()

    # 6. Attach Operation to Final BOM
    op_attach_payload = {
        "operation_id": operation_id,
        "sequence": 10
    }
    resp = await async_client.post(f"/api/v1/boms/{final_bom_id}/operations", json=op_attach_payload, headers=token_headers)
    assert resp.status_code == 200

    # Activate Final BOM
    resp = await async_client.post(f"/api/v1/boms/{final_bom_id}/activate", headers=token_headers)
    assert resp.status_code == 200

    # 7. Get BOM Tree
    resp = await async_client.get(f"/api/v1/boms/{final_bom_id}/tree", headers=token_headers)
    assert resp.status_code == 200
    tree = resp.json()
    assert tree["id"] == final_bom_id
    assert len(tree["children"]) == 1
    child_sub = tree["children"][0]
    assert child_sub["id"] == sub_variant_id
    assert len(child_sub["children"]) == 1
    child_mat = child_sub["children"][0]
    assert child_mat["id"] == mat_id

    # 8. Get BOM Cost
    resp = await async_client.get(f"/api/v1/boms/{final_bom_id}/cost", headers=token_headers)
    assert resp.status_code == 200
    cost_data = resp.json()
    # Operation cost: (30 + 15) mins = 45 mins = 0.75 hours. 0.75 * 120 = 90.0
    # Materials currently have cost 0 in DB.
    assert "cost" in cost_data
    assert float(cost_data["cost"]) == 90.0

    # 9. Test Circular Dependency validation
    # Try creating a BOM for Sub-Assembly that requires Final Product
    circ_bom_payload = {
        "version": "2.0",
        "valid_from": "2026-01-01T00:00:00Z",
        "lines": [
            {"variant_id": final_variant_id, "quantity": 1.0, "unit_id": unit_id}
        ]
    }
    resp = await async_client.post(f"/api/v1/products/{sub_variant_id}/boms", json=circ_bom_payload, headers=token_headers)
    # Expected to fail due to circular reference during creation
    assert resp.status_code == 400
    assert "Circular dependency" in resp.json()["detail"] or "cannot reference its own product" in resp.json()["detail"]
