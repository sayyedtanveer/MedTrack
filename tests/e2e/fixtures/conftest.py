"""
Shared pytest fixtures for MedTrack E2E integration tests.

Provides:
  - async_client      — httpx AsyncClient wired to the test FastAPI app via ASGI transport
  - test_tenant       — isolated TenantModel row created once per test session
  - admin_user        — UserModel row with role="admin" + JWT token helper
  - seed_number_series — seeds all 9 entity-type NumberSeriesConfig rows for the test tenant

All fixtures use the SQLite in-memory database already configured in
backend/tests/conftest.py.  This file merely extends those base fixtures with
the session-scoped tenant / user rows that the new E2E suites require.

Requirements: 0–41 (shared infrastructure for all Track-C integration tests)
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, cast

# ── path bootstrap ────────────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Patch PostgreSQL JSONB → generic JSON so SQLite can compile models.
try:
    from sqlalchemy import JSON as _SA_JSON
    from sqlalchemy.dialects import postgresql as _pg
    _pg.JSONB = _SA_JSON  # type: ignore[attr-defined]
except Exception:
    pass

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from backend.app.config import settings as app_settings
from backend.app.infrastructure.persistence.database import Base
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.infrastructure.persistence.models.number_series_models import (
    NumberSeriesConfigModel,
)
from backend.app.infrastructure.security.jwt_handler import JWTHandler
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher

# ── helpers ───────────────────────────────────────────────────────────────────

_password_hasher = BcryptPasswordHasher()

_jwt_handler = JWTHandler(
    secret_key=app_settings.jwt_secret_key,
    algorithm=app_settings.jwt_algorithm,
    expiry_minutes=app_settings.jwt_expiry_minutes,
)

#: The 9 entity types defined in Requirement 0 / NumberSeries design.
NUMBER_SERIES_ENTITY_TYPES = [
    "material",
    "product",
    "purchase_order",
    "sales_order",
    "invoice",
    "grn",
    "work_order",
    "batch",
    "customer",
    "supplier",
]

# Default prefix / padding for each entity type used in seeding.
_DEFAULT_NUMBER_SERIES: dict[str, dict] = {
    "material":       {"prefix": "MAT",  "sequence_length": 6},
    "product":        {"prefix": "PRD",  "sequence_length": 6},
    "purchase_order": {"prefix": "PO",   "sequence_length": 6},
    "sales_order":    {"prefix": "SO",   "sequence_length": 6},
    "invoice":        {"prefix": "INV",  "sequence_length": 6},
    "grn":            {"prefix": "GRN",  "sequence_length": 6},
    "work_order":     {"prefix": "WO",   "sequence_length": 6},
    "batch":          {"prefix": "BAT",  "sequence_length": 6},
    "customer":       {"prefix": "CUST", "sequence_length": 6},
    "supplier":       {"prefix": "SUPP", "sequence_length": 6},
}


# ─────────────────────────────────────────────────────────────────────────────
# Session-scoped event loop
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the entire test session (required by session-scoped async fixtures)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─────────────────────────────────────────────────────────────────────────────
# In-memory SQLite engine (session-scoped, shared across all E2E tests)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
async def e2e_db_engine():
    """
    Async SQLite in-memory engine with the full MedTrack schema.

    Session-scoped so all E2E suites share one schema initialisation pass.
    Each suite isolates data via a unique test_tenant row.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="session")
