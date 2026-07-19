"""
Pytest configuration and shared fixtures for MedTrack test suite.
Provides async client, authentication, database sessions, and test data.
"""

import os
import sys

# Ensure repository root is on sys.path so tests can import the `backend` package.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Map PostgreSQL-specific JSONB type to SQLAlchemy generic JSON for tests
# so modules that import JSONB can still be used with SQLite in-memory DB.
try:
    from sqlalchemy import JSON as SA_JSON
    from sqlalchemy.dialects import postgresql
    postgresql.JSONB = SA_JSON
except Exception:
    pass


import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Generator, cast

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.config import settings
from backend.app.main import app
from backend.app.infrastructure.container import Container
from backend.app.infrastructure.context.request_context import RequestContext
from backend.app.infrastructure.persistence.database import Base
from backend.app.infrastructure.security.jwt_handler import JWTHandler
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher
from backend.app.infrastructure.audit.audit_service import AuditService
from backend.app.infrastructure.logging.error_logger import ErrorLogger
from backend.app.infrastructure.logging.repository import ErrorLogRepository


password_hasher = BcryptPasswordHasher()
jwt_handler = JWTHandler(
    secret_key=settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
    expiry_minutes=settings.jwt_expiry_minutes,
)


# ───────────────────────────────────────────────────────────────────────────────
# Test Database Configuration
# ───────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine():
    """Create an async SQLAlchemy engine for testing using SQLite in-memory database."""
    test_database_url = "sqlite+aiosqlite:///:memory:"
    
    engine = create_async_engine(
        test_database_url,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Allow SQLite to compile models that use PostgreSQL-specific types (e.g. JSONB)
    # by mapping them to generic SQLAlchemy types for testing.
    from sqlalchemy import JSON as SA_JSON
    from sqlalchemy.dialects import postgresql
    postgresql.JSONB = SA_JSON

    # Ensure clean schema: drop any existing tables then create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with AsyncSession(test_db_engine, expire_on_commit=False) as session:
        yield session
        # Cleanup after each test
        await session.rollback()


# Backward-compatible alias:
# Some e2e tests expect a fixture named `session`.
@pytest.fixture
async def session(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Alias for db_session (backward compatibility)."""
    yield db_session


@pytest.fixture(scope="session")
def test_container(test_db_engine) -> Generator[Container, None, None]:
    """Build a DI container for tests using the SQLite in-memory database."""
    session_factory = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    container = Container.create(settings)
    container.db_engine = test_db_engine
    container.session_factory = session_factory
    container.audit_service = AuditService(session_factory=session_factory)
    container.error_log_repository = ErrorLogRepository(session_factory=session_factory)
    container.error_logger = ErrorLogger(session_factory=session_factory)
    yield container


# ───────────────────────────────────────────────────────────────────────────────
# Test Tenant & User Fixtures
# ───────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def test_tenant_id() -> uuid.UUID:
    """Return a fixed test tenant ID."""
    return uuid.UUID("b5ef68c4-18be-4fa6-a439-a23c34877550")


@pytest.fixture
def test_user_id() -> uuid.UUID:
    """Return a fixed test user ID."""
    return uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.fixture
def test_user_email() -> str:
    """Return test user email."""
    return "test@medtrack-demo.com"


@pytest.fixture
def test_user_password() -> str:
    """Return test user password."""
    return "TestPassword123!"


@pytest.fixture
def test_user_data(test_user_id: uuid.UUID, test_user_email: str, test_user_password: str) -> dict:
    """Return test user data with hashed password."""
    return {
        "id": test_user_id,
        "email": test_user_email,
        "password_hash": password_hasher.hash(test_user_password),
        "role": "admin",
        "is_active": True,
        "is_superuser": False,
    }


# ───────────────────────────────────────────────────────────────────────────────
# Authentication Fixtures
# ───────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def token_headers(test_user_id: uuid.UUID, test_tenant_id: uuid.UUID) -> dict:
    """Return authorization headers with valid JWT token."""
    access_token = jwt_handler.create_access_token(
        user_id=str(test_user_id),
        tenant_id=str(test_tenant_id),
        role="admin",
    )
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Tenant-ID": str(test_tenant_id),
    }


@pytest.fixture
def tenant_context(test_tenant_id: uuid.UUID, test_user_id: uuid.UUID) -> RequestContext:
    """Return a request context object for the test tenant/user."""
    return RequestContext(
        correlation_id=None,
        tenant_id=str(test_tenant_id),
        user_id=str(test_user_id),
        ip_address=None,
    )


# ───────────────────────────────────────────────────────────────────────────────
# API Client Fixtures
# ───────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sync_client() -> TestClient:
    """Provide a synchronous TestClient (for requests-based testing)."""
    return TestClient(app)


@pytest.fixture
async def async_client(test_container: Container, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP client for testing.
    Ensures the app uses the SQLite in-memory test container.
    """
    monkeypatch.setattr(
        "backend.app.main.Container.create",
        classmethod(lambda cls, settings: test_container),
    )
    app.state.container = test_container
    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ───────────────────────────────────────────────────────────────────────────────
# Authenticated API Fixtures
# ───────────────────────────────────────────────────────────────────────────────

@pytest.fixture
async def authenticated_async_client(
    async_client: AsyncClient,
    token_headers: dict,
) -> AsyncClient:
    """Provide an async client with authorization headers pre-configured."""
    async_client.headers.update(token_headers)
    return async_client


@pytest.fixture
def authenticated_sync_client(
    sync_client: TestClient,
    token_headers: dict,
) -> TestClient:
    """Provide a sync client with authorization headers pre-configured."""
    sync_client.headers.update(token_headers)
    return sync_client


# ───────────────────────────────────────────────────────────────────────────────
# Test Data Fixtures
# ───────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_product_template() -> dict:
    """Return a sample product template for testing."""
    return {
        "name": "Test Product Template",
        "code": "TEST-001",
        "description": "A test product template",
        "attributes": [
            {
                "name": "Color",
                "data_type": "text",
                "is_required": True,
                "allowed_values": ["Red", "Blue", "Green"],
            },
            {
                "name": "Size",
                "data_type": "text",
                "is_required": True,
                "allowed_values": ["S", "M", "L", "XL"],
            },
        ],
    }


@pytest.fixture
def sample_variant_data() -> dict:
    """Return sample variant data."""
    return {
        "variant_key": "TEST-001-RED-M",
        "sku": "SKU-001-RED-M",
        "attributes": {
            "Color": "Red",
            "Size": "M",
        },
        "attributes_text": "Color: Red, Size: M",
    }


@pytest.fixture
def sample_bom_create_payload() -> dict:
    """Return a sample BOM creation payload."""
    return {
        "version": "v1.0",
        "valid_from": datetime.utcnow().isoformat(),
        "template_id": str(uuid.uuid4()),
        "lines": [],
    }


@pytest.fixture
def sample_operation_data() -> dict:
    """Return sample operation data."""
    return {
        "code": "OP-001",
        "name": "Test Operation",
        "description": "A test operation",
        "process_type": "assembly",
        "estimated_time_hours": 2.5,
        "estimated_labor_cost": 50.00,
    }


@pytest.fixture
def sample_material_data() -> dict:
    """Return sample material data."""
    return {
        "code": "MAT-001",
        "name": "Test Material",
        "description": "A test material",
        "unit_of_measure": "KG",
        "unit_cost": 100.00,
    }


# ───────────────────────────────────────────────────────────────────────────────
# Pytest Configuration
# ───────────────────────────────────────────────────────────────────────────────

def pytest_collection_modifyitems(items):
    """Mark all tests that use async fixtures with asyncio marker."""
    for item in items:
        if "async_client" in item.fixturenames or "db_session" in item.fixturenames:
            item.add_marker(pytest.mark.asyncio)
