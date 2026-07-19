import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import MultipleResultsFound

from backend.app.interfaces.api.v1.routes.self_service_password_reset_router import (
    ForgotPasswordRequest,
    request_password_reset,
)
from backend.app.infrastructure.persistence.models.user_model import UserModel


class _FakeQueryResult:
    def __init__(self, rows):
        self._rows = rows

    def scalar_one_or_none(self):
        if len(self._rows) > 1:
            raise MultipleResultsFound("Multiple rows found")
        return self._rows[0] if self._rows else None

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeEmailService:
    def __init__(self):
        self.sent_messages = []

    async def send_email(self, **kwargs):
        self.sent_messages.append(kwargs)


@pytest.mark.asyncio
async def test_request_password_reset_handles_duplicate_email_rows():
    tenant_id = uuid.uuid4()
    user_a = UserModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="sayyedtanveer1410@gmail.com",
        hashed_password="hashed",
        first_name="First",
        last_name="User",
        role="admin",
        is_active=True,
    )
    user_b = UserModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="sayyedtanveer1410@gmail.com",
        hashed_password="hashed",
        first_name="Second",
        last_name="User",
        role="admin",
        is_active=True,
    )

    session = AsyncMock()
    session.execute.side_effect = [
        _FakeQueryResult([user_a, user_b]),
        _FakeQueryResult([]),
    ]
    session.commit = AsyncMock()
    session.add = MagicMock()

    email_service = _FakeEmailService()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(container=SimpleNamespace(email_service=email_service))
        )
    )

    response = await request_password_reset(
        request_body=ForgotPasswordRequest(email="sayyedtanveer1410@gmail.com"),
        request=request,
        background_tasks=MagicMock(),
        session=session,
    )

    assert response.success is True
    assert len(email_service.sent_messages) == 1
    assert "sayyedtanveer1410@gmail.com" in email_service.sent_messages[0]["to"]
