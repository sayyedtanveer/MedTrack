from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.application.client_portal.service import ClientPortalService
from backend.app.infrastructure.security.jwt_handler import JWTHandler
from backend.app.interfaces.api.v1.routes import client_portal as client_routes


def build_service_stub() -> SimpleNamespace:
    return SimpleNamespace(
        login_client=AsyncMock(),
        refresh_client_session=AsyncMock(),
        request_password_reset=AsyncMock(),
        reset_password=AsyncMock(),
        get_dashboard=AsyncMock(),
        list_orders=AsyncMock(),
        get_order=AsyncMock(),
        get_order_tracking=AsyncMock(),
        create_reorder=AsyncMock(),
        request_order_cancellation=AsyncMock(),
        list_invoices=AsyncMock(),
        get_invoice=AsyncMock(),
        build_invoice_pdf=AsyncMock(),
        get_credit=AsyncMock(),
        get_profile=AsyncMock(),
        update_profile=AsyncMock(),
        list_addresses=AsyncMock(),
        create_address=AsyncMock(),
        update_address=AsyncMock(),
        delete_address=AsyncMock(),
        get_notifications=AsyncMock(),
        mark_notification_read=AsyncMock(),
        get_notification_settings=AsyncMock(),
        update_notification_settings=AsyncMock(),
        get_support_faq=AsyncMock(),
        submit_support_request=AsyncMock(),
    )


def build_test_client(monkeypatch: pytest.MonkeyPatch, service: SimpleNamespace) -> tuple[TestClient, JWTHandler]:
    jwt_handler = JWTHandler("client-route-secret-key-with-32-bytes", "HS256", 60)
    app = FastAPI()
    app.state.container = SimpleNamespace(
        jwt_handler=jwt_handler,
        password_hasher=object(),
        email_service=object(),
        session_factory=lambda: None,
        environment="test",
    )
    app.include_router(client_routes.router)

    async def override_db_session():
        yield object()

    app.dependency_overrides[client_routes._get_db_session] = override_db_session
    monkeypatch.setattr(client_routes, "_service", lambda request, session: service)
    return TestClient(app), jwt_handler


def auth_headers(
    jwt_handler: JWTHandler,
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: str = "client",
    cid: uuid.UUID | str | None = None,
    include_client_id: bool = True,
) -> dict[str, str]:
    extra_claims = {}
    if include_client_id:
        extra_claims["cid"] = str(cid) if cid is not None else None
    token = jwt_handler.create_access_token(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        role=role,
        extra_claims=extra_claims or None,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_client_route_service_helpers():
    container = SimpleNamespace(
        jwt_handler="jwt",
        password_hasher="hasher",
        email_service="mailer",
        environment="stage",
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(container=container)))

    assert client_routes._get_container(request) is container

    service = client_routes._service(request, session="db-session")
    assert isinstance(service, ClientPortalService)
    assert service.session == "db-session"
    assert service.password_hasher == "hasher"
    assert service.jwt_handler == "jwt"
    assert service.email_service == "mailer"
    assert service.environment == "stage"

    class DummySessionContext:
        async def __aenter__(self):
            return "session-from-factory"

        async def __aexit__(self, exc_type, exc, tb):
            return False

    request.app.state.container.session_factory = lambda: DummySessionContext()
    generator = client_routes._get_db_session(request)
    yielded = await anext(generator)
    assert yielded == "session-from-factory"
    await generator.aclose()


