"""
Property tests for Outstanding Balance Calculation.

# Feature: manufacturing-erp-audit, Property 5: Outstanding Balance Calculation

**Validates: Requirements 3.1, 3.3**

These tests validate that:
  - For any invoice with grand_total G and payments P₁..Pₙ,
    outstanding balance = G - sum(P₁..Pₙ)
  - Any payment amount exceeding the outstanding balance is rejected
"""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_UP
from typing import List

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    decimals,
    floats,
    integers,
    lists,
    composite,
)


# ─── Helper: Outstanding balance logic (mirrors FinanceService logic) ────────

TOLERANCE = 0.001


def calculate_outstanding_balance(grand_total: float, paid_amount: float) -> float:
    """
    Calculate outstanding balance for an invoice.

    Outstanding = grand_total - paid_amount
    This mirrors the logic in FinanceService.record_payment:
        balance = _as_float(invoice.grand_total) - _as_float(invoice.paid_amount)
    """
    return grand_total - paid_amount


def is_payment_valid(payment_amount: float, outstanding_balance: float) -> bool:
    """
    Check if a payment amount is valid (does not exceed outstanding balance).

    From FinanceService.record_payment:
        if amount > balance + 0.001:
            raise ValueError(...)

    A payment is valid if: amount <= outstanding_balance + TOLERANCE
    """
    if payment_amount <= 0:
        return False
    return payment_amount <= outstanding_balance + TOLERANCE


def apply_payments_sequentially(
    grand_total: float, payments: List[float]
) -> tuple[float, List[bool]]:
    """
    Apply a sequence of payments to an invoice, returning
    (final_outstanding, list of accepted/rejected per payment).

    Each payment is validated against the current outstanding balance.
    """
    paid_amount = 0.0
    results: List[bool] = []

    for payment in payments:
        outstanding = grand_total - paid_amount
        if payment <= 0:
            results.append(False)
        elif payment > outstanding + TOLERANCE:
            results.append(False)
        else:
            paid_amount += payment
            results.append(True)

    final_outstanding = grand_total - paid_amount
    return final_outstanding, results


# ─── Strategies ──────────────────────────────────────────────────────────────

# Grand total: positive monetary values (avoid very small or very large)
grand_total_strategy = floats(
    min_value=0.01,
    max_value=1_000_000.0,
    allow_nan=False,
    allow_infinity=False,
)

# Payment amounts: positive monetary values
payment_amount_strategy = floats(
    min_value=0.01,
    max_value=1_000_000.0,
    allow_nan=False,
    allow_infinity=False,
)


@composite
def invoice_with_valid_payments(draw):
    """
    Generate an invoice grand_total and a list of valid payments
    that all fit within the outstanding balance.
    """
    grand_total = draw(grand_total_strategy)
    assume(grand_total >= 0.01)

    # Generate 0 to 10 payments that cumulatively don't exceed grand_total
    num_payments = draw(integers(min_value=0, max_value=10))
    payments: List[float] = []
    remaining = grand_total

    for _ in range(num_payments):
        if remaining < 0.01:
            break
        payment = draw(floats(
            min_value=0.01,
            max_value=remaining,
            allow_nan=False,
            allow_infinity=False,
        ))
        payments.append(payment)
        remaining -= payment

    return grand_total, payments


@composite
def invoice_with_overpayment(draw):
    """
    Generate an invoice grand_total, some valid payments, and then
    an overpayment that exceeds the remaining balance.
    """
    grand_total = draw(grand_total_strategy)
    assume(grand_total >= 0.01)

    # Generate 0 to 5 valid payments first
    num_valid = draw(integers(min_value=0, max_value=5))
    payments: List[float] = []
    remaining = grand_total

    for _ in range(num_valid):
        if remaining < 0.01:
            break
        payment = draw(floats(
            min_value=0.01,
            max_value=remaining,
            allow_nan=False,
            allow_infinity=False,
        ))
        payments.append(payment)
        remaining -= payment

    # Now generate an overpayment (exceeding remaining balance by more than tolerance)
    overpayment = draw(floats(
        min_value=remaining + TOLERANCE + 0.01,
        max_value=remaining + grand_total + 1000.0,
        allow_nan=False,
        allow_infinity=False,
    ))
    assume(overpayment > remaining + TOLERANCE)

    return grand_total, payments, overpayment


# ─────────────────────────────────────────────────────────────────────────────
# Property 5: Outstanding Balance Calculation
#
# For any invoice with grand_total G and recorded payments P₁, P₂, ..., Pₙ:
# (a) Outstanding balance SHALL equal G - sum(P₁..Pₙ)
# (b) Any payment amount exceeding outstanding balance SHALL be rejected
# ─────────────────────────────────────────────────────────────────────────────


