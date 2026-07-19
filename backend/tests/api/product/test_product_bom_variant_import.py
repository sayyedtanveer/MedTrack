from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def _create_category(
    async_client: AsyncClient,
    token_headers: dict,
    *,
    prefix: str,
) -> str:
    response = await async_client.post(
        "/api/v1/inventory/master-data/categories",
        json={
            "name": f"{prefix} Category",
            "code_prefix": prefix[:10],
        },
        headers=token_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_template(
    async_client: AsyncClient,
    token_headers: dict,
    *,
    code: str,
    attributes: list[dict] | None = None,
) -> dict:
    category_id = await _create_category(async_client, token_headers, prefix=code.replace("-", "")[:10])
    response = await async_client.post(
        "/api/v1/products/templates",
        json={
            "code": code,
            "name": f"{code} Product",
            "category_id": category_id,
            "attributes": attributes or [],
        },
        headers=token_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_variant_csv_template_import_and_bulk_status(
    async_client: AsyncClient,
    token_headers: dict,
):
    run_id = str(uuid.uuid4())[:8].upper()
    template = await _create_template(
        async_client,
        token_headers,
        code=f"IMP-{run_id}",
        attributes=[
            {"key": "SIZE", "label": "Size", "values": ["S", "M"]},
            {"key": "COLOR", "label": "Color", "values": ["Blue", "Green"]},
        ],
    )

    template_response = await async_client.get(
        f"/api/v1/products/templates/{template['id']}/variants/import-template",
        headers=token_headers,
    )
    assert template_response.status_code == 200, template_response.text
    assert "SIZE,COLOR,standard_cost,selling_price" in template_response.json()["csv_content"]

    csv_data = "SIZE,COLOR,standard_cost,selling_price\nS,Blue,10.50,25.00\nM,Green,12.00,28.00\n"
    import_response = await async_client.post(
        f"/api/v1/products/templates/{template['id']}/variants/bulk-import",
        json={"csv_data": csv_data},
        headers=token_headers,
    )
    assert import_response.status_code == 200, import_response.text
    imported = import_response.json()
    assert imported["success_count"] == 2
    assert imported["error_count"] == 0
    assert len(imported["variant_ids"]) == 2

    deactivate_response = await async_client.post(
        f"/api/v1/products/templates/{template['id']}/variants/bulk-deactivate",
        json={"variant_ids": imported["variant_ids"]},
        headers=token_headers,
    )
    assert deactivate_response.status_code == 200, deactivate_response.text
    assert deactivate_response.json()["success_count"] == 2

    activate_response = await async_client.post(
        f"/api/v1/products/templates/{template['id']}/variants/bulk-activate",
        json={"variant_ids": imported["variant_ids"]},
        headers=token_headers,
    )
    assert activate_response.status_code == 200, activate_response.text
    assert activate_response.json()["success_count"] == 2


async def test_bom_duplicate_components_and_operation_persistence(
    async_client: AsyncClient,
    token_headers: dict,
):
    run_id = str(uuid.uuid4())[:8].upper()
    target = await _create_template(async_client, token_headers, code=f"BOM-TGT-{run_id}")
    component = await _create_template(async_client, token_headers, code=f"BOM-CMP-{run_id}")

    duplicate_response = await async_client.post(
        f"/api/v1/products/{target['id']}/boms",
        json={
            "version": f"dup-{run_id}",
            "valid_from": datetime.now(timezone.utc).isoformat(),
            "template_id": target["id"],
            "lines": [
                {"template_id": component["id"], "quantity": 1, "scrap_percentage": 0},
                {"template_id": component["id"], "quantity": 2, "scrap_percentage": 0},
            ],
        },
        headers=token_headers,
    )
    assert duplicate_response.status_code == 400
    assert "Duplicate template component" in duplicate_response.json()["detail"]

    bom_response = await async_client.post(
        f"/api/v1/products/{target['id']}/boms",
        json={
            "version": f"route-{run_id}",
            "valid_from": datetime.now(timezone.utc).isoformat(),
            "template_id": target["id"],
            "lines": [],
        },
        headers=token_headers,
    )
    assert bom_response.status_code == 201, bom_response.text
    bom = bom_response.json()

    workstation_response = await async_client.post(
        "/api/v1/workstations",
        json={
            "code": f"WS-{run_id}",
            "name": "Assembly Cell",
            "capacity_hours_per_day": 8,
            "hourly_rate": 500,
        },
        headers=token_headers,
    )
    assert workstation_response.status_code == 201, workstation_response.text

    operation_response = await async_client.post(
        "/api/v1/operations",
        json={
            "name": "Final Assembly",
            "workstation_id": workstation_response.json(),
            "setup_time": 15,
            "run_time": 3,
            "description": "Assemble and inspect one unit.",
        },
        headers=token_headers,
    )
    assert operation_response.status_code == 201, operation_response.text

    attach_response = await async_client.post(
        f"/api/v1/boms/{bom['id']}/operations",
        json={"operation_id": operation_response.json(), "sequence": 10},
        headers=token_headers,
    )
    assert attach_response.status_code == 200, attach_response.text

    fetched = await async_client.get(f"/api/v1/boms/{bom['id']}", headers=token_headers)
    assert fetched.status_code == 200, fetched.text
    fetched_json = fetched.json()
    assert fetched_json["operations_count"] == 1
    assert fetched_json["operations"][0]["sequence"] == 10

    remove_response = await async_client.delete(
        f"/api/v1/boms/{bom['id']}/operations/{fetched_json['operations'][0]['id']}",
        headers=token_headers,
    )
    assert remove_response.status_code == 204, remove_response.text

    after_delete = await async_client.get(f"/api/v1/boms/{bom['id']}", headers=token_headers)
    assert after_delete.status_code == 200, after_delete.text
    assert after_delete.json()["operations_count"] == 0
