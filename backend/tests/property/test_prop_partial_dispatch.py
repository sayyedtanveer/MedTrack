"""
Property tests for Partial Dispatch Quantity Constraints.

# Feature: manufacturing-erp-audit, Property 12: Partial Dispatch Quantity Constraints

**Validates: Requirements 20.1, 20.2, 20.7**

These tests validate that:
  - For any SO line with allocated_quantity A and dispatched_quantity D,
    the maximum dispatchable quantity = A - D
  - Any dispatch_quantity exceeding A - D is rejected
  - After dispatch, the new dispatched_quantity = D + dispatched amount
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    decimals,
    integers,
    composite,
    lists,
    tuples,
)


# ─── Strategies ──────────────────────────────────────────────────────────────

# Positive quantities representing allocated amounts (non-zero)
positive_quantity = decimals(
    min_value=Decimal("0.001"),
    max_value=Decimal("100000.000"),
    places=3,
    allow_nan=False,
    allow_infinity=False,
)

# Non-negative quantities
non_negative_quantity = decimals(
    min_value=Decimal("0.000"),
    max_value=Decimal("100000.000"),
    places=3,
    allow_nan=False,
    allow_infinity=False,
)


@composite
def so_line_with_dispatch_capacity(draw):
    """
    Generate an SO line with allocated_quantity > dispatched_quantity
    (i.e., there is remaining capacity to dispatch).

    Returns: (allocated_quantity, dispatched_quantity)
    """
    allocated = draw(positive_quantity)
    # dispatched must be less than allocated to have remaining capacity
    max_dispatched = allocated - Decimal("0.001")
    if max_dispatched < Decimal("0"):
        max_dispatched = Decimal("0")
    dispatched = draw(decimals(
        min_value=Decimal("0.000"),
        max_value=max_dispatched,
        places=3,
        allow_nan=False,
        allow_infinity=False,
    ))
    return allocated, dispatched


@composite
def so_line_fully_dispatched(draw):
    """
    Generate an SO line where allocated_quantity == dispatched_quantity
    (no remaining capacity).

    Returns: (allocated_quantity, dispatched_quantity)
    """
    allocated = draw(positive_quantity)
    return allocated, allocated


@composite
def valid_dispatch_request(draw):
    """
    Generate an SO line and a valid dispatch quantity that does not exceed
    the max dispatchable (allocated - dispatched).

    Returns: (allocated_quantity, dispatched_quantity, dispatch_quantity)
    """
    allocated, dispatched = draw(so_line_with_dispatch_capacity())
    max_dispatchable = allocated - dispatched
    assume(max_dispatchable > Decimal("0"))

    dispatch_qty = draw(decimals(
        min_value=Decimal("0.001"),
        max_value=max_dispatchable,
        places=3,
        allow_nan=False,
        allow_infinity=False,
    ))
    return allocated, dispatched, dispatch_qty


@composite
def invalid_dispatch_request(draw):
    """
    Generate an SO line and a dispatch quantity that EXCEEDS the max
    dispatchable (allocated - dispatched).

    Returns: (allocated_quantity, dispatched_quantity, dispatch_quantity)
    """
    allocated, dispatched = draw(so_line_with_dispatch_capacity())
    max_dispatchable = allocated - dispatched
    assume(max_dispatchable > Decimal("0"))

    # Generate a quantity exceeding the max dispatchable
    excess = draw(decimals(
        min_value=Decimal("0.001"),
        max_value=Decimal("100000.000"),
        places=3,
        allow_nan=False,
        allow_infinity=False,
    ))
    dispatch_qty = max_dispatchable + excess
    return allocated, dispatched, dispatch_qty


@composite
def multiple_dispatch_sequence(draw):
    """
    Generate an SO line and a sequence of valid dispatches that
    cumulatively do not exceed allocated_quantity.

    Returns: (allocated_quantity, initial_dispatched, dispatch_amounts_list)
    """
    allocated = draw(positive_quantity)
    assume(allocated >= Decimal("0.010"))

    initial_dispatched = draw(decimals(
        min_value=Decimal("0.000"),
        max_value=allocated - Decimal("0.001"),
        places=3,
        allow_nan=False,
        allow_infinity=False,
    ))

    remaining = allocated - initial_dispatched
    assume(remaining >= Decimal("0.001"))

    # Generate 1 to 5 valid dispatch amounts
    num_dispatches = draw(integers(min_value=1, max_value=5))
    dispatch_amounts: List[Decimal] = []
    current_remaining = remaining

    for _ in range(num_dispatches):
        if current_remaining < Decimal("0.001"):
            break
        amount = draw(decimals(
            min_value=Decimal("0.001"),
            max_value=current_remaining,
            places=3,
            allow_nan=False,
            allow_infinity=False,
        ))
        dispatch_amounts.append(amount)
        current_remaining -= amount

    assume(len(dispatch_amounts) > 0)
    return allocated, initial_dispatched, dispatch_amounts


# ─── Helper: Partial dispatch logic (mirrors PartialFulfillmentService) ──────

def calculate_max_dispatchable(
    allocated_quantity: Decimal, dispatched_quantity: Decimal
) -> Decimal:
    """
    Calculate the maximum dispatchable quantity for an SO line.

    Mirrors PartialFulfillmentService.validate_dispatch_quantities:
        max_dispatchable = allocated - dispatched
    """
    return allocated_quantity - dispatched_quantity


def validate_dispatch_quantity(
    dispatch_quantity: Decimal,
    allocated_quantity: Decimal,
    dispatched_quantity: Decimal,
) -> bool:
    """
    Validate whether a dispatch quantity is acceptable.

    From PartialFulfillmentService.validate_dispatch_quantities:
        - dispatch_quantity must be > 0
        - dispatch_quantity must be <= (allocated - dispatched)
    """
    if dispatch_quantity <= Decimal("0"):
        return False
    max_dispatchable = calculate_max_dispatchable(allocated_quantity, dispatched_quantity)
    return dispatch_quantity <= max_dispatchable


def update_dispatched_quantity(
    current_dispatched: Decimal, dispatch_amount: Decimal
) -> Decimal:
    """
    Calculate the new dispatched_quantity after a dispatch.

    From PartialFulfillmentService.update_dispatched_quantities:
        line.dispatched_quantity = current_dispatched + qty
    """
    return current_dispatched + dispatch_amount


# ─────────────────────────────────────────────────────────────────────────────
# Property 12: Partial Dispatch Quantity Constraints
#
# For any sales order line with allocated_quantity A and previously
# dispatched_quantity D:
# (a) The maximum dispatchable quantity for a new delivery note SHALL equal A - D
# (b) Any dispatch_quantity exceeding A - D SHALL be rejected
# (c) After dispatch, the new dispatched_quantity SHALL equal D + dispatched amount
# ─────────────────────────────────────────────────────────────────────────────


class TestMaxDispatchableCalculation:
    """**Validates: Requirements 20.1**"""

    @given(data=so_line_with_dispatch_capacity())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_max_dispatchable_equals_allocated_minus_dispatched(
        self, data: tuple[Decimal, Decimal]
    ):
        """
        Property 12a: max_dispatchable = allocated_quantity - dispatched_quantity.
        """
        allocated, dispatched = data
        assume(allocated > dispatched)

        result = calculate_max_dispatchable(allocated, dispatched)
        expected = allocated - dispatched

        assert result == expected, (
            f"Max dispatchable mismatch: allocated={allocated}, "
            f"dispatched={dispatched}, got={result}, expected={expected}"
        )

    @given(data=so_line_with_dispatch_capacity())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_max_dispatchable_is_positive_when_capacity_remains(
        self, data: tuple[Decimal, Decimal]
    ):
        """
        Property 12a: max_dispatchable > 0 when allocated > dispatched.
        """
        allocated, dispatched = data
        assume(allocated > dispatched)

        result = calculate_max_dispatchable(allocated, dispatched)

        assert result > Decimal("0"), (
            f"Max dispatchable should be positive: allocated={allocated}, "
            f"dispatched={dispatched}, result={result}"
        )

    @given(data=so_line_fully_dispatched())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_max_dispatchable_is_zero_when_fully_dispatched(
        self, data: tuple[Decimal, Decimal]
    ):
        """
        Property 12a: max_dispatchable = 0 when allocated == dispatched.
        """
        allocated, dispatched = data

        result = calculate_max_dispatchable(allocated, dispatched)

        assert result == Decimal("0"), (
            f"Max dispatchable should be zero when fully dispatched: "
            f"allocated={allocated}, dispatched={dispatched}, result={result}"
        )

    @given(allocated=positive_quantity)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_max_dispatchable_equals_allocated_when_nothing_dispatched(
        self, allocated: Decimal
    ):
        """
        Property 12a: max_dispatchable = allocated when dispatched = 0 (first dispatch).
        """
        dispatched = Decimal("0")

        result = calculate_max_dispatchable(allocated, dispatched)

        assert result == allocated, (
            f"Max dispatchable should equal allocated when nothing dispatched: "
            f"allocated={allocated}, result={result}"
        )


class TestDispatchQuantityRejection:
    """**Validates: Requirements 20.2**"""

    @given(data=invalid_dispatch_request())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_dispatch_exceeding_max_is_rejected(
        self, data: tuple[Decimal, Decimal, Decimal]
    ):
        """
        Property 12b: Any dispatch_quantity > (allocated - dispatched) SHALL be rejected.
        """
        allocated, dispatched, dispatch_qty = data
        assume(dispatch_qty > calculate_max_dispatchable(allocated, dispatched))

        is_valid = validate_dispatch_quantity(dispatch_qty, allocated, dispatched)

        assert not is_valid, (
            f"Overshoot should be rejected: allocated={allocated}, "
            f"dispatched={dispatched}, dispatch_qty={dispatch_qty}, "
            f"max_dispatchable={calculate_max_dispatchable(allocated, dispatched)}"
        )

    @given(data=valid_dispatch_request())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_dispatch_within_max_is_accepted(
        self, data: tuple[Decimal, Decimal, Decimal]
    ):
        """
        Property 12b: Any dispatch_quantity <= (allocated - dispatched) SHALL be accepted.
        """
        allocated, dispatched, dispatch_qty = data

        is_valid = validate_dispatch_quantity(dispatch_qty, allocated, dispatched)

        assert is_valid, (
            f"Valid dispatch should be accepted: allocated={allocated}, "
            f"dispatched={dispatched}, dispatch_qty={dispatch_qty}, "
            f"max_dispatchable={calculate_max_dispatchable(allocated, dispatched)}"
        )

    @given(data=so_line_with_dispatch_capacity())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_dispatch_exactly_at_max_is_accepted(
        self, data: tuple[Decimal, Decimal]
    ):
        """
        Property 12b: dispatch_quantity == max_dispatchable is valid (dispatches all remaining).
        """
        allocated, dispatched = data
        assume(allocated > dispatched)

        max_dispatchable = calculate_max_dispatchable(allocated, dispatched)
        is_valid = validate_dispatch_quantity(max_dispatchable, allocated, dispatched)

        assert is_valid, (
            f"Dispatch at exact max should be accepted: allocated={allocated}, "
            f"dispatched={dispatched}, max_dispatchable={max_dispatchable}"
        )

    @given(data=so_line_fully_dispatched())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_any_dispatch_rejected_when_fully_dispatched(
        self, data: tuple[Decimal, Decimal]
    ):
        """
        Property 12b: When dispatched == allocated, any positive dispatch is rejected.
        """
        allocated, dispatched = data
        dispatch_qty = Decimal("0.001")

        is_valid = validate_dispatch_quantity(dispatch_qty, allocated, dispatched)

        assert not is_valid, (
            f"Dispatch on fully-dispatched line should be rejected: "
            f"allocated={allocated}, dispatched={dispatched}, dispatch_qty={dispatch_qty}"
        )

    @given(data=so_line_with_dispatch_capacity())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_zero_dispatch_quantity_is_rejected(
        self, data: tuple[Decimal, Decimal]
    ):
        """
        Property 12b: dispatch_quantity of 0 is always rejected.
        """
        allocated, dispatched = data

        is_valid = validate_dispatch_quantity(Decimal("0"), allocated, dispatched)

        assert not is_valid, (
            f"Zero dispatch should be rejected: allocated={allocated}, "
            f"dispatched={dispatched}"
        )

    @given(data=so_line_with_dispatch_capacity())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_negative_dispatch_quantity_is_rejected(
        self, data: tuple[Decimal, Decimal]
    ):
        """
        Property 12b: Negative dispatch_quantity is always rejected.
        """
        allocated, dispatched = data

        is_valid = validate_dispatch_quantity(Decimal("-1.000"), allocated, dispatched)

        assert not is_valid, (
            f"Negative dispatch should be rejected: allocated={allocated}, "
            f"dispatched={dispatched}"
        )


class TestDispatchedQuantityUpdate:
    """**Validates: Requirements 20.7**"""

    @given(data=valid_dispatch_request())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_dispatched_quantity_updated_correctly_after_dispatch(
        self, data: tuple[Decimal, Decimal, Decimal]
    ):
        """
        Property 12c: After dispatch, new dispatched_quantity = D + dispatched amount.
        """
        allocated, dispatched, dispatch_qty = data

        new_dispatched = update_dispatched_quantity(dispatched, dispatch_qty)
        expected = dispatched + dispatch_qty

        assert new_dispatched == expected, (
            f"Dispatched quantity update mismatch: dispatched={dispatched}, "
            f"dispatch_qty={dispatch_qty}, new_dispatched={new_dispatched}, "
            f"expected={expected}"
        )

    @given(data=valid_dispatch_request())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_new_dispatched_never_exceeds_allocated(
        self, data: tuple[Decimal, Decimal, Decimal]
    ):
        """
        Property 12c: After a valid dispatch, new dispatched_quantity <= allocated_quantity.
        """
        allocated, dispatched, dispatch_qty = data

        new_dispatched = update_dispatched_quantity(dispatched, dispatch_qty)

        assert new_dispatched <= allocated, (
            f"New dispatched exceeds allocated: allocated={allocated}, "
            f"dispatched={dispatched}, dispatch_qty={dispatch_qty}, "
            f"new_dispatched={new_dispatched}"
        )

    @given(data=valid_dispatch_request())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_remaining_capacity_decreases_after_dispatch(
        self, data: tuple[Decimal, Decimal, Decimal]
    ):
        """
        Property 12c: After dispatch, max_dispatchable decreases by the dispatched amount.
        """
        allocated, dispatched, dispatch_qty = data

        max_before = calculate_max_dispatchable(allocated, dispatched)
        new_dispatched = update_dispatched_quantity(dispatched, dispatch_qty)
        max_after = calculate_max_dispatchable(allocated, new_dispatched)

        decrease = max_before - max_after
        assert decrease == dispatch_qty, (
            f"Max dispatchable did not decrease by dispatch amount: "
            f"max_before={max_before}, max_after={max_after}, "
            f"decrease={decrease}, dispatch_qty={dispatch_qty}"
        )

    @given(data=multiple_dispatch_sequence())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_sequential_dispatches_accumulate_correctly(
        self, data: tuple[Decimal, Decimal, List[Decimal]]
    ):
        """
        Property 12c: Multiple sequential dispatches accumulate dispatched_quantity correctly.
        After n dispatches, dispatched_quantity = initial_dispatched + sum(all dispatch amounts).
        """
        allocated, initial_dispatched, dispatch_amounts = data

        current_dispatched = initial_dispatched
        for amount in dispatch_amounts:
            # Each dispatch should be valid
            assert validate_dispatch_quantity(amount, allocated, current_dispatched), (
                f"Sequential dispatch should be valid: allocated={allocated}, "
                f"current_dispatched={current_dispatched}, amount={amount}"
            )
            current_dispatched = update_dispatched_quantity(current_dispatched, amount)

        expected_final = initial_dispatched + sum(dispatch_amounts)
        assert current_dispatched == expected_final, (
            f"Final dispatched mismatch after sequential dispatches: "
            f"initial={initial_dispatched}, amounts={dispatch_amounts}, "
            f"final={current_dispatched}, expected={expected_final}"
        )

    @given(data=multiple_dispatch_sequence())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_sequential_dispatches_never_exceed_allocated(
        self, data: tuple[Decimal, Decimal, List[Decimal]]
    ):
        """
        Property 12c: After any number of valid sequential dispatches,
        dispatched_quantity never exceeds allocated_quantity.
        """
        allocated, initial_dispatched, dispatch_amounts = data

        current_dispatched = initial_dispatched
        for amount in dispatch_amounts:
            current_dispatched = update_dispatched_quantity(current_dispatched, amount)
            assert current_dispatched <= allocated, (
                f"Dispatched exceeded allocated after sequential dispatch: "
                f"allocated={allocated}, current_dispatched={current_dispatched}"
            )

    @given(data=so_line_with_dispatch_capacity())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_dispatch_full_remaining_sets_dispatched_to_allocated(
        self, data: tuple[Decimal, Decimal]
    ):
        """
        Property 12c: Dispatching the full remaining amount sets dispatched == allocated.
        """
        allocated, dispatched = data
        assume(allocated > dispatched)

        max_dispatchable = calculate_max_dispatchable(allocated, dispatched)
        new_dispatched = update_dispatched_quantity(dispatched, max_dispatchable)

        assert new_dispatched == allocated, (
            f"Full dispatch should set dispatched to allocated: "
            f"allocated={allocated}, dispatched={dispatched}, "
            f"max_dispatchable={max_dispatchable}, new_dispatched={new_dispatched}"
        )
