from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.application.client_portal import service as client_service_module
from backend.app.application.client_portal.service import ClientPortalService
from backend.app.infrastructure.persistence.models.finance_models import InvoiceModel, NotificationModel
from backend.app.infrastructure.persistence.models.sales_models import ClientAddressModel, ClientModel, SalesOrderLineModel, SalesOrderModel
from backend.app.infrastructure.persistence.models.user_model import (
    ClientNotificationSettingsModel,
    PasswordResetTokenModel,
    UserModel,
)
from backend.app.infrastructure.security.jwt_handler import JWTHandler
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher


class FakeScalarResult:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)


class FakeExecuteResult:
    def __init__(self, items=None):
        self._items = list(items or [])

    def scalars(self):
        return FakeScalarResult(self._items)


class FakeSession:
    def __init__(self, scalar_values=None, execute_values=None, get_values=None):
        self.scalar_values = list(scalar_values or [])
        self.execute_values = list(execute_values or [])
        self.get_values = dict(get_values or {})
        self.added = []
        self.deleted = []
        self.commits = 0
        self.flushes = 0
        self.refreshed = []

    async def scalar(self, *_args, **_kwargs):
        return self.scalar_values.pop(0) if self.scalar_values else None

    async def execute(self, *_args, **_kwargs):
        return self.execute_values.pop(0) if self.execute_values else FakeExecuteResult()

    async def get(self, _model, key):
        return self.get_values.get(key)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def flush(self):
        self.flushes += 1

    async def refresh(self, obj):
        now = datetime.now(timezone.utc)
        if getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = now
        self.refreshed.append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)


class FakeEmailService:
    def __init__(self):
        self.sent = []

    async def send_email(self, **payload):
        self.sent.append(payload)


class FakeNotificationService:
    instances: list["FakeNotificationService"] = []

    def __init__(self, _session):
        self.broadcasts = []
        self.sends = []
        FakeNotificationService.instances.append(self)

    async def broadcast_to_role(self, **payload):
        self.broadcasts.append(payload)
        return 1

    async def send(self, **payload):
        self.sends.append(payload)
        return SimpleNamespace(id=uuid.uuid4())


def make_user(tenant_id: uuid.UUID, client_id: uuid.UUID | None = None, role: str = "client", active: bool = True) -> UserModel:
    hasher = BcryptPasswordHasher()
    return UserModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="client@example.com",
        hashed_password=hasher.hash("Secret123!"),
        first_name="Client",
        last_name="User",
        role=role,
        client_id=client_id,
        supplier_id=None,
        is_active=active,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_client(tenant_id: uuid.UUID, client_id: uuid.UUID | None = None, credit_limit: float = 1000, credit_used: float = 200) -> ClientModel:
    return ClientModel(
        id=client_id or uuid.uuid4(),
        tenant_id=tenant_id,
        code="CLI-001",
        name="Acme Hospitals",
        email="ops@acme.com",
        phone="99999",
        address="Mumbai",
        gst_number="GST123",
        credit_limit=credit_limit,
        credit_used=credit_used,
        payment_terms_days=30,
        is_active=True,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_order(tenant_id: uuid.UUID, client_id: uuid.UUID, status: str = "CONFIRMED") -> SalesOrderModel:
    order = SalesOrderModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client_id,
        order_number="SO-20260329-001",
        order_date="2026-03-29",
        delivery_date="2026-04-05",
        status=status,
        payment_status="PENDING",
        subtotal=100,
        discount_amount=0,
        tax_amount=18,
        grand_total=118,
        notes="Initial note",
        created_by="sales",
        is_active=True,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        lines=[],
    )
    return order


def build_service(session: FakeSession, environment: str = "test") -> ClientPortalService:
    return ClientPortalService(
        session=session,
        password_hasher=BcryptPasswordHasher(),
        jwt_handler=JWTHandler("test-secret-key-with-32-characters", "HS256", 60),
        email_service=FakeEmailService(),
        environment=environment,
    )


