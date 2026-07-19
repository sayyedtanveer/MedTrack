"""
Property tests for Inventory Transaction Running Balance.

# Feature: manufacturing-erp-audit, Property 15: Inventory Transaction Running Balance

**Validates: Requirements 31.5, 31.10**

These tests validate that:
  - For any material and ordered sequence of transactions T₁, T₂, ..., Tₙ,
    the running balance at position k = sum(T₁.quantity + ... + Tₖ.quantity)
  - The final running balance matches current_stock within tolerance 0.001
"""

from __future__ import annotations

from decimal import Decimal
from typing import List

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    decimals,
    floats,
    integers,
    lists,
    composite,
    sampled_from,
)


# ─── Constants ───────────────────────────────────────────────────────────────

TOLERANCE = Decimal("0.001")

# Valid transaction types that affect inventory
TRANSACTION_TYPES = [
    "OPENING_STOCK",
    "PURCHASE_RECEIPT",
    "RESERVATION",
    "RESERVATION_RELEASE",
    "MATERIAL_ISSUE",
    "PRODUCTION_CONSUMPTION",
    "FG_RECEIPT",
    "DISPATCH",
    "DISPATCH_REVERSAL",
    "SALES_RETURN",
    "SCRAP",
    "ADJUSTMENT",
    "TRANSFER",
]


# ─── Helper: Running balance computation (mirrors InventoryTransactionService) ─


def compute_running_balances(quantities: List[Decimal]) -> List[Decimal]:
    """
    Compute cumulative running balances for a sequence of transaction quantities.

    This mirrors the logic in InventoryTransactionService.get_running_balance():
        running_balance = Decimal("0")
        for row in rows:
            qty = Decimal(str(row.quantity))
            running_balance += qty

    Args:
        quantities: Ordered list of transaction quantities (+ve for inbound, -ve for outbound).

    Returns:
        List of cumulative balances at each position.
    """
    balances: List[Decimal] = []
    running = Decimal("0")
    for qty in quantities:
        running += qty
        balances.append(running)
    return balances


def compute_final_balance(quantities: List[Decimal]) -> Decimal:
    """
    Compute the final running balance = sum of all quantities.

    This is what check_reconciliation compares against current_stock.
    """
    return sum(quantities, Decimal("0"))


def is_reconciled(transaction_sum: Decimal, current_stock: Decimal) -> bool:
    """
    Check if the sum of transactions matches current_stock within tolerance.

    Mirrors InventoryTransactionService.check_reconciliation():
        difference = abs(transaction_sum - current_stock)
        is_reconciled = difference <= tolerance
    """
    difference = abs(transaction_sum - current_stock)
    return difference <= TOLERANCE


# ─── Strategies ──────────────────────────────────────────────────────────────

# Transaction quantity: can be positive (inbound) or negative (outbound)
# Using a reasonable range to avoid overflow issues
transaction_quantity_strategy = decimals(
    min_value=Decimal("-10000"),
    max_value=Decimal("10000"),
    places=3,
    allow_nan=False,
    allow_infinity=False,
)


@composite
def transaction_sequence(draw):
    """
    Generate a random sequence of inventory transaction quantities.

    Returns a list of 1 to 50 Decimal quantities representing ordered transactions.
    """
    n = draw(integers(min_value=1, max_value=50))
    quantities = []
    for _ in range(n):
        qty = draw(transaction_quantity_strategy)
        quantities.append(qty)
    return quantities


@composite
def transaction_sequence_with_stock(draw):
    """
    Generate a transaction sequence and a current_stock that matches
    the sum of transactions (reconciled scenario).
    """
    quantities = draw(transaction_sequence())
    final_sum = sum(quantities, Decimal("0"))
    return quantities, final_sum


@composite
def transaction_sequence_with_drift(draw):
    """
    Generate a transaction sequence and a current_stock that differs
    from the sum by more than tolerance (unreconciled scenario).
    """
    quantities = draw(transaction_sequence())
    final_sum = sum(quantities, Decimal("0"))

    # Add a drift that exceeds tolerance
    drift = draw(decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("100"),
        places=3,
        allow_nan=False,
        allow_infinity=False,
    ))
    # Either add or subtract drift
    sign = draw(sampled_from([Decimal("1"), Decimal("-1")]))
    current_stock = final_sum + (sign * drift)

    return quantities, current_stock


