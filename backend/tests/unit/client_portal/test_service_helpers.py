from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.application.client_portal.service import (
    ClientPortalService,
    _build_minimal_pdf,
    _money,
    _payment_link,
)
from backend.app.infrastructure.persistence.models.finance_models import InvoiceModel, NotificationModel, PaymentModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.sales_models import ClientAddressModel, ClientModel, SalesOrderLineModel, SalesOrderModel
from backend.app.infrastructure.persistence.models.user_model import ClientNotificationSettingsModel


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
    def __init__(self, scalar_values=None, execute_values=None):
        self.scalar_values = list(scalar_values or [])
        self.execute_values = list(execute_values or [])
        self.added = []
        self.commits = 0
        self.refreshed = []

    async def scalar(self, *_args, **_kwargs):
        return self.scalar_values.pop(0) if self.scalar_values else None

    async def execute(self, *_args, **_kwargs):
        return self.execute_values.pop(0) if self.execute_values else FakeExecuteResult()

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)


def build_service(session: FakeSession | None = None) -> ClientPortalService:
    return ClientPortalService(
        session=session or FakeSession(),
        password_hasher=SimpleNamespace(hash=lambda value: value, verify=lambda plain, hashed: plain == hashed),
        jwt_handler=SimpleNamespace(create_access_token=lambda **_: "token"),
        email_service=None,
        environment="test",
    )