def test_client_auth_routes(monkeypatch: pytest.MonkeyPatch):
    service = build_service_stub()
    client, jwt_handler = build_test_client(monkeypatch, service)
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    client_id = uuid.uuid4()

    service.login_client.return_value = {
        "access_token": "access-token",
        "token_type": "bearer",
        "user_id": user_id,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "email": "client@example.com",
        "role": "client",
        "full_name": "Client User",
    }
    response = client.post(
        "/client/auth/login",
        json={"email": "client@example.com", "password": "Secret123!", "tenant_id": str(tenant_id)},
    )
    assert response.status_code == 200
    service.login_client.assert_awaited_once_with("client@example.com", "Secret123!", tenant_id)

    service.login_client.reset_mock(side_effect=True)
    service.login_client.side_effect = ValueError("Invalid email or password")
    response = client.post(
        "/client/auth/login",
        json={"email": "client@example.com", "password": "Secret123!", "tenant_id": str(tenant_id)},
    )
    assert response.status_code == 401

    headers = auth_headers(jwt_handler, user_id=user_id, tenant_id=tenant_id, cid=client_id)
    response = client.post("/client/auth/logout", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "logged_out"}

    service.refresh_client_session.return_value = {"access_token": "refreshed-token", "token_type": "bearer"}
    response = client.post("/client/auth/refresh", headers=headers)
    assert response.status_code == 200
    refresh_payload = service.refresh_client_session.await_args.args[0]
    assert refresh_payload["role"] == "client"
    assert refresh_payload["cid"] == str(client_id)

    service.refresh_client_session.reset_mock(side_effect=True)
    service.refresh_client_session.side_effect = ValueError("bad refresh")
    response = client.post("/client/auth/refresh", headers=headers)
    assert response.status_code == 400

    service.request_password_reset.return_value = {"message": "queued", "reset_token": "reset-token"}
    response = client.post(
        "/client/auth/forgot-password",
        json={"email": "client@example.com", "tenant_id": str(tenant_id)},
    )
    assert response.status_code == 200
    service.request_password_reset.assert_awaited_once_with("client@example.com", tenant_id)

    service.reset_password.return_value = {"message": "Password updated successfully"}
    response = client.post(
        "/client/auth/reset-password",
        json={"token": "reset-token-123", "new_password": "LongerPass123!"},
    )
    assert response.status_code == 200
    service.reset_password.assert_awaited_once_with("reset-token-123", "LongerPass123!")

    service.reset_password.reset_mock(side_effect=True)
    service.reset_password.side_effect = ValueError("invalid token")
    response = client.post(
        "/client/auth/reset-password",
        json={"token": "reset-token-123", "new_password": "LongerPass123!"},
    )
    assert response.status_code == 400