@pytest.mark.asyncio
async def test_login_refresh_reset_and_password_reset_flows():
    tenant_id = uuid.uuid4()
    client_id = uuid.uuid4()
    user = make_user(tenant_id, client_id)
    session = FakeSession(get_values={user.id: user})
    service = build_service(session)
    service._get_client_user_by_email = AsyncMock(return_value=user)

    login = await service.login_client(user.email, "Secret123!", tenant_id)
    assert login["client_id"] == client_id
    assert service.jwt_handler.decode_token(login["access_token"])["cid"] == str(client_id)

    refreshed = await service.refresh_client_session({"sub": str(user.id), "tid": str(tenant_id), "role": "client", "cid": str(client_id)})
    assert refreshed["token_type"] == "bearer"

    reset_request = await service.request_password_reset(user.email, tenant_id)
    assert "reset_token" in reset_request
    assert isinstance(session.added[-1], PasswordResetTokenModel)
    assert service.email_service.sent

    token_row = PasswordResetTokenModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user.id,
        token_hash=service._hash_token("valid-token"),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        used_at=None,
        created_at=datetime.now(timezone.utc),
    )
    service._get_reset_token = AsyncMock(return_value=token_row)
    response = await service.reset_password("valid-token", "ChangedSecret123!")
    assert response["message"] == "Password updated successfully"
    assert token_row.used_at is not None
    assert service.password_hasher.verify("ChangedSecret123!", user.hashed_password) is True


@pytest.mark.asyncio
async def test_login_and_refresh_validation_errors():
    tenant_id = uuid.uuid4()
    client_id = uuid.uuid4()
    inactive_user = make_user(tenant_id, client_id, active=False)
    session = FakeSession()
    service = build_service(session)
    service._get_client_user_by_email = AsyncMock(return_value=inactive_user)

    with pytest.raises(ValueError, match="Account is inactive"):
        await service.login_client(inactive_user.email, "Secret123!", tenant_id)

    service._get_client_user_by_email = AsyncMock(return_value=make_user(tenant_id, None))
    with pytest.raises(ValueError, match="Client account is not linked"):
        await service.login_client("client@example.com", "Secret123!", tenant_id)

    with pytest.raises(ValueError, match="missing client context"):
        await service.refresh_client_session({"sub": "u", "tid": "t", "role": "client"})

    service._get_reset_token = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="invalid or expired"):
        await service.reset_password("bad-token", "NextPassword123!")


@pytest.mark.asyncio
async def test_dashboard_tracking_credit_profile_and_notification_flows(monkeypatch):
    tenant_id = uuid.uuid4()
    client = make_client(tenant_id)
    user = make_user(tenant_id, client.id)
    order = make_order(tenant_id, client.id, status="SHIPPED")
    settings = ClientNotificationSettingsModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client.id,
        user_id=user.id,
        order_confirmed=True,
        order_shipped=True,
        order_delivered=True,
        invoice_overdue=True,
        low_credit=True,
        marketing=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    note = NotificationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user.id,
        type="ORDER_SHIPPED",
        title="Shipped",
        message="On the way",
        reference_type="sales_order",
        reference_id=order.id,
        is_read=False,
        sent_at=datetime.now(timezone.utc),
        email_sent=False,
    )
    session = FakeSession(
        scalar_values=[4, 2, Decimal("220.00"), Decimal("80.00"), 1, 1, note],
        execute_values=[FakeExecuteResult([note])],
    )
    service = build_service(session)
    service._get_user_and_client = AsyncMock(return_value=(user, client))
    service._ensure_notifications = AsyncMock()
    service._query_orders = AsyncMock(return_value={"items": [{"id": "ord-1"}]})
    service._get_client_order = AsyncMock(return_value=order)
    service._get_client = AsyncMock(return_value=client)
    service._get_or_create_notification_settings = AsyncMock(return_value=settings)
    service.list_addresses = AsyncMock(return_value=[{"id": "addr-1"}])

    dashboard = await service.get_dashboard(tenant_id, client.id, user.id)
    tracking = await service.get_order_tracking(tenant_id, client.id, order.id)
    credit = await service.get_credit(tenant_id, client.id)
    profile = await service.get_profile(tenant_id, client.id, user.id)
    notifications = await service.get_notifications(tenant_id, client.id, user.id, unread_only=True)

    assert dashboard["kpis"]["orders"] == 4
    assert tracking["current_status"] == "SHIPPED"
    assert credit["credit_limit"] == 1000.0
    assert profile["company"]["name"] == client.name
    assert notifications["unread_count"] == 1

    session.scalar_values = [None]
    with pytest.raises(ValueError, match="Notification not found"):
        await service.mark_notification_read(tenant_id, user.id, uuid.uuid4())

    session.scalar_values = [note]
    result = await service.mark_notification_read(tenant_id, user.id, note.id)
    assert result == {"marked_read": 1}

    updated_settings = await service.update_notification_settings(tenant_id, client.id, user.id, {"marketing": True})
    assert updated_settings["marketing"] is True

    updated_contact = await service.update_profile(tenant_id, client.id, user.id, {"first_name": "Updated"})
    assert updated_contact["first_name"] == "Updated"


