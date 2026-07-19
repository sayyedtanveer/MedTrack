"""Unit test fixtures for product module."""

import pytest
from backend.tests.conftest_factories import (
    create_product_template_payload,
    create_product_variant_payload,
)


@pytest.fixture
def product_template_payload():
    """Fixture for product template creation."""
    return create_product_template_payload()


@pytest.fixture
def product_variant_payload(product_template_payload):
    """Fixture for product variant creation."""
    return create_product_variant_payload(
        template_id=product_template_payload["id"]
        if "id" in product_template_payload
        else str(__import__("uuid").uuid4())
    )
