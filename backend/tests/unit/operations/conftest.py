"""Unit test fixtures for operations module."""

import pytest
from backend.tests.conftest_factories import (
    create_operation_payload,
    create_workstation_payload,
)


@pytest.fixture
def operation_payload():
    """Fixture for operation creation payload."""
    return create_operation_payload()


@pytest.fixture
def workstation_payload():
    """Fixture for workstation creation payload."""
    return create_workstation_payload()