@pytest.mark.asyncio
async def test_reorder_invoice_address_and_support_flows(monkeypatch):
    tenant_id = uuid.uuid4()
    client = make_client(tenant_id, credit_limit=100, credit_used=90)
    user = make_user(tenant_id, client.id)
    source_order = make_order(tenant_id, client.id)
    line = SalesOrderLineModel(
        id=uuid.uuid4(),
        sales_order_id=source_order.id,
        product_id=uuid.uuid4(),
        product_type="variant",
        uom_id=uuid.uuid4(),
        quantity=2,
        unit_price=25,
        tax_rate=18,
        tax_amount=9,
        line_total=59,
        allocated_quantity=0,
        shipped_quantity=0,
        backorder_quantity=0,
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    source_order.lines = [line]
    invoice = InvoiceModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invoice_number="INV-001",
        sales_order_id=source_order.id,
        client_id=client.id,
        client_name=client.name,
        client_address=client.address,
        client_gst_number=client.gst_number,
        status="OVERDUE",
        invoice_date=date(2026, 3, 25),
        due_date=date(2026, 3, 28),
        subtotal=50,
        discount_amount=0,
        tax_amount=9,
        grand_total=59,
        paid_amount=10,
        notes="Overdue",
        terms="Net 3",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        lines=[],
        payments=[],
    )
    address = ClientAddressModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client.id,
        type="shipping",
        label="Main",
        contact_name="Ops",
        address_line1="Line 1",
        address_line2=None,
        city="Mumbai",
        state="MH",
        postal_code="400001",
        country="India",
        phone="99999",
        email="ship@example.com",
        is_default=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session = FakeSession(
        scalar_values=[1, client],
        execute_values=[FakeExecuteResult([invoice]), FakeExecuteResult([address])],
    )
    service = build_service(session)
    service._get_client_order = AsyncMock(side_effect=[source_order, source_order])
    service._next_order_number = AsyncMock(return_value="SO-20260329-099")
    service._estimate_availability = AsyncMock(
        return_value={
            "source": "material_stock",
            "available_quantity": 1.0,
            "status": "backorder",
            "backorder_warning": True,
            "message": "Requested quantity exceeds currently available stock.",
        }
    )
    service._get_client = AsyncMock(return_value=client)
    service._serialize_order = AsyncMock(return_value={"id": "new-order", "order_number": "SO-20260329-099", "lines": []})
    service._get_client_invoice = AsyncMock(return_value=invoice)
    service._get_address = AsyncMock(return_value=address)
    service._ensure_single_default_address = AsyncMock()

    reorder = await service.create_reorder(tenant_id, client.id, source_order.id)
    invoices = await service.list_invoices(tenant_id, client.id, status="overdue")
    pdf_name, pdf_bytes = await service.build_invoice_pdf(tenant_id, client.id, invoice.id)
    created_address = await service.create_address(tenant_id, client.id, {"type": "shipping", "address_line1": "Dock", "is_default": True})
    updated_address = await service.update_address(tenant_id, client.id, address.id, {"label": "Updated", "is_default": True})
    deleted = await service.delete_address(tenant_id, client.id, address.id)

    monkeypatch.setattr(client_service_module, "NotificationService", FakeNotificationService)
    FakeNotificationService.instances.clear()
    support = await service.submit_support_request(tenant_id, client.id, user.id, "Need help", "Please call back.")
    faq = await service.get_support_faq()

    assert reorder["credit_warning"] is True
    assert invoices["items"][0]["invoice_number"] == "INV-001"
    assert pdf_name == "INV-001"
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert created_address["type"] == "shipping"
    assert updated_address["label"] == "Updated"
    assert deleted == {"status": "deleted"}
    assert support["status"] == "submitted"
    assert len(FakeNotificationService.instances[0].broadcasts) == 3
    assert len(faq) == 3


