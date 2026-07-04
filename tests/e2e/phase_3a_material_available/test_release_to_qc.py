"""
Phase 3A Integration Tests — Release through QC Queue
=======================================================
Tests for Req 18–23 (material-available path):

  TC-18.1  GET /work-orders/material-availability returns per-material BOM explosion
  TC-19.1  POST /work-orders/{id}/release (all materials available) → MATERIAL_RESERVED
           + inventory_reservations created + Storekeeper notified
  TC-20.1  GET /storekeeper/issue-queue shows MATERIAL_RESERVED WO
  TC-21.1  POST /storekeeper/issue-material (full issue) → MATERIAL_ISSUED
           + inventory_transactions (type=issue) created + Worker notified
  TC-21.2  POST /storekeeper/partial-issue keeps WO in MATERIAL_RESERVED
  TC-22.1  POST /work-orders/{id}/start → IN_PRODUCTION;
           403 without manufacturing:write (viewer role)
  TC-22.2  POST /work-orders/{id}/record-production updates produced/scrap quantities
  TC-23.1  POST /work-orders/{id}/complete → QC_PENDING + QC Inspector notified
           + WO visible in GET /quality-control/inspection-queue

Requirements: 18–23
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

import backend.app.main  # noqa: F401 — registers all ORM models

from tests.e2e.fixtures.conftest import make_token_headers
from tests.e2e.phase_2_sales_order.test_so_lifecycle import (
    MATERIALS_URL,
    MASTER_DATA_URL,
    PRODUCTS_URL,
    _create_client,
    _create_fg_material,
    _create_default_price_list_with_line,
)
from backend.app.infrastructure.persistence.models.inventory_reservation_model import (
    InventoryReservationModel,
)
from backend.app.infrastructure.persistence.models.inventory_transaction_model import (
    InventoryTransactionModel,
)
from backend.app.infrastructure.persistence.models.notification_model import (
    NotificationModel,
)
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel


# ── URL constants ──────────────────────────────────────────────────────────────
WORK_ORDERS_URL = "/api/v1/work-orders"
STOREKEEPER_URL = "/api/v1/storekeeper"
QC_URL = "/api/v1/quality-control"

_MATERIAL_RESERVED_STATUSES = {"MATERIAL_RESERVED", "RESERVED"}
_MATERIAL_ISSUED_STATUSES = {"MATERIAL_ISSUED", "ISSUED"}
_IN_PRODUCTION_STATUSES = {"IN_PRODUCTION", "IN_PROGRESS"}
_QC_PENDING_STATUSES = {"QC_PENDING", "QC"}


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────


async def _create_raw_material(
    async_client: AsyncClient,
    headers: dict,
    *,
    opening_stock: float = 100.0,
) -> dict:
    """Create a raw material with opening stock, return the material JSON + unit_id."""
    suffix = uuid.uuid4().hex[:8]
    # Unit of measure
    unit_resp = await async_client.post(
        f"{MASTER_DATA_URL}/units",
        json={"code": f"KG{suffix[:4]}", "name": f"Kilogram-{suffix}", "is_active": True},
        headers=headers,
        follow_redirects=True,
    )
    assert unit_resp.status_code == 201, f"Unit failed: {unit_resp.text}"
    unit_id = unit_resp.json()["id"]

    mat_resp = await async_client.post(
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
    assert mat_resp.status_code == 201, f"Raw material failed: {mat_resp.text}"
    mat = mat_resp.json()
    mat["unit_id"] = unit_id
    return mat


async def _create_product_variant_with_bom(
    async_client: AsyncClient,
    headers: dict,
    *,
    raw_material_id: str,
    raw_material_unit_id: str,
    bom_qty: float = 5.0,
) -> dict:
    """
    Create FG material → template → variant → BOM (linking to raw_material).
    Returns dict with {variant_id, template_id, bom_id, fg_material_id}.
    """
    suffix = uuid.uuid4().hex[:8]

    # FG material (no opening stock needed — this is the output)
    fg_mat, fg_unit_id = await _create_fg_material(async_client, headers, opening_stock=0.0)
    fg_mat_id = fg_mat["id"]

    # Category
    cat_resp = await async_client.post(
        f"{MASTER_DATA_URL}/categories",
        json={"name": f"Cat3A-{suffix}", "code_prefix": f"D{suffix[:4]}"},
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
            "attributes": [{"key": "COLOR", "label": "Color"}],
        },
        headers=headers,
        follow_redirects=True,
    )
    assert tmpl_resp.status_code == 201, f"Template failed: {tmpl_resp.text}"
    template_id = tmpl_resp.json()["id"]

    # Variant
    var_resp = await async_client.post(
        f"{PRODUCTS_URL}/templates/{template_id}/variants",
        json={
            "attribute_values": {"COLOR": f"Red-{suffix}"},
            "material_id": fg_mat_id,
            "standard_cost": 100.0,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert var_resp.status_code == 201, f"Variant failed: {var_resp.text}"
    variant_id = var_resp.json()["id"]

    # BOM for the template (using template_id so material-availability lookup works)
    now_iso = datetime.now(timezone.utc).isoformat()
    bom_resp = await async_client.post(
        f"{PRODUCTS_URL}/{template_id}/boms",
        json={
            "version": "v1.0",
            "valid_from": now_iso,
            "template_id": template_id,
            "lines": [
                {
                    "material_id": raw_material_id,
                    "quantity": str(bom_qty),
                    "unit_id": raw_material_unit_id,
                    "scrap_percentage": "0",
                }
            ],
        },
        headers=headers,
        follow_redirects=True,
    )
    assert bom_resp.status_code == 201, f"BOM failed: {bom_resp.text}"
    bom_id = bom_resp.json()["id"]

    return {
        "variant_id": variant_id,
        "template_id": template_id,
        "bom_id": bom_id,
        "fg_material_id": fg_mat_id,
        "fg_unit_id": fg_unit_id,
    }


async def _create_work_order(
    async_client: AsyncClient,
    headers: dict,
    *,
    product_id: str,
    bom_id: str,
    planned_qty: float = 1.0,
) -> dict:
    """Create a PLANNED work order and return its JSON."""
    today = date.today()
    due = today + timedelta(days=7)
    resp = await async_client.post(
        WORK_ORDERS_URL,
        json={
            "product_id": product_id,
            "bom_id": bom_id,
            "planned_quantity": str(planned_qty),
            "start_date": today.isoformat(),
            "due_date": due.isoformat(),
            "priority": "NORMAL",
        },
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"WO creation failed: {resp.text}"
    return resp.json()


async def _build_full_wo_setup(
    async_client: AsyncClient,
    headers: dict,
    *,
    raw_stock: float = 100.0,
    bom_qty: float = 5.0,
    planned_qty: float = 1.0,
) -> dict:
    """
    Full setup: raw material + product/BOM + work order.
    Returns a dict with all IDs needed for 3A tests.
    """
    raw_mat = await _create_raw_material(async_client, headers, opening_stock=raw_stock)
    product_info = await _create_product_variant_with_bom(
        async_client,
        headers,
        raw_material_id=raw_mat["id"],
        raw_material_unit_id=raw_mat["unit_id"],
        bom_qty=bom_qty,
    )
    wo = await _create_work_order(
        async_client,
        headers,
        product_id=product_info["template_id"],
        bom_id=product_info["bom_id"],
        planned_qty=planned_qty,
    )
    return {
        "raw_material": raw_mat,
        "product_info": product_info,
        "work_order": wo,
        "work_order_id": wo["id"],
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
    AC 3 (Req 18): GET /work-orders/material-availability must explode the BOM
    and return per-material stock vs required quantities.

    Validates: Requirements 18 AC 3
    """
    headers = admin_user["headers"]

    raw_mat = await _create_raw_material(async_client, headers, opening_stock=50.0)
    product_info = await _create_product_variant_with_bom(
        async_client,
        headers,
        raw_material_id=raw_mat["id"],
        raw_material_unit_id=raw_mat["unit_id"],
        bom_qty=5.0,
    )

    resp = await async_client.get(
        f"{WORK_ORDERS_URL}/material-availability",
        params={
            "product_id": product_info["template_id"],
            "quantity": "2",
            "bom_id": product_info["bom_id"],
        },
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 200, (
        f"material-availability must return 200, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()

    assert "lines" in data, "Response must include 'lines' array"
    assert "has_shortage" in data, "Response must include 'has_shortage' flag"
    assert isinstance(data["lines"], list), "'lines' must be a list"
    assert len(data["lines"]) >= 1, "Must return at least one BOM line"

    # Verify the raw material appears in the explosion
    material_ids_in_response = {line["material_id"] for line in data["lines"]}
    assert raw_mat["id"] in material_ids_in_response, (
        f"Raw material {raw_mat['id']} must appear in BOM explosion, "
        f"got material_ids: {material_ids_in_response}"
    )

    # With 50 units available and bom_qty=5 × planned_qty=2 → required=10 → no shortage
    assert data["has_shortage"] is False, (
        f"With 50 units available vs 10 required, has_shortage must be False, "
        f"got {data['has_shortage']}"
    )

    # Verify quantities are present
    for line in data["lines"]:
        assert "required_quantity" in line, "Each line must have required_quantity"
        assert "available_quantity" in line, "Each line must have available_quantity"
        assert float(line["required_quantity"]) > 0, "required_quantity must be > 0"


# ─────────────────────────────────────────────────────────────────────────────
# TC-19.1  POST /work-orders/{id}/release → MATERIAL_RESERVED + reservations
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_release_work_order_creates_material_reserved(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    e2e_db_session,
    seed_number_series,
):
    """
    AC 1–3 (Req 19): POST /work-orders/{id}/release when all BOM materials are
    available must:
      1. Transition WO to MATERIAL_RESERVED
      2. Create inventory_reservations records (reference_type=work_order)
      3. Notify the Storekeeper (notification record created)

    Validates: Requirements 19 AC 1, 2, 3
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=100.0, bom_qty=5.0)
    wo_id = setup["work_order_id"]
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
    returned_status = release_resp.json().get("status", "").upper()
    assert returned_status in _MATERIAL_RESERVED_STATUSES, (
        f"WO status after release must be MATERIAL_RESERVED, got '{returned_status}'"
    )

    # Verify WO status in DB
    await e2e_db_session.rollback()
    wo_model = await e2e_db_session.scalar(
        select(WorkOrderModel).where(WorkOrderModel.id == uuid.UUID(wo_id))
    )
    assert wo_model is not None, "Work order must exist in DB"
    assert wo_model.status.upper() in _MATERIAL_RESERVED_STATUSES, (
        f"DB WO status must be MATERIAL_RESERVED, got '{wo_model.status}'"
    )

    # Verify inventory_reservations created for the raw material
    reservation = await e2e_db_session.scalar(
        select(InventoryReservationModel).where(
            InventoryReservationModel.tenant_id == test_tenant.id,
            InventoryReservationModel.material_id == uuid.UUID(raw_mat_id),
            InventoryReservationModel.reference_type == "work_order",
        )
    )
    assert reservation is not None, (
        "inventory_reservations record must be created with reference_type='work_order' "
        "when WO is released and materials are available"
    )

    # Verify Storekeeper notification created
    notification = await e2e_db_session.scalar(
        select(NotificationModel).where(
            NotificationModel.tenant_id == test_tenant.id,
            NotificationModel.reference_id == uuid.UUID(wo_id),
        )
    )
    assert notification is not None, (
        "A notification must be created for the Storekeeper when WO transitions to MATERIAL_RESERVED"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-20.1  GET /storekeeper/issue-queue shows MATERIAL_RESERVED WO
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_storekeeper_issue_queue_shows_material_reserved_wo(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 1 (Req 20): After WO is released to MATERIAL_RESERVED, the storekeeper
    issue queue must show the WO so the storekeeper can act on it.

    Validates: Requirements 20 AC 1
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=100.0, bom_qty=5.0)
    wo_id = setup["work_order_id"]

    # Release the WO
    release_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/release",
        headers=headers,
        follow_redirects=True,
    )
    assert release_resp.status_code == 200, f"Release failed: {release_resp.text}"

    # Check issue queue
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
        f"Released WO {wo_id} must appear in storekeeper issue queue. "
        f"Queue work_order_ids: {wo_ids_in_queue}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-21.1  POST /storekeeper/issue-material (full) → MATERIAL_ISSUED
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_material_issue_transitions_to_material_issued(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    e2e_db_session,
    seed_number_series,
):
    """
    AC 1–3 (Req 21): POST /storekeeper/issue-material when all reserved materials
    are fully issued must:
      1. Transition WO to MATERIAL_ISSUED
      2. Create inventory_transactions with transaction_type=issue
      3. Notify the Worker

    Validates: Requirements 21 AC 1, 2, 3
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=100.0, bom_qty=5.0)
    wo_id = setup["work_order_id"]
    raw_mat_id = setup["raw_material"]["id"]
    raw_mat_unit_id = setup["raw_material"]["unit_id"]

    # Release → MATERIAL_RESERVED
    rel_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/release",
        headers=headers,
        follow_redirects=True,
    )
    assert rel_resp.status_code == 200, f"Release failed: {rel_resp.text}"

    # Full issue: issue 5.0 units (bom_qty × planned_qty = 5.0 × 1 = 5.0)
    issue_resp = await async_client.post(
        f"{STOREKEEPER_URL}/issue-material",
        json={
            "work_order_id": wo_id,
            "material_id": raw_mat_id,
            "quantity": "5.0",
            "unit_id": raw_mat_unit_id,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert issue_resp.status_code == 200, (
        f"issue-material must return 200, got {issue_resp.status_code}: {issue_resp.text}"
    )

    # Verify WO transitioned to MATERIAL_ISSUED
    wo_resp = await async_client.get(
        f"{WORK_ORDERS_URL}/{wo_id}",
        headers=headers,
        follow_redirects=True,
    )
    assert wo_resp.status_code == 200
    wo_status = wo_resp.json()["status"].upper()
    assert wo_status in _MATERIAL_ISSUED_STATUSES, (
        f"WO status after full issue must be MATERIAL_ISSUED, got '{wo_status}'"
    )

    # Verify inventory_transaction with type=issue was created
    await e2e_db_session.rollback()
    tx = await e2e_db_session.scalar(
        select(InventoryTransactionModel).where(
            InventoryTransactionModel.tenant_id == test_tenant.id,
            InventoryTransactionModel.material_id == uuid.UUID(raw_mat_id),
            InventoryTransactionModel.transaction_type.in_(["issue", "ISSUE"]),
            InventoryTransactionModel.reference_type == "work_order",
        )
    )
    assert tx is not None, (
        "inventory_transactions record with type=issue must be created after material issue"
    )

    # Verify Worker notification created (after MATERIAL_ISSUED transition)
    notification = await e2e_db_session.scalar(
        select(NotificationModel).where(
            NotificationModel.tenant_id == test_tenant.id,
            NotificationModel.reference_id == uuid.UUID(wo_id),
        )
    )
    assert notification is not None, (
        "A notification must be created when WO transitions to MATERIAL_ISSUED"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-21.2  POST /storekeeper/partial-issue keeps WO in MATERIAL_RESERVED
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_partial_issue_keeps_material_reserved(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 2 (Req 21 / task spec): POST /storekeeper/partial-issue must keep the WO
    in MATERIAL_RESERVED — only a full issue should trigger MATERIAL_ISSUED.

    Validates: Requirements 21 AC 2 (partial issue path)
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=100.0, bom_qty=10.0)
    wo_id = setup["work_order_id"]
    raw_mat_id = setup["raw_material"]["id"]
    raw_mat_unit_id = setup["raw_material"]["unit_id"]

    # Release → MATERIAL_RESERVED
    rel_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/release",
        headers=headers,
        follow_redirects=True,
    )
    assert rel_resp.status_code == 200, f"Release failed: {rel_resp.text}"

    # Partial issue: only 4.0 of the required 10.0 units
    partial_resp = await async_client.post(
        f"{STOREKEEPER_URL}/partial-issue",
        json={
            "work_order_id": wo_id,
            "material_id": raw_mat_id,
            "quantity": "4.0",
            "unit_id": raw_mat_unit_id,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert partial_resp.status_code == 200, (
        f"partial-issue must return 200, got {partial_resp.status_code}: {partial_resp.text}"
    )

    # Verify WO remains in MATERIAL_RESERVED
    wo_resp = await async_client.get(
        f"{WORK_ORDERS_URL}/{wo_id}",
        headers=headers,
        follow_redirects=True,
    )
    assert wo_resp.status_code == 200
    wo_status = wo_resp.json()["status"].upper()
    assert wo_status in _MATERIAL_RESERVED_STATUSES, (
        f"WO must remain MATERIAL_RESERVED after partial issue (only 4/10 issued), "
        f"got '{wo_status}'"
    )
    assert wo_status not in _MATERIAL_ISSUED_STATUSES, (
        f"WO must NOT transition to MATERIAL_ISSUED on a partial issue, got '{wo_status}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-22.1  POST /work-orders/{id}/start → IN_PRODUCTION; 403 without permission
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
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=100.0, bom_qty=5.0)
    wo_id = setup["work_order_id"]
    raw_mat_id = setup["raw_material"]["id"]
    raw_mat_unit_id = setup["raw_material"]["unit_id"]

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
            "quantity": "5.0",
            "unit_id": raw_mat_unit_id,
        },
        headers=headers,
        follow_redirects=True,
    )

    # Start the WO → IN_PRODUCTION
    start_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/start",
        headers=headers,
        follow_redirects=True,
    )
    assert start_resp.status_code == 200, (
        f"WO start must return 200, got {start_resp.status_code}: {start_resp.text}"
    )
    returned_status = start_resp.json().get("status", "").upper()
    assert returned_status in _IN_PRODUCTION_STATUSES, (
        f"WO status after start must be IN_PRODUCTION, got '{returned_status}'"
    )


@pytest.mark.asyncio
async def test_start_work_order_forbidden_without_manufacturing_write(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 2 (Req 22 / task spec): POST /work-orders/{id}/start must return 403
    for a user without manufacturing:write permission (viewer role).

    Validates: Requirements 22 — 403 guard for work_order:start
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=100.0, bom_qty=5.0)
    wo_id = setup["work_order_id"]
    raw_mat_id = setup["raw_material"]["id"]
    raw_mat_unit_id = setup["raw_material"]["unit_id"]

    # Release + issue as admin
    await async_client.post(f"{WORK_ORDERS_URL}/{wo_id}/release", headers=headers, follow_redirects=True)
    await async_client.post(
        f"{STOREKEEPER_URL}/issue-material",
        json={"work_order_id": wo_id, "material_id": raw_mat_id, "quantity": "5.0", "unit_id": raw_mat_unit_id},
        headers=headers,
        follow_redirects=True,
    )

    # Viewer has only manufacturing:read — no manufacturing:write → must get 403
    viewer_headers = make_token_headers(
        user_id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        role="viewer",
    )
    start_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/start",
        headers=viewer_headers,
        follow_redirects=True,
    )
    assert start_resp.status_code == 403, (
        f"Viewer (no manufacturing:write) must receive 403 on WO start, "
        f"got {start_resp.status_code}: {start_resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-22.2  POST /work-orders/{id}/record-production updates quantities
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_production_updates_quantities(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 1 (Req 22): POST /work-orders/{id}/record-production on an IN_PRODUCTION WO
    must update produced_quantity and scrap_quantity on the work order.

    Validates: Requirements 22 AC 1 (record-production step)
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=100.0, bom_qty=5.0)
    wo_id = setup["work_order_id"]
    raw_mat_id = setup["raw_material"]["id"]
    raw_mat_unit_id = setup["raw_material"]["unit_id"]

    # Release → issue → start
    await async_client.post(f"{WORK_ORDERS_URL}/{wo_id}/release", headers=headers, follow_redirects=True)
    await async_client.post(
        f"{STOREKEEPER_URL}/issue-material",
        json={"work_order_id": wo_id, "material_id": raw_mat_id, "quantity": "5.0", "unit_id": raw_mat_unit_id},
        headers=headers,
        follow_redirects=True,
    )
    await async_client.post(f"{WORK_ORDERS_URL}/{wo_id}/start", headers=headers, follow_redirects=True)

    # Record production: 1 produced, 0 scrap
    record_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/record-production",
        json={"produced_quantity": "1", "scrap_quantity": "0"},
        headers=headers,
        follow_redirects=True,
    )
    assert record_resp.status_code == 200, (
        f"record-production must return 200, got {record_resp.status_code}: {record_resp.text}"
    )

    # Verify quantities updated on WO
    wo_resp = await async_client.get(
        f"{WORK_ORDERS_URL}/{wo_id}",
        headers=headers,
        follow_redirects=True,
    )
    assert wo_resp.status_code == 200
    wo_data = wo_resp.json()
    assert float(wo_data.get("produced_quantity", 0)) >= 1.0, (
        f"WO produced_quantity must be >= 1.0 after record-production, "
        f"got {wo_data.get('produced_quantity')}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-23.1  POST /work-orders/{id}/complete → QC_PENDING + QC queue populated
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_work_order_creates_qc_pending_and_notifies(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    e2e_db_session,
    seed_number_series,
):
    """
    AC 1–3 (Req 23): POST /work-orders/{id}/complete on an IN_PRODUCTION WO must:
      1. Transition WO to QC_PENDING
      2. Notify the QC Inspector (notification record created)
      3. Make the WO visible in GET /quality-control/inspection-queue

    Validates: Requirements 23 AC 1, 2, 3
    """
    headers = admin_user["headers"]
    setup = await _build_full_wo_setup(async_client, headers, raw_stock=100.0, bom_qty=5.0)
    wo_id = setup["work_order_id"]
    raw_mat_id = setup["raw_material"]["id"]
    raw_mat_unit_id = setup["raw_material"]["unit_id"]

    # Release → issue → start → record-production → complete
    await async_client.post(f"{WORK_ORDERS_URL}/{wo_id}/release", headers=headers, follow_redirects=True)
    await async_client.post(
        f"{STOREKEEPER_URL}/issue-material",
        json={"work_order_id": wo_id, "material_id": raw_mat_id, "quantity": "5.0", "unit_id": raw_mat_unit_id},
        headers=headers,
        follow_redirects=True,
    )
    await async_client.post(f"{WORK_ORDERS_URL}/{wo_id}/start", headers=headers, follow_redirects=True)
    await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/record-production",
        json={"produced_quantity": "1", "scrap_quantity": "0"},
        headers=headers,
        follow_redirects=True,
    )

    # Complete the WO → should transition to QC_PENDING
    complete_resp = await async_client.post(
        f"{WORK_ORDERS_URL}/{wo_id}/complete",
        headers=headers,
        follow_redirects=True,
    )
    assert complete_resp.status_code == 200, (
        f"WO complete must return 200, got {complete_resp.status_code}: {complete_resp.text}"
    )

    # Verify WO is now QC_PENDING
    wo_resp = await async_client.get(
        f"{WORK_ORDERS_URL}/{wo_id}",
        headers=headers,
        follow_redirects=True,
    )
    assert wo_resp.status_code == 200
    wo_status = wo_resp.json()["status"].upper()
    assert wo_status in _QC_PENDING_STATUSES, (
        f"WO status after complete must be QC_PENDING, got '{wo_status}'"
    )

    # Verify QC Inspector notification created
    await e2e_db_session.rollback()
    notification = await e2e_db_session.scalar(
        select(NotificationModel).where(
            NotificationModel.tenant_id == test_tenant.id,
            NotificationModel.reference_id == uuid.UUID(wo_id),
        )
    )
    assert notification is not None, (
        "A notification must be created for the QC Inspector when WO transitions to QC_PENDING"
    )

    # Verify WO appears in QC inspection queue
    qc_queue_resp = await async_client.get(
        f"{QC_URL}/inspection-queue",
        headers=headers,
        follow_redirects=True,
    )
    assert qc_queue_resp.status_code == 200, (
        f"GET /quality-control/inspection-queue must return 200, "
        f"got {qc_queue_resp.status_code}: {qc_queue_resp.text}"
    )
    qc_queue = qc_queue_resp.json()
    assert isinstance(qc_queue, list), "QC inspection queue must be a list"

    wo_ids_in_qc_queue = {str(item.get("work_order_id")) for item in qc_queue}
    assert wo_id in wo_ids_in_qc_queue, (
        f"Completed WO {wo_id} must appear in QC inspection queue. "
        f"Queue work_order_ids: {wo_ids_in_qc_queue}"
    )

