"""
Phase 0 Integration Tests — Number Series Configuration
=========================================================
Tests for: GET /settings/number-series
           PUT /settings/number-series/{entity_type}
           GET /settings/number-series/{entity_type}/preview

Covers:
  TC-0.1  GET /settings/number-series returns all 9 entity types
  TC-0.2  PUT /settings/number-series/{entity_type} accepts valid prefix/padding
  TC-0.3  Rejects invalid prefix (> 10 chars) with 422
  TC-0.4  Rejects invalid padding / sequence_length (> 10) with 422
  TC-0.5  GET /settings/number-series/{entity_type}/preview returns formatted
          code without incrementing the sequence counter
  TC-0.6  Audit log entry written to number_series_audit_log on config change

Requirements: 0 (Req 0 AC 1–5)
"""
from __future__ import annotations

# Import the FastAPI app at module-level so all SQLAlchemy models are registered
# into Base.metadata before the session-scoped e2e_db_engine fixture calls
# Base.metadata.create_all().  Without this, models with cross-domain FK
# references (e.g. users.client_id → sales_clients.id) are not yet known to
# SQLAlchemy and create_all raises NoReferencedTableError.
import backend.app.main  # noqa: F401  (side-effect: registers all ORM models)

import pytest
from httpx import AsyncClient
from sqlalchemy import select, func

from backend.app.infrastructure.persistence.models.number_series_models import (
    NumberSeriesAuditLogModel,
)

BASE_URL = "/api/v1/settings/number-series"

# The 9 entity types specified in Requirement 0, AC 1.
# (The implementation seeds 10 — "batch" is included. We assert at least these 9.)
REQUIRED_ENTITY_TYPES = {
    "material",
    "product",
    "purchase_order",
    "sales_order",
    "invoice",
    "grn",
    "work_order",
    "customer",
    "supplier",
}