def e2e_session_factory(e2e_db_engine):
    """Session factory used to build short-lived sessions in fixtures."""
    return async_sessionmaker(
        bind=e2e_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Per-test DB session
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
async def e2e_db_session(e2e_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Function-scoped async session; rolls back after each test."""
    async with e2e_session_factory() as session:
        yield session
        await session.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# Isolated tenant (session-scoped — one tenant per test session)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
async def test_tenant(e2e_session_factory) -> TenantModel:
    """
    Create (or reuse) an isolated TenantModel row for this test session.

    Each pytest run gets a fresh UUID so test sessions never collide even
    when running against a shared database.
    """
    tenant_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    tenant = TenantModel(
        id=tenant_id,
        name="E2E Test Tenant",
        slug=f"e2e-{tenant_id.hex[:8]}",
        plan="enterprise",
        is_active=True,
        is_deleted=False,
        deleted_at=None,
        currency_code="USD",
        currency_symbol="$",
        company_name="E2E Corp",
        created_at=now,
        updated_at=now,
    )
    async with e2e_session_factory() as session:
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

    return tenant


# ─────────────────────────────────────────────────────────────────────────────
# Admin user + JWT helper (session-scoped)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
async def admin_user(
    e2e_session_factory, test_tenant: TenantModel
) -> dict:
    """
    Create an admin UserModel row for the test tenant.

    Returns a dict with keys:
        id          — uuid.UUID
        email       — str
        password    — str (plaintext, for login tests)
        token       — str  (Bearer JWT, pre-generated)
        headers     — dict {"Authorization": "Bearer …", "X-Tenant-ID": "…"}
    """
    user_id = uuid.uuid4()
    password = "AdminPass1!"
    now = datetime.now(timezone.utc)

    user = UserModel(
        id=user_id,
        tenant_id=test_tenant.id,
        email=f"admin-{user_id.hex[:8]}@e2e-test.local",
        hashed_password=_password_hasher.hash(password),
        first_name="Admin",
        last_name="E2E",
        role="admin",
        is_active=True,
        is_deleted=False,
        deleted_at=None,
        totp_enabled=False,
        backup_codes=[],
        created_at=now,
        updated_at=now,
    )
    async with e2e_session_factory() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = _make_jwt(user_id=user_id, tenant_id=test_tenant.id, role="admin")

    return {
        "id": user_id,
        "email": user.email,
        "password": password,
        "token": token,
        "headers": {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(test_tenant.id),
        },
    }


def _make_jwt(*, user_id: uuid.UUID, tenant_id: uuid.UUID, role: str) -> str:
    """Generate a JWT access token for the given user/tenant/role tuple."""
    return _jwt_handler.create_access_token(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        role=role,
    )


def make_token_headers(
    user_id: uuid.UUID, tenant_id: uuid.UUID, role: str = "admin"
) -> dict:
    """
    Helper available to tests that need to create per-role token headers.

    Usage::

        headers = make_token_headers(user_id=some_id, tenant_id=tenant.id, role="qc")
    """
    token = _make_jwt(user_id=user_id, tenant_id=tenant_id, role=role)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Number Series seed — all 9 entity types (session-scoped)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
async def seed_number_series(
    e2e_session_factory, test_tenant: TenantModel
) -> list[NumberSeriesConfigModel]:
    """
    Seed NumberSeriesConfigModel rows for all 9 entity types defined in
    Requirement 0 for the test tenant.

    Idempotent: existing rows are left unchanged (upsert-style via SELECT first).

    Returns the list of seeded/existing config rows.
    """
    now = datetime.now(timezone.utc)
    configs: list[NumberSeriesConfigModel] = []

    async with e2e_session_factory() as session:
        for entity_type in NUMBER_SERIES_ENTITY_TYPES:
            defaults = _DEFAULT_NUMBER_SERIES[entity_type]

            # Check if already seeded (idempotent)
            existing = await session.scalar(
                select(NumberSeriesConfigModel).where(
                    NumberSeriesConfigModel.tenant_id == test_tenant.id,
                    NumberSeriesConfigModel.entity_type == entity_type,
                )
            )
            if existing is not None:
                configs.append(existing)
                continue

            cfg = NumberSeriesConfigModel(
                id=uuid.uuid4(),
                tenant_id=test_tenant.id,
                entity_type=entity_type,
                auto_generate=True,
                manual_override="never",
                prefix=defaults["prefix"],
                include_abbreviation=False,
                abbreviation_length=3,
                sequence_length=defaults["sequence_length"],
                separator="-",
                lock_after_save=True,
                created_at=now,
                updated_at=now,
            )
            session.add(cfg)
            configs.append(cfg)

        await session.commit()
        # Refresh all to get DB-assigned defaults if any
        for cfg in configs:
            try:
                await session.refresh(cfg)
            except Exception:
                pass

    return configs


# ─────────────────────────────────────────────────────────────────────────────
# Async HTTP client wired to the FastAPI app
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
async def async_client(
    e2e_db_engine, e2e_session_factory
) -> AsyncGenerator[AsyncClient, None]:
    """
    httpx AsyncClient backed by ASGITransport — issues requests directly to the
    FastAPI application without a live server.

    The app's DI container is patched to use the shared in-memory SQLite engine
    so all E2E tests run without touching the real PostgreSQL database.

    The SlowAPI rate-limiter is switched to an in-memory storage backend so
    tests do not require a running Redis instance.
    """
    from backend.app.main import app
    from backend.app.infrastructure.container import Container
    from backend.app.infrastructure.audit.audit_service import AuditService
    from backend.app.infrastructure.logging.error_logger import ErrorLogger
    from backend.app.infrastructure.logging.repository import ErrorLogRepository

    # ── Patch rate-limiter to use in-memory storage (no Redis needed) ─────────
    # The module-level `limiter` singleton in backend.app.middleware.rate_limiting
    # is already attached to app.state.limiter by create_application().  We swap
    # its storage backend here so all test requests bypass Redis entirely.
    from slowapi import Limiter
    from backend.app.middleware.rate_limiting import get_user_id
    in_memory_limiter = Limiter(
        key_func=get_user_id,
        default_limits=["10000/minute"],  # effectively unlimited for tests
        storage_uri="memory://",
    )
    app.state.limiter = in_memory_limiter
    # Also patch the module-level limiter so route decorators see the same object
    import backend.app.middleware.rate_limiting as _rl_module
    _original_limiter = _rl_module.limiter
    _rl_module.limiter = in_memory_limiter
    # ─────────────────────────────────────────────────────────────────────────

    container = Container.create(app_settings)
    container.db_engine = e2e_db_engine
    container.session_factory = e2e_session_factory
    container.audit_service = AuditService(session_factory=e2e_session_factory)
    container.error_log_repository = ErrorLogRepository(session_factory=e2e_session_factory)
    container.error_logger = ErrorLogger(session_factory=e2e_session_factory)

    app.state.container = container

    transport = ASGITransport(app=cast(Any, app))
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        # Restore original limiter after the test
        _rl_module.limiter = _original_limiter
        app.state.limiter = _original_limiter


@pytest.fixture
async def authenticated_client(
    async_client: AsyncClient, admin_user: dict
) -> AsyncClient:
    """
    Convenience fixture: async_client pre-loaded with admin Authorization headers.

    Use this for tests that don't need to vary the authenticated role.
    """
    async_client.headers.update(admin_user["headers"])
    return async_client
