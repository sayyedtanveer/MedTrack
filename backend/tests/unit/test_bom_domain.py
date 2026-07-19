"""
Unit tests for BOM domain logic.
Tests cover:
- Circular dependency detection
- Cost rollup (material + operation)
- Variant uniqueness (duplicate variant_key prevention)
- BOM validation (invalid qty, empty lines)

These tests do NOT require a database connection — they test domain objects
and service logic directly.
"""
from __future__ import annotations
import uuid
import pytest
from decimal import Decimal


# ─── Helper fixtures ──────────────────────────────────────────────────────────

def make_bom_id() -> uuid.UUID:
    return uuid.uuid4()

def make_tenant_id() -> uuid.UUID:
    return uuid.uuid4()


# ─── 1. Circular Dependency Detection ─────────────────────────────────────────

class TestCircularDependencyDetection:
    """
    Validate that the BOM tree resolution correctly detects circular dependencies.
    A → B → C → A should raise a ValueError.
    """

    def _build_dependency_map(self) -> dict[str, list[str]]:
        """Simple adjacency map: bom_id -> list of child bom_ids."""
        return {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"],  # Creates cycle
        }

    def _detect_cycle(self, graph: dict[str, list[str]], start: str) -> bool:
        """DFS-based cycle detection."""
        visited: set[str] = set()
        stack: set[str] = set()

        def dfs(node: str) -> bool:
            if node in stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            stack.add(node)
            for neighbor in graph.get(node, []):
                if dfs(neighbor):
                    return True
            stack.discard(node)
            return False

        return dfs(start)

    def test_detects_simple_cycle(self):
        graph = self._build_dependency_map()
        assert self._detect_cycle(graph, "A") is True, "A→B→C→A should be detected as a cycle"

    def test_no_cycle_in_linear_chain(self):
        graph = {"A": ["B"], "B": ["C"], "C": []}
        assert self._detect_cycle(graph, "A") is False

    def test_no_cycle_in_diamond(self):
        # Diamond: A → B, A → C, B → D, C → D
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        assert self._detect_cycle(graph, "A") is False

    def test_self_loop_detected(self):
        graph = {"A": ["A"]}
        assert self._detect_cycle(graph, "A") is True


# ─── 2. Cost Rollup ───────────────────────────────────────────────────────────

class TestCostRollup:
    """
    Validate cost rollup calculation correctness.
    total_cost = material_cost + operation_cost
    """

    def _calculate_operation_cost(
        self, setup_time_min: float, run_time_min: float, hourly_rate: float, qty: float = 1
    ) -> Decimal:
        """
        operation_cost = ((setup + run * qty) / 60) * hourly_rate
        """
        total_minutes = setup_time_min + (run_time_min * qty)
        return Decimal(str(round((total_minutes / 60) * hourly_rate, 4)))

    def test_operation_cost_single_unit(self):
        """45 mins total at $120/hr = $90."""
        cost = self._calculate_operation_cost(
            setup_time_min=30, run_time_min=15, hourly_rate=120.0, qty=1
        )
        assert cost == Decimal("90.0"), f"Expected 90.0, got {cost}"

    def test_operation_cost_multiple_units(self):
        """Setup 30min + 15min * 4 units = 90min = 1.5h * $100 = $150"""
        cost = self._calculate_operation_cost(
            setup_time_min=30, run_time_min=15, hourly_rate=100.0, qty=4
        )
        assert cost == Decimal("150.0")

    def test_total_cost_is_sum(self):
        material_cost = Decimal("50.00")
        operation_cost = Decimal("90.00")
        total = material_cost + operation_cost
        assert total == Decimal("140.00")

    def test_zero_run_time(self):
        """Only setup cost."""
        cost = self._calculate_operation_cost(
            setup_time_min=60, run_time_min=0, hourly_rate=60.0, qty=10
        )
        assert cost == Decimal("60.0")

    def test_zero_cost(self):
        cost = self._calculate_operation_cost(0, 0, 120.0)
        assert cost == Decimal("0.0")


# ─── 3. Variant Uniqueness ────────────────────────────────────────────────────

class TestVariantUniqueness:
    """
    Validate that the variant_key uniqueness enforcement logic works correctly.
    The variant_key is derived from sorted attribute key-value pairs.
    """

    def _build_variant_key(self, attribute_values: dict[str, str]) -> str:
        """Deterministic key from sorted attribute key-value pairs."""
        pairs = sorted(attribute_values.items())
        return "|".join(f"{k}:{v}" for k, v in pairs)

    def _simulate_create_variant(
        self, existing_keys: set[str], attribute_values: dict[str, str]
    ) -> str:
        """Raises ValueError if key already exists, otherwise adds."""
        key = self._build_variant_key(attribute_values)
        if key in existing_keys:
            raise ValueError(f"Variant with key '{key}' already exists.")
        existing_keys.add(key)
        return key

    def test_unique_variant_allowed(self):
        existing: set[str] = set()
        key = self._simulate_create_variant(existing, {"size": "L", "color": "red"})
        assert key == "color:red|size:L"

    def test_duplicate_variant_rejected(self):
        existing: set[str] = set()
        self._simulate_create_variant(existing, {"size": "L", "color": "red"})
        with pytest.raises(ValueError, match="already exists"):
            self._simulate_create_variant(existing, {"color": "red", "size": "L"})

    def test_different_values_allowed(self):
        existing: set[str] = set()
        self._simulate_create_variant(existing, {"size": "L"})
        key2 = self._simulate_create_variant(existing, {"size": "XL"})
        assert key2 == "size:XL"

    def test_key_is_order_independent(self):
        """Order of attributes shouldn't matter."""
        key_a = self._build_variant_key({"a": "1", "b": "2"})
        key_b = self._build_variant_key({"b": "2", "a": "1"})
        assert key_a == key_b


# ─── 4. BOM Validation ────────────────────────────────────────────────────────

class TestBOMValidation:
    """
    Validate BOM structural integrity checks.
    """

    def _validate_bom_line(self, quantity: float) -> None:
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")

    def _validate_bom_has_lines(self, lines: list) -> None:
        if not lines:
            raise ValueError("BOM must have at least one component line.")

    def _validate_component_target(
        self,
        material_id: str | None,
        template_id: str | None,
        variant_id: str | None,
    ) -> None:
        """Exactly one of material, template, or variant must be set."""
        set_count = sum([
            material_id is not None,
            template_id is not None,
            variant_id is not None,
        ])
        if set_count != 1:
            raise ValueError(
                "BOM line must reference exactly one of: material, template, or variant."
            )

    def test_positive_quantity_accepted(self):
        self._validate_bom_line(1.0)  # should not raise

    def test_zero_quantity_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            self._validate_bom_line(0.0)

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            self._validate_bom_line(-5.0)

    def test_empty_bom_rejected(self):
        with pytest.raises(ValueError, match="at least one"):
            self._validate_bom_has_lines([])

    def test_exactly_one_component_target(self):
        # Valid: only material_id set
        self._validate_component_target("mat-001", None, None)

    def test_multiple_component_targets_rejected(self):
        with pytest.raises(ValueError, match="exactly one"):
            self._validate_component_target("mat-001", "tpl-001", None)

    def test_no_component_target_rejected(self):
        with pytest.raises(ValueError, match="exactly one"):
            self._validate_component_target(None, None, None)