# ─────────────────────────────────────────────────────────────────────────────
# TC-0.1  GET /settings/number-series returns all required entity types
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_number_series_returns_all_required_entity_types(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 1: GET /settings/number-series must return a configurable entry for each
    of the 9 required entity types.

    Validates: Requirements 0 AC 1
    """
    response = await async_client.get(
        f"{BASE_URL}",
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert response.status_code == 200, (
        f"Expected 200 but got {response.status_code}: {response.text}"
    )

    configs = response.json()
    assert isinstance(configs, list), "Response must be a JSON array"
    assert len(configs) >= 9, (
        f"Expected at least 9 entity type configs, got {len(configs)}"
    )

    entity_types = {c["entity_type"] for c in configs}
    missing = REQUIRED_ENTITY_TYPES - entity_types
    assert not missing, (
        f"Missing required entity types in response: {missing}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-0.2  PUT accepts valid prefix and padding (sequence_length)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_put_number_series_accepts_valid_prefix_and_padding(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 2: A valid prefix (1–10 uppercase alphanumeric) and valid padding width
    (sequence_length 4–10) must be accepted and persisted.

    Validates: Requirements 0 AC 2
    """
    payload = {
        "prefix": "MATV2",       # 5 uppercase alphanumeric chars — valid
        "sequence_length": 8,    # within allowed range 4–10
        "separator": "-",
        "auto_generate": True,
    }

    response = await async_client.put(
        f"{BASE_URL}/material",
        json=payload,
        headers=admin_user["headers"],
    )

    assert response.status_code == 200, (
        f"Expected 200 but got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert data["prefix"] == "MATV2"
    assert data["sequence_length"] == 8
    assert data["entity_type"] == "material"


# ─────────────────────────────────────────────────────────────────────────────
# TC-0.3  Rejects prefix that exceeds 10 characters
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_put_number_series_rejects_prefix_longer_than_10_chars(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 2: prefix must be 1–10 uppercase alphanumeric characters.
    A prefix of 11 characters must be rejected with HTTP 422.

    Validates: Requirements 0 AC 2
    """
    # First capture the current prefix so we can verify it didn't change
    get_before = await async_client.get(
        f"{BASE_URL}/product",
        headers=admin_user["headers"],
    )
    assert get_before.status_code == 200
    prefix_before = get_before.json()["prefix"]

    # Attempt to set an invalid 11-char prefix
    response = await async_client.put(
        f"{BASE_URL}/product",
        json={"prefix": "ABCDEFGHIJK"},  # 11 chars — invalid
        headers=admin_user["headers"],
    )

    assert response.status_code == 422, (
        f"Expected 422 for prefix > 10 chars, got {response.status_code}: {response.text}"
    )

    # Verify previous valid state is preserved
    get_after = await async_client.get(
        f"{BASE_URL}/product",
        headers=admin_user["headers"],
    )
    assert get_after.status_code == 200
    assert get_after.json()["prefix"] == prefix_before, (
        "Previous valid prefix must be preserved after a rejected update"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-0.4  Rejects invalid padding (sequence_length out of allowed range)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_put_number_series_rejects_invalid_padding(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 2: padding width (sequence_length) must be between 4 and 10.
    Values of 3 (below min) and 11 (above max) must be rejected with HTTP 422.

    NOTE: Requirement 0 AC 2 specifies 1–12 digits; the API schema enforces
    the tighter constraint of 4–10 as the implemented validation range.

    Validates: Requirements 0 AC 2
    """
    # sequence_length below minimum (< 4)
    resp_low = await async_client.put(
        f"{BASE_URL}/sales_order",
        json={"sequence_length": 3},
        headers=admin_user["headers"],
    )
    assert resp_low.status_code == 422, (
        f"Expected 422 for sequence_length=3 (below min 4), "
        f"got {resp_low.status_code}: {resp_low.text}"
    )

    # sequence_length above maximum (> 10)
    resp_high = await async_client.put(
        f"{BASE_URL}/sales_order",
        json={"sequence_length": 11},
        headers=admin_user["headers"],
    )
    assert resp_high.status_code == 422, (
        f"Expected 422 for sequence_length=11 (above max 10), "
        f"got {resp_high.status_code}: {resp_high.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-0.5  GET preview returns formatted code without incrementing sequence
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_preview_returns_formatted_code_without_incrementing_sequence(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
    e2e_db_session,
    test_tenant,
):
    """
    AC 4: GET /settings/number-series/{entity_type}/preview must return a
    formatted code example without incrementing the sequence counter.

    The test calls preview twice and verifies:
    - Both calls return 200 with a non-empty `preview` and `format_pattern`
    - The returned preview strings are identical (sequence was NOT incremented)

    Validates: Requirements 0 AC 4
    """
    from backend.app.infrastructure.persistence.models.number_series_models import (
        NumberSeriesSequenceModel,
    )

    # Configure a known prefix/sequence for the work_order entity
    await async_client.put(
        f"{BASE_URL}/work_order",
        json={"prefix": "WO", "sequence_length": 6, "separator": "-", "auto_generate": True},
        headers=admin_user["headers"],
    )

    # First preview call
    resp1 = await async_client.get(
        f"{BASE_URL}/work_order/preview",
        headers=admin_user["headers"],
    )
    assert resp1.status_code == 200, (
        f"First preview call failed: {resp1.status_code} {resp1.text}"
    )
    data1 = resp1.json()
    assert "preview" in data1 and data1["preview"], "preview field must be non-empty"
    assert "format_pattern" in data1 and data1["format_pattern"], (
        "format_pattern field must be non-empty"
    )

    # Second preview call — should return the same formatted code
    resp2 = await async_client.get(
        f"{BASE_URL}/work_order/preview",
        headers=admin_user["headers"],
    )
    assert resp2.status_code == 200, (
        f"Second preview call failed: {resp2.status_code} {resp2.text}"
    )
    data2 = resp2.json()

    assert data1["preview"] == data2["preview"], (
        f"Sequence was incremented between preview calls: "
        f"first={data1['preview']!r}, second={data2['preview']!r}"
    )

    # Verify the sequence counter row (if it exists) was NOT advanced
    from sqlalchemy import select
    seq_row = await e2e_db_session.scalar(
        select(NumberSeriesSequenceModel).where(
            NumberSeriesSequenceModel.tenant_id == test_tenant.id,
            NumberSeriesSequenceModel.entity_type == "work_order",
        )
    )
    if seq_row is not None:
        # The next_number should still be at its initial value (1) because
        # no codes have been generated — only previewed.
        assert seq_row.next_number == 1, (
            f"Sequence counter was incremented by preview call; "
            f"next_number={seq_row.next_number}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TC-0.6  Audit log entry written to number_series_audit_log on change
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_put_number_series_writes_audit_log_entry(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
    e2e_db_session,
    test_tenant,
):
    """
    AC 5: A change to a number series config must produce an entry in
    number_series_audit_log containing previous values, new values, user
    identity, and timestamp.

    Validates: Requirements 0 AC 5
    """
    # Count existing audit entries for invoice before the update
    count_before = await e2e_db_session.scalar(
        select(func.count(NumberSeriesAuditLogModel.id)).where(
            NumberSeriesAuditLogModel.tenant_id == test_tenant.id,
            NumberSeriesAuditLogModel.entity_type == "invoice",
        )
    )
    count_before = count_before or 0

    # Trigger a config change
    put_resp = await async_client.put(
        f"{BASE_URL}/invoice",
        json={"prefix": "INVTEST", "separator": "/"},
        headers=admin_user["headers"],
    )
    assert put_resp.status_code == 200, (
        f"PUT failed: {put_resp.status_code} {put_resp.text}"
    )

    # Flush the session so we see the newly committed row
    await e2e_db_session.rollback()

    count_after = await e2e_db_session.scalar(
        select(func.count(NumberSeriesAuditLogModel.id)).where(
            NumberSeriesAuditLogModel.tenant_id == test_tenant.id,
            NumberSeriesAuditLogModel.entity_type == "invoice",
        )
    )
    count_after = count_after or 0

    assert count_after > count_before, (
        f"Expected a new audit log entry after PUT, "
        f"but count stayed at {count_after}"
    )

    # Fetch the most recent entry and verify required fields are present
    latest_entry = await e2e_db_session.scalar(
        select(NumberSeriesAuditLogModel)
        .where(
            NumberSeriesAuditLogModel.tenant_id == test_tenant.id,
            NumberSeriesAuditLogModel.entity_type == "invoice",
        )
        .order_by(NumberSeriesAuditLogModel.timestamp.desc())
        .limit(1)
    )

    assert latest_entry is not None, "Audit log entry must exist after config change"
    assert latest_entry.entity_type == "invoice"
    assert latest_entry.event_type == "config_changed"
    assert latest_entry.user_id is not None, "user_id must be recorded"
    assert latest_entry.timestamp is not None, "timestamp must be recorded"
    # old_value and new_value capture the previous and new state
    assert latest_entry.new_value is not None, "new_value must be recorded"
    # old_value may be None if this is the first change, otherwise it should exist
    # We just verify the audit endpoint also surfaces this entry
    audit_api_resp = await async_client.get(
        f"{BASE_URL}/audit-log",
        params={"entity_type": "invoice"},
        headers=admin_user["headers"],
    )
    assert audit_api_resp.status_code == 200
    audit_data = audit_api_resp.json()
    assert audit_data["total"] >= 1, (
        "GET /audit-log must return at least one entry after config change"
    )
    entry_types = {e["event_type"] for e in audit_data["items"]}
    assert "config_changed" in entry_types, (
        "Audit log must contain a 'config_changed' entry after PUT"
    )
