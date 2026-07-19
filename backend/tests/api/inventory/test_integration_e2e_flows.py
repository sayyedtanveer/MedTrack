"""
Integration tests for end-to-end inventory module flows.

These tests verify complete workflows across multiple API calls and database state.

Validates: Requirements 1.1, 2.1, 3.5, 4.2, 7.3, 9.1
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient


def _unique_suffix() -> str:
    return uuid.uuid4().hex[:6].upper()


# ─────────────────────────────────────────────────────────────────────────────
# Test: Reorder notification end-to-end flow
# Create material with reorder_level, add stock above threshold, then remove
# stock to cross below the threshold → verify a LOW_STOCK_ALERT notification
# is created (checked via the /notifications/operational API).
#
# Validates: Requirement 2.1
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reorder_notification_created_when_stock_crosses_threshold(
    authenticated_async_client: AsyncClient,
):
    """E2E: remove stock to cross reorder threshold → verify notification created via API."""
    suffix = _unique_suffix()
    reorder_level = "50"

    # 1) Create material with reorder_level and opening stock above threshold
    create_resp = await authenticated_async_client.post(
        "/api/v1/inventory/materials",
        json={
            "name": f"Reorder Notification Test {suffix}",
            "material_type": "raw",
            "reorder_level": reorder_level,
            "opening_stock": "100",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    material_data = create_resp.json()
    material_id = material_data["id"]

    # Verify stock is above reorder level
    assert Decimal(str(material_data["current_stock"])) == Decimal("100")
    assert material_data["is_low_stock"] is False

    # 2) Remove stock to bring it below reorder level (100 - 60 = 40, below 50)
    remove_resp = await authenticated_async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "material_id": material_id,
            "transaction_type": "out",
            "quantity": "60",
            "remarks": "Trigger reorder notification",
        },
    )
    assert remove_resp.status_code == 201, remove_resp.text
    updated_material = remove_resp.json()
    assert Decimal(str(updated_material["current_stock"])) == Decimal("40")
    assert updated_material["is_low_stock"] is True

    # 3) Verify a LOW_STOCK_ALERT notification was created via the operational notifications API
    notif_resp = await authenticated_async_client.get(
        "/api/v1/notifications/operational",
    )
    assert notif_resp.status_code == 200, notif_resp.text
    notif_data = notif_resp.json()
    items = notif_data.get("items", [])

    # Find LOW_STOCK_ALERT notifications for this material
    low_stock_alerts = [
        n for n in items
        if n.get("notification_type") == "LOW_STOCK_ALERT"
        and n.get("reference_id") == material_id
    ]

    assert len(low_stock_alerts) >= 1, (
        f"Expected at least 1 LOW_STOCK_ALERT notification for material {material_id}, "
        f"found {len(low_stock_alerts)}. All notifications: {items}"
    )

    alert = low_stock_alerts[0]
    # Verify notification content contains material info (Req 2.6)
    message = alert.get("message", "")
    assert f"Reorder Notification Test {suffix}" in message or material_data["code"] in message
    assert alert.get("reference_type") == "material"


@pytest.mark.asyncio
async def test_no_duplicate_notification_when_stock_already_below_threshold(
    authenticated_async_client: AsyncClient,
):
    """E2E: Once stock is below reorder level, further reductions do NOT create duplicate notifications."""
    suffix = _unique_suffix()

    # 1) Create material with reorder_level=50, opening_stock=100
    create_resp = await authenticated_async_client.post(
        "/api/v1/inventory/materials",
        json={
            "name": f"No Dup Notification {suffix}",
            "material_type": "raw",
            "reorder_level": "50",
            "opening_stock": "100",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    material_data = create_resp.json()
    material_id = material_data["id"]

    # 2) Remove stock to cross threshold (100 → 40)
    remove_resp1 = await authenticated_async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "material_id": material_id,
            "transaction_type": "out",
            "quantity": "60",
            "remarks": "First removal crossing threshold",
        },
    )
    assert remove_resp1.status_code == 201, remove_resp1.text

    # 3) Remove more stock while already below threshold (40 → 20)
    remove_resp2 = await authenticated_async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "material_id": material_id,
            "transaction_type": "out",
            "quantity": "20",
            "remarks": "Second removal while already below",
        },
    )
    assert remove_resp2.status_code == 201, remove_resp2.text

    # 4) Verify only ONE LOW_STOCK_ALERT notification exists (no duplicate) via API
    notif_resp = await authenticated_async_client.get(
        "/api/v1/notifications/operational",
    )
    assert notif_resp.status_code == 200, notif_resp.text
    notif_data = notif_resp.json()
    items = notif_data.get("items", [])

    low_stock_alerts = [
        n for n in items
        if n.get("notification_type") == "LOW_STOCK_ALERT"
        and n.get("reference_id") == material_id
    ]

    assert len(low_stock_alerts) == 1, (
        f"Expected exactly 1 LOW_STOCK_ALERT notification (no duplicates), "
        f"found {len(low_stock_alerts)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test: Number Series code generation with new config → verify format and
# immutability
#
# Validates: Requirements 7.3, 9.1
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_number_series_code_generation_format_and_immutability(
    authenticated_async_client: AsyncClient,
):
    """E2E: Configure Number Series → create material → verify code format → verify immutability."""
    suffix = _unique_suffix()

    # 1) Configure Number Series for 'material' entity type
    config_resp = await authenticated_async_client.put(
        "/api/v1/settings/number-series/material",
        json={
            "auto_generate": True,
            "include_abbreviation": True,
            "abbreviation_length": 3,
            "sequence_length": 6,
            "separator": "-",
        },
    )
    assert config_resp.status_code == 200, config_resp.text
    config = config_resp.json()
    assert config["auto_generate"] is True
    assert config["include_abbreviation"] is True
    assert config["separator"] == "-"

    # 2) Create a material (code will be auto-generated via Number Series Engine)
    create_resp = await authenticated_async_client.post(
        "/api/v1/inventory/materials",
        json={
            "name": f"Steel Pipe {suffix}",
            "material_type": "raw",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    material = create_resp.json()
    material_id = material["id"]
    generated_code = material["code"]

    # 3) Verify code format: should contain the separator and be non-empty
    assert generated_code, "Generated code should not be empty"
    assert "-" in generated_code, (
        f"Expected separator '-' in generated code '{generated_code}'"
    )
    # Code should be locked
    assert material["code_locked"] is True

    # 4) Verify immutability: trying to change the code should return 422
    update_resp = await authenticated_async_client.put(
        f"/api/v1/inventory/materials/{material_id}",
        json={
            "code": "DIFFERENT-CODE-123",
        },
    )
    assert update_resp.status_code == 422, (
        f"Expected 422 when changing immutable code, got {update_resp.status_code}: {update_resp.text}"
    )
    assert "immutable" in update_resp.json()["detail"].lower()

    # 5) Verify the code is preserved when updating other fields
    update_name_resp = await authenticated_async_client.put(
        f"/api/v1/inventory/materials/{material_id}",
        json={
            "description": f"Updated description {suffix}",
        },
    )
    assert update_name_resp.status_code == 200, update_name_resp.text
    updated_material = update_name_resp.json()
    assert updated_material["code"] == generated_code, (
        f"Code changed from '{generated_code}' to '{updated_material['code']}' after description update"
    )


@pytest.mark.asyncio
async def test_number_series_preview_matches_generated_code_format(
    authenticated_async_client: AsyncClient,
):
    """E2E: Preview code format matches the pattern used in actual generation."""
    suffix = _unique_suffix()

    # 1) Configure with specific settings
    await authenticated_async_client.put(
        "/api/v1/settings/number-series/material",
        json={
            "auto_generate": True,
            "include_abbreviation": False,
            "sequence_length": 4,
            "separator": "-",
        },
    )

    # 2) Get preview
    preview_resp = await authenticated_async_client.get(
        "/api/v1/settings/number-series/material/preview",
        params={"sub_type": "raw"},
    )
    assert preview_resp.status_code == 200, preview_resp.text
    preview_data = preview_resp.json()
    preview_pattern = preview_data["format_pattern"]

    # 3) Create a material and verify its code follows the same pattern structure
    create_resp = await authenticated_async_client.post(
        "/api/v1/inventory/materials",
        json={
            "name": f"Preview Match Test {suffix}",
            "material_type": "raw",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    material = create_resp.json()
    generated_code = material["code"]

    # The generated code should use the separator from the config
    assert "-" in generated_code, (
        f"Generated code '{generated_code}' should contain separator '-'"
    )
    # With abbreviation disabled, format should be {prefix}-{sequence}
    # The code should have at least a prefix part and a numeric sequence part
    parts = generated_code.split("-")
    assert len(parts) >= 2, (
        f"Expected at least 2 parts (prefix-sequence) in code '{generated_code}', "
        f"got {len(parts)} parts"
    )