@pytest.mark.asyncio
async def test_cancellation_validation_and_notification_generation(monkeypatch):
    tenant_id = uuid.uuid4()
    client = make_client(tenant_id, credit_limit=100, credit_used=95)
    user = make_user(tenant_id, client.id)
    delivered_order = make_order(tenant_id, client.id, status="DELIVERED")
    confirmed_order = make_order(tenant_id, client.id, status="CONFIRMED")
    overdue_invoice = InvoiceModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invoice_number="INV-OVERDUE",
        sales_order_id=confirmed_order.id,
        client_id=client.id,
        client_name=client.name,
        client_address=client.address,
        client_gst_number=client.gst_number,
        status="OVERDUE",
        invoice_date=date.today(),
        due_date=date.today() - timedelta(days=1),
        subtotal=10,
        discount_amount=0,
        tax_amount=0,
        grand_total=10,
        paid_amount=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        lines=[],
        payments=[],
    )
    settings = ClientNotificationSettingsModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client.id,
        user_id=user.id,
        order_confirmed=True,
        order_shipped=True,
        order_delivered=True,
        invoice_overdue=True,
        low_credit=True,
        marketing=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service = build_service(FakeSession())
    service._get_client_order = AsyncMock(return_value=delivered_order)
    with pytest.raises(ValueError, match="can no longer be cancelled"):
        await service.request_order_cancellation(tenant_id, client.id, user.id, delivered_order.id)

    monkeypatch.setattr(client_service_module, "NotificationService", FakeNotificationService)
    FakeNotificationService.instances.clear()
    service._get_client_order = AsyncMock(return_value=confirmed_order)
    cancelled = await service.request_order_cancellation(tenant_id, client.id, user.id, confirmed_order.id)
    assert cancelled == {"status": "requested"}
    assert len(FakeNotificationService.instances[0].broadcasts) == 3

    execute_values = [
        FakeExecuteResult([confirmed_order]),
        FakeExecuteResult([]),
        FakeExecuteResult([]),
        FakeExecuteResult([overdue_invoice]),
    ]
    scalar_values = [None, None, None, None]
    session = FakeSession(scalar_values=scalar_values, execute_values=execute_values)
    service = build_service(session)
    service._get_or_create_notification_settings = AsyncMock(return_value=settings)
    service._get_client = AsyncMock(return_value=client)
    FakeNotificationService.instances.clear()
    monkeypatch.setattr(client_service_module, "NotificationService", FakeNotificationService)

    await service._ensure_notifications(tenant_id, client.id, user.id)
    sends = FakeNotificationService.instances[0].sends
    assert {payload["notification_type"] for payload in sends} >= {"ORDER_CONFIRMED", "INVOICE_OVERDUE", "LOW_CREDIT"}


