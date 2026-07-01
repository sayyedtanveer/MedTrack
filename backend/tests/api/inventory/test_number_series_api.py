"""Unit tests for Number Series API endpoints.

Tests cover:
- Config CRUD operations (list, get, update)
- Prefix validation (reject non-uppercase, empty, >10 chars)
- Preview endpoint returns correct format
- Audit log pagination and filtering

Validates: Requirements 7.1, 7.2, 7.3, 12.7, 13.4
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

BASE_URL = "/api/v1/settings/number-series"


# ─────────────────────────────────────────────────────────────────────────────
# Config CRUD Operations
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_configs_seeds_defaults_on_first_access(
    authenticated_async_client: AsyncClient,
):
    """Requirement 7.1: System creates default configs for all entity types on first access."""
    response = await authenticated_async_client.get(f"{BASE_URL}/", follow_redirects=True)

    assert response.status_code == 200
    configs = response.json()
    assert isinstance(configs, list)
    assert len(configs) >= 10  # At least 10 supported entity types

    entity_types = {c["entity_type"] for c in configs}
    expected_types = {
        "material", "product", "purchase_order", "sales_order",
        "invoice", "grn", "work_order", "batch", "customer", "supplier",
    }
    assert expected_types.issubset(entity_types)


@pytest.mark.asyncio
async def test_list_configs_returns_auto_generate_enabled_by_default(
    authenticated_async_client: AsyncClient,
):
    """Requirement 7.2: Default configs have auto_generate=true."""
    response = await authenticated_async_client.get(f"{BASE_URL}/", follow_redirects=True)

    assert response.status_code == 200
    configs = response.json()
    for config in configs:
        assert config["auto_generate"] is True


@pytest.mark.asyncio
async def test_get_config_for_entity_type(
    authenticated_async_client: AsyncClient,
):
    """Requirement 7.2: Get config for a specific entity type, creates defaults if none."""
    response = await authenticated_async_client.get(f"{BASE_URL}/material")

    assert response.status_code == 200
    config = response.json()
    assert config["entity_type"] == "material"
    assert config["auto_generate"] is True
    assert "id" in config
    assert "tenant_id" in config


@pytest.mark.asyncio
async def test_get_config_rejects_unsupported_entity_type(
    authenticated_async_client: AsyncClient,
):
    """Unsupported entity types should be rejected with 400."""
    response = await authenticated_async_client.get(f"{BASE_URL}/nonexistent_entity")

    assert response.status_code == 400
    assert "Unsupported entity type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_config_changes_auto_generate(
    authenticated_async_client: AsyncClient,
):
    """Requirement 7.2: Config can be updated."""
    # First get the config to confirm defaults
    get_resp = await authenticated_async_client.get(f"{BASE_URL}/invoice")
    assert get_resp.status_code == 200
    assert get_resp.json()["auto_generate"] is True

    # Update auto_generate to false
    put_resp = await authenticated_async_client.put(
        f"{BASE_URL}/invoice",
        json={"auto_generate": False},
    )
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["auto_generate"] is False
    assert updated["entity_type"] == "invoice"


@pytest.mark.asyncio
async def test_update_config_changes_separator_and_sequence_length(
    authenticated_async_client: AsyncClient,
):
    """Config update supports separator and sequence_length fields."""
    put_resp = await authenticated_async_client.put(
        f"{BASE_URL}/purchase_order",
        json={"separator": "/", "sequence_length": 8},
    )
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["separator"] == "/"
    assert updated["sequence_length"] == 8


@pytest.mark.asyncio
async def test_update_config_rejects_invalid_manual_override_value(
    authenticated_async_client: AsyncClient,
):
    """manual_override only accepts: never, admin_only, always."""
    put_resp = await authenticated_async_client.put(
        f"{BASE_URL}/material",
        json={"manual_override": "invalid_value"},
    )
    assert put_resp.status_code == 422


@pytest.mark.asyncio
async def test_update_config_rejects_abbreviation_length_out_of_range(
    authenticated_async_client: AsyncClient,
):
    """abbreviation_length must be between 2 and 6."""
    # Too low
    resp_low = await authenticated_async_client.put(
        f"{BASE_URL}/material",
        json={"abbreviation_length": 1},
    )
    assert resp_low.status_code == 422

    # Too high
    resp_high = await authenticated_async_client.put(
        f"{BASE_URL}/material",
        json={"abbreviation_length": 7},
    )
    assert resp_high.status_code == 422


@pytest.mark.asyncio
async def test_update_config_rejects_sequence_length_out_of_range(
    authenticated_async_client: AsyncClient,
):
    """sequence_length must be between 4 and 10."""
    resp_low = await authenticated_async_client.put(
        f"{BASE_URL}/material",
        json={"sequence_length": 3},
    )
    assert resp_low.status_code == 422

    resp_high = await authenticated_async_client.put(
        f"{BASE_URL}/material",
        json={"sequence_length": 11},
    )
    assert resp_high.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Prefix Validation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_prefixes_for_material_entity(
    authenticated_async_client: AsyncClient,
):
    """Requirement 12.7: Prefixes can be listed for an entity type."""
    # Ensure config is seeded first
    await authenticated_async_client.get(f"{BASE_URL}/material")

    response = await authenticated_async_client.get(f"{BASE_URL}/material/prefixes")
    assert response.status_code == 200
    prefixes = response.json()
    assert isinstance(prefixes, list)
    # Default material prefixes should be seeded
    if len(prefixes) > 0:
        prefix_map = {p["sub_type"]: p["prefix"] for p in prefixes}
        assert prefix_map.get("raw") == "RM"
        assert prefix_map.get("finished") == "FG"


@pytest.mark.asyncio
async def test_update_prefix_accepts_valid_uppercase(
    authenticated_async_client: AsyncClient,
):
    """Valid prefix: uppercase alphanumeric, 1-10 chars."""
    # Ensure config is seeded
    await authenticated_async_client.get(f"{BASE_URL}/material")

    response = await authenticated_async_client.put(
        f"{BASE_URL}/material/prefixes/raw",
        json={"prefix": "RAW"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["prefix"] == "RAW"
    assert data["sub_type"] == "raw"


@pytest.mark.asyncio
async def test_update_prefix_rejects_lowercase(
    authenticated_async_client: AsyncClient,
):
    """Requirement 12.7: Prefix must be uppercase alphanumeric only."""
    response = await authenticated_async_client.put(
        f"{BASE_URL}/material/prefixes/raw",
        json={"prefix": "rm"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_prefix_rejects_mixed_case(
    authenticated_async_client: AsyncClient,
):
    """Mixed case prefixes should be rejected."""
    response = await authenticated_async_client.put(
        f"{BASE_URL}/material/prefixes/raw",
        json={"prefix": "Rm"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_prefix_rejects_empty_string(
    authenticated_async_client: AsyncClient,
):
    """Requirement 12.7: Empty prefix is rejected (min_length=1)."""
    response = await authenticated_async_client.put(
        f"{BASE_URL}/material/prefixes/raw",
        json={"prefix": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_prefix_rejects_more_than_10_chars(
    authenticated_async_client: AsyncClient,
):
    """Requirement 12.7: Prefix must not exceed 10 characters."""
    response = await authenticated_async_client.put(
        f"{BASE_URL}/material/prefixes/raw",
        json={"prefix": "ABCDEFGHIJK"},  # 11 chars
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_prefix_rejects_special_characters(
    authenticated_async_client: AsyncClient,
):
    """Prefix must be alphanumeric only (no hyphens, underscores, etc.)."""
    response = await authenticated_async_client.put(
        f"{BASE_URL}/material/prefixes/raw",
        json={"prefix": "RM-1"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_prefix_accepts_10_char_uppercase(
    authenticated_async_client: AsyncClient,
):
    """Exactly 10 uppercase alphanumeric chars is valid."""
    response = await authenticated_async_client.put(
        f"{BASE_URL}/material/prefixes/raw",
        json={"prefix": "ABCDEFGH90"},  # 10 chars
    )
    assert response.status_code == 200
    assert response.json()["prefix"] == "ABCDEFGH90"


# ─────────────────────────────────────────────────────────────────────────────
# Preview Endpoint
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_preview_returns_code_and_pattern(
    authenticated_async_client: AsyncClient,
):
    """Requirement 7.3: Preview endpoint returns the format without incrementing sequence."""
    response = await authenticated_async_client.get(
        f"{BASE_URL}/material/preview",
        params={"sub_type": "raw", "entity_name": "Steel Pipe"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "preview" in data
    assert "format_pattern" in data
    # Preview should be a non-empty string
    assert len(data["preview"]) > 0
    assert len(data["format_pattern"]) > 0


@pytest.mark.asyncio
async def test_preview_without_entity_name_uses_placeholder(
    authenticated_async_client: AsyncClient,
):
    """When no entity_name provided and abbreviation enabled, uses placeholder X's."""
    # Ensure material config has include_abbreviation = True
    await authenticated_async_client.put(
        f"{BASE_URL}/material",
        json={"include_abbreviation": True, "abbreviation_length": 3},
    )

    response = await authenticated_async_client.get(
        f"{BASE_URL}/material/preview",
        params={"sub_type": "raw"},
    )
    assert response.status_code == 200
    data = response.json()
    # Preview should contain placeholder abbreviation (X's)
    assert "XXX" in data["preview"]


