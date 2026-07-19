"""Unit test fixtures for inventory module."""

import pytest
from backend.tests.conftest_factories import (
    create_material_payload,
    create_stock_adjustment_payload,
    create_batch_payload,
)


@pytest.fixture
def material_payload():
    """Fixture for material creation payload."""
    return create_material_payload()


@pytest.fixture
def stock_adjustment_payload(material_payload):
    """Fixture for stock adjustment payload."""
    # Extract material_id if it exists in the fixture, otherwise use a placeholder
    material_id = material_payload.get("id", "test-material-id")
    return create_stock_adjustment_payload(
        material_id=material_id,
        quantity_change=10.0,
    )


@pytest.fixture
def batch_payload(material_payload):
    """Fixture for batch/lot payload."""
    material_id = material_payload.get("id", "test-material-id")
    return create_batch_payload(material_id=material_id)