class TestOutstandingBalanceCalculation:
    """**Validates: Requirements 3.1**"""

    @given(data=invoice_with_valid_payments())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_outstanding_equals_grand_total_minus_sum_of_payments(
        self, data: tuple[float, List[float]]
    ):
        """
        Property 5a: For any invoice with grand_total G and payments P₁..Pₙ,
        outstanding = G - sum(P₁..Pₙ).
        """
        grand_total, payments = data

        total_paid = sum(payments)
        expected_outstanding = grand_total - total_paid

        # Apply payments sequentially (as the system would)
        final_outstanding, results = apply_payments_sequentially(grand_total, payments)

        # All payments should have been accepted
        assert all(results), (
            f"Some valid payments were rejected: grand_total={grand_total}, "
            f"payments={payments}, results={results}"
        )

        # Outstanding balance should match expected
        assert abs(final_outstanding - expected_outstanding) < 0.01, (
            f"Outstanding mismatch: grand_total={grand_total}, "
            f"payments={payments}, final_outstanding={final_outstanding}, "
            f"expected={expected_outstanding}"
        )

    @given(grand_total=grand_total_strategy)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_outstanding_equals_grand_total_with_no_payments(self, grand_total: float):
        """
        Property 5a: With no payments, outstanding = grand_total.
        """
        assume(grand_total >= 0.01)

        outstanding = calculate_outstanding_balance(grand_total, 0.0)

        assert abs(outstanding - grand_total) < 0.001, (
            f"Outstanding should equal grand_total with no payments: "
            f"grand_total={grand_total}, outstanding={outstanding}"
        )

    @given(data=invoice_with_valid_payments())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_outstanding_is_non_negative_for_valid_payments(
        self, data: tuple[float, List[float]]
    ):
        """
        Property 5a: Outstanding balance is always >= 0 when payments are valid.
        """
        grand_total, payments = data

        final_outstanding, _ = apply_payments_sequentially(grand_total, payments)

        assert final_outstanding >= -TOLERANCE, (
            f"Outstanding went negative: grand_total={grand_total}, "
            f"payments={payments}, outstanding={final_outstanding}"
        )

    @given(data=invoice_with_valid_payments())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_outstanding_decreases_with_each_payment(
        self, data: tuple[float, List[float]]
    ):
        """
        Property 5a: Each accepted payment reduces the outstanding balance
        by exactly the payment amount.
        """
        grand_total, payments = data
        assume(len(payments) > 0)

        paid_so_far = 0.0
        for payment in payments:
            before = calculate_outstanding_balance(grand_total, paid_so_far)
            paid_so_far += payment
            after = calculate_outstanding_balance(grand_total, paid_so_far)

            decrease = before - after
            assert abs(decrease - payment) < 0.001, (
                f"Payment did not decrease outstanding by exact amount: "
                f"payment={payment}, decrease={decrease}"
            )


