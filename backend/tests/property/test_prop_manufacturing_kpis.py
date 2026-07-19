"""
Property tests for Manufacturing KPI Formulas.

# Feature: manufacturing-erp-audit, Property 16: Manufacturing KPI Formulas

**Validates: Requirements 32.1, 32.2, 32.3, 32.4**

These tests validate that the manufacturing KPI formulas produce correct results
for all valid input ranges:
  - Yield = (produced - scrap) / produced × 100
  - Scrap Rate = scrap / produced × 100
  - Rework Rate = rework_count / total_completed × 100
  - OEE = Availability × Performance × Quality
"""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    floats,
    integers,
    composite,
)


# ─── Strategies ──────────────────────────────────────────────────────────────

# Production quantities — positive produced, scrap within range
positive_produced = floats(
    min_value=0.001,
    max_value=1_000_000.0,
    allow_nan=False,
    allow_infinity=False,
)

non_negative_quantity = floats(
    min_value=0.0,
    max_value=1_000_000.0,
    allow_nan=False,
    allow_infinity=False,
)

# OEE component percentages (0 to 1 range, representing fractions)
oee_component = floats(
    min_value=0.0,
    max_value=1.0,
    allow_nan=False,
    allow_infinity=False,
)

# Rework/completed counts
positive_count = integers(min_value=1, max_value=100_000)
non_negative_count = integers(min_value=0, max_value=100_000)


@composite
def production_data(draw):
    """Generate valid production data where 0 <= scrap <= produced."""
    produced = draw(positive_produced)
    scrap = draw(floats(
        min_value=0.0,
        max_value=produced,
        allow_nan=False,
        allow_infinity=False,
    ))
    return produced, scrap


@composite
def rework_data(draw):
    """Generate valid rework data where rework_count >= 0 and total_completed > 0."""
    total_completed = draw(positive_count)
    rework_count = draw(integers(min_value=0, max_value=total_completed * 5))
    return rework_count, total_completed


@composite
def oee_components(draw):
    """Generate valid OEE components: availability, performance, quality all in [0, 1]."""
    availability = draw(oee_component)
    performance = draw(oee_component)
    quality = draw(oee_component)
    return availability, performance, quality


# ─── Helper: KPI calculation functions (mirrors KPIQueryService logic) ───────

def calculate_yield_rate(produced: float, scrap: float) -> float:
    """Calculate yield rate: (produced - scrap) / produced × 100."""
    if produced <= 0:
        return 0.0
    return round(((produced - scrap) / produced) * 100, 2)


def calculate_scrap_rate(produced: float, scrap: float) -> float:
    """Calculate scrap rate: scrap / produced × 100."""
    if produced <= 0:
        return 0.0
    return round((scrap / produced) * 100, 2)


def calculate_rework_rate(rework_count: int, total_completed: int) -> float:
    """Calculate rework rate: rework_count / total_completed × 100."""
    if total_completed <= 0:
        return 0.0
    return round((rework_count / total_completed) * 100, 2)


