"""API test fixtures for BOM module."""

import pytest


@pytest.fixture
async def auth_headers(token_headers):
    """API test authorization fixture."""
    return token_headers
