"""
Property tests for Full Allocation Triggers Dispatch Readiness (Property 10).

**Validates: Requirements 7.6, 19.8, 21.6**

Property 10: For any sales order, the status SHALL transition to READY_FOR_DISPATCH
if and only if every non-SHORT_CLOSED line has allocated_quantity >= ordered_quantity.
If any line has allocated_quantity < ordered_quantity and is not SHORT_CLOSED, the
sales order SHALL NOT transition to READY_FOR_DISPATCH.

# Feature: manufacturing-erp-audit, Property 10: Full Allocation Triggers Dispatch Readiness
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    decimals,
    integers,
    lists,
    composite,
    sampled_from,
    booleans,
)

from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderModel,
    SalesOrderLineModel,
    ClientModel,
)
from backend.app.application.sales.partial_fulfillment_service import (
    PartialFulfillmentService,
)
from backend.app.domain.sales.value_objects.order_status import OrderStatus


# ─── Strategies ──────────────────────────────────────────────────────────────

# Ordered quantity for each SO line: realistic positive amounts
ordered_quantity_strategy = decimals(
    min_value=Decimal("1.0"),
    max_value=Decimal("10000.0"),
    places=1,
    allow_nan=False,
    allow_infinity=False,
)

# Line statuses that are NOT SHORT_CLOSED (active lines needing allocation)
ACTIVE_LINE_STATUSES = ["PENDING", "ALLOCATED", "PARTIAL", "BACKORDER"]

# Statuses that CAN transition to READY_FOR_DISPATCH (per OrderStatus.can_transition_to)
STATUSES_CAN_TRANSITION_TO_DISPATCH = ["PRODUCTION", "READY"]


@composite
def fully_allocated_so_lines(draw):
    """Generate SO lines where ALL non-SHORT_CLOSED lines have allocated >= ordered.

    This should trigger the SO transition to READY_FOR_DISPATCH.
    """
    num_lines = draw(integers(min_value=1, max_value=6))
    lines = []

    for _ in range(num_lines):
        ordered = draw(ordered_quantity_strategy)
        # Decide if this line is SHORT_CLOSED or fully allocated
        is_short_closed = draw(booleans())

        if is_short_closed:
            # SHORT_CLOSED lines: can have any allocated_quantity (doesn't matter)
            allocated = draw(decimals(
                min_value=Decimal("0.0"),
                max_value=Decimal("10000.0"),
                places=1,
                allow_nan=False,
                allow_infinity=False,
            ))
            line_status = "SHORT_CLOSED"
        else:
            # Non-SHORT_CLOSED lines: allocated >= ordered (fully allocated)
            extra = draw(decimals(
                min_value=Decimal("0.0"),
                max_value=Decimal("500.0"),
                places=1,
                allow_nan=False,
                allow_infinity=False,
            ))
            allocated = ordered + extra
            line_status = draw(sampled_from(ACTIVE_LINE_STATUSES))

        lines.append({
            "quantity": ordered,
            "allocated_quantity": allocated,
            "line_status": line_status,
        })

    # Ensure at least one non-SHORT_CLOSED line exists (otherwise it's trivially true
    # but with no real allocation to check)
    has_active = any(l["line_status"] != "SHORT_CLOSED" for l in lines)
    assume(has_active)

    return lines


@composite
def partially_allocated_so_lines(draw):
    """Generate SO lines where at least ONE non-SHORT_CLOSED line has allocated < ordered.

    This should NOT trigger the SO transition to READY_FOR_DISPATCH.
    """
    num_lines = draw(integers(min_value=1, max_value=6))
    lines = []
    has_under_allocated = False

    for i in range(num_lines):
        ordered = draw(ordered_quantity_strategy)
        is_short_closed = draw(booleans())

        if is_short_closed:
            # SHORT_CLOSED lines: irrelevant to the check
            allocated = draw(decimals(
                min_value=Decimal("0.0"),
                max_value=Decimal("10000.0"),
                places=1,
                allow_nan=False,
                allow_infinity=False,
            ))
            line_status = "SHORT_CLOSED"
        else:
            # For non-SHORT_CLOSED lines, randomly decide if fully or under-allocated
            # But ensure at least one is under-allocated
            if i == num_lines - 1 and not has_under_allocated:
                # Force this line to be under-allocated
                make_under = True
            else:
                make_under = draw(booleans())

            if make_under and not is_short_closed:
                # Under-allocated: allocated < ordered
                max_alloc = ordered - Decimal("0.1")
                if max_alloc < Decimal("0.0"):
                    max_alloc = Decimal("0.0")
                allocated = draw(decimals(
                    min_value=Decimal("0.0"),
                    max_value=max_alloc,
                    places=1,
                    allow_nan=False,
                    allow_infinity=False,
                ))
                has_under_allocated = True
            else:
                # Fully allocated
                extra = draw(decimals(
                    min_value=Decimal("0.0"),
                    max_value=Decimal("500.0"),
                    places=1,
                    allow_nan=False,
                    allow_infinity=False,
                ))
                allocated = ordered + extra

            line_status = draw(sampled_from(ACTIVE_LINE_STATUSES))

        lines.append({
            "quantity": ordered,
            "allocated_quantity": allocated,
            "line_status": line_status,
        })

    # Ensure we actually have an under-allocated non-SHORT_CLOSED line
    assume(any(
        Decimal(str(l["allocated_quantity"])) < Decimal(str(l["quantity"]))
        and l["line_status"] != "SHORT_CLOSED"
        for l in lines
    ))

    return lines


@composite
def mixed_so_lines_with_expected_result(draw):
    """Generate SO lines with random allocations and compute expected dispatch readiness.

    Returns (lines, expected_fully_allocated: bool).
    """
    num_lines = draw(integers(min_value=1, max_value=6))
    lines = []

    for _ in range(num_lines):
        ordered = draw(ordered_quantity_strategy)
        is_short_closed = draw(booleans())

        if is_short_closed:
            allocated = draw(decimals(
                min_value=Decimal("0.0"),
                max_value=Decimal("10000.0"),
                places=1,
                allow_nan=False,
                allow_infinity=False,
            ))
            line_status = "SHORT_CLOSED"
        else:
            allocated = draw(decimals(
                min_value=Decimal("0.0"),
                max_value=Decimal("15000.0"),
                places=1,
                allow_nan=False,
                allow_infinity=False,
            ))
            line_status = draw(sampled_from(ACTIVE_LINE_STATUSES))

        lines.append({
            "quantity": ordered,
            "allocated_quantity": allocated,
            "line_status": line_status,
        })

    # Compute expected: all non-SHORT_CLOSED lines must have allocated >= ordered
    expected_fully_allocated = all(
        Decimal(str(l["allocated_quantity"])) >= Decimal(str(l["quantity"]))
        for l in lines
        if l["line_status"] != "SHORT_CLOSED"
    )

    # Ensure at least one non-SHORT_CLOSED line to avoid trivial cases
    has_active = any(l["line_status"] != "SHORT_CLOSED" for l in lines)
    assume(has_active)

    return lines, expected_fully_allocated


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _create_so_with_lines(
    db_session, lines_data: List[dict], so_status: str = "PRODUCTION"
):
    """Create a sales order with lines in the database.

    Returns (tenant_id, sales_order).
    """
    tenant_id = uuid.uuid4()
    client_id = uuid.uuid4()
    sales_order_id = uuid.uuid4()

    # Create tenant
    tenant = TenantModel(
        id=tenant_id,
        name="Test Tenant",
        slug=f"test-{tenant_id.hex[:8]}",
        is_active=True,
    )
    db_session.add(tenant)

    # Create client
    client = ClientModel(
        id=client_id,
        tenant_id=tenant_id,
        code=f"CLI-{client_id.hex[:8]}",
        name="Test Client",
        is_active=True,
    )
    db_session.add(client)

    # Create sales order
    sales_order = SalesOrderModel(
        id=sales_order_id,
        tenant_id=tenant_id,
        order_number=f"SO-{sales_order_id.hex[:8]}",
        client_id=client_id,
        order_date=date.today().isoformat(),
        delivery_date=date.today().isoformat(),
        status=so_status,
        payment_status="PENDING",
        grand_total=0,
        subtotal=0,
        is_deleted=False,
    )
    db_session.add(sales_order)

    # Create SO lines
    for line_data in lines_data:
        line = SalesOrderLineModel(
            id=uuid.uuid4(),
            sales_order_id=sales_order_id,
            product_id=uuid.uuid4(),
            product_type="finished",
            uom_id=uuid.uuid4(),
            quantity=float(line_data["quantity"]),
            unit_price=10.0,
            tax_rate=0.0,
            tax_amount=0.0,
            line_total=float(line_data["quantity"]) * 10.0,
            allocated_quantity=float(line_data["allocated_quantity"]),
            dispatched_quantity=0.0,
            shipped_quantity=0.0,
            backorder_quantity=0.0,
            line_status=line_data["line_status"],
            status="PENDING",
        )
        db_session.add(line)

    await db_session.flush()

    return tenant_id, sales_order


# ─────────────────────────────────────────────────────────────────────────────
# Property 10: Full Allocation Triggers Dispatch Readiness
#
# Sub-property A: SO transitions to READY_FOR_DISPATCH when all non-SHORT_CLOSED
#                 lines have allocated_quantity >= ordered_quantity
# Sub-property B: SO does NOT transition when any non-SHORT_CLOSED line has
#                 allocated_quantity < ordered_quantity
# Sub-property C: The biconditional holds for arbitrary line configurations
# ─────────────────────────────────────────────────────────────────────────────


class TestFullAllocationTriggersDispatchReadiness:
    """**Validates: Requirements 7.6, 19.8, 21.6**

    Property 10: Full Allocation Triggers Dispatch Readiness.
    """

    @given(lines_data=fully_allocated_so_lines())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_fully_allocated_transitions_to_ready_for_dispatch(
        self,
        lines_data: List[dict],
        db_session,
    ):
        """Property 10A: SO SHALL transition to READY_FOR_DISPATCH when every
        non-SHORT_CLOSED line has allocated_quantity >= ordered_quantity.

        **Validates: Requirements 7.6, 19.8**
        """
        try:
            # Use PRODUCTION status which can transition to READY_FOR_DISPATCH
            tenant_id, sales_order = await _create_so_with_lines(
                db_session, lines_data, so_status="PRODUCTION"
            )

            # Execute the dispatch readiness check
            service = PartialFulfillmentService(db_session)
            result = await service._check_dispatch_readiness(tenant_id, sales_order)

            # Verify SO transitioned to READY_FOR_DISPATCH
            assert result is True, (
                f"Expected SO to transition to READY_FOR_DISPATCH when all "
                f"non-SHORT_CLOSED lines are fully allocated, but got result={result}. "
                f"Lines: {lines_data}"
            )
            assert sales_order.status == OrderStatus.READY_FOR_DISPATCH.value, (
                f"Expected SO status to be READY_FOR_DISPATCH but got "
                f"{sales_order.status}. Lines: {lines_data}"
            )
        finally:
            await db_session.rollback()

    @given(lines_data=partially_allocated_so_lines())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_partially_allocated_does_not_transition(
        self,
        lines_data: List[dict],
        db_session,
    ):
        """Property 10B: SO SHALL NOT transition to READY_FOR_DISPATCH when any
        non-SHORT_CLOSED line has allocated_quantity < ordered_quantity.

        **Validates: Requirements 7.6, 19.8, 21.6**
        """
        try:
            tenant_id, sales_order = await _create_so_with_lines(
                db_session, lines_data, so_status="PRODUCTION"
            )

            # Execute the dispatch readiness check
            service = PartialFulfillmentService(db_session)
            result = await service._check_dispatch_readiness(tenant_id, sales_order)

            # Verify SO did NOT transition
            assert result is False, (
                f"Expected SO NOT to transition to READY_FOR_DISPATCH when "
                f"under-allocated lines exist, but got result={result}. "
                f"Lines: {lines_data}"
            )
            assert sales_order.status == "PRODUCTION", (
                f"Expected SO status to remain PRODUCTION but got "
                f"{sales_order.status}. Lines: {lines_data}"
            )
        finally:
            await db_session.rollback()

    @given(data=mixed_so_lines_with_expected_result())
    @settings(
        max_examples=80,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_biconditional_dispatch_readiness(
        self,
        data: tuple,
        db_session,
    ):
        """Property 10C: SO transitions to READY_FOR_DISPATCH if and only if
        every non-SHORT_CLOSED line has allocated_quantity >= ordered_quantity.

        **Validates: Requirements 7.6, 19.8, 21.6**
        """
        lines_data, expected_fully_allocated = data

        try:
            tenant_id, sales_order = await _create_so_with_lines(
                db_session, lines_data, so_status="PRODUCTION"
            )

            # Execute the dispatch readiness check
            service = PartialFulfillmentService(db_session)
            result = await service._check_dispatch_readiness(tenant_id, sales_order)

            # Verify the biconditional
            if expected_fully_allocated:
                assert result is True, (
                    f"Expected SO to transition (all lines fully allocated) "
                    f"but got result={result}. Lines: {lines_data}"
                )
                assert sales_order.status == OrderStatus.READY_FOR_DISPATCH.value, (
                    f"Expected READY_FOR_DISPATCH but got {sales_order.status}"
                )
            else:
                assert result is False, (
                    f"Expected SO NOT to transition (under-allocated lines exist) "
                    f"but got result={result}. Lines: {lines_data}"
                )
                assert sales_order.status == "PRODUCTION", (
                    f"Expected PRODUCTION but got {sales_order.status}"
                )
        finally:
            await db_session.rollback()

    @given(lines_data=fully_allocated_so_lines())
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_short_closed_lines_are_excluded_from_check(
        self,
        lines_data: List[dict],
        db_session,
    ):
        """Property 10: SHORT_CLOSED lines SHALL NOT prevent dispatch readiness
        regardless of their allocated_quantity.

        **Validates: Requirements 19.8**
        """
        # Ensure we have at least one SHORT_CLOSED line with under-allocation
        # to prove it's excluded from the check
        short_closed_lines = [l for l in lines_data if l["line_status"] == "SHORT_CLOSED"]
        assume(len(short_closed_lines) > 0)

        # Force SHORT_CLOSED lines to have allocated < ordered (to prove exclusion)
        for line in short_closed_lines:
            line["allocated_quantity"] = Decimal("0.0")

        try:
            tenant_id, sales_order = await _create_so_with_lines(
                db_session, lines_data, so_status="PRODUCTION"
            )

            service = PartialFulfillmentService(db_session)
            result = await service._check_dispatch_readiness(tenant_id, sales_order)

            # Should still transition because SHORT_CLOSED lines are excluded
            assert result is True, (
                f"Expected SO to transition even with SHORT_CLOSED lines having "
                f"zero allocation. Lines: {lines_data}"
            )
            assert sales_order.status == OrderStatus.READY_FOR_DISPATCH.value
        finally:
            await db_session.rollback()

    @given(lines_data=fully_allocated_so_lines())
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_no_transition_when_status_cannot_reach_dispatch(
        self,
        lines_data: List[dict],
        db_session,
    ):
        """Property 10: SO SHALL NOT transition if current status doesn't allow
        transition to READY_FOR_DISPATCH, even when fully allocated.

        **Validates: Requirements 7.6**
        """
        # DRAFT cannot transition to READY_FOR_DISPATCH
        try:
            tenant_id, sales_order = await _create_so_with_lines(
                db_session, lines_data, so_status="DRAFT"
            )

            service = PartialFulfillmentService(db_session)
            result = await service._check_dispatch_readiness(tenant_id, sales_order)

            # Should NOT transition because DRAFT cannot reach READY_FOR_DISPATCH
            assert result is False, (
                f"Expected no transition from DRAFT even when fully allocated, "
                f"but got result={result}"
            )
            assert sales_order.status == "DRAFT"
        finally:
            await db_session.rollback()
