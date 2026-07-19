"""
Property tests for bulk onboarding opening stock classification and validation.

**Validates: Requirements 4.2, 4.3, 4.4**

These tests validate two correctness properties:
  - Property 5: Bulk onboarding opening stock classification
  - Property 12: Bulk upload non-numeric opening stock validation
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    decimals,
    text,
    floats,
    integers,
    one_of,
    just,
    sampled_from,
    composite,
)

from backend.app.interfaces.api.v1.routes.material_onboarding import _validate_row


# ─── Strategies ──────────────────────────────────────────────────────────────

# Valid positive opening stock values as strings (what would appear in CSV)
positive_opening_stock_strings = decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
).map(str)

# Non-negative opening stock (includes zero)
non_negative_opening_stock_strings = decimals(
    min_value=Decimal("0"),
    max_value=Decimal("999999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
).map(str)

# Non-numeric strings that should fail validation
non_numeric_strings = text(
    min_size=1, max_size=20,
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+=[]{}|;:'\",<>?/\\"
).filter(lambda s: s.strip() != "" and not _is_numeric(s))

# Negative numeric strings
negative_opening_stock_strings = decimals(
    min_value=Decimal("-999999"),
    max_value=Decimal("-0.01"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
).map(str)

# Material names for row data
material_names = text(
    min_size=3, max_size=50,
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ",
).filter(lambda s: s.strip() and len(s.strip()) >= 3)

# Item codes for row data
item_codes = text(
    min_size=3, max_size=20,
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",
).filter(lambda s: s.strip() and len(s.strip()) >= 3)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _is_numeric(s: str) -> bool:
    """Check if string is numeric (after stripping commas)."""
    try:
        float(s.strip().replace(",", ""))
        return True
    except (ValueError, TypeError):
        return False


def _base_data(name: str = "Test Material", code: str = "MAT-001", **overrides) -> dict:
    """Return a minimal valid row data dict with optional overrides."""
    data = {
        "material_name": name,
        "item_code": code,
        "uom": "KG",
        "material_category": "Raw Materials",
    }
    data.update(overrides)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# Property 5: Bulk onboarding opening stock classification
#
# For rows classified as "new" with positive opening_stock, a Stock In
# transaction with reference_type="onboarding_opening_balance" is created.
# For rows classified as "update", opening_stock is ignored.
# ─────────────────────────────────────────────────────────────────────────────


class TestBulkOnboardingOpeningStockClassification:
    """**Validates: Requirements 4.2, 4.3**"""

    @given(
        opening_stock=positive_opening_stock_strings,
        name=material_names,
        code=item_codes,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_new_row_with_positive_opening_stock_passes_validation(
        self,
        opening_stock: str,
        name: str,
        code: str,
    ):
        """Property 5: For any row classified as 'new' with positive opening_stock,
        the row passes validation (no opening_stock errors) and is classified as 'new',
        meaning a Stock In transaction with reference_type='onboarding_opening_balance'
        would be created during execution."""
        data = _base_data(name=name, code=code, opening_stock=opening_stock)
        # Empty existing_codes dict means the row will be classified as "new"
        classification, status, issues, _pc = _validate_row(data, 1, {})

        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert opening_issues == [], f"Unexpected opening_stock issues: {opening_issues}"
        assert classification == "new"
        assert status == "ready"

    @given(
        opening_stock=positive_opening_stock_strings,
        name=material_names,
        code=item_codes,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_update_row_classification_ignores_opening_stock(
        self,
        opening_stock: str,
        name: str,
        code: str,
    ):
        """Property 5: For any row classified as 'update' (existing code found),
        opening_stock is accepted without error, but classification is 'update',
        meaning opening_stock will be ignored during execution and stock remains unchanged."""
        data = _base_data(name=name, code=code, opening_stock=opening_stock)
        # Provide existing_codes so the row matches and is classified as "update"
        existing_codes = {code.upper(): {"item_code": code, "name": name}}
        classification, status, issues, _pc = _validate_row(data, 1, existing_codes)

        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert opening_issues == [], f"Unexpected opening_stock issues: {opening_issues}"
        assert classification == "update"
        assert status == "ready"

    @given(
        opening_stock=positive_opening_stock_strings,
        name=material_names,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_new_row_opening_stock_value_preserved_in_data(
        self,
        opening_stock: str,
        name: str,
    ):
        """Property 5: The opening_stock value remains in the row data dict
        after validation, ensuring it's available during execute_session for
        creating the onboarding_opening_balance transaction."""
        data = _base_data(name=name, opening_stock=opening_stock)
        _validate_row(data, 1, {})
        # After validation, data still has opening_stock — it's not stripped
        assert data["opening_stock"] == opening_stock


# ─────────────────────────────────────────────────────────────────────────────
# Property 12: Bulk upload non-numeric opening stock validation
#
# For rows with non-numeric opening_stock, a validation error is reported.
# ─────────────────────────────────────────────────────────────────────────────


class TestBulkUploadNonNumericOpeningStockValidation:
    """**Validates: Requirement 4.4**"""

    @given(
        non_numeric_value=non_numeric_strings,
        name=material_names,
        code=item_codes,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_non_numeric_opening_stock_produces_validation_error(
        self,
        non_numeric_value: str,
        name: str,
        code: str,
    ):
        """Property 12: For any row containing a non-numeric value in the
        opening_stock column, the system reports a validation error for that
        specific row during the preview/validation step."""
        data = _base_data(name=name, code=code, opening_stock=non_numeric_value)
        classification, status, issues, _pc = _validate_row(data, 1, {})

        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert len(opening_issues) == 1, (
            f"Expected exactly 1 opening_stock error for value '{non_numeric_value}', "
            f"got {len(opening_issues)}: {opening_issues}"
        )
        assert opening_issues[0]["severity"] == "error"
        assert "non-negative" in opening_issues[0]["message"]
        # Row should be classified as error/skip
        assert status == "error"
        assert classification == "skip"

    @given(
        negative_value=negative_opening_stock_strings,
        name=material_names,
        code=item_codes,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_negative_opening_stock_produces_validation_error(
        self,
        negative_value: str,
        name: str,
        code: str,
    ):
        """Property 12: For any row containing a negative numeric value in the
        opening_stock column, the system reports a validation error indicating
        opening stock must be a non-negative number."""
        data = _base_data(name=name, code=code, opening_stock=negative_value)
        classification, status, issues, _pc = _validate_row(data, 1, {})

        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert len(opening_issues) == 1, (
            f"Expected exactly 1 opening_stock error for negative value '{negative_value}', "
            f"got {len(opening_issues)}: {opening_issues}"
        )
        assert opening_issues[0]["severity"] == "error"
        assert "non-negative" in opening_issues[0]["message"]
        assert status == "error"
        assert classification == "skip"

    @given(
        valid_value=non_negative_opening_stock_strings,
        name=material_names,
        code=item_codes,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_valid_numeric_opening_stock_produces_no_validation_error(
        self,
        valid_value: str,
        name: str,
        code: str,
    ):
        """Property 12 (inverse): For any row containing a valid non-negative
        numeric value in opening_stock, no validation error is produced for
        that field."""
        data = _base_data(name=name, code=code, opening_stock=valid_value)
        _cls, _status, issues, _pc = _validate_row(data, 1, {})

        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert opening_issues == [], (
            f"Unexpected opening_stock error for valid value '{valid_value}': {opening_issues}"
        )
