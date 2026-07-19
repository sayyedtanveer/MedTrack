"""Unit test fixtures for BOM module."""

import pytest
from uuid import uuid4
from backend.tests.conftest_factories import (
    create_bom_payload,
    create_bom_line_payload,
    create_bom_with_lines_payload,
)


@pytest.fixture
def sample_bom_product_id():
    """Fixture for a test product ID used in BOM tests."""
    return str(uuid4())


@pytest.fixture
def bom_payload(sample_bom_product_id):
    """Fixture for BOM creation payload."""
    return create_bom_payload(product_id=sample_bom_product_id)


@pytest.fixture
def bom_with_lines_payload(sample_bom_product_id):
    """Fixture for BOM with line items."""
    return create_bom_with_lines_payload(
        product_id=sample_bom_product_id,
        num_lines=3,
    )


@pytest.fixture
def bom_line_payload():
    """Fixture for single BOM line item."""
    return create_bom_line_payload(quantity=2.0)
