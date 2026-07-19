"""Unit tests for opening_stock validation in material onboarding."""
import pytest

from backend.app.interfaces.api.v1.routes.material_onboarding import _validate_row


def _base_data(**overrides):
    """Return a minimal valid row data dict with optional overrides."""
    data = {
        "material_name": "Test Material",
        "item_code": "MAT-001",
        "uom": "KG",
        "material_category": "Raw Materials",
    }
    data.update(overrides)
    return data


class TestOpeningStockValidation:
    """Tests for opening_stock column validation in _validate_row."""

    def test_valid_opening_stock_numeric(self):
        data = _base_data(opening_stock="100")
        _cls, _status, issues, _pc = _validate_row(data, 2, {})
        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert opening_issues == []

    def test_valid_opening_stock_decimal(self):
        data = _base_data(opening_stock="50.5")
        _cls, _status, issues, _pc = _validate_row(data, 2, {})
        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert opening_issues == []

    def test_valid_opening_stock_zero(self):
        data = _base_data(opening_stock="0")
        _cls, _status, issues, _pc = _validate_row(data, 2, {})
        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert opening_issues == []

    def test_valid_opening_stock_max_value(self):
        data = _base_data(opening_stock="999999999.99")
        _cls, _status, issues, _pc = _validate_row(data, 2, {})
        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert opening_issues == []

    def test_empty_opening_stock_no_error(self):
        data = _base_data(opening_stock="")
        _cls, _status, issues, _pc = _validate_row(data, 2, {})
        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert opening_issues == []

    def test_missing_opening_stock_no_error(self):
        data = _base_data()
        # No opening_stock key at all
        _cls, _status, issues, _pc = _validate_row(data, 2, {})
        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert opening_issues == []

    def test_non_numeric_opening_stock_error(self):
        data = _base_data(opening_stock="abc")
        _cls, _status, issues, _pc = _validate_row(data, 2, {})
        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert len(opening_issues) == 1
        assert opening_issues[0]["severity"] == "error"
        assert "non-negative" in opening_issues[0]["message"]

    def test_negative_opening_stock_error(self):
        data = _base_data(opening_stock="-5")
        _cls, _status, issues, _pc = _validate_row(data, 2, {})
        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert len(opening_issues) == 1
        assert opening_issues[0]["severity"] == "error"
        assert "non-negative" in opening_issues[0]["message"]

    def test_exceeds_max_value_error(self):
        data = _base_data(opening_stock="1000000000")
        _cls, _status, issues, _pc = _validate_row(data, 2, {})
        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert len(opening_issues) == 1
        assert opening_issues[0]["severity"] == "error"
        assert "999,999,999.99" in opening_issues[0]["message"]

    def test_exceeds_max_value_just_above_boundary(self):
        data = _base_data(opening_stock="999999999.999")
        _cls, _status, issues, _pc = _validate_row(data, 2, {})
        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert len(opening_issues) == 1
        assert opening_issues[0]["severity"] == "error"
        assert "999,999,999.99" in opening_issues[0]["message"]

    def test_opening_stock_with_commas(self):
        """Commas in numeric values should be handled (stripped)."""
        data = _base_data(opening_stock="1,000")
        _cls, _status, issues, _pc = _validate_row(data, 2, {})
        opening_issues = [i for i in issues if i["field"] == "opening_stock"]
        assert opening_issues == []

    def test_row_classified_as_error_when_opening_stock_invalid(self):
        """Row should be in error/skip state when opening_stock is invalid."""
        data = _base_data(opening_stock="invalid")
        _cls, status, issues, _pc = _validate_row(data, 2, {})
        assert status == "error"
        assert _cls == "skip"
