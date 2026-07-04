"""
E2E test suite root conftest — re-exports all shared fixtures.

Fixtures defined in tests/e2e/fixtures/conftest.py are discovered here
so that every phase subdirectory (phase_0_business_config/, phase_1_company_setup/,
etc.) automatically has access to them without extra imports.
"""
# Re-export all shared fixtures by importing the fixtures module.
# pytest collects conftest.py files from the rootdir down, so this file
# is the canonical conftest for the entire tests/e2e/ tree.
from tests.e2e.fixtures.conftest import (  # noqa: F401
    event_loop,
    e2e_db_engine,
    e2e_session_factory,
    e2e_db_session,
    test_tenant,
    admin_user,
    _make_jwt,
    make_token_headers,
    seed_number_series,
    async_client,
    authenticated_client,
    NUMBER_SERIES_ENTITY_TYPES,
    _DEFAULT_NUMBER_SERIES,
)
