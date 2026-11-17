"""Workspace authentication on an isolated database through the HTTP routes."""
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateTable

from backend.app.config import settings
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.user_model import PasswordResetTokenModel, UserModel
from backend.app.infrastructure.security.jwt_handler import JWTHandler
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher
from backend.app.main import create_application


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(_column_type, _compiler, **_kwargs):
    return "JSON"


@pytest_asyncio.fixture
async def workspace_auth(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "cors_origins", "http://testserver")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for model in (TenantModel, UserModel, PasswordResetTokenModel):
            await conn.execute(CreateTable(model.__table__, include_foreign_key_constraints=[]))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    first, second, pending, deleted = [uuid4() for _ in range(4)]
    async with factory() as session:
        session.add_all([
            TenantModel(id=first, name="First", slug="first", status="active"),
            TenantModel(id=second, name="Second", slug="second", status="active"),
            TenantModel(id=pending, name="Pending", slug="pending", status="pending"),
            TenantModel(id=deleted, name="Deleted", slug="deleted", status="active", is_deleted=True),
        ])
        for tenant, email, password, active in [
            (first, "shared@example.com", "First1", True),
            (second, "SHARED@example.com", "Second1", True),
            (first, "same-password@example.com", "Shared1", True),
            (second, "same-password@example.com", "Shared1", True),
            (first, "solo@example.com", "Single1", True),
            (deleted, "solo@example.com", "Deleted1", True),
            (pending, "pending@example.com", "Pending1", True),
            (second, "inactive@example.com", "Inactive1", False),
        ]:
            session.add(UserModel(tenant_id=tenant, email=email, first_name="Test", last_name="User",
                                  role="admin", hashed_password=password, is_active=active))
        await session.commit()
    jwt = JWTHandler(uuid4().hex, "HS256", 10)
    mail = AsyncMock()
    app = create_application()
    app.state.container = SimpleNamespace(
        session_factory=factory, jwt_handler=jwt,
        password_hasher=SimpleNamespace(verify=lambda supplied, stored: supplied == stored, hash=lambda value: value),
        email_service=SimpleNamespace(send_email=mail),
        task_service=Mock(), event_dispatcher=AsyncMock(),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield SimpleNamespace(client=client, first=first, second=second, jwt=jwt, mail=mail, factory=factory)
    await engine.dispose()


async def sign_in(case, email, password, **selector):
    return await case.client.post("/api/v1/auth/login", json={"email": email, "password": password, **selector})


@pytest.mark.asyncio
async def test_unique_login_normalizes_email_and_uses_membership_for_jwt(workspace_auth):
    case = workspace_auth
    response = await sign_in(case, "SOLO@example.com", "Single1")
    assert response.status_code == 200
    assert response.json()["tenant_id"] == str(case.first)
    assert case.jwt.decode_token(response.json()["access_token"])["tid"] == str(case.first)
    assert (await sign_in(case, "solo@example.com", "Deleted1")).status_code == 401
    assert (await sign_in(case, "inactive@example.com", "Inactive1")).status_code == 401


@pytest.mark.asyncio
async def test_shared_login_requires_matching_workspace_and_credentials(workspace_auth):
    case = workspace_auth
    ambiguous = await sign_in(case, "shared@example.com", "First1")
    unknown = await sign_in(case, "missing@example.com", "First1")
    assert ambiguous.status_code == unknown.status_code == 401
    assert ambiguous.json()["detail"]["code"] == "WORKSPACE_REQUIRED"
    assert "access_token" not in ambiguous.json()
    wrong_password = await sign_in(case, "shared@example.com", "Wrong")
    assert wrong_password.status_code == 401
    assert wrong_password.json() == unknown.json()
    response = await sign_in(case, "shared@example.com", "Second1", workspace_slug="second")
    assert response.status_code == 200
    assert case.jwt.decode_token(response.json()["access_token"])["tid"] == str(case.second)
    assert (await sign_in(case, "shared@example.com", "First1", workspace_slug="second")).status_code == 401
    assert (await sign_in(case, "shared@example.com", "Second1",
                          tenant_id=str(case.first), workspace_slug="second")).status_code == 401
    legacy = await sign_in(case, "shared@example.com", "First1", tenant_id=str(case.first))
    assert legacy.json()["tenant_id"] == str(case.first)
    assert (await sign_in(case, "solo@example.com", "Single1", tenant_id=str(case.second))).status_code == 401
    assert (await sign_in(case, "solo@example.com", "Single1", tenant_id="bad")).status_code == 400


@pytest.mark.asyncio
async def test_identical_credentials_still_require_explicit_workspace(workspace_auth):
    case = workspace_auth
    email, password = "same-password@example.com", "Shared1"
    response = await sign_in(case, email, password)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "WORKSPACE_REQUIRED"
    assert "access_token" not in response.json()
    for slug, expected_tenant in (("first", case.first), ("second", case.second)):
        response = await sign_in(case, email, password, workspace_slug=slug)
        assert response.status_code == 200
        assert case.jwt.decode_token(response.json()["access_token"])["tid"] == str(expected_tenant)


@pytest.mark.asyncio
async def test_tenant_approval_state_requires_correct_credentials(workspace_auth):
    case = workspace_auth
    assert (await sign_in(case, "pending@example.com", "Wrong")).status_code == 401
    pending = await sign_in(case, "pending@example.com", "Pending1")
    assert pending.status_code == 403 and "access_token" not in pending.json()


@pytest.mark.asyncio
async def test_password_reset_issues_token_only_in_the_requested_workspace(workspace_auth):
    case = workspace_auth
    path = "/api/v1/forgot-password/request"
    body = {"email": "shared@example.com"}
    ambiguous = await case.client.post(path, json=body)
    malformed = await case.client.post(path, json={"email": "solo@example.com", "tenant_id": "bad"})
    mismatch = await case.client.post(path, json={**body, "tenant_id": str(case.first), "workspace_slug": "second"})
    assert ambiguous.json() == malformed.json() == mismatch.json()
    case.mail.assert_not_awaited()
    selected = await case.client.post(path, json={**body, "workspace_slug": "second"})
    assert selected.status_code == 200 and selected.json() == ambiguous.json()
    case.mail.assert_awaited_once()
    async with case.factory() as session:
        row = (await session.execute(
            select(PasswordResetTokenModel.tenant_id, UserModel.tenant_id)
            .join(UserModel, UserModel.id == PasswordResetTokenModel.user_id)
        )).one()
        assert row == (case.second, case.second)

    token = re.search(r"reset-password\?token=([A-Za-z0-9_-]+)", case.mail.await_args.kwargs["body"])[1]
    reset = await case.client.post("/api/v1/forgot-password/reset", json={"token": token, "new_password": "NewPassword123"})
    assert reset.status_code == 200
    async with case.factory() as session:
        users = dict((await session.execute(select(UserModel.tenant_id, UserModel.hashed_password).where(
            UserModel.email.in_(("shared@example.com", "SHARED@example.com"))
        ))).all())
    assert users[case.first] == "First1"
    assert BcryptPasswordHasher().verify("NewPassword123", users[case.second])


@pytest.mark.asyncio
async def test_registration_accepts_generated_slug_and_keeps_approval_gate(workspace_auth):
    case = workspace_auth
    path = "/api/v1/auth/register-tenant"
    payload = {
        "name": "New Engineering", "slug": "new-engineering", "plan": "starter",
        "admin_email": "solo@example.com", "admin_first_name": "New", "admin_last_name": "Admin",
        "admin_password": "ExamplePass123",
    }
    created = await case.client.post(path, json=payload)
    assert created.status_code == 201
    assert created.json()["slug"] == "new-engineering"
    assert created.json()["access_token"] is None
    assert (await case.client.post(path, json=payload)).status_code in (409, 422)
    assert (await sign_in(case, "solo@example.com", "Single1")).status_code == 401
    assert (await sign_in(case, "solo@example.com", "Single1", workspace_slug="first")).status_code == 200