@pytest.mark.asyncio
async def test_public_wrappers_and_lookup_guards():
    tenant_id = uuid.uuid4()
    client = make_client(tenant_id)
    user = make_user(tenant_id, client.id)
    order = make_order(tenant_id, client.id)
    invoice = InvoiceModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invoice_number="INV-WRAP-001",
        sales_order_id=order.id,
        client_id=client.id,
        client_name=client.name,
        client_address=client.address,
        client_gst_number=client.gst_number,
        status="PAID",
        invoice_date=date(2026, 3, 29),
        due_date=date(2026, 3, 29),
        subtotal=10,
        discount_amount=0,
        tax_amount=0,
        grand_total=10,
        paid_amount=10,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        lines=[],
        payments=[],
    )
    address = ClientAddressModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client.id,
        type="billing",
        label="HQ",
        contact_name="Finance",
        address_line1="Line 1",
        address_line2=None,
        city="Mumbai",
        state="MH",
        postal_code="400001",
        country="India",
        phone="99999",
        email="finance@example.com",
        is_default=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    settings = ClientNotificationSettingsModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client.id,
        user_id=user.id,
        order_confirmed=False,
        order_shipped=False,
        order_delivered=False,
        invoice_overdue=False,
        low_credit=False,
        marketing=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service_for_hash = build_service(FakeSession())
    token_row = PasswordResetTokenModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user.id,
        token_hash=service_for_hash._hash_token("lookup-token"),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        used_at=None,
        created_at=datetime.now(timezone.utc),
    )
    session = FakeSession(scalar_values=[user, order, invoice, user, client, client, order, invoice, address, token_row])
    service = build_service(session)
    service._query_orders = AsyncMock(return_value={"items": ["ok"]})
    service._serialize_order = AsyncMock(return_value={"id": str(order.id)})
    service._get_or_create_notification_settings = AsyncMock(return_value=settings)

    lookup_user = await service._get_client_user_by_email(user.email, tenant_id)
    wrapper_orders = await service.list_orders(tenant_id, client.id, 2, 25, "draft", "SO-")
    wrapper_order = await service.get_order(tenant_id, client.id, order.id)
    wrapper_invoice = await service.get_invoice(tenant_id, client.id, invoice.id)
    wrapper_settings = await service.get_notification_settings(tenant_id, client.id, user.id)
    fetched_user, fetched_client = await service._get_user_and_client(tenant_id, client.id, user.id)
    fetched_client_direct = await service._get_client(tenant_id, client.id)
    fetched_order = await service._get_client_order(tenant_id, client.id, order.id)
    fetched_invoice = await service._get_client_invoice(tenant_id, client.id, invoice.id)
    fetched_address = await service._get_address(tenant_id, client.id, address.id)
    fetched_token = await service._get_reset_token("lookup-token")
    await service._ensure_single_default_address(client.id, "shipping", None)

    assert lookup_user.id == user.id
    assert wrapper_orders["items"] == ["ok"]
    assert wrapper_order["id"] == str(order.id)
    assert wrapper_invoice["invoice_number"] == invoice.invoice_number
    assert wrapper_settings["marketing"] is False
    assert fetched_user.id == user.id
    assert fetched_client.id == client.id
    assert fetched_client_direct.id == client.id
    assert fetched_order.id == order.id
    assert fetched_invoice.id == invoice.id
    assert fetched_address.id == address.id
    assert fetched_token.id == token_row.id

    error_service = build_service(FakeSession(scalar_values=[None, None, None, None, None]))
    with pytest.raises(ValueError, match="Client user not found"):
        await error_service._get_user_and_client(tenant_id, client.id, user.id)
    with pytest.raises(ValueError, match="Client not found"):
        await error_service._get_client(tenant_id, client.id)
    with pytest.raises(ValueError, match="Order not found"):
        await error_service._get_client_order(tenant_id, client.id, order.id)
    with pytest.raises(ValueError, match="Invoice not found"):
        await error_service._get_client_invoice(tenant_id, client.id, invoice.id)
    with pytest.raises(ValueError, match="Address not found"):
        await error_service._get_address(tenant_id, client.id, address.id)


@pytest.mark.asyncio
async def test_password_reset_unknown_user_invalid_password_and_disabled_notifications(monkeypatch):
    tenant_id = uuid.uuid4()
    client_id = uuid.uuid4()
    user = make_user(tenant_id, client_id)
    service = build_service(FakeSession())
    service._get_client_user_by_email = AsyncMock(side_effect=[user, None])

    with pytest.raises(ValueError, match="Invalid email or password"):
        await service.login_client(user.email, "WrongPassword!", tenant_id)

    reset_response = await service.request_password_reset("missing@example.com", tenant_id)
    assert "reset_token" not in reset_response

    admin_user = make_user(tenant_id, client_id, role="admin")
    bad_reset_service = build_service(FakeSession(get_values={admin_user.id: admin_user}))
    bad_reset_service._get_reset_token = AsyncMock(return_value=PasswordResetTokenModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=admin_user.id,
        token_hash="hash",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        used_at=None,
        created_at=datetime.now(timezone.utc),
    ))
    with pytest.raises(ValueError, match="valid client user"):
        await bad_reset_service.reset_password("token", "NewSecret123!")

    disabled_settings = ClientNotificationSettingsModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client_id,
        user_id=user.id,
        order_confirmed=False,
        order_shipped=False,
        order_delivered=False,
        invoice_overdue=False,
        low_credit=False,
        marketing=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    disabled_notification_service = build_service(FakeSession())
    disabled_notification_service._get_or_create_notification_settings = AsyncMock(return_value=disabled_settings)
    monkeypatch.setattr(client_service_module, "NotificationService", FakeNotificationService)
    FakeNotificationService.instances.clear()
    await disabled_notification_service._ensure_notifications(tenant_id, client_id, user.id)
    assert FakeNotificationService.instances[0].sends == []