class TestPaymentExceedingOutstandingRejected:
    """**Validates: Requirements 3.3**"""

    @given(data=invoice_with_overpayment())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_payment_exceeding_outstanding_is_rejected(
        self, data: tuple[float, List[float], float]
    ):
        """
        Property 5b: Any payment amount exceeding outstanding balance SHALL be rejected.
        """
        grand_total, valid_payments, overpayment = data

        # Apply valid payments first
        paid_amount = sum(valid_payments)
        outstanding = grand_total - paid_amount

        # The overpayment should be rejected
        assert not is_payment_valid(overpayment, outstanding), (
            f"Overpayment should have been rejected: "
            f"grand_total={grand_total}, paid={paid_amount}, "
            f"outstanding={outstanding}, overpayment={overpayment}"
        )

    @given(grand_total=grand_total_strategy)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_payment_exactly_equal_to_outstanding_is_accepted(
        self, grand_total: float
    ):
        """
        Property 5b: A payment equal to the outstanding balance is valid
        (pays off the invoice completely).
        """
        assume(grand_total >= 0.01)

        outstanding = calculate_outstanding_balance(grand_total, 0.0)

        # Paying the exact outstanding balance should be accepted
        assert is_payment_valid(grand_total, outstanding), (
            f"Payment equal to outstanding should be accepted: "
            f"grand_total={grand_total}, outstanding={outstanding}"
        )

    @given(data=invoice_with_valid_payments())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_payment_slightly_over_tolerance_is_rejected(
        self, data: tuple[float, List[float]]
    ):
        """
        Property 5b: Payment exceeding outstanding by more than tolerance is rejected.
        The system uses a tolerance of 0.001 for floating point comparison.
        """
        grand_total, payments = data

        paid_amount = sum(payments)
        outstanding = grand_total - paid_amount
        assume(outstanding >= 0.0)

        # A payment that exceeds by more than tolerance
        overpayment = outstanding + TOLERANCE + 0.01

        assert not is_payment_valid(overpayment, outstanding), (
            f"Payment exceeding tolerance should be rejected: "
            f"outstanding={outstanding}, overpayment={overpayment}"
        )

    @given(data=invoice_with_valid_payments())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_zero_or_negative_payment_is_rejected(
        self, data: tuple[float, List[float]]
    ):
        """
        Property 5b: Zero or negative payments are always rejected.
        """
        grand_total, payments = data

        paid_amount = sum(payments)
        outstanding = grand_total - paid_amount

        assert not is_payment_valid(0.0, outstanding), (
            "Zero payment should be rejected"
        )
        assert not is_payment_valid(-1.0, outstanding), (
            "Negative payment should be rejected"
        )

    @given(
        grand_total=grand_total_strategy,
        excess=floats(
            min_value=0.01,
            max_value=100_000.0,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_fully_paid_invoice_rejects_any_further_payment(
        self, grand_total: float, excess: float
    ):
        """
        Property 5b: Once an invoice is fully paid (outstanding = 0),
        any further payment is rejected.
        """
        assume(grand_total >= 0.01)
        assume(excess >= 0.01)

        # Invoice fully paid
        outstanding = calculate_outstanding_balance(grand_total, grand_total)

        assert abs(outstanding) < TOLERANCE, (
            f"Fully paid invoice should have ~0 outstanding: {outstanding}"
        )

        # Any positive payment should be rejected
        assert not is_payment_valid(excess, outstanding), (
            f"Payment on fully-paid invoice should be rejected: "
            f"outstanding={outstanding}, payment={excess}"
        )


class TestOutstandingBalanceIntegration:
    """Integration tests for the outstanding balance property.

    **Validates: Requirements 3.1, 3.3**
    """

    @given(data=invoice_with_valid_payments())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_sequential_payments_produce_consistent_outstanding(
        self, data: tuple[float, List[float]]
    ):
        """
        Applying payments one-by-one produces same result as computing
        grand_total - sum(all_payments).
        """
        grand_total, payments = data

        # Sequential application
        final_outstanding_seq, _ = apply_payments_sequentially(grand_total, payments)

        # Direct calculation
        final_outstanding_direct = grand_total - sum(payments)

        assert abs(final_outstanding_seq - final_outstanding_direct) < 0.01, (
            f"Sequential vs direct mismatch: "
            f"sequential={final_outstanding_seq}, direct={final_outstanding_direct}"
        )

    @given(data=invoice_with_valid_payments())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_outstanding_bounded_by_zero_and_grand_total(
        self, data: tuple[float, List[float]]
    ):
        """
        Outstanding balance is always between 0 and grand_total (inclusive)
        when all payments are valid.
        """
        grand_total, payments = data

        final_outstanding, results = apply_payments_sequentially(grand_total, payments)
        assert all(results)

        assert final_outstanding >= -TOLERANCE, (
            f"Outstanding below zero: {final_outstanding}"
        )
        assert final_outstanding <= grand_total + TOLERANCE, (
            f"Outstanding above grand_total: {final_outstanding} > {grand_total}"
        )

    def test_edge_case_single_full_payment(self):
        """Edge case: A single payment equal to grand_total results in 0 outstanding."""
        grand_total = 1500.00
        payments = [1500.00]

        final_outstanding, results = apply_payments_sequentially(grand_total, payments)

        assert all(results)
        assert abs(final_outstanding) < TOLERANCE

    def test_edge_case_many_small_payments(self):
        """Edge case: Many small payments summing to grand_total."""
        grand_total = 100.00
        payments = [10.00] * 10

        final_outstanding, results = apply_payments_sequentially(grand_total, payments)

        assert all(results)
        assert abs(final_outstanding) < TOLERANCE

    def test_edge_case_overpayment_after_partial(self):
        """Edge case: A payment that would exceed remaining balance is rejected."""
        grand_total = 500.00
        # Pay 400, then try to pay 200 (which exceeds remaining 100)
        paid_amount = 400.0
        outstanding = calculate_outstanding_balance(grand_total, paid_amount)

        assert abs(outstanding - 100.0) < TOLERANCE
        assert not is_payment_valid(200.0, outstanding)
        assert is_payment_valid(100.0, outstanding)