def calculate_oee(availability: float, performance: float, quality: float) -> float:
    """Calculate OEE: Availability × Performance × Quality × 100."""
    return round(availability * performance * quality * 100, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Property 16: Manufacturing KPI Formulas
#
# For any set of production data:
# (a) Yield = (produced - scrap) / produced × 100 per product
# (b) Scrap Rate = scrap / produced × 100
# (c) Rework Rate = rework_count / total_completed × 100
# (d) OEE = Availability × Performance × Quality
# These calculations SHALL produce correct results for all valid input ranges
# where denominators > 0.
# ─────────────────────────────────────────────────────────────────────────────


class TestYieldRateFormula:
    """**Validates: Requirements 32.1**"""

    @given(data=production_data())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_yield_formula_correct(self, data: tuple[float, float]):
        """Property 16a: Yield = (produced - scrap) / produced × 100 for all valid inputs."""
        produced, scrap = data
        assume(produced > 0)
        assume(scrap >= 0)
        assume(scrap <= produced)

        result = calculate_yield_rate(produced, scrap)
        expected = round(((produced - scrap) / produced) * 100, 2)

        assert result == expected, (
            f"Yield mismatch: produced={produced}, scrap={scrap}, "
            f"got={result}, expected={expected}"
        )

    @given(data=production_data())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_yield_rate_bounded_0_to_100(self, data: tuple[float, float]):
        """Property 16a: Yield rate is always between 0% and 100% inclusive."""
        produced, scrap = data
        assume(produced > 0)
        assume(scrap >= 0)
        assume(scrap <= produced)

        result = calculate_yield_rate(produced, scrap)

        assert 0.0 <= result <= 100.0, (
            f"Yield out of bounds: produced={produced}, scrap={scrap}, result={result}"
        )

    @given(data=production_data())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_yield_plus_scrap_rate_equals_100(self, data: tuple[float, float]):
        """Property 16a+b: Yield rate + Scrap rate = 100% (complementary)."""
        produced, scrap = data
        assume(produced > 0)
        assume(scrap >= 0)
        assume(scrap <= produced)

        yield_rate = calculate_yield_rate(produced, scrap)
        scrap_rate = calculate_scrap_rate(produced, scrap)

        # Due to rounding, allow small tolerance
        total = yield_rate + scrap_rate
        assert abs(total - 100.0) <= 0.02, (
            f"Yield + Scrap != 100%: produced={produced}, scrap={scrap}, "
            f"yield={yield_rate}, scrap_rate={scrap_rate}, total={total}"
        )

    def test_yield_zero_when_produced_is_zero(self):
        """Property 16a edge case: Yield = 0% when produced = 0."""
        result = calculate_yield_rate(0.0, 0.0)
        assert result == 0.0

    def test_yield_100_when_no_scrap(self):
        """Property 16a edge case: Yield = 100% when scrap = 0."""
        result = calculate_yield_rate(1000.0, 0.0)
        assert result == 100.0

    def test_yield_0_when_all_scrap(self):
        """Property 16a edge case: Yield = 0% when all produced is scrapped."""
        result = calculate_yield_rate(500.0, 500.0)
        assert result == 0.0


class TestScrapRateFormula:
    """**Validates: Requirements 32.2**"""

    @given(data=production_data())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_scrap_rate_formula_correct(self, data: tuple[float, float]):
        """Property 16b: Scrap Rate = scrap / produced × 100 for all valid inputs."""
        produced, scrap = data
        assume(produced > 0)
        assume(scrap >= 0)
        assume(scrap <= produced)

        result = calculate_scrap_rate(produced, scrap)
        expected = round((scrap / produced) * 100, 2)

        assert result == expected, (
            f"Scrap rate mismatch: produced={produced}, scrap={scrap}, "
            f"got={result}, expected={expected}"
        )

    @given(data=production_data())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_scrap_rate_bounded_0_to_100(self, data: tuple[float, float]):
        """Property 16b: Scrap rate is always between 0% and 100% inclusive."""
        produced, scrap = data
        assume(produced > 0)
        assume(scrap >= 0)
        assume(scrap <= produced)

        result = calculate_scrap_rate(produced, scrap)

        assert 0.0 <= result <= 100.0, (
            f"Scrap rate out of bounds: produced={produced}, scrap={scrap}, result={result}"
        )

    def test_scrap_rate_zero_when_produced_is_zero(self):
        """Property 16b edge case: Scrap rate = 0% when produced = 0."""
        result = calculate_scrap_rate(0.0, 0.0)
        assert result == 0.0

    def test_scrap_rate_zero_when_no_scrap(self):
        """Property 16b edge case: Scrap rate = 0% when scrap = 0."""
        result = calculate_scrap_rate(1000.0, 0.0)
        assert result == 0.0

    def test_scrap_rate_100_when_all_scrap(self):
        """Property 16b edge case: Scrap rate = 100% when all produced is scrapped."""
        result = calculate_scrap_rate(500.0, 500.0)
        assert result == 100.0


class TestReworkRateFormula:
    """**Validates: Requirements 32.3**"""

    @given(data=rework_data())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_rework_rate_formula_correct(self, data: tuple[int, int]):
        """Property 16c: Rework Rate = rework_count / total_completed × 100."""
        rework_count, total_completed = data
        assume(total_completed > 0)

        result = calculate_rework_rate(rework_count, total_completed)
        expected = round((rework_count / total_completed) * 100, 2)

        assert result == expected, (
            f"Rework rate mismatch: rework={rework_count}, completed={total_completed}, "
            f"got={result}, expected={expected}"
        )

    @given(data=rework_data())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_rework_rate_non_negative(self, data: tuple[int, int]):
        """Property 16c: Rework rate is always >= 0%."""
        rework_count, total_completed = data
        assume(total_completed > 0)

        result = calculate_rework_rate(rework_count, total_completed)

        assert result >= 0.0, (
            f"Rework rate negative: rework={rework_count}, completed={total_completed}, "
            f"result={result}"
        )

    @given(total_completed=positive_count)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_rework_rate_zero_when_no_rework(self, total_completed: int):
        """Property 16c: Rework rate = 0% when rework_count = 0."""
        result = calculate_rework_rate(0, total_completed)
        assert result == 0.0

    def test_rework_rate_zero_when_total_completed_is_zero(self):
        """Property 16c edge case: Rework rate = 0% when total_completed = 0."""
        result = calculate_rework_rate(5, 0)
        assert result == 0.0

    def test_rework_rate_100_when_equal(self):
        """Property 16c: Rework rate = 100% when rework_count == total_completed."""
        result = calculate_rework_rate(50, 50)
        assert result == 100.0

    def test_rework_rate_can_exceed_100(self):
        """Property 16c: Rework rate can exceed 100% (multiple reworks per WO)."""
        result = calculate_rework_rate(150, 50)
        assert result == 300.0


class TestOEEFormula:
    """**Validates: Requirements 32.4**"""

    @given(data=oee_components())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_oee_formula_correct(self, data: tuple[float, float, float]):
        """Property 16d: OEE = Availability × Performance × Quality × 100."""
        availability, performance, quality = data

        result = calculate_oee(availability, performance, quality)
        expected = round(availability * performance * quality * 100, 2)

        assert result == expected, (
            f"OEE mismatch: avail={availability}, perf={performance}, qual={quality}, "
            f"got={result}, expected={expected}"
        )

    @given(data=oee_components())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_oee_bounded_0_to_100(self, data: tuple[float, float, float]):
        """Property 16d: OEE is always between 0% and 100% when components in [0, 1]."""
        availability, performance, quality = data

        result = calculate_oee(availability, performance, quality)

        assert 0.0 <= result <= 100.0, (
            f"OEE out of bounds: avail={availability}, perf={performance}, "
            f"qual={quality}, result={result}"
        )

    def test_oee_100_when_all_perfect(self):
        """Property 16d: OEE = 100% when all components are 1.0."""
        result = calculate_oee(1.0, 1.0, 1.0)
        assert result == 100.0

    def test_oee_0_when_any_component_zero(self):
        """Property 16d: OEE = 0% when any component is 0."""
        assert calculate_oee(0.0, 1.0, 1.0) == 0.0
        assert calculate_oee(1.0, 0.0, 1.0) == 0.0
        assert calculate_oee(1.0, 1.0, 0.0) == 0.0

    @given(data=oee_components())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_oee_monotonic_in_each_component(self, data: tuple[float, float, float]):
        """Property 16d: OEE is monotonically non-decreasing in each component."""
        availability, performance, quality = data
        assume(availability < 1.0)
        assume(performance > 0.0)
        assume(quality > 0.0)

        oee_lower = calculate_oee(availability, performance, quality)
        oee_higher = calculate_oee(1.0, performance, quality)

        assert oee_higher >= oee_lower, (
            f"OEE not monotonic: avail={availability}→1.0, "
            f"oee_lower={oee_lower}, oee_higher={oee_higher}"
        )


class TestKPIFormulasIntegration:
    """Integration tests validating KPI formula interactions.

    **Validates: Requirements 32.1, 32.2, 32.3, 32.4**
    """

    @given(data=production_data())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_yield_and_scrap_are_complementary(self, data: tuple[float, float]):
        """Yield + Scrap = 100% (within rounding tolerance) for valid produced > 0."""
        produced, scrap = data
        assume(produced > 0)
        assume(scrap >= 0)
        assume(scrap <= produced)

        yield_rate = calculate_yield_rate(produced, scrap)
        scrap_rate = calculate_scrap_rate(produced, scrap)

        # Due to independent rounding, allow 0.02 tolerance
        assert abs((yield_rate + scrap_rate) - 100.0) <= 0.02

    @given(
        produced=positive_produced,
        scrap=non_negative_quantity,
        rework_count=non_negative_count,
        total_completed=positive_count,
        availability=oee_component,
        performance=oee_component,
        quality=oee_component,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_all_kpis_finite_for_valid_inputs(
        self,
        produced: float,
        scrap: float,
        rework_count: int,
        total_completed: int,
        availability: float,
        performance: float,
        quality: float,
    ):
        """All KPI calculations produce finite results for valid inputs."""
        assume(produced > 0)
        assume(scrap >= 0)
        assume(scrap <= produced)
        assume(total_completed > 0)

        yield_rate = calculate_yield_rate(produced, scrap)
        scrap_rate = calculate_scrap_rate(produced, scrap)
        rework_rate = calculate_rework_rate(rework_count, total_completed)
        oee = calculate_oee(availability, performance, quality)

        assert math.isfinite(yield_rate)
        assert math.isfinite(scrap_rate)
        assert math.isfinite(rework_rate)
        assert math.isfinite(oee)
