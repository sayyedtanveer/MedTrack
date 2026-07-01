from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel


async def _create_location(async_client, headers: dict[str, str], *, name: str, code: str) -> str:
    response = await async_client.post(
        "/api/v1/inventory/master-data/locations",
        json={
            "name": name,
            "code": code,
            "type": "warehouse",
            "is_active": True,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.asyncio
async def test_inventory_transfer_moves_stock_between_locations(
    async_client,
    token_headers,
    db_session,
    test_tenant_id,
):
    run_id = uuid.uuid4().hex[:6].upper()
    source_location_id = await _create_location(
        async_client,
        token_headers,
        name=f"Source Warehouse {run_id}",
        code=f"WH-SRC-{run_id}",
    )
    target_location_id = await _create_location(
        async_client,
        token_headers,
        name=f"Target Warehouse {run_id}",
        code=f"WH-TGT-{run_id}",
    )

    material_resp = await async_client.post(
        "/api/v1/inventory/materials",
        json={
            "code": f"RM-TRANSFER-{run_id}",
            "name": f"Transfer Test Material {run_id}",
            "description": "Used to validate transfer flow",
            "material_type": "raw",
        },
        headers=token_headers,
    )
    assert material_resp.status_code == 201, material_resp.text
    material_id = material_resp.json()["id"]
    material_uuid = uuid.UUID(material_id)

    add_resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "material_id": material_id,
            "transaction_type": "in",
            "quantity": "9",
            "to_location_id": source_location_id,
            "remarks": "Seed transfer stock",
        },
        headers=token_headers,
    )
    assert add_resp.status_code == 201, add_resp.text

    transfer_resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "material_id": material_id,
            "transaction_type": "transfer",
            "quantity": "4",
            "from_location_id": source_location_id,
            "to_location_id": target_location_id,
            "remarks": "Move to target warehouse",
        },
        headers=token_headers,
    )
    assert transfer_resp.status_code == 201, transfer_resp.text

    stock_rows = (
        await db_session.execute(
            select(StockLevelModel).where(
                StockLevelModel.tenant_id == test_tenant_id,
                StockLevelModel.material_id == material_uuid,
                StockLevelModel.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    buckets = {
        (str(row.location_id), row.stock_status): Decimal(str(row.quantity))
        for row in stock_rows
    }

    assert buckets[(source_location_id, "available")] == Decimal("5")
    assert buckets[(target_location_id, "available")] == Decimal("4")


@pytest.mark.asyncio
async def test_transfer_rejects_same_source_and_destination_location(
    async_client,
    token_headers,
):
    """Requirement 3.3: Transfer with from_location_id == to_location_id returns 400."""
    run_id = uuid.uuid4().hex[:6].upper()
    location_id = await _create_location(
        async_client,
        token_headers,
        name=f"Same Location {run_id}",
        code=f"WH-SAME-{run_id}",
    )

    material_resp = await async_client.post(
        "/api/v1/inventory/materials",
        json={
            "code": f"RM-SAME-{run_id}",
            "name": f"Same Loc Test Material {run_id}",
            "material_type": "raw",
        },
        headers=token_headers,
    )
    assert material_resp.status_code == 201, material_resp.text
    material_id = material_resp.json()["id"]

    transfer_resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "material_id": material_id,
            "transaction_type": "transfer",
            "quantity": "5",
            "from_location_id": location_id,
            "to_location_id": location_id,
        },
        headers=token_headers,
    )
    assert transfer_resp.status_code == 400, transfer_resp.text
    assert "Source and destination locations must be different" in transfer_resp.json()["detail"]


@pytest.mark.asyncio
async def test_transfer_rejects_insufficient_stock_at_source(
    async_client,
    token_headers,
):
    """Requirement 3.6: Transfer with insufficient stock at source returns 400 with available quantity."""
    run_id = uuid.uuid4().hex[:6].upper()
    source_location_id = await _create_location(
        async_client,
        token_headers,
        name=f"Low Source {run_id}",
        code=f"WH-LOW-{run_id}",
    )
    target_location_id = await _create_location(
        async_client,
        token_headers,
        name=f"Target {run_id}",
        code=f"WH-TGT2-{run_id}",
    )

    material_resp = await async_client.post(
        "/api/v1/inventory/materials",
        json={
            "code": f"RM-INSUF-{run_id}",
            "name": f"Insufficient Stock Material {run_id}",
            "material_type": "raw",
        },
        headers=token_headers,
    )
    assert material_resp.status_code == 201, material_resp.text
    material_id = material_resp.json()["id"]

    # Add only 3 units to the source location
    add_resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "material_id": material_id,
            "transaction_type": "in",
            "quantity": "3",
            "to_location_id": source_location_id,
            "remarks": "Seed small stock",
        },
        headers=token_headers,
    )
    assert add_resp.status_code == 201, add_resp.text

    # Try to transfer 10 units (more than available)
    transfer_resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "material_id": material_id,
            "transaction_type": "transfer",
            "quantity": "10",
            "from_location_id": source_location_id,
            "to_location_id": target_location_id,
            "remarks": "Attempt oversized transfer",
        },
        headers=token_headers,
    )
    assert transfer_resp.status_code == 400, transfer_resp.text
    detail = transfer_resp.json()["detail"]
    # The error should mention available quantity
    assert "3" in detail or "insufficient" in detail.lower() or "only" in detail.lower()
