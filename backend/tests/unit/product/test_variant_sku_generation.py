"""
Phase 4 unit tests — Variant SKU generation integrity.

Tests:
  1. Template with no attributes → clean SKU (no trailing hyphen)
  2. Template with one attribute → correct suffix
  3. Template with multiple attributes → correct joined suffix
  4. Deterministic: same inputs produce same code
  5. No trailing hyphen for any input
  6. Zero-attribute variant produces distinct code from template
  7. _build_variant_name works for no-attribute template
  8. _build_variant_key works for no-attribute template (empty string)
"""

import pytest
from backend.app.domain.product.entities.item_variant import (
    _build_variant_code,
    _build_variant_name,
    _build_variant_key,
)


class TestBuildVariantCode:
    """Unit tests for _build_variant_code()."""

    def test_no_attributes_no_trailing_hyphen(self):
        """Zero-attribute template: code must not end with '-'."""
        code = _build_variant_code("FG-MT-0006", [], {})
        assert not code.endswith("-"), f"Code ends with hyphen: {code!r}"

    def test_no_attributes_distinct_from_template(self):
        """Zero-attribute variant code must differ from parent template code."""
        template_code = "FG-MT-0006"
        code = _build_variant_code(template_code, [], {})
        assert code != template_code.upper(), (
            f"Variant code {code!r} collides with template code {template_code.upper()!r}"
        )

    def test_no_attributes_produces_default_suffix(self):
        """Zero-attribute template produces code with -DEFAULT suffix."""
        code = _build_variant_code("FG-MT-0006", [], {})
        assert code == "FG-MT-0006-DEFAULT", f"Got: {code!r}"

    def test_no_attributes_uppercase_template(self):
        """Template code is uppercased regardless of input casing."""
        code = _build_variant_code("fg-mt-0006", [], {})
        assert code == "FG-MT-0006-DEFAULT"

    def test_one_attribute_produces_correct_suffix(self):
        """Single-attribute template produces code with one value appended."""
        code = _build_variant_code("PIPE", ["SIZE"], {"SIZE": "10MM"})
        assert code == "PIPE-10MM"

    def test_multiple_attributes_joined_correctly(self):
        """Multi-attribute template joins values with hyphens."""
        code = _build_variant_code("TSHIRT", ["SIZE", "COLOR"], {"SIZE": "SMALL", "COLOR": "RED"})
        assert code == "TSHIRT-SMALL-RED"

    def test_attribute_values_uppercased(self):
        """Attribute values are uppercased in the generated code."""
        code = _build_variant_code("Widget", ["SIZE"], {"SIZE": "large"})
        assert code == "WIDGET-LARGE"

    def test_attribute_values_stripped(self):
        """Attribute values are stripped of whitespace."""
        code = _build_variant_code("PIPE", ["SIZE"], {"SIZE": "  10MM  "})
        assert code == "PIPE-10MM"

    def test_deterministic_same_inputs_same_code(self):
        """Same inputs always produce the same code."""
        args = ("FG-MT-0010", ["SIZE", "COLOR"], {"SIZE": "LARGE", "COLOR": "BLUE"})
        assert _build_variant_code(*args) == _build_variant_code(*args)

    def test_deterministic_no_attribute(self):
        """Zero-attribute case is also deterministic."""
        assert _build_variant_code("FG-MT-0001", [], {}) == _build_variant_code("FG-MT-0001", [], {})

    def test_no_trailing_hyphen_for_various_inputs(self):
        """No code should ever end with a hyphen."""
        cases = [
            ("FG-A", [], {}),
            ("FG-B", ["SIZE"], {"SIZE": "M"}),
            ("FG-C", ["SIZE", "COLOR"], {"SIZE": "L", "COLOR": "GREEN"}),
        ]
        for template_code, keys, values in cases:
            code = _build_variant_code(template_code, keys, values)
            assert not code.endswith("-"), f"Code {code!r} ends with hyphen"

    def test_code_has_no_double_hyphens(self):
        """Generated code should not have adjacent double hyphens."""
        code = _build_variant_code("FG-MT-0005", ["SIZE"], {"SIZE": "10MM"})
        assert "--" not in code, f"Code has double hyphens: {code!r}"


class TestBuildVariantName:
    """Unit tests for _build_variant_name()."""

    def test_no_attributes_name_matches_template(self):
        """Zero-attribute variant name equals the template name (no extra suffix)."""
        name = _build_variant_name("Steel Pipe", [], {})
        assert name == "Steel Pipe"

    def test_one_attribute_name(self):
        name = _build_variant_name("Steel Pipe", ["SIZE"], {"SIZE": "10mm"})
        assert name == "Steel Pipe - 10mm"

    def test_multiple_attributes_joined_with_slash(self):
        name = _build_variant_name("T-Shirt", ["SIZE", "COLOR"], {"SIZE": "Small", "COLOR": "Red"})
        assert name == "T-Shirt - Small / Red"


class TestBuildVariantKey:
    """Unit tests for _build_variant_key()."""

    def test_no_attributes_produces_empty_key(self):
        """Zero-attribute template produces an empty variant_key."""
        key = _build_variant_key([], {})
        assert key == ""

    def test_single_attribute_key(self):
        key = _build_variant_key(["SIZE"], {"SIZE": "LARGE"})
        assert key == "SIZE=LARGE"

    def test_multiple_attributes_key(self):
        key = _build_variant_key(["SIZE", "COLOR"], {"SIZE": "SMALL", "COLOR": "RED"})
        assert key == "SIZE=SMALL|COLOR=RED"

    def test_key_values_uppercased(self):
        key = _build_variant_key(["SIZE"], {"SIZE": "large"})
        assert key == "SIZE=LARGE"