def test_client_portal_routes_happy_path(monkeypatch: pytest.MonkeyPatch):
    service = build_service_stub()
    client, jwt_handler = build_test_client(monkeypatch, service)
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    order_id = uuid.uuid4()
    invoice_id = uuid.uuid4()
    address_id = uuid.uuid4()
    notification_id = uuid.uuid4()
    headers = auth_headers(jwt_handler, user_id=user_id, tenant_id=tenant_id, cid=client_id)

    service.get_dashboard.return_value = {"welcome_name": "Client"}
    service.list_orders.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20, "pages": 0}
    service.get_order.return_value = {"id": str(order_id)}
    service.get_order_tracking.return_value = {"order_id": str(order_id), "current_status": "SHIPPED"}
    service.create_reorder.return_value = {"id": str(order_id), "status": "DRAFT", "credit_warning": False}
    service.request_order_cancellation.return_value = {"status": "requested"}
    service.list_invoices.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20, "pages": 0}
    service.get_invoice.return_value = {"id": str(invoice_id), "invoice_number": "INV-001"}
    service.build_invoice_pdf.return_value = ("INV-001", b"%PDF-1.4 sample")
    service.get_credit.return_value = {"credit_limit": 1000.0}
    service.get_profile.return_value = {"company": {"id": str(client_id)}}
    service.update_profile.return_value = {"id": str(user_id), "first_name": "Updated"}
    service.list_addresses.return_value = [{"id": str(address_id)}]
    service.create_address.return_value = {"id": str(address_id), "type": "shipping"}
    service.update_address.return_value = {"id": str(address_id), "label": "Dock"}
    service.delete_address.return_value = {"status": "deleted"}
    service.get_notifications.return_value = {"items": [], "total": 0, "unread_count": 0, "page": 1, "pages": 0}
    service.mark_notification_read.return_value = {"marked_read": 1}
    service.get_notification_settings.return_value = {"marketing": False}
    service.update_notification_settings.return_value = {"marketing": True}
    service.get_support_faq.return_value = [{"question": "How?", "answer": "Like this."}]
    service.submit_support_request.return_value = {"ticket_id": str(uuid.uuid4()), "status": "submitted"}

    assert client.get("/client/dashboard", headers=headers).status_code == 200
    service.get_dashboard.assert_awaited_once_with(tenant_id, client_id, user_id)

    response = client.get("/client/orders?status=shipped&search=SO-123&page=2&page_size=5", headers=headers)
    assert response.status_code == 200
    service.list_orders.assert_awaited_once_with(tenant_id, client_id, 2, 5, "shipped", "SO-123")

    assert client.get(f"/client/orders/{order_id}", headers=headers).status_code == 200
    service.get_order.assert_awaited_once_with(tenant_id, client_id, order_id)

    assert client.get(f"/client/orders/{order_id}/tracking", headers=headers).status_code == 200
    service.get_order_tracking.assert_awaited_once_with(tenant_id, client_id, order_id)

    reorder_body = {
        "order_id": str(order_id),
        "notes": "Need asap",
        "lines": [
            {
                "product_id": str(uuid.uuid4()),
                "product_type": "variant",
                "uom_id": str(uuid.uuid4()),
                "quantity": "2",
                "unit_price": "25",
                "tax_rate": "18",
            }
        ],
    }
    response = client.post("/client/orders/reorder", headers=headers, json=reorder_body)
    assert response.status_code == 201
    reorder_args = service.create_reorder.await_args.args
    assert reorder_args[0:3] == (tenant_id, client_id, order_id)
    assert reorder_args[3][0]["product_type"] == "variant"
    assert reorder_args[4] == "Need asap"

    assert client.post(f"/client/orders/{order_id}/cancel-request", headers=headers).status_code == 200
    service.request_order_cancellation.assert_awaited_once_with(tenant_id, client_id, user_id, order_id)

    response = client.get("/client/invoices?status=overdue&page=2&page_size=5", headers=headers)
    assert response.status_code == 200
    service.list_invoices.assert_awaited_once_with(tenant_id, client_id, 2, 5, "overdue")

    assert client.get(f"/client/invoices/{invoice_id}", headers=headers).status_code == 200
    service.get_invoice.assert_awaited_once_with(tenant_id, client_id, invoice_id)

    response = client.get(f"/client/invoices/{invoice_id}/pdf", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'filename="INV-001.pdf"' in response.headers["content-disposition"]

    assert client.get("/client/credit", headers=headers).status_code == 200
    service.get_credit.assert_awaited_once_with(tenant_id, client_id)

    assert client.get("/client/profile", headers=headers).status_code == 200
    service.get_profile.assert_awaited_once_with(tenant_id, client_id, user_id)

    response = client.put("/client/profile", headers=headers, json={"first_name": "Updated"})
    assert response.status_code == 200
    service.update_profile.assert_awaited_once_with(tenant_id, client_id, user_id, {"first_name": "Updated"})

    assert client.get("/client/addresses", headers=headers).status_code == 200
    service.list_addresses.assert_awaited_once_with(tenant_id, client_id)

    response = client.post(
        "/client/addresses",
        headers=headers,
        json={"type": "shipping", "address_line1": "Dock 7", "is_default": True},
    )
    assert response.status_code == 201
    service.create_address.assert_awaited_once_with(
        tenant_id,
        client_id,
        {"type": "shipping", "label": None, "contact_name": None, "address_line1": "Dock 7", "address_line2": None,
         "city": None, "state": None, "postal_code": None, "country": None, "phone": None, "email": None, "is_default": True},
    )

    response = client.put(f"/client/addresses/{address_id}", headers=headers, json={"label": "Dock"})
    assert response.status_code == 200
    service.update_address.assert_awaited_once_with(tenant_id, client_id, address_id, {"label": "Dock"})

    assert client.delete(f"/client/addresses/{address_id}", headers=headers).status_code == 200
    service.delete_address.assert_awaited_once_with(tenant_id, client_id, address_id)

    response = client.get("/client/notifications?unread_only=true&page=2&page_size=5", headers=headers)
    assert response.status_code == 200
    service.get_notifications.assert_awaited_once_with(tenant_id, client_id, user_id, True, 2, 5)

    assert client.put(f"/client/notifications/{notification_id}/read", headers=headers).status_code == 200
    service.mark_notification_read.assert_awaited_once_with(tenant_id, user_id, notification_id)

    assert client.get("/client/notifications/settings", headers=headers).status_code == 200
    service.get_notification_settings.assert_awaited_once_with(tenant_id, client_id, user_id)

    response = client.put("/client/notifications/settings", headers=headers, json={"marketing": True})
    assert response.status_code == 200
    service.update_notification_settings.assert_awaited_once_with(tenant_id, client_id, user_id, {"marketing": True})

    assert client.get("/client/support/faq", headers=headers).status_code == 200
    service.get_support_faq.assert_awaited_once_with()

    response = client.post(
        "/client/support/contact",
        headers=headers,
        json={"subject": "Need help", "message": "Please help with my latest shipment."},
    )
    assert response.status_code == 201
    service.submit_support_request.assert_awaited_once_with(
        tenant_id,
        client_id,
        user_id,
        "Need help",
        "Please help with my latest shipment.",
    )


def test_client_portal_route_error_mapping(monkeypatch: pytest.MonkeyPatch):
    service = build_service_stub()
    client, jwt_handler = build_test_client(monkeypatch, service)
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    order_id = uuid.uuid4()
    invoice_id = uuid.uuid4()
    address_id = uuid.uuid4()
    notification_id = uuid.uuid4()
    headers = auth_headers(jwt_handler, user_id=user_id, tenant_id=tenant_id, cid=client_id)

    service.get_order.side_effect = ValueError("Order not found")
    assert client.get(f"/client/orders/{order_id}", headers=headers).status_code == 404

    service.get_order_tracking.side_effect = ValueError("Order not found")
    assert client.get(f"/client/orders/{order_id}/tracking", headers=headers).status_code == 404

    service.create_reorder.side_effect = ValueError("Cannot reorder")
    assert client.post("/client/orders/reorder", headers=headers, json={"order_id": str(order_id)}).status_code == 400

    service.request_order_cancellation.side_effect = ValueError("Cannot cancel")
    assert client.post(f"/client/orders/{order_id}/cancel-request", headers=headers).status_code == 400

    service.get_invoice.side_effect = ValueError("Invoice not found")
    assert client.get(f"/client/invoices/{invoice_id}", headers=headers).status_code == 404

    service.build_invoice_pdf.side_effect = ValueError("Invoice not found")
    assert client.get(f"/client/invoices/{invoice_id}/pdf", headers=headers).status_code == 404

    service.update_address.side_effect = ValueError("Address not found")
    assert client.put(f"/client/addresses/{address_id}", headers=headers, json={"label": "Missing"}).status_code == 404

    service.delete_address.side_effect = ValueError("Address not found")
    assert client.delete(f"/client/addresses/{address_id}", headers=headers).status_code == 404

    service.mark_notification_read.side_effect = ValueError("Notification not found")
    assert client.put(f"/client/notifications/{notification_id}/read", headers=headers).status_code == 404


def test_client_portal_dependency_guards(monkeypatch: pytest.MonkeyPatch):
    service = build_service_stub()
    service.get_dashboard.return_value = {"welcome_name": "Client"}
    client, jwt_handler = build_test_client(monkeypatch, service)
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    client_id = uuid.uuid4()

    assert client.get("/client/dashboard").status_code == 401
    assert client.get("/client/dashboard", headers={"Authorization": "Bearer invalid"}).status_code == 401

    admin_headers = auth_headers(jwt_handler, user_id=user_id, tenant_id=tenant_id, role="admin", cid=client_id)
    response = client.get("/client/dashboard", headers=admin_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Client portal access requires a client account"

    missing_client_headers = auth_headers(
        jwt_handler,
        user_id=user_id,
        tenant_id=tenant_id,
        role="client",
        include_client_id=False,
    )
    response = client.get("/client/dashboard", headers=missing_client_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Client portal: user must be linked to a client"

    invalid_client_headers = auth_headers(
        jwt_handler,
        user_id=user_id,
        tenant_id=tenant_id,
        role="client",
        cid="not-a-uuid",
    )
    response = client.get("/client/dashboard", headers=invalid_client_headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid client id in token"
