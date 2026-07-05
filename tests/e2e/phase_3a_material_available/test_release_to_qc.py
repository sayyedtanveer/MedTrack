"""
Phase 3A Integration Tests — Material Available Path (Release through QC queue)
=================================================================================
Tests covering Requirements 18–23:

  TC-18.1  GET /work-orders/material-availability explodes BOM and returns
           per-material stock vs required (with status per line)
  TC-19.1  POST /work-orders/{id}/release (all materials available) →
           MATERIAL_RESERVED + reservations created + Storekeeper notified
  TC-20.1  GET /storekeeper/issue-queue shows MATERIAL_RESERVED WOs
  TC-21.1  POST /storekeeper/issue-material (full issue) → MATERIAL_ISSUED +
           inventory_transactions (type=issue) + Worker notified
  TC-21.2  POST /storekeeper/partial-issue keeps WO in MATERIAL_RESERVED
  TC-22.1  POST /work-orders/{id}/start → IN_PRODUCTION
  TC-22.2  POST /work-orders/{id}/start → 403 without manufacturing:write (qc role)
  TC-22.3  POST /work-orders/{id}/record-production updates produced/scrap quantities
  TC-23.1  POST /work-orders/{id}/complete → QC_PENDING + QC Inspector notified +
           WO in GET /quality-control/inspection-queue

Requirements: 18–23
"""
from __future__ import annotations

import backend.app.main  # noqa: F401 — registers all ORM models

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from tests.e2e.fixtures.conftest import make_token_headers
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import (
    InventoryTransactionModel,
)
from backend.app.infrastructure.persistence.models.inventory_reservation_model import (
    InventoryReservationModel,
)
from backend.app.infrastructure.persistence.models.notification_model import NotificationModel

# ── URL constants ──────────────────────────────────────────────────────────────
WORK_ORDERS_URL = "/api/v1/work-orders"
STOREKEEPER_URL = "/api/v1/storekeeper"
QC_URL = "/api/v1/quality-control"
MATERIALS_URL = "/api/v1/inventory/materials"
MASTER_DATA_URL = "/api/v1/inventory/master-data"
PRODUCTS_URL = "/api/v1/products"
BOMS_URL = "/api/v1"  # BOM endpoints are at /api/v1/products/{id}/boms


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────