def make_client() -> ClientModel:
    return ClientModel(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        code="CLI-001",
        name="Acme Hospitals",
        email="client@example.com",
        phone="9999999999",
        address="Mumbai",
        gst_number="GST123",
        credit_limit=1000,
        credit_used=850,
        payment_terms_days=30,
        is_active=True,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_order(client_id: uuid.UUID | None = None) -> SalesOrderModel:
    return SalesOrderModel(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        client_id=client_id or uuid.uuid4(),
        order_number="SO-20260329-001",
        order_date="2026-03-29",
        delivery_date="2026-04-05",
        status="SHIPPED",
        payment_status="PENDING",
        subtotal=100,
        discount_amount=0,
        tax_amount=18,
        grand_total=118,
        notes="Handle carefully",
        created_by="client-portal",
        is_active=True,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        lines=[],
    )


def make_line(order_id: uuid.UUID) -> SalesOrderLineModel:
    return SalesOrderLineModel(
        id=uuid.uuid4(),
        sales_order_id=order_id,
        product_id=uuid.uuid4(),
        product_type="variant",
        uom_id=uuid.uuid4(),
        quantity=5,
        unit_price=20,
        tax_rate=18,
        tax_amount=18,
        line_total=118,
        allocated_quantity=3,
        shipped_quantity=2,
        backorder_quantity=1,
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_invoice(client_id: uuid.UUID | None = None) -> InvoiceModel:
    payment = PaymentModel(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        payment_number="PAY-001",
        invoice_id=uuid.uuid4(),
        client_id=client_id or uuid.uuid4(),
        amount=50,
        payment_date=date(2026, 3, 30),
        payment_method="BANK_TRANSFER",
        created_at=datetime.now(timezone.utc),
    )
    invoice = InvoiceModel(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        invoice_number="INV-001",
        sales_order_id=uuid.uuid4(),
        client_id=client_id or uuid.uuid4(),
        client_name="Acme Hospitals",
        client_address="Mumbai",
        client_gst_number="GST123",
        status="OVERDUE",
        invoice_date=date(2026, 3, 25),
        due_date=date(2026, 3, 28),
        subtotal=100,
        discount_amount=5,
        tax_amount=18,
        grand_total=113,
        paid_amount=50,
        notes="Pay soon",
        terms="Net 3",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        lines=[],
        payments=[payment],
    )
    return invoice


@pytest.mark.asyncio
async def test_helper_functions_and_pdf_generation():
    pdf = _build_minimal_pdf(["Invoice INV-001", "Line 1"])
    assert pdf.startswith(b"%PDF-1.4")
    assert _money(Decimal("12.345")) == 12.35
    assert _payment_link("INV-001").endswith("INV-001")


def test_build_timeline_and_credit_serialization():
    service = build_service()
    client = make_client()

    shipped = service._build_timeline("SHIPPED")
    cancelled = service._build_timeline("CANCELLED")
    credit = service._serialize_credit(client)

    assert shipped[-2]["status"] == "current"
    assert cancelled[2]["status"] == "cancelled"
    assert credit["is_low_credit"] is True
    assert credit["credit_remaining"] == 150.0


def test_invoice_address_notification_and_settings_serializers():
    service = build_service()
    client = make_client()
    invoice = make_invoice(client.id)
    address = ClientAddressModel(
        id=uuid.uuid4(),
        tenant_id=client.tenant_id,
        client_id=client.id,
        type="shipping",
        label="Main Warehouse",
        contact_name="Operations",
        address_line1="Line 1",
        address_line2="Line 2",
        city="Mumbai",
        state="MH",
        postal_code="400001",
        country="India",
        phone="9999999999",
        email="ship@example.com",
        is_default=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    notification = NotificationModel(
        id=uuid.uuid4(),
        tenant_id=client.tenant_id,
        user_id=uuid.uuid4(),
        type="ORDER_SHIPPED",
        title="Shipped",
        message="Order shipped",
        reference_type="sales_order",
        reference_id=uuid.uuid4(),
        is_read=False,
        sent_at=datetime.now(timezone.utc),
        email_sent=False,
    )
    settings = ClientNotificationSettingsModel(
        id=uuid.uuid4(),
        tenant_id=client.tenant_id,
        client_id=client.id,
        user_id=uuid.uuid4(),
        order_confirmed=True,
        order_shipped=True,
        order_delivered=False,
        invoice_overdue=True,
        low_credit=True,
        marketing=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    invoice_payload = service._serialize_invoice(invoice)
    address_payload = service._serialize_address(address)
    notification_payload = service._serialize_notification(notification)
    settings_payload = service._serialize_notification_settings(settings)

    assert invoice_payload["payment_link"].endswith("INV-001")
    assert address_payload["type"] == "shipping"
    assert notification_payload["reference_type"] == "sales_order"
    assert settings_payload["order_confirmed"] is True


@pytest.mark.asyncio
async def test_estimate_availability_unknown_and_backorder():
    missing_material_session = FakeSession(scalar_values=[None])
    service = build_service(missing_material_session)

    unknown = await service._estimate_availability(uuid.uuid4(), uuid.uuid4(), Decimal("5"))
    assert unknown["status"] == "unknown"

    material = MaterialModel(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        code="MAT-001",
        name="Steel",
        current_cost=10,
        current_stock=3,
        reserved_stock=1,
        is_batch_tracked=False,
        is_serialized=False,
        inspection_required=False,
        is_active=True,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    backorder_session = FakeSession(scalar_values=[material])
    service = build_service(backorder_session)

    availability = await service._estimate_availability(material.tenant_id, material.id, Decimal("5"))
    assert availability["backorder_warning"] is True
    assert availability["available_quantity"] == 2.0


@pytest.mark.asyncio
async def test_resolve_product_name_uses_variant_then_material_then_fallback():
    tenant_id = uuid.uuid4()
    product_id = uuid.uuid4()

    variant = ItemVariantModel(
        id=product_id,
        tenant_id=tenant_id,
        template_id=uuid.uuid4(),
        code="VAR-001",
        name="Variant Name",
        variant_key="SIZE=M",
        attribute_values={},
        standard_cost=0,
        is_active=True,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    service = build_service(FakeSession(scalar_values=[variant]))
    assert await service._resolve_product_name(tenant_id, product_id) == ("Variant Name", "VAR-001")

    material = MaterialModel(
        id=product_id,
        tenant_id=tenant_id,
        code="MAT-001",
        name="Material Name",
        current_cost=0,
        current_stock=0,
        reserved_stock=0,
        is_batch_tracked=False,
        is_serialized=False,
        inspection_required=False,
        is_active=True,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    service = build_service(FakeSession(scalar_values=[None, material]))
    assert await service._resolve_product_name(tenant_id, product_id) == ("Material Name", "MAT-001")

    service = build_service(FakeSession(scalar_values=[None, None]))
    fallback_name, fallback_code = await service._resolve_product_name(tenant_id, product_id)
    assert fallback_name.startswith("Product ")
    assert fallback_code is None


@pytest.mark.asyncio
async def test_serialize_order_and_query_orders():
    order = make_order()
    line = make_line(order.id)
    order.lines = [line]

    service = build_service(FakeSession())
    service._resolve_product_name = AsyncMock(return_value=("Variant Name", "VAR-001"))
    service._estimate_availability = AsyncMock(
        return_value={
            "source": "material_stock",
            "available_quantity": 10.0,
            "status": "available",
            "backorder_warning": False,
            "message": "Stock appears available.",
        }
    )

    payload = await service._serialize_order(order, include_lines=True)
    assert payload["line_count"] == 1
    assert payload["lines"][0]["product_name"] == "Variant Name"

    session = FakeSession(
        scalar_values=[1],
        execute_values=[FakeExecuteResult([order])],
    )
    service = build_service(session)
    service._serialize_order = AsyncMock(return_value={"id": str(order.id), "order_number": order.order_number})
    paged = await service._query_orders(order.tenant_id, order.client_id, 1, 10, search="SO-")
    assert paged["total"] == 1
    assert paged["items"][0]["order_number"] == order.order_number


@pytest.mark.asyncio
async def test_settings_creation_default_address_and_token_helpers():
    client = make_client()
    user_id = uuid.uuid4()
    existing = ClientAddressModel(
        id=uuid.uuid4(),
        tenant_id=client.tenant_id,
        client_id=client.id,
        type="shipping",
        label="Old",
        contact_name=None,
        address_line1="Old Line",
        address_line2=None,
        city=None,
        state=None,
        postal_code=None,
        country=None,
        phone=None,
        email=None,
        is_default=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    session = FakeSession(
        scalar_values=[None, 7],
        execute_values=[FakeExecuteResult([existing])],
    )
    service = build_service(session)

    settings = await service._get_or_create_notification_settings(client.tenant_id, client.id, user_id)
    await service._ensure_single_default_address(client.id, "shipping", uuid.uuid4())
    next_order = await service._next_order_number(client.tenant_id)

    assert isinstance(settings, ClientNotificationSettingsModel)
    assert existing.is_default is False
    assert next_order.endswith("008")
    assert service._hash_token("abc") == service._hash_token("abc")
