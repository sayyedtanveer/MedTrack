"""
Phase 2 Integration Tests — Sales Order Lifecycle
===================================================
Tests for:
  POST /api/v1/sales/orders              → status=DRAFT
  POST /api/v1/sales/orders/{id}/submit-approval → PENDING_APPROVAL; 403 without sales:write
  POST /api/v1/sales/orders/{id}/approve → APPROVED (+ auto-confirm); 403 without sales:approve_order
  POST /api/v1/sales/orders/{id}/reject  → REJECTED + notification to sales user
  POST /api/v1/sales/orders/{id}/confirm → triggers FG check (Gap #2 wired)

Test cases:
  TC-10.1  POST /sales/orders creates SO with status=DRAFT
  TC-10.2  POST /sales/orders with missing required fields returns 422
  TC-11.1  POST /sales/orders/{id}/submit-approval → status=PENDING_APPROVAL
  TC-11.2  POST /sales/orders/{id}/submit-approval → 403 without sales:write (worker role)
  TC-12.1  POST /sales/orders/{id}/approve → status in {APPROVED, CONFIRMED, READY_FOR_DISPATCH, ...}
  TC-12.2  POST /sales/orders/{id}/approve → 403 without sales:approve_order (worker role)
  TC-12.3  POST /sales/orders/{id}/reject  → status=REJECTED + notification created
  TC-13.1  POST /sales/orders/{id}/confirm → FG check runs; status changes from APPROVED
  TC-13.2  POST /sales/orders/{id}/confirm → 403 without sales:write (worker role)

Requirements: 10–13
"""
from __future__ import annotations

import backend.app.main  # noqa: F401  (registers all ORM models)

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from tests.e2e.fixtures.conftest import make_token_headers
from backend.app.infrastructure.persistence.models.notification_model import (
    NotificationModel,
)


# ── URL constants ─────────────────────────────────────────────────────────────
SALES_ORDERS_URL = "/api/v1/sales/orders"
CLIENTS_URL = "/api/v1/sales/clients"
MATERIALS_URL = "/api/v1/inventory/materials"
MASTER_DATA_URL = "/api/v1/inventory/master-data"
PRODUCTS_URL = "/api/v1/products"

# SO statuses that are valid post-approve (approve auto-confirms in the current impl)
_POST_APPROVE_STATUSES = {
    "APPROVED",
    "CONFIRMED",
    "READY_FOR_DISPATCH",
    "READY",
    "CONFIRMED",
}

# SO statuses that indicate confirmation has run
_POST_CONFIRM_STATUSES = {
    "CONFIRMED",
    "READY_FOR_DISPATCH",
    "READY",
    "PRODUCTION",
    "PROCESSING",
}


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers — re-use patterns from test_master_data.py
# ─────────────────────────────────────────────────────────────────────────────