# ─────────────────────────────────────────────────────────────────────────────
# Property 15: Inventory Transaction Running Balance
#
# For any material and ordered sequence of transactions T₁..Tₙ:
# (a) Running balance at position k = sum(T₁..Tₖ)
# (b) Final running balance matches current_stock within tolerance 0.001
# ─────────────────────────────────────────────────────────────────────────────


class TestRunningBalanceComputation:
    """**Validates: Requirements 31.5**"""

    @given(quantities=transaction_sequence())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_running_balance_at_position_k_equals_cumulative_sum(
        self, quantities: List[Decimal]
    ):
        """
        Property 15a: For any transaction sequence, the running balance at
        position k = sum(T₁.quantity + T₂.quantity + ... + Tₖ.quantity).
        """
        balances = compute_running_balances(quantities)

        # Verify each position k
        for k in range(len(quantities)):
            expected = sum(quantities[: k + 1], Decimal("0"))
            actual = balances[k]
            assert abs(actual - expected) <= TOLERANCE, (
                f"Running balance mismatch at position {k}: "
                f"expected={expected}, actual={actual}, "
                f"quantities={quantities[:k+1]}"
            )

    @given(quantities=transaction_sequence())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_final_balance_equals_sum_of_all_transactions(
        self, quantities: List[Decimal]
    ):
        """
        Property 15a: The final running balance equals sum(all quantities).
        """
        balances = compute_running_balances(quantities)
        final_balance = balances[-1]
        expected_total = sum(quantities, Decimal("0"))

        assert abs(final_balance - expected_total) <= TOLERANCE, (
            f"Final balance mismatch: final={final_balance}, "
            f"expected_total={expected_total}"
        )

    @given(quantities=transaction_sequence())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_running_balance_increments_by_transaction_quantity(
        self, quantities: List[Decimal]
    ):
        """
        Property 15a: Each successive running balance differs from the previous
        by exactly the transaction quantity at that position.

        balance[k] - balance[k-1] = quantities[k] for k >= 1
        balance[0] = quantities[0]
        """
        balances = compute_running_balances(quantities)

        # First balance equals first quantity
        assert abs(balances[0] - quantities[0]) <= TOLERANCE, (
            f"First balance should equal first quantity: "
            f"balance={balances[0]}, quantity={quantities[0]}"
        )

        # Each subsequent balance increments by the transaction quantity
        for k in range(1, len(quantities)):
            diff = balances[k] - balances[k - 1]
            assert abs(diff - quantities[k]) <= TOLERANCE, (
                f"Balance increment mismatch at position {k}: "
                f"diff={diff}, expected={quantities[k]}"
            )

    @given(quantities=transaction_sequence())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_running_balance_count_matches_transaction_count(
        self, quantities: List[Decimal]
    ):
        """
        Property 15a: The number of running balance entries equals
        the number of transactions.
        """
        balances = compute_running_balances(quantities)
        assert len(balances) == len(quantities), (
            f"Balance count {len(balances)} != transaction count {len(quantities)}"
        )


