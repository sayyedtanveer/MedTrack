"""
Property tests for Order Tracking Date Calculations.

# Feature: manufacturing-erp-audit, Property 20: Order Tracking Date Calculations

**Validates: Requirements 28.2, 28.3, 28.4, 28.6**

These tests validate that:
  - Estimated Completion Date = max(due_date) of incomplete work orders
  - Expected Dispatch Date = Estimated Completion + dispatch_lead_days (default 1)
  - Expected Delivery Date = Expected Dispatch + delivery_lead_days (default 3)
  - When no WOs are linked, Estimated Completion = today
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    composite,
    dates,
    integers,
    lists,
    sampled_from,
    booleans,
    just,
    one_of,
)


# ─── Constants ────────────────────────────────────────────────────────────────

# Statuses considered "completed" (WO will not contribute to estimated completion)
COMPLETED_STATUSES = frozenset({
    "FG_RECEIVED", "COMPLETED", "CLOSED", "CANCELLED", "REJECTED"
})

# Statuses considered "incomplete" (WO contributes to estimated completion)
INCOMPLETE_STATUSES = [
    "PLANNED", "RELEASED", "MATERIAL_PENDING", "MATERIAL_RESERVED",
    "MATERIAL_ISSUED", "IN_PRODUCTION", "QC_PENDING", "QC_APPROVED",
    "PRODUCTION_HOLD", "REWORK",
]

ALL_WO_STATUSES = INCOMPLETE_STATUSES + list(COMPLETED_STATUSES)

# Default lead times per Requirements 28.3 and 28.4
DEFAULT_DISPATCH_LEAD_DAYS = 1
DEFAULT_DELIVERY_LEAD_DAYS = 3


# ─── Data Types ───────────────────────────────────────────────────────────────

class WorkOrderData:
    """Simple representation of a work order for property testing."""

    def __init__(self, status: str, due_date: Optional[date]):
        self.status = status
        self.due_date = due_date

    def __repr__(self):
        return f"WO(status={self.status}, due_date={self.due_date})"


# ─── Strategies ───────────────────────────────────────────────────────────────

# Date range: reasonable manufacturing dates
reasonable_dates = dates(
    min_value=date(2020, 1, 1),
    max_value=date(2035, 12, 31),
)

# Positive lead times (at least 1 day)
positive_lead_time = integers(min_value=1, max_value=30)


@composite
def work_order_incomplete(draw):
    """Generate a work order with an incomplete status and a due date."""
    status = draw(sampled_from(INCOMPLETE_STATUSES))
    due_date = draw(reasonable_dates)
    return WorkOrderData(status=status, due_date=due_date)


@composite
def work_order_completed(draw):
    """Generate a work order with a completed status and a due date."""
    status = draw(sampled_from(list(COMPLETED_STATUSES)))
    due_date = draw(reasonable_dates)
    return WorkOrderData(status=status, due_date=due_date)


@composite
def work_order_any(draw):
    """Generate a work order with any status."""
    status = draw(sampled_from(ALL_WO_STATUSES))
    due_date = draw(reasonable_dates)
    return WorkOrderData(status=status, due_date=due_date)


@composite
def so_with_incomplete_wos(draw):
    """
    Generate a sales order scenario with at least one incomplete work order.

    Returns: (list of work orders, dispatch_lead_days, delivery_lead_days)
    """
    # At least 1 incomplete WO
    incomplete_wos = draw(lists(work_order_incomplete(), min_size=1, max_size=10))
    # Optionally some completed WOs
    completed_wos = draw(lists(work_order_completed(), min_size=0, max_size=5))
    all_wos = incomplete_wos + completed_wos

    dispatch_lead = draw(positive_lead_time)
    delivery_lead = draw(positive_lead_time)

    return all_wos, dispatch_lead, delivery_lead


@composite
def so_with_only_completed_wos(draw):
    """
    Generate a sales order scenario with work orders that are all completed.

    Returns: (list of work orders, dispatch_lead_days, delivery_lead_days)
    """
    completed_wos = draw(lists(work_order_completed(), min_size=1, max_size=10))

    dispatch_lead = draw(positive_lead_time)
    delivery_lead = draw(positive_lead_time)

    return completed_wos, dispatch_lead, delivery_lead


@composite
def so_with_no_wos(draw):
    """
    Generate a sales order scenario with no linked work orders.

    Returns: (dispatch_lead_days, delivery_lead_days)
    """
    dispatch_lead = draw(positive_lead_time)
    delivery_lead = draw(positive_lead_time)

    return dispatch_lead, delivery_lead


@composite
def so_with_mixed_wos_and_default_leads(draw):
    """
    Generate a sales order with mixed WOs using default lead times.

    Returns: (list of work orders,)
    """
    incomplete_wos = draw(lists(work_order_incomplete(), min_size=1, max_size=8))
    completed_wos = draw(lists(work_order_completed(), min_size=0, max_size=4))
    all_wos = incomplete_wos + completed_wos

    return all_wos


# ─── Helper: Date calculation logic (mirrors workflow endpoint) ───────────────

def calculate_estimated_completion(
    work_orders: List[WorkOrderData],
) -> Optional[date]:
    """
    Calculate Estimated Completion Date from linked work orders.

    Logic (Req 28.2, 28.6):
    - If there are incomplete WOs with due dates: max(due_date) of incomplete WOs
    - If no WOs exist: today
    - If all WOs are completed: None (no calculation needed)
    """
    if not work_orders:
        return date.today()

    incomplete_wos = [
        wo for wo in work_orders if wo.status not in COMPLETED_STATUSES
    ]

    if incomplete_wos:
        due_dates = [wo.due_date for wo in incomplete_wos if wo.due_date is not None]
        if due_dates:
            return max(due_dates)

    return None


def calculate_expected_dispatch(
    estimated_completion: Optional[date],
    dispatch_lead_days: int,
) -> Optional[date]:
    """
    Calculate Expected Dispatch Date (Req 28.3).

    Expected Dispatch = Estimated Completion + dispatch_lead_days
    """
    if estimated_completion is None:
        return None
    return estimated_completion + timedelta(days=dispatch_lead_days)


def calculate_expected_delivery(
    expected_dispatch: Optional[date],
    delivery_lead_days: int,
) -> Optional[date]:
    """
    Calculate Expected Delivery Date (Req 28.4).

    Expected Delivery = Expected Dispatch + delivery_lead_days
    """
    if expected_dispatch is None:
        return None
    return expected_dispatch + timedelta(days=delivery_lead_days)


# ─────────────────────────────────────────────────────────────────────────────
# Property 20: Order Tracking Date Calculations
#
# For any sales order with linked work orders:
# (a) Estimated Completion Date = max(due_date) of incomplete WOs
# (b) Expected Dispatch Date = Estimated Completion + dispatch_lead_days
# (c) Expected Delivery Date = Expected Dispatch + delivery_lead_days
# (d) When no WOs are linked, Estimated Completion = today
# ─────────────────────────────────────────────────────────────────────────────


class TestEstimatedCompletionDate:
    """**Validates: Requirements 28.2, 28.6**"""

    @given(data=so_with_incomplete_wos())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_estimated_completion_is_max_due_date_of_incomplete_wos(
        self, data: tuple[List[WorkOrderData], int, int]
    ):
        """
        Property 20a: Estimated Completion = max(due_date) of incomplete WOs.
        """
        work_orders, _, _ = data

        incomplete_wos = [
            wo for wo in work_orders if wo.status not in COMPLETED_STATUSES
        ]
        assume(len(incomplete_wos) > 0)
        incomplete_due_dates = [wo.due_date for wo in incomplete_wos if wo.due_date is not None]
        assume(len(incomplete_due_dates) > 0)

        result = calculate_estimated_completion(work_orders)
        expected = max(incomplete_due_dates)

        assert result == expected, (
            f"Estimated completion mismatch: got={result}, expected={expected}, "
            f"incomplete_wos={incomplete_wos}"
        )

    @given(data=so_with_incomplete_wos())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_completed_wos_do_not_affect_estimated_completion(
        self, data: tuple[List[WorkOrderData], int, int]
    ):
        """
        Property 20a: Completed WOs' due dates do not influence estimated completion.
        """
        work_orders, _, _ = data

        incomplete_wos = [
            wo for wo in work_orders if wo.status not in COMPLETED_STATUSES
        ]
        assume(len(incomplete_wos) > 0)
        incomplete_due_dates = [wo.due_date for wo in incomplete_wos if wo.due_date is not None]
        assume(len(incomplete_due_dates) > 0)

        # Result should be based only on incomplete WOs
        result = calculate_estimated_completion(work_orders)
        max_incomplete = max(incomplete_due_dates)

        # Even if a completed WO has a later due date, it should not change result
        assert result == max_incomplete, (
            f"Completed WOs should not affect estimated completion: "
            f"result={result}, max_incomplete={max_incomplete}"
        )

    @given(data=so_with_no_wos())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_no_wos_returns_today(self, data: tuple[int, int]):
        """
        Property 20d: When no WOs are linked, Estimated Completion = today.
        """
        _, _ = data

        result = calculate_estimated_completion([])

        assert result == date.today(), (
            f"No WOs should return today: got={result}, expected={date.today()}"
        )

    @given(data=so_with_only_completed_wos())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_all_completed_wos_returns_none(
        self, data: tuple[List[WorkOrderData], int, int]
    ):
        """
        Property 20a: When all WOs are completed, no estimated completion is calculated.
        """
        work_orders, _, _ = data

        result = calculate_estimated_completion(work_orders)

        assert result is None, (
            f"All-completed WOs should return None: got={result}, "
            f"work_orders={work_orders}"
        )

    @given(wo=work_order_incomplete())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_single_incomplete_wo_due_date_is_estimated_completion(
        self, wo: WorkOrderData
    ):
        """
        Property 20a: With a single incomplete WO, its due_date is the estimated completion.
        """
        assume(wo.due_date is not None)

        result = calculate_estimated_completion([wo])

        assert result == wo.due_date, (
            f"Single WO due_date mismatch: got={result}, expected={wo.due_date}"
        )


class TestExpectedDispatchDate:
    """**Validates: Requirements 28.3**"""

    @given(data=so_with_incomplete_wos())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_dispatch_equals_completion_plus_dispatch_lead(
        self, data: tuple[List[WorkOrderData], int, int]
    ):
        """
        Property 20b: Expected Dispatch = Estimated Completion + dispatch_lead_days.
        """
        work_orders, dispatch_lead, _ = data

        estimated_completion = calculate_estimated_completion(work_orders)
        assume(estimated_completion is not None)

        result = calculate_expected_dispatch(estimated_completion, dispatch_lead)
        expected = estimated_completion + timedelta(days=dispatch_lead)

        assert result == expected, (
            f"Dispatch date mismatch: got={result}, expected={expected}, "
            f"estimated_completion={estimated_completion}, "
            f"dispatch_lead={dispatch_lead}"
        )

    @given(dispatch_lead=positive_lead_time)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_dispatch_with_no_completion_is_none(self, dispatch_lead: int):
        """
        Property 20b: When estimated_completion is None, dispatch is None.
        """
        result = calculate_expected_dispatch(None, dispatch_lead)

        assert result is None, (
            f"Dispatch with no completion should be None: got={result}"
        )

    @given(data=so_with_no_wos())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_dispatch_with_no_wos_uses_today(self, data: tuple[int, int]):
        """
        Property 20b + 20d: No WOs → Estimated Completion = today →
        Dispatch = today + dispatch_lead.
        """
        dispatch_lead, _ = data

        estimated_completion = calculate_estimated_completion([])
        result = calculate_expected_dispatch(estimated_completion, dispatch_lead)
        expected = date.today() + timedelta(days=dispatch_lead)

        assert result == expected, (
            f"No-WO dispatch mismatch: got={result}, expected={expected}, "
            f"dispatch_lead={dispatch_lead}"
        )

    @given(
        completion_date=reasonable_dates,
        lead1=positive_lead_time,
        lead2=positive_lead_time,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_larger_dispatch_lead_gives_later_dispatch(
        self, completion_date: date, lead1: int, lead2: int
    ):
        """
        Property 20b: A larger dispatch_lead_days always gives a later dispatch date.
        """
        assume(lead1 != lead2)

        dispatch1 = calculate_expected_dispatch(completion_date, lead1)
        dispatch2 = calculate_expected_dispatch(completion_date, lead2)

        if lead1 > lead2:
            assert dispatch1 > dispatch2
        else:
            assert dispatch1 < dispatch2


class TestExpectedDeliveryDate:
    """**Validates: Requirements 28.4**"""

    @given(data=so_with_incomplete_wos())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_delivery_equals_dispatch_plus_delivery_lead(
        self, data: tuple[List[WorkOrderData], int, int]
    ):
        """
        Property 20c: Expected Delivery = Expected Dispatch + delivery_lead_days.
        """
        work_orders, dispatch_lead, delivery_lead = data

        estimated_completion = calculate_estimated_completion(work_orders)
        assume(estimated_completion is not None)

        expected_dispatch = calculate_expected_dispatch(estimated_completion, dispatch_lead)
        result = calculate_expected_delivery(expected_dispatch, delivery_lead)
        expected = expected_dispatch + timedelta(days=delivery_lead)

        assert result == expected, (
            f"Delivery date mismatch: got={result}, expected={expected}, "
            f"expected_dispatch={expected_dispatch}, delivery_lead={delivery_lead}"
        )

    @given(delivery_lead=positive_lead_time)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_delivery_with_no_dispatch_is_none(self, delivery_lead: int):
        """
        Property 20c: When expected_dispatch is None, delivery is None.
        """
        result = calculate_expected_delivery(None, delivery_lead)

        assert result is None, (
            f"Delivery with no dispatch should be None: got={result}"
        )

    @given(data=so_with_no_wos())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_delivery_with_no_wos_uses_today_chain(self, data: tuple[int, int]):
        """
        Property 20c + 20d: No WOs → Completion = today → Dispatch = today + dispatch_lead →
        Delivery = today + dispatch_lead + delivery_lead.
        """
        dispatch_lead, delivery_lead = data

        estimated_completion = calculate_estimated_completion([])
        expected_dispatch = calculate_expected_dispatch(estimated_completion, dispatch_lead)
        result = calculate_expected_delivery(expected_dispatch, delivery_lead)
        expected = date.today() + timedelta(days=dispatch_lead + delivery_lead)

        assert result == expected, (
            f"No-WO delivery mismatch: got={result}, expected={expected}, "
            f"dispatch_lead={dispatch_lead}, delivery_lead={delivery_lead}"
        )


class TestEndToEndDateChain:
    """**Validates: Requirements 28.2, 28.3, 28.4, 28.6**"""

    @given(data=so_with_incomplete_wos())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_full_date_chain_ordering(
        self, data: tuple[List[WorkOrderData], int, int]
    ):
        """
        Property 20: Completion < Dispatch < Delivery (strict ordering with positive leads).
        """
        work_orders, dispatch_lead, delivery_lead = data

        estimated_completion = calculate_estimated_completion(work_orders)
        assume(estimated_completion is not None)

        expected_dispatch = calculate_expected_dispatch(estimated_completion, dispatch_lead)
        expected_delivery = calculate_expected_delivery(expected_dispatch, delivery_lead)

        assert expected_dispatch > estimated_completion, (
            f"Dispatch should be after completion: "
            f"dispatch={expected_dispatch}, completion={estimated_completion}"
        )
        assert expected_delivery > expected_dispatch, (
            f"Delivery should be after dispatch: "
            f"delivery={expected_delivery}, dispatch={expected_dispatch}"
        )

    @given(data=so_with_incomplete_wos())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_full_date_chain_total_offset(
        self, data: tuple[List[WorkOrderData], int, int]
    ):
        """
        Property 20: Delivery = Completion + dispatch_lead + delivery_lead.
        """
        work_orders, dispatch_lead, delivery_lead = data

        estimated_completion = calculate_estimated_completion(work_orders)
        assume(estimated_completion is not None)

        expected_dispatch = calculate_expected_dispatch(estimated_completion, dispatch_lead)
        expected_delivery = calculate_expected_delivery(expected_dispatch, delivery_lead)

        total_lead = dispatch_lead + delivery_lead
        expected = estimated_completion + timedelta(days=total_lead)

        assert expected_delivery == expected, (
            f"End-to-end date chain mismatch: delivery={expected_delivery}, "
            f"expected={expected}, completion={estimated_completion}, "
            f"dispatch_lead={dispatch_lead}, delivery_lead={delivery_lead}"
        )

    @given(data=so_with_incomplete_wos())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_default_leads_give_4_day_total_offset(
        self, data: tuple[List[WorkOrderData], int, int]
    ):
        """
        Property 20: With default leads (1 + 3), delivery = completion + 4 days.
        """
        work_orders, _, _ = data

        estimated_completion = calculate_estimated_completion(work_orders)
        assume(estimated_completion is not None)

        expected_dispatch = calculate_expected_dispatch(
            estimated_completion, DEFAULT_DISPATCH_LEAD_DAYS
        )
        expected_delivery = calculate_expected_delivery(
            expected_dispatch, DEFAULT_DELIVERY_LEAD_DAYS
        )

        expected = estimated_completion + timedelta(days=4)

        assert expected_delivery == expected, (
            f"Default leads should give +4 days total: delivery={expected_delivery}, "
            f"expected={expected}, completion={estimated_completion}"
        )

    @given(wos=lists(work_order_any(), min_size=1, max_size=10))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_adding_later_incomplete_wo_extends_completion(
        self, wos: List[WorkOrderData]
    ):
        """
        Property 20: Adding an incomplete WO with a later due_date extends estimated completion.
        """
        # Get current estimated completion
        current_completion = calculate_estimated_completion(wos)
        assume(current_completion is not None)

        # Create a new WO with a later due date
        later_date = current_completion + timedelta(days=5)
        new_wo = WorkOrderData(status="IN_PRODUCTION", due_date=later_date)
        extended_wos = wos + [new_wo]

        new_completion = calculate_estimated_completion(extended_wos)

        assert new_completion == later_date, (
            f"Adding later WO should extend completion: "
            f"new_completion={new_completion}, expected={later_date}, "
            f"previous_completion={current_completion}"
        )

    @given(wos=lists(work_order_incomplete(), min_size=2, max_size=8))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_removing_latest_wo_reduces_completion(
        self, wos: List[WorkOrderData]
    ):
        """
        Property 20: Removing the WO with latest due_date reduces estimated completion
        to the next latest.
        """
        due_dates = [wo.due_date for wo in wos if wo.due_date is not None]
        assume(len(due_dates) >= 2)
        assume(len(set(due_dates)) >= 2)  # Need at least 2 distinct dates

        # Find the WO with the latest due_date and remove it
        max_date = max(due_dates)
        remaining_wos = [wo for wo in wos if wo.due_date != max_date]
        assume(len(remaining_wos) > 0)

        remaining_dates = [wo.due_date for wo in remaining_wos if wo.due_date is not None]
        assume(len(remaining_dates) > 0)

        new_completion = calculate_estimated_completion(remaining_wos)
        expected = max(remaining_dates)

        assert new_completion == expected, (
            f"Removing latest WO should reduce completion: "
            f"new_completion={new_completion}, expected={expected}, "
            f"removed_date={max_date}"
        )