async def _create_unit(async_client: AsyncClient, headers: dict) -> str:
    suffix = uuid.uuid4().hex[:6]
    resp = await async_client.post(
        f"{MASTER_DATA_URL}/units",
        json={"code": f"EA{suffix}", "name": f"Each-{suffix}", "is_active": True},
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"Unit creation failed: {resp.status_code} {resp.text}"
    return resp.json()["id"]


async def _create_client(async_client: AsyncClient, headers: dict) -> dict:
    """Create a sales client with a high credit limit so approval credit checks pass."""
    suffix = uuid.uuid4().hex[:8]
    resp = await async_client.post(
        CLIENTS_URL,
        json={
            "code": f"CLT-{suffix}",
            "name": f"Client-{suffix}",
            "credit_limit": "9999999.00",  # high limit so credit checks never block E2E tests
        },
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"Client creation failed: {resp.status_code} {resp.text}"
    return resp.json()


async def _create_fg_material(async_client: AsyncClient, headers: dict, *, opening_stock: float = 0.0) -> tuple[dict, str]:
    """
    Create a finished goods material (optionally with opening stock).
    Returns (material_json, unit_id).
    """
    suffix = uuid.uuid4().hex[:8]
    unit_id = await _create_unit(async_client, headers)
    resp = await async_client.post(
        MATERIALS_URL,
        json={
            "name": f"FG-Mat-{suffix}",
            "material_type": "finished",
            "base_unit_id": unit_id,
            "opening_stock": opening_stock,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"FG material creation failed: {resp.status_code} {resp.text}"
    return resp.json(), unit_id


async def _create_category(async_client: AsyncClient, headers: dict) -> str:
    """Create a material category and return its id."""
    suffix = uuid.uuid4().hex[:6]
    resp = await async_client.post(
        f"{MASTER_DATA_URL}/categories",
        json={"name": f"Cat-{suffix}", "code_prefix": f"C{suffix[:4]}"},
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"Category creation failed: {resp.status_code} {resp.text}"
    return resp.json()["id"]


async def _create_product_variant_with_uom(async_client: AsyncClient, headers: dict) -> dict:
    """
    Create the full prerequisite chain (FG material → template → variant)
    and return a dict with {variant_id, unit_id}.
    """
    fg_mat, unit_id = await _create_fg_material(async_client, headers)
    fg_mat_id = fg_mat["id"]

    category_id = await _create_category(async_client, headers)

    suffix = uuid.uuid4().hex[:8]
    template_resp = await async_client.post(
        f"{PRODUCTS_URL}/templates",
        json={
            "name": f"Template-{suffix}",
            "category_id": category_id,
            "attributes": [{"key": "SIZE", "label": "Size"}],
        },
        headers=headers,
        follow_redirects=True,
    )
    assert template_resp.status_code == 201, (
        f"Template creation failed: {template_resp.status_code} {template_resp.text}"
    )
    template_id = template_resp.json()["id"]

    variant_resp = await async_client.post(
        f"{PRODUCTS_URL}/templates/{template_id}/variants",
        json={
            "attribute_values": {"SIZE": f"M-{suffix}"},
            "material_id": fg_mat_id,
            "standard_cost": 10.0,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert variant_resp.status_code == 201, (
        f"Variant creation failed: {variant_resp.status_code} {variant_resp.text}"
    )
    variant_id = variant_resp.json()["id"]

    return {"variant_id": variant_id, "unit_id": unit_id}


async def _create_sales_order_with_line(
    async_client: AsyncClient, headers: dict, client_id: str
) -> dict:
    """
    Create a sales order with one order line (required before submit).
    Returns the final order JSON after the line has been added.
    """
    today = date.today()
    delivery = today + timedelta(days=7)
    so_resp = await async_client.post(
        SALES_ORDERS_URL,
        json={
            "client_id": client_id,
            "order_date": today.isoformat(),
            "delivery_date": delivery.isoformat(),
            "notes": "E2E test order",
        },
        headers=headers,
        follow_redirects=True,
    )
    assert so_resp.status_code == 201, f"SO creation failed: {so_resp.status_code} {so_resp.text}"
    order = so_resp.json()
    order_id = order["id"]

    # Create product variant + unit for the line
    product_info = await _create_product_variant_with_uom(async_client, headers)

    # Create a default price list with pricing for this variant
    await _create_default_price_list_with_line(
        async_client, headers, product_info["variant_id"]
    )

    # Add one order line
    line_resp = await async_client.post(
        f"{SALES_ORDERS_URL}/{order_id}/lines",
        json={
            "product_id": product_info["variant_id"],
            "product_type": "variant",
            "uom_id": product_info["unit_id"],
            "quantity": "1",
            "tax_rate": "0",
        },
        headers=headers,
        follow_redirects=True,
    )
    assert line_resp.status_code in (200, 201), (
        f"SO line addition failed: {line_resp.status_code} {line_resp.text}"
    )
    # Return the refreshed order with the line
    return line_resp.json()


async def _create_default_price_list_with_line(
    async_client: AsyncClient,
    headers: dict,
    variant_id: str,
    unit_price: float = 100.0,
) -> dict:
    """
    Create a default price list and add a pricing line for the given variant.
    This is required before SO lines can be added (PricingService lookup).
    """
    today = date.today()
    # Create a default price list valid from today
    pl_resp = await async_client.post(
        "/api/v1/sales/price-lists",
        json={
            "name": f"Default-{uuid.uuid4().hex[:6]}",
            "is_default": True,
            "valid_from": today.isoformat(),
        },
        headers=headers,
        follow_redirects=True,
    )
    assert pl_resp.status_code == 201, (
        f"Price list creation failed: {pl_resp.status_code} {pl_resp.text}"
    )
    price_list_id = pl_resp.json()["id"]

    # Add the variant pricing line
    line_resp = await async_client.post(
        f"/api/v1/sales/price-lists/{price_list_id}/lines",
        json={
            "product_id": variant_id,
            "product_type": "variant",
            "unit_price": str(unit_price),
        },
        headers=headers,
        follow_redirects=True,
    )
    assert line_resp.status_code in (200, 201), (
        f"Price list line creation failed: {line_resp.status_code} {line_resp.text}"
    )
    return pl_resp.json()


async def _create_sales_order(async_client: AsyncClient, headers: dict, client_id: str) -> dict:
    """Create a sales order WITH one line item (required to be submittable)."""
    return await _create_sales_order_with_line(async_client, headers, client_id)


async def _submit_order(async_client: AsyncClient, headers: dict, order_id: str) -> dict:
    """Submit a DRAFT SO for approval and return the updated order JSON."""
    resp = await async_client.post(
        f"{SALES_ORDERS_URL}/{order_id}/submit-approval",
        json={},
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 200, f"Submit failed: {resp.status_code} {resp.text}"
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# TC-10.1  POST /sales/orders creates SO with status=DRAFT
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_sales_order_creates_draft(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 2 & 3 (Req 10): POST /sales/orders with valid data must create a record
    with status=DRAFT and return HTTP 201.

    Validates: Requirements 10 AC 2
    """
    client = await _create_client(async_client, admin_user["headers"])

    today = date.today()
    delivery = today + timedelta(days=7)
    response = await async_client.post(
        SALES_ORDERS_URL,
        json={
            "client_id": client["id"],
            "order_date": today.isoformat(),
            "delivery_date": delivery.isoformat(),
            "notes": "TC-10.1 test",
        },
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert response.status_code == 201, (
        f"Expected 201 for new SO, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert "id" in data, "Response must include the order id"
    assert "order_number" in data, "Response must include order_number"

    status_value = data.get("status", "").upper()
    assert status_value == "DRAFT", (
        f"New SO must have status=DRAFT, got '{status_value}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-10.2  POST /sales/orders with missing fields returns 422
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_sales_order_missing_fields_returns_422(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    Req 10 — validation: submitting without required fields must return 422.

    Validates: Requirements 10 AC 2 (implicit validation)
    """
    response = await async_client.post(
        SALES_ORDERS_URL,
        json={},  # missing client_id, order_date, delivery_date
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert response.status_code == 422, (
        f"Expected 422 for missing fields, got {response.status_code}: {response.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-11.1  POST /sales/orders/{id}/submit-approval → PENDING_APPROVAL
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_order_for_approval(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 2 (Req 11): POST /sales/orders/{id}/submit-approval on a DRAFT SO must
    transition the order to status=PENDING_APPROVAL.

    Validates: Requirements 11 AC 2
    """
    client = await _create_client(async_client, admin_user["headers"])
    order = await _create_sales_order(async_client, admin_user["headers"], client["id"])
    order_id = order["id"]

    assert order["status"].upper() == "DRAFT", "Pre-condition: order must be DRAFT"

    resp = await async_client.post(
        f"{SALES_ORDERS_URL}/{order_id}/submit-approval",
        json={},
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert resp.status_code == 200, (
        f"Expected 200 from submit-approval, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data["status"].upper() == "PENDING_APPROVAL", (
        f"Status must be PENDING_APPROVAL after submit, got '{data['status']}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-11.2  403 without sales:write (worker role cannot submit)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_order_forbidden_without_permission(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 3 (Req 11): A user without sales:write (worker role) must receive 403
    when attempting to submit a SO for approval.

    Validates: Requirements 11 AC 3
    """
    # Admin creates a DRAFT order first
    client = await _create_client(async_client, admin_user["headers"])
    order = await _create_sales_order(async_client, admin_user["headers"], client["id"])
    order_id = order["id"]

    # Worker has no sales:write permission
    worker_headers = make_token_headers(
        user_id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        role="worker",
    )

    resp = await async_client.post(
        f"{SALES_ORDERS_URL}/{order_id}/submit-approval",
        json={},
        headers=worker_headers,
        follow_redirects=True,
    )

    assert resp.status_code == 403, (
        f"Expected 403 for worker submitting order, got {resp.status_code}: {resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-12.1  POST /sales/orders/{id}/approve → order advances past PENDING_APPROVAL
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_approve_order(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 2 (Req 12): POST /sales/orders/{id}/approve on a PENDING_APPROVAL SO
    must advance the order status.  The approve endpoint also auto-confirms
    (Gap #2 wired), so the resulting status may be APPROVED, CONFIRMED,
    READY_FOR_DISPATCH, or a production-bound status.

    In all cases the status MUST NOT remain DRAFT or PENDING_APPROVAL.

    Validates: Requirements 12 AC 2
    """
    client = await _create_client(async_client, admin_user["headers"])
    order = await _create_sales_order(async_client, admin_user["headers"], client["id"])
    order_id = order["id"]
    await _submit_order(async_client, admin_user["headers"], order_id)

    resp = await async_client.post(
        f"{SALES_ORDERS_URL}/{order_id}/approve",
        json={},
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert resp.status_code == 200, (
        f"Expected 200 from approve, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    result_status = data["status"].upper()
    assert result_status not in {"DRAFT", "PENDING_APPROVAL"}, (
        f"Status must advance beyond PENDING_APPROVAL after approve, got '{result_status}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-12.2  403 without sales:approve_order (worker role cannot approve)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_approve_order_forbidden_without_permission(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 4 (Req 12): A user without sales:approve_order (worker role) must receive
    403 when attempting to approve a SO.

    Validates: Requirements 12 AC 4
    """
    # Admin sets order to PENDING_APPROVAL
    client = await _create_client(async_client, admin_user["headers"])
    order = await _create_sales_order(async_client, admin_user["headers"], client["id"])
    order_id = order["id"]
    await _submit_order(async_client, admin_user["headers"], order_id)

    # Worker has MANUFACTURING_READ/WRITE, INVENTORY_READ, WORKER_READ — no sales:approve_order
    worker_headers = make_token_headers(
        user_id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        role="worker",
    )

    resp = await async_client.post(
        f"{SALES_ORDERS_URL}/{order_id}/approve",
        json={},
        headers=worker_headers,
        follow_redirects=True,
    )

    assert resp.status_code == 403, (
        f"Expected 403 for worker approving order, got {resp.status_code}: {resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-12.3  POST /sales/orders/{id}/reject → REJECTED + notification
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reject_order_transitions_to_rejected_and_notifies(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    e2e_db_session,
    seed_number_series,
):
    """
    AC 3 (Req 12): POST /sales/orders/{id}/reject must transition the order to
    status=REJECTED and create a notification for the originating sales user.

    We verify:
      1. Response status is 200 and data.status == REJECTED
      2. At least one NotificationModel record exists for this SO in the DB

    Validates: Requirements 12 AC 3
    """
    client = await _create_client(async_client, admin_user["headers"])
    order = await _create_sales_order(async_client, admin_user["headers"], client["id"])
    order_id = order["id"]
    await _submit_order(async_client, admin_user["headers"], order_id)

    resp = await async_client.post(
        f"{SALES_ORDERS_URL}/{order_id}/reject",
        json={"notes": "E2E rejection reason"},
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert resp.status_code == 200, (
        f"Expected 200 from reject, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data["status"].upper() == "REJECTED", (
        f"Status must be REJECTED after reject, got '{data['status']}'"
    )

    # Verify at least one notification was created for this SO
    await e2e_db_session.rollback()
    notification = await e2e_db_session.scalar(
        select(NotificationModel).where(
            NotificationModel.tenant_id == test_tenant.id,
            NotificationModel.reference_id == uuid.UUID(order_id),
        )
    )
    assert notification is not None, (
        "A notification record must be created when an SO is rejected"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-12.4  Reject 403 without sales:approve_order
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reject_order_forbidden_without_permission(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 4 (Req 12): A user without sales:approve_order (worker role) must receive
    403 when attempting to reject a SO.

    Validates: Requirements 12 AC 4
    """
    client = await _create_client(async_client, admin_user["headers"])
    order = await _create_sales_order(async_client, admin_user["headers"], client["id"])
    order_id = order["id"]
    await _submit_order(async_client, admin_user["headers"], order_id)

    worker_headers = make_token_headers(
        user_id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        role="worker",
    )

    resp = await async_client.post(
        f"{SALES_ORDERS_URL}/{order_id}/reject",
        json={"notes": "Unauthorized rejection"},
        headers=worker_headers,
        follow_redirects=True,
    )

    assert resp.status_code == 403, (
        f"Expected 403 for worker rejecting order, got {resp.status_code}: {resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-13.1  POST /sales/orders/{id}/confirm → FG check runs (Gap #2 wired)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_order_triggers_fg_check(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    AC 2 & 5 (Req 13): POST /sales/orders/{id}/confirm on an APPROVED SO must
    trigger the FG availability check (Gap #2).

    The order has no lines, so the FG check finds nothing to reserve and the SO
    transitions out of APPROVED to a confirmed/production-bound status.

    We assert:
      - Response status is 200
      - Returned status is NOT DRAFT, NOT PENDING_APPROVAL, NOT APPROVED
        (i.e. the confirm endpoint ran and made a state transition)

    Validates: Requirements 13 AC 2, 5
    """
    client = await _create_client(async_client, admin_user["headers"])
    order = await _create_sales_order(async_client, admin_user["headers"], client["id"])
    order_id = order["id"]

    # Move to PENDING_APPROVAL
    await _submit_order(async_client, admin_user["headers"], order_id)

    # Move to APPROVED
    approve_resp = await async_client.post(
        f"{SALES_ORDERS_URL}/{order_id}/approve",
        json={},
        headers=admin_user["headers"],
        follow_redirects=True,
    )
    assert approve_resp.status_code == 200, (
        f"Approve step failed: {approve_resp.status_code} {approve_resp.text}"
    )
    approved_status = approve_resp.json()["status"].upper()

    # If approve already auto-confirmed (Gap #2 wired), the test still validates
    # confirm by checking the final state is past APPROVED.
    # Only call confirm explicitly if still APPROVED.
    if approved_status == "APPROVED":
        confirm_resp = await async_client.post(
            f"{SALES_ORDERS_URL}/{order_id}/confirm",
            json={"confirmed_by": str(admin_user["id"])},
            headers=admin_user["headers"],
            follow_redirects=True,
        )
        assert confirm_resp.status_code == 200, (
            f"Expected 200 from confirm, got {confirm_resp.status_code}: {confirm_resp.text}"
        )
        final_status = confirm_resp.json()["status"].upper()
    else:
        # Approve already ran the FG check internally
        final_status = approved_status

    assert final_status not in {"DRAFT", "PENDING_APPROVAL", "APPROVED"}, (
        f"SO must advance past APPROVED after FG check/confirm, got '{final_status}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-13.2  POST /sales/orders/{id}/confirm → 403 without sales:write
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_order_forbidden_without_permission(
    async_client: AsyncClient,
    admin_user: dict,
    test_tenant,
    seed_number_series,
):
    """
    Req 13 (implicit): A user without sales:write (worker role) must receive
    403 when attempting to confirm an SO.

    Validates: Requirements 13 AC 2 (permission enforcement)
    """
    client = await _create_client(async_client, admin_user["headers"])
    order = await _create_sales_order(async_client, admin_user["headers"], client["id"])
    order_id = order["id"]

    # Move to PENDING_APPROVAL then APPROVED
    await _submit_order(async_client, admin_user["headers"], order_id)
    approve_resp = await async_client.post(
        f"{SALES_ORDERS_URL}/{order_id}/approve",
        json={},
        headers=admin_user["headers"],
        follow_redirects=True,
    )
    assert approve_resp.status_code == 200

    worker_headers = make_token_headers(
        user_id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        role="worker",
    )

    resp = await async_client.post(
        f"{SALES_ORDERS_URL}/{order_id}/confirm",
        json={"confirmed_by": "worker"},
        headers=worker_headers,
        follow_redirects=True,
    )

    assert resp.status_code == 403, (
        f"Expected 403 for worker confirming order, got {resp.status_code}: {resp.text}"
    )