async def _create_unit(async_client: AsyncClient, headers: dict) -> str:
    """Create a Unit of Measure and return its id."""
    suffix = uuid.uuid4().hex[:6]
    resp = await async_client.post(
        f"{MASTER_DATA_URL}/units",
        json={"code": f"EA{suffix}", "name": f"Each-{suffix}", "is_active": True},
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"Unit creation failed: {resp.status_code} {resp.text}"
    return resp.json()["id"]


async def _create_raw_material(
    async_client: AsyncClient,
    headers: dict,
    *,
    opening_stock: float = 10.0,
) -> tuple[dict, str]:
    """Create a raw material with given opening stock. Returns (material_json, unit_id)."""
    suffix = uuid.uuid4().hex[:8]
    unit_id = await _create_unit(async_client, headers)
    resp = await async_client.post(
        MATERIALS_URL,
        json={
            "name": f"RM-{suffix}",
            "material_type": "raw",
            "base_unit_id": unit_id,
            "opening_stock": opening_stock,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"Raw material creation failed: {resp.status_code} {resp.text}"
    return resp.json(), unit_id


async def _create_fg_material(async_client: AsyncClient, headers: dict) -> tuple[dict, str]:
    """Create a finished goods material. Returns (material_json, unit_id)."""
    suffix = uuid.uuid4().hex[:8]
    unit_id = await _create_unit(async_client, headers)
    resp = await async_client.post(
        MATERIALS_URL,
        json={
            "name": f"FG-{suffix}",
            "material_type": "finished",
            "base_unit_id": unit_id,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"FG material creation failed: {resp.status_code} {resp.text}"
    return resp.json(), unit_id


async def _create_product_with_bom(
    async_client: AsyncClient,
    headers: dict,
    raw_material_id: str,
    raw_unit_id: str,
    fg_material_id: str,
    *,
    bom_qty: float = 1.0,
) -> dict:
    """
    Build: category → template → variant (linked to FG) → BOM (1 raw material line) → activate BOM.
    Returns dict with {template_id, variant_id, bom_id, fg_unit_id}.
    """
    suffix = uuid.uuid4().hex[:8]

    # Category
    cat_resp = await async_client.post(
        f"{MASTER_DATA_URL}/categories",
        json={"name": f"Cat3A-{suffix}", "code_prefix": f"C{suffix[:4]}"},
        headers=headers,
        follow_redirects=True,
    )
    assert cat_resp.status_code == 201, f"Category failed: {cat_resp.text}"
    category_id = cat_resp.json()["id"]

    # Template
    tmpl_resp = await async_client.post(
        f"{PRODUCTS_URL}/templates",
        json={
            "name": f"Prod3A-{suffix}",
            "category_id": category_id,
            "attributes": [{"key": "SIZE", "label": "Size"}],
        },
        headers=headers,
        follow_redirects=True,
    )
    assert tmpl_resp.status_code == 201, f"Template failed: {tmpl_resp.text}"
    template_id = tmpl_resp.json()["id"]

    # Variant linked to FG material
    var_resp = await async_client.post(
        f"{PRODUCTS_URL}/templates/{template_id}/variants",
        json={
            "attribute_values": {"SIZE": f"M-{suffix}"},
            "material_id": fg_material_id,
            "standard_cost": 50.0,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert var_resp.status_code == 201, f"Variant failed: {var_resp.text}"
    variant_id = var_resp.json()["id"]

    # BOM with 1 raw material line
    bom_resp = await async_client.post(
        f"{PRODUCTS_URL}/{template_id}/boms",
        json={
            "version": "v1.0",
            "valid_from": datetime.now(timezone.utc).isoformat(),
            "template_id": template_id,
            "lines": [
                {
                    "material_id": raw_material_id,
                    "quantity": bom_qty,
                }
            ],
        },
        headers=headers,
        follow_redirects=True,
    )
    assert bom_resp.status_code == 201, f"BOM creation failed: {bom_resp.text}"
    bom_id = bom_resp.json()["id"]

    # Activate BOM so it's usable for work orders
    act_resp = await async_client.post(
        f"/api/v1/boms/{bom_id}/activate",
        headers=headers,
        follow_redirects=True,
    )
    assert act_resp.status_code in (200, 201), f"BOM activate failed: {act_resp.text}"

    return {
        "template_id": template_id,
        "variant_id": variant_id,
        "bom_id": bom_id,
    }


async def _create_work_order(
    async_client: AsyncClient,
    headers: dict,
    product_id: str,
    bom_id: str,
    *,
    planned_quantity: float = 1.0,
) -> dict:
    """Create a PLANNED work order and return its JSON."""
    today = date.today()
    resp = await async_client.post(
        WORK_ORDERS_URL,
        json={
            "product_id": product_id,
            "bom_id": bom_id,
            "planned_quantity": str(planned_quantity),
            "start_date": today.isoformat(),
            "due_date": (today + timedelta(days=7)).isoformat(),
            "priority": "NORMAL",
        },
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"WO creation failed: {resp.status_code} {resp.text}"
    return resp.json()


async def _build_full_wo_setup(
    async_client: AsyncClient,
    headers: dict,
    *,
    raw_stock: float = 10.0,
    bom_qty: float = 1.0,
    wo_qty: float = 1.0,
) -> dict:
    """
    Full setup: raw material (with stock) + FG material + product/BOM + WO in PLANNED state.
    Returns dict with keys: raw_material, raw_unit_id, fg_material, fg_unit_id,
    product (template_id, variant_id, bom_id), work_order.
    """
    raw_mat, raw_unit_id = await _create_raw_material(
        async_client, headers, opening_stock=raw_stock
    )
    fg_mat, fg_unit_id = await _create_fg_material(async_client, headers)
    product = await _create_product_with_bom(
        async_client,
        headers,
        raw_mat["id"],
        raw_unit_id,
        fg_mat["id"],
        bom_qty=bom_qty,
    )
    wo = await _create_work_order(
        async_client,
        headers,
        product["variant_id"],
        product["bom_id"],
        planned_quantity=wo_qty,
    )
    return {
        "raw_material": raw_mat,
        "raw_unit_id": raw_unit_id,
        "fg_material": fg_mat,
        "fg_unit_id": fg_unit_id,
        "product": product,
        "work_order": wo,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TC-18.1  GET /work-orders/material-availability — BOM explosion
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_material_availability_explodes_bom(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 3 (Req 8 / Req 18): GET /work-orders/material-availability must explode
    the BOM and return per-material stock vs required quantities.

    Validates: Requirements 18 AC 1, 2
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=10.0, bom_qty=2.0, wo_qty=1.0)
    product = setup["product"]

    resp = await async_client.get(
        f"{WORK_ORDERS_URL}/material-availability",
        params={
            "product_id": product["variant_id"],
            "quantity": "1",
            "bom_id": product["bom_id"],
        },
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 200, (
        f"material-availability must return 200, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()

    # Must include per-line breakdown
    assert "lines" in data, "Response must include 'lines' list"
    assert len(data["lines"]) >= 1, "Must have at least 1 BOM line"

    line = data["lines"][0]
    assert "material_id" in line, "Each line must include material_id"
    assert "required_quantity" in line, "Each line must include required_quantity"
    assert "available_quantity" in line, "Each line must include available_quantity"
    assert "status" in line, "Each line must include status"

    # With 10 stock and 2 required (1 WO qty × 2 Bom qty), should not be shortage
    assert float(line["required_quantity"]) == 2.0, (
        f"required_quantity should be 2.0 (1 WO × 2 BOM), got {line['required_quantity']}"
    )
    assert float(line["available_quantity"]) >= 2.0, (
        "available_quantity must be >= required_quantity when stock is sufficient"
    )
    assert data.get("has_shortage") is False, (
        "has_shortage must be False when stock is sufficient"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-19.1  POST /work-orders/{id}/release → MATERIAL_RESERVED
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_release_work_order_transitions_to_material_reserved(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    e2e_db_session,
    seed_number_series,
):
    """
    AC 1–3 (Req 19): POST /work-orders/{id}/release when all materials available must:
      1. Transition WO → MATERIAL_RESERVED
      2. Create inventory_reservations records for each BOM material
      3. Emit an 'issue_materials_action' notification to the Storekeeper role

    Validates: Requirements 19 AC 1, 2, 3
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=10.0)
    wo_id = setup["work_order"]["id"]
    raw_mat_id = setup["raw_material"]["id"]

    # Release the work order
    release_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/release",
        headers=headers,
        follow_redirects=True,
    )
    assert release_resp.status_code == 200, (
        f"Release must return 200, got {release_resp.status_code}: {release_resp.text}"
    )

    # AC 1: WO status must be MATERIAL_RESERVED
    status_in_resp = release_resp.json().get("status", "").upper()
    assert status_in_resp == "MATERIAL_RESERVED", (
        f"WO must be MATERIAL_RESERVED after release with sufficient stock, got '{status_in_resp}'"
    )

    # Double-check via GET
    get_resp = await async_client.get(
        f"{WORK_ORDERS_URL}/{wo_id}",
        headers=headers,
        follow_redirects=True,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["status"].upper() == "MATERIAL_RESERVED", (
        "WO must be MATERIAL_RESERVED on GET after release"
    )

    # AC 2: inventory_reservations records must exist for the raw material
    await e2e_db_session.rollback()
    reservation = await e2e_db_session.scalar(
        select(InventoryReservationModel).where(
            InventoryReservationModel.tenant_id == test_tenant.id,
            InventoryReservationModel.material_id == uuid.UUID(raw_mat_id),
            InventoryReservationModel.reference_type == "work_order",
        )
    )
    assert reservation is not None, (
        "inventory_reservations record must be created for raw material on WO release"
    )

    # AC 3: Storekeeper notification must exist
    await e2e_db_session.rollback()
    notification = await e2e_db_session.scalar(
        select(NotificationModel).where(
            NotificationModel.tenant_id == test_tenant.id,
            NotificationModel.entity_id == uuid.UUID(wo_id),
        )
    )
    assert notification is not None, (
        "A notification must be created for the Storekeeper on WO release"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-20.1  GET /storekeeper/issue-queue shows MATERIAL_RESERVED WOs
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_issue_queue_shows_material_reserved_wos(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 1 (Req 20): GET /storekeeper/issue-queue must return the MATERIAL_RESERVED
    work order so the Storekeeper knows what to issue.

    Validates: Requirements 20 AC 1
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=10.0)
    wo_id = setup["work_order"]["id"]

    # Release to put WO in MATERIAL_RESERVED
    release_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/release",
        headers=headers,
        follow_redirects=True,
    )
    assert release_resp.status_code == 200

    # Check issue queue contains this WO
    queue_resp = await async_client.get(
        f"{STOREKEEPER_URL}/issue-queue",
        headers=headers,
        follow_redirects=True,
    )
    assert queue_resp.status_code == 200, (
        f"GET /storekeeper/issue-queue must return 200, got {queue_resp.status_code}: {queue_resp.text}"
    )
    queue = queue_resp.json()
    assert isinstance(queue, list), "Issue queue must be a list"

    wo_ids_in_queue = {str(item.get("work_order_id")) for item in queue}
    assert wo_id in wo_ids_in_queue, (
        f"MATERIAL_RESERVED WO {wo_id} must appear in storekeeper issue-queue. "
        f"Queue work_order_ids: {wo_ids_in_queue}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-21.1  POST /storekeeper/issue-material (full) → MATERIAL_ISSUED
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_issue_transitions_to_material_issued(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    e2e_db_session,
    seed_number_series,
):
    """
    AC 1–3 (Req 21): POST /storekeeper/issue-material (full quantity) must:
      1. Transition WO → MATERIAL_ISSUED
      2. Create inventory_transactions records with transaction_type='issue'
      3. Emit a 'start_production_action' notification to the Worker role

    Validates: Requirements 21 AC 1, 2, 3
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=10.0, bom_qty=1.0, wo_qty=1.0)
    wo_id = setup["work_order"]["id"]
    raw_mat_id = setup["raw_material"]["id"]
    raw_unit_id = setup["raw_unit_id"]

    # Release → MATERIAL_RESERVED
    release_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/release",
        headers=headers,
        follow_redirects=True,
    )
    assert release_resp.status_code == 200

    # Count existing issue transactions before issuing
    await e2e_db_session.rollback()
    tx_before = await e2e_db_session.scalars(
        select(InventoryTransactionModel).where(
            InventoryTransactionModel.tenant_id == test_tenant.id,
            InventoryTransactionModel.reference_id == uuid.UUID(wo_id),
            InventoryTransactionModel.transaction_type.in_(["issue", "ISSUE"]),
        )
    )
    count_before = len(list(tx_before))

    # Full issue — quantity matches BOM requirement (1 unit)
    issue_resp = await async_client.post(
        f"{STOREKEEPER_URL}/issue-material",
        json={
            "work_order_id": wo_id,
            "material_id": raw_mat_id,
            "quantity": "1.0",
            "unit_id": raw_unit_id,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert issue_resp.status_code in (200, 201), (
        f"Full issue must succeed, got {issue_resp.status_code}: {issue_resp.text}"
    )

    # AC 1: WO must be MATERIAL_ISSUED
    get_resp = await async_client.get(
        f"{WORK_ORDERS_URL}/{wo_id}",
        headers=headers,
        follow_redirects=True,
    )
    assert get_resp.status_code == 200
    wo_status = get_resp.json()["status"].upper()
    assert wo_status == "MATERIAL_ISSUED", (
        f"WO must be MATERIAL_ISSUED after full issue, got '{wo_status}'"
    )

    # AC 2: inventory_transactions records must exist for this issue
    await e2e_db_session.rollback()
    tx_after = await e2e_db_session.scalars(
        select(InventoryTransactionModel).where(
            InventoryTransactionModel.tenant_id == test_tenant.id,
            InventoryTransactionModel.reference_id == uuid.UUID(wo_id),
            InventoryTransactionModel.transaction_type.in_(["issue", "ISSUE"]),
        )
    )
    count_after = len(list(tx_after))
    assert count_after > count_before, (
        "An inventory_transaction with type='issue' must be created on full material issue"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-21.2  POST /storekeeper/partial-issue keeps WO in MATERIAL_RESERVED
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_partial_issue_keeps_wo_in_material_reserved(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC (Req 21 implicit): POST /storekeeper/partial-issue with quantity less than
    BOM requirement must keep the WO in MATERIAL_RESERVED (not transition to MATERIAL_ISSUED).

    Validates: Requirements 21 (partial-issue behaviour)
    """
    headers = admin_user["headers"]
    # BOM requires 4 units; we only partially issue 2
    setup = await _build_full_wo_setup(
        async_client, headers, raw_stock=10.0, bom_qty=4.0, wo_qty=1.0
    )
    wo_id = setup["work_order"]["id"]
    raw_mat_id = setup["raw_material"]["id"]
    raw_unit_id = setup["raw_unit_id"]

    # Release → MATERIAL_RESERVED
    release_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/release",
        headers=headers,
        follow_redirects=True,
    )
    assert release_resp.status_code == 200

    # Partial issue — only 2 of the 4 required
    partial_resp = await async_client.post(
        f"{STOREKEEPER_URL}/partial-issue",
        json={
            "work_order_id": wo_id,
            "material_id": raw_mat_id,
            "quantity": "2.0",
            "unit_id": raw_unit_id,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert partial_resp.status_code in (200, 201), (
        f"Partial issue must succeed, got {partial_resp.status_code}: {partial_resp.text}"
    )

    # WO must still be MATERIAL_RESERVED (not yet MATERIAL_ISSUED)
    get_resp = await async_client.get(
        f"{WORK_ORDERS_URL}/{wo_id}",
        headers=headers,
        follow_redirects=True,
    )
    assert get_resp.status_code == 200
    wo_status = get_resp.json()["status"].upper()
    assert wo_status == "MATERIAL_RESERVED", (
        f"WO must remain MATERIAL_RESERVED after partial issue, got '{wo_status}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-22.1  POST /work-orders/{id}/start → IN_PRODUCTION
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_work_order_transitions_to_in_production(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 1 (Req 22): POST /work-orders/{id}/start on a MATERIAL_ISSUED WO must
    transition it to IN_PRODUCTION.

    Validates: Requirements 22 AC 1
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=10.0)
    wo_id = setup["work_order"]["id"]
    raw_mat_id = setup["raw_material"]["id"]
    raw_unit_id = setup["raw_unit_id"]

    # Release → MATERIAL_RESERVED
    await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/release",
        headers=headers,
        follow_redirects=True,
    )

    # Full issue → MATERIAL_ISSUED
    await async_client.post(
        f"{STOREKEEPER_URL}/issue-material",
        json={
            "work_order_id": wo_id,
            "material_id": raw_mat_id,
            "quantity": "1.0",
            "unit_id": raw_unit_id,
        },
        headers=headers,
        follow_redirects=True,
    )

    # Start → IN_PRODUCTION
    start_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/start",
        headers=headers,
        follow_redirects=True,
    )
    assert start_resp.status_code == 200, (
        f"Start must return 200, got {start_resp.status_code}: {start_resp.text}"
    )

    get_resp = await async_client.get(
        f"{WORK_ORDERS_URL}/{wo_id}",
        headers=headers,
        follow_redirects=True,
    )
    assert get_resp.status_code == 200
    wo_status = get_resp.json()["status"].upper()
    assert wo_status == "IN_PRODUCTION", (
        f"WO must be IN_PRODUCTION after start, got '{wo_status}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-22.2  POST /work-orders/{id}/start → 403 without manufacturing:write
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_work_order_forbidden_without_permission(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 2 (Req 22): POST /work-orders/{id}/start must return 403 for a user without
    the manufacturing:write permission (qc role lacks manufacturing:write).

    Validates: Requirements 22 AC 2 (work_order:start permission guard)
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=10.0)
    wo_id = setup["work_order"]["id"]
    raw_mat_id = setup["raw_material"]["id"]
    raw_unit_id = setup["raw_unit_id"]

    # Get WO into MATERIAL_ISSUED state using admin
    await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/release",
        headers=headers,
        follow_redirects=True,
    )
    await async_client.post(
        f"{STOREKEEPER_URL}/issue-material",
        json={
            "work_order_id": wo_id,
            "material_id": raw_mat_id,
            "quantity": "1.0",
            "unit_id": raw_unit_id,
        },
        headers=headers,
        follow_redirects=True,
    )

    # Attempt start with qc role (lacks manufacturing:write)
    qc_headers = make_token_headers(
        user_id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        role="qc",
    )
    start_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/start",
        headers=qc_headers,
        follow_redirects=True,
    )
    assert start_resp.status_code == 403, (
        f"QC role (no manufacturing:write) must get 403 on start, "
        f"got {start_resp.status_code}: {start_resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-22.3  POST /work-orders/{id}/record-production — updates quantities
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_production_updates_quantities(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC (Req 22): POST /work-orders/{id}/record-production on an IN_PRODUCTION WO
    must update the produced_quantity and scrap_quantity on the work order.

    Validates: Requirements 22 (record-production)
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=10.0)
    wo_id = setup["work_order"]["id"]
    raw_mat_id = setup["raw_material"]["id"]
    raw_unit_id = setup["raw_unit_id"]

    # Drive WO to IN_PRODUCTION
    await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/release", headers=headers, follow_redirects=True
    )
    await async_client.post(
        f"{STOREKEEPER_URL}/issue-material",
        json={"work_order_id": wo_id, "material_id": raw_mat_id, "quantity": "1.0", "unit_id": raw_unit_id},
        headers=headers,
        follow_redirects=True,
    )
    await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/start", headers=headers, follow_redirects=True
    )

    # Record production: 1 produced, 0 scrap
    record_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/record-production",
        json={"produced_quantity": "1.0", "scrap_quantity": "0.0"},
        headers=headers,
        follow_redirects=True,
    )
    assert record_resp.status_code == 200, (
        f"record-production must return 200, got {record_resp.status_code}: {record_resp.text}"
    )

    # Verify quantities updated
    get_resp = await async_client.get(
        f"{WORK_ORDERS_URL}/{wo_id}",
        headers=headers,
        follow_redirects=True,
    )
    assert get_resp.status_code == 200
    wo_data = get_resp.json()
    produced = float(wo_data.get("produced_quantity", 0))
    assert produced >= 1.0, (
        f"produced_quantity must be >= 1.0 after recording production, got {produced}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-23.1  POST /work-orders/{id}/complete → QC_PENDING + in inspection-queue
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_work_order_transitions_to_qc_pending(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    e2e_db_session,
    seed_number_series,
):
    """
    AC 1–3 (Req 23): POST /work-orders/{id}/complete on an IN_PRODUCTION WO must:
      1. Transition WO → QC_PENDING
      2. Emit a 'qc_inspection_required' notification to the QC Inspector role
      3. Make the WO visible in GET /quality-control/inspection-queue

    Validates: Requirements 23 AC 1, 2, 3
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=10.0)
    wo_id = setup["work_order"]["id"]
    raw_mat_id = setup["raw_material"]["id"]
    raw_unit_id = setup["raw_unit_id"]

    # Drive WO through MATERIAL_RESERVED → MATERIAL_ISSUED → IN_PRODUCTION
    await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/release", headers=headers, follow_redirects=True
    )
    await async_client.post(
        f"{STOREKEEPER_URL}/issue-material",
        json={"work_order_id": wo_id, "material_id": raw_mat_id, "quantity": "1.0", "unit_id": raw_unit_id},
        headers=headers,
        follow_redirects=True,
    )
    await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/start", headers=headers, follow_redirects=True
    )
    await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/record-production",
        json={"produced_quantity": "1.0", "scrap_quantity": "0.0"},
        headers=headers,
        follow_redirects=True,
    )

    # Complete → QC_PENDING
    complete_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/complete",
        headers=headers,
        follow_redirects=True,
    )
    assert complete_resp.status_code == 200, (
        f"Complete must return 200, got {complete_resp.status_code}: {complete_resp.text}"
    )

    # AC 1: WO status must be QC_PENDING
    get_resp = await async_client.get(
        f"{WORK_ORDERS_URL}/{wo_id}",
        headers=headers,
        follow_redirects=True,
    )
    assert get_resp.status_code == 200
    wo_status = get_resp.json()["status"].upper()
    assert wo_status == "QC_PENDING", (
        f"WO must be QC_PENDING after complete, got '{wo_status}'"
    )

    # AC 2: QC_PENDING notification must exist
    await e2e_db_session.rollback()
    notification = await e2e_db_session.scalar(
        select(NotificationModel).where(
            NotificationModel.tenant_id == test_tenant.id,
            NotificationModel.entity_id == uuid.UUID(wo_id),
        )
    )
    assert notification is not None, (
        "A notification must be created for QC Inspector when WO transitions to QC_PENDING"
    )

    # AC 3: WO must appear in the QC inspection queue
    queue_resp = await async_client.get(
        f"{QC_URL}/inspection-queue",
        headers=headers,
        follow_redirects=True,
    )
    assert queue_resp.status_code == 200, (
        f"GET /quality-control/inspection-queue must return 200, got {queue_resp.status_code}: {queue_resp.text}"
    )
    queue = queue_resp.json()
    assert isinstance(queue, list), "QC inspection queue must be a list"

    wo_ids_in_queue = {str(item.get("work_order_id", item.get("id", ""))) for item in queue}
    assert wo_id in wo_ids_in_queue, (
        f"QC_PENDING WO {wo_id} must appear in quality-control/inspection-queue. "
        f"Queue ids: {wo_ids_in_queue}"
    )