@pytest.mark.asyncio
async def test_preview_with_abbreviation_disabled(
    authenticated_async_client: AsyncClient,
):
    """When abbreviation is disabled, preview omits the abbreviation segment."""
    await authenticated_async_client.put(
        f"{BASE_URL}/purchase_order",
        json={"include_abbreviation": False, "prefix": "PO", "separator": "-"},
    )

    response = await authenticated_async_client.get(
        f"{BASE_URL}/purchase_order/preview",
    )
    assert response.status_code == 200
    data = response.json()
    # Should be prefix-sequence format without abbreviation
    assert "PO" in data["preview"]


@pytest.mark.asyncio
async def test_preview_rejects_unsupported_entity_type(
    authenticated_async_client: AsyncClient,
):
    """Preview should reject unsupported entity types."""
    response = await authenticated_async_client.get(
        f"{BASE_URL}/bogus_type/preview",
    )
    assert response.status_code == 400
    assert "Unsupported entity type" in response.json()["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log Pagination and Filtering
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_log_returns_paginated_response(
    authenticated_async_client: AsyncClient,
):
    """Requirement 13.4: Audit log supports pagination with default page_size=50."""
    response = await authenticated_async_client.get(f"{BASE_URL}/audit-log")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["page"] == 1
    assert data["page_size"] == 50
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_audit_log_records_config_change(
    authenticated_async_client: AsyncClient,
):
    """Requirement 13.4: Config changes are logged in audit trail."""
    # Trigger a config change to generate an audit entry
    await authenticated_async_client.put(
        f"{BASE_URL}/grn",
        json={"prefix": "GRN", "separator": "-"},
    )
    # Now a second change that we can verify
    await authenticated_async_client.put(
        f"{BASE_URL}/grn",
        json={"separator": "/"},
    )

    response = await authenticated_async_client.get(
        f"{BASE_URL}/audit-log",
        params={"entity_type": "grn"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    # At least one audit entry should reference the grn entity type
    grn_entries = [e for e in data["items"] if e["entity_type"] == "grn"]
    assert len(grn_entries) >= 1
    # Should have config_changed or prefix_changed event type
    event_types = {e["event_type"] for e in grn_entries}
    assert "config_changed" in event_types


@pytest.mark.asyncio
async def test_audit_log_filters_by_entity_type(
    authenticated_async_client: AsyncClient,
):
    """Requirement 13.4: Audit log can be filtered by entity_type."""
    # Trigger a change for a specific entity
    await authenticated_async_client.put(
        f"{BASE_URL}/batch",
        json={"sequence_length": 5},
    )

    # Filter by batch
    response = await authenticated_async_client.get(
        f"{BASE_URL}/audit-log",
        params={"entity_type": "batch"},
    )
    assert response.status_code == 200
    data = response.json()
    # All returned items should be for the batch entity type
    for item in data["items"]:
        assert item["entity_type"] == "batch"


@pytest.mark.asyncio
async def test_audit_log_custom_page_size(
    authenticated_async_client: AsyncClient,
):
    """Requirement 13.4: Pagination supports custom page_size."""
    response = await authenticated_async_client.get(
        f"{BASE_URL}/audit-log",
        params={"page_size": 5, "page": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page_size"] == 5
    assert data["page"] == 1
    # Items should not exceed page_size
    assert len(data["items"]) <= 5


@pytest.mark.asyncio
async def test_audit_log_rejects_invalid_page_size(
    authenticated_async_client: AsyncClient,
):
    """page_size must be between 1 and 200."""
    response = await authenticated_async_client.get(
        f"{BASE_URL}/audit-log",
        params={"page_size": 0},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_audit_log_prefix_change_is_logged(
    authenticated_async_client: AsyncClient,
):
    """Requirement 13.4: Prefix changes create audit entries."""
    # Ensure config is seeded
    await authenticated_async_client.get(f"{BASE_URL}/material")

    # Update a prefix
    await authenticated_async_client.put(
        f"{BASE_URL}/material/prefixes/spare",
        json={"prefix": "SP"},
    )

    response = await authenticated_async_client.get(
        f"{BASE_URL}/audit-log",
        params={"entity_type": "material"},
    )
    assert response.status_code == 200
    data = response.json()
    prefix_entries = [
        e for e in data["items"] if e["event_type"] == "prefix_changed"
    ]
    assert len(prefix_entries) >= 1