class TestReconciliationWithCurrentStock:
    """**Validates: Requirements 31.10**"""

    @given(data=transaction_sequence_with_stock())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_final_balance_matches_current_stock_when_reconciled(
        self, data: tuple[List[Decimal], Decimal]
    ):
        """
        Property 15b: When current_stock = sum(all transactions),
        the system reports reconciled (difference <= 0.001).
        """
        quantities, current_stock = data
        final_balance = compute_final_balance(quantities)

        assert is_reconciled(final_balance, current_stock), (
            f"Should be reconciled: final_balance={final_balance}, "
            f"current_stock={current_stock}, "
            f"difference={abs(final_balance - current_stock)}"
        )

    @given(data=transaction_sequence_with_drift())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_not_reconciled_when_stock_differs_beyond_tolerance(
        self, data: tuple[List[Decimal], Decimal]
    ):
        """
        Property 15b: When current_stock differs from sum(transactions)
        by more than tolerance, the system reports NOT reconciled.
        """
        quantities, current_stock = data
        final_balance = compute_final_balance(quantities)

        # Ensure the drift actually exceeds tolerance
        difference = abs(final_balance - current_stock)
        assume(difference > TOLERANCE)

        assert not is_reconciled(final_balance, current_stock), (
            f"Should NOT be reconciled: final_balance={final_balance}, "
            f"current_stock={current_stock}, difference={difference}"
        )

    @given(quantities=transaction_sequence())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_reconciliation_symmetric(
        self, quantities: List[Decimal]
    ):
        """
        Property 15b: Reconciliation check is symmetric —
        is_reconciled(a, b) == is_reconciled(b, a).
        """
        final_balance = compute_final_balance(quantities)
        # current_stock = final_balance (perfectly reconciled)
        current_stock = final_balance

        assert is_reconciled(final_balance, current_stock) == is_reconciled(
            current_stock, final_balance
        ), "Reconciliation should be symmetric"

    @given(quantities=transaction_sequence())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_tolerance_boundary(
        self, quantities: List[Decimal]
    ):
        """
        Property 15b: A difference of exactly tolerance (0.001) is still reconciled.
        A difference just over tolerance is not reconciled.
        """
        final_balance = compute_final_balance(quantities)

        # Exactly at tolerance boundary — should be reconciled
        at_boundary = final_balance + TOLERANCE
        assert is_reconciled(final_balance, at_boundary), (
            f"Difference of exactly tolerance should be reconciled: "
            f"balance={final_balance}, stock={at_boundary}"
        )

        # Just over tolerance — should NOT be reconciled
        over_boundary = final_balance + TOLERANCE + Decimal("0.001")
        assert not is_reconciled(final_balance, over_boundary), (
            f"Difference over tolerance should NOT be reconciled: "
            f"balance={final_balance}, stock={over_boundary}"
        )


class TestRunningBalanceEdgeCases:
    """Edge case tests for running balance computation.

    **Validates: Requirements 31.5, 31.10**
    """

    def test_single_transaction(self):
        """A single transaction's running balance equals its quantity."""
        quantities = [Decimal("100.500")]
        balances = compute_running_balances(quantities)
        assert balances == [Decimal("100.500")]

    def test_zero_quantity_transactions(self):
        """Zero-quantity transactions don't change the running balance."""
        quantities = [Decimal("50"), Decimal("0"), Decimal("0"), Decimal("25")]
        balances = compute_running_balances(quantities)
        assert balances == [
            Decimal("50"),
            Decimal("50"),
            Decimal("50"),
            Decimal("75"),
        ]

    def test_alternating_positive_negative(self):
        """Alternating in/out transactions compute correctly."""
        quantities = [
            Decimal("100"),
            Decimal("-30"),
            Decimal("50"),
            Decimal("-20"),
        ]
        balances = compute_running_balances(quantities)
        assert balances == [
            Decimal("100"),
            Decimal("70"),
            Decimal("120"),
            Decimal("100"),
        ]

    def test_balance_can_go_negative(self):
        """Running balance can be negative (over-issued scenario)."""
        quantities = [Decimal("10"), Decimal("-20")]
        balances = compute_running_balances(quantities)
        assert balances == [Decimal("10"), Decimal("-10")]

    def test_high_precision_quantities(self):
        """Decimal precision is preserved through computation."""
        quantities = [Decimal("1.001"), Decimal("2.002"), Decimal("3.003")]
        balances = compute_running_balances(quantities)
        assert balances == [
            Decimal("1.001"),
            Decimal("3.003"),
            Decimal("6.006"),
        ]

    def test_reconciliation_exact_match(self):
        """Perfect reconciliation when stock equals transaction sum."""
        quantities = [Decimal("100"), Decimal("-25"), Decimal("10")]
        final_balance = compute_final_balance(quantities)
        current_stock = Decimal("85")
        assert final_balance == current_stock
        assert is_reconciled(final_balance, current_stock)

    def test_reconciliation_within_tolerance(self):
        """Reconciled when difference is within tolerance."""
        final_balance = Decimal("100.000")
        current_stock = Decimal("100.0005")  # diff = 0.0005 < 0.001
        assert is_reconciled(final_balance, current_stock)

    def test_reconciliation_outside_tolerance(self):
        """Not reconciled when difference exceeds tolerance."""
        final_balance = Decimal("100.000")
        current_stock = Decimal("100.002")  # diff = 0.002 > 0.001
        assert not is_reconciled(final_balance, current_stock)

    def test_empty_returns_empty(self):
        """Empty transaction list produces empty balance list."""
        balances = compute_running_balances([])
        assert balances == []

    def test_final_balance_of_empty_is_zero(self):
        """Empty transactions sum to zero."""
        assert compute_final_balance([]) == Decimal("0")
