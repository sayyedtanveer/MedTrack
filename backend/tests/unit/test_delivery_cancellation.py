"""Unit tests for delivery cancellation with inventory restoration.

Tests cover:
- POST /deliveries/{id}/cancel endpoint: transition to CANCELLED, create DISPATCH_REVERSAL transactions
- Only allow cancellation for DRAFT/PACKING statuses; reject for SHIPPED
- Create audit_log entry and delivery_cancelled notification
- Update SO line dispatched_quantity

Requirements: 33.1, 33.2, 33.3, 33.4, 33.5, 33.6, 33.7
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.application.delivery.delivery_service import DeliveryService
from backend.app.infrastructure.persistence.models.delivery_model import (
    DeliveryLineModel,
    DeliveryOrderModel,
)
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderLineModel,
    SalesOrderModel,
)


def _make_sales_order_line(
    line_id=None,
    product_id=None,
    quantity=10.0,
    allocated_quantity=10.0,
    dispatched_quantity=5.0,
    shipped_quantity=0.0,
) -> MagicMock:
    """Create a mock SalesOrderLineModel."""
    line = MagicMock(spec=SalesOrderLineModel)
    line.id = line_id or uuid.uuid4()
    line.product_id = product_id or uuid.uuid4()
    line.quantity = quantity
    line.allocated_quantity = allocated_quantity
    line.dispatched_quantity = dispatched_quantity
    line.shipped_quantity = shipped_quantity
    line.updated_at = datetime.now(timezone.utc)
    return line


def _make_sales_order(
    order_id=None,
    tenant_id=None,
    order_number="SO-000001",
    status="READY_FOR_DISPATCH",
    lines=None,
) -> MagicMock:
    """Create a mock SalesOrderModel."""
    order = MagicMock(spec=SalesOrderModel)
    order.id = order_id or uuid.uuid4()
    order.tenant_id = tenant_id or uuid.uuid4()
    order.order_number = order_number
    order.status = status
    order.lines = lines or []
    return order


def _make_delivery(
    delivery_id=None,
    tenant_id=None,
    sales_order_id=None,
    delivery_number="DO-000001",
    status="DRAFT",
    lines=None,
) -> MagicMock:
    """Create a mock DeliveryOrderModel."""
    delivery = MagicMock(spec=DeliveryOrderModel)
    delivery.id = delivery_id or uuid.uuid4()
    delivery.tenant_id = tenant_id or uuid.uuid4()
    delivery.sales_order_id = sales_order_id or uuid.uuid4()
    delivery.delivery_number = delivery_number
    delivery.status = status
    delivery.cancelled_at = None
    delivery.cancelled_by = None
    delivery.cancellation_reason = None
    delivery.updated_at = datetime.now(timezone.utc)
    delivery.lines = lines or []
    return delivery


def _make_delivery_line(
    line_id=None,
    delivery_order_id=None,
    sales_order_line_id=None,
    variant_id=None,
    quantity=5.0,
) -> MagicMock:
    """Create a mock DeliveryLineModel."""
    dl = MagicMock(spec=DeliveryLineModel)
    dl.id = line_id or uuid.uuid4()
    dl.delivery_order_id = delivery_order_id or uuid.uuid4()
    dl.sales_order_line_id = sales_order_line_id or uuid.uuid4()
    dl.variant_id = variant_id or uuid.uuid4()
    dl.quantity = quantity
    return dl


class TestDeliveryCancellationStatusValidation:
    """Req 33.2: Only DRAFT/PACKING can be cancelled; reject for SHIPPED."""

    @pytest.mark.asyncio
    async def test_cancel_raises_error_for_shipped_delivery(self):
        """SHIPPED deliveries cannot be cancelled (Req 33.5)."""
        session = AsyncMock()
        service = DeliveryService(session)

        delivery = _make_delivery(status="SHIPPED")
        service.get = AsyncMock(return_value=delivery)

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with pytest.raises(ValueError, match="Cannot cancel delivery in SHIPPED status"):
            await service.cancel(
                tenant_id=tenant_id,
                delivery_id=delivery.id,
                cancelled_by=user_id,
            )

    @pytest.mark.asyncio
    async def test_cancel_raises_error_for_delivered_delivery(self):
        """DELIVERED deliveries cannot be cancelled."""
        session = AsyncMock()
        service = DeliveryService(session)

        delivery = _make_delivery(status="DELIVERED")
        service.get = AsyncMock(return_value=delivery)

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with pytest.raises(ValueError, match="Cannot cancel delivery in DELIVERED status"):
            await service.cancel(
                tenant_id=tenant_id,
                delivery_id=delivery.id,
                cancelled_by=user_id,
            )

    @pytest.mark.asyncio
    async def test_cancel_allows_draft_status(self):
        """DRAFT deliveries can be cancelled (Req 33.1)."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        service = DeliveryService(session)

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        so_line_id = uuid.uuid4()
        variant_id = uuid.uuid4()

        so_line = _make_sales_order_line(line_id=so_line_id, product_id=variant_id, dispatched_quantity=5.0)
        order = _make_sales_order(tenant_id=tenant_id, lines=[so_line])
        dl = _make_delivery_line(sales_order_line_id=so_line_id, variant_id=variant_id, quantity=5.0)
        delivery = _make_delivery(tenant_id=tenant_id, sales_order_id=order.id, status="DRAFT", lines=[dl])

        service.get = AsyncMock(return_value=delivery)
        service._sales_order_or_error = AsyncMock(return_value=order)

        with patch("backend.app.application.delivery.delivery_service.AuditLogService") as mock_audit_cls, \
             patch("backend.app.application.delivery.delivery_service.NotificationService") as mock_notif_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            mock_notif = AsyncMock()
            mock_notif_cls.return_value = mock_notif

            result = await service.cancel(
                tenant_id=tenant_id,
                delivery_id=delivery.id,
                cancelled_by=user_id,
                reason="Customer requested cancellation",
            )

        # Verify delivery status transitioned
        assert delivery.status == "CANCELLED"
        assert delivery.cancelled_by == user_id
        assert delivery.cancellation_reason == "Customer requested cancellation"
        assert delivery.cancelled_at is not None

    @pytest.mark.asyncio
    async def test_cancel_allows_packing_status(self):
        """PACKING deliveries can be cancelled (Req 33.1)."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        service = DeliveryService(session)

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        so_line_id = uuid.uuid4()
        variant_id = uuid.uuid4()

        so_line = _make_sales_order_line(line_id=so_line_id, product_id=variant_id, dispatched_quantity=3.0)
        order = _make_sales_order(tenant_id=tenant_id, lines=[so_line])
        dl = _make_delivery_line(sales_order_line_id=so_line_id, variant_id=variant_id, quantity=3.0)
        delivery = _make_delivery(tenant_id=tenant_id, sales_order_id=order.id, status="PACKING", lines=[dl])

        service.get = AsyncMock(return_value=delivery)
        service._sales_order_or_error = AsyncMock(return_value=order)

        with patch("backend.app.application.delivery.delivery_service.AuditLogService") as mock_audit_cls, \
             patch("backend.app.application.delivery.delivery_service.NotificationService") as mock_notif_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            mock_notif = AsyncMock()
            mock_notif_cls.return_value = mock_notif

            result = await service.cancel(
                tenant_id=tenant_id,
                delivery_id=delivery.id,
                cancelled_by=user_id,
            )

        assert delivery.status == "CANCELLED"


class TestDeliveryCancellationInventoryRestoration:
    """Req 33.3, 33.4: Create DISPATCH_REVERSAL transactions, update dispatched_quantity."""

    @pytest.mark.asyncio
    async def test_cancel_creates_dispatch_reversal_transactions(self):
        """Cancellation creates DISPATCH_REVERSAL transactions with positive quantities (Req 33.3)."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        service = DeliveryService(session)

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        so_line_id = uuid.uuid4()
        variant_id = uuid.uuid4()

        so_line = _make_sales_order_line(line_id=so_line_id, product_id=variant_id, dispatched_quantity=5.0)
        order = _make_sales_order(tenant_id=tenant_id, lines=[so_line])
        dl = _make_delivery_line(sales_order_line_id=so_line_id, variant_id=variant_id, quantity=5.0)
        delivery = _make_delivery(tenant_id=tenant_id, sales_order_id=order.id, status="DRAFT", lines=[dl])

        service.get = AsyncMock(return_value=delivery)
        service._sales_order_or_error = AsyncMock(return_value=order)

        added_objects = []
        session.add = lambda obj: added_objects.append(obj)

        with patch("backend.app.application.delivery.delivery_service.AuditLogService") as mock_audit_cls, \
             patch("backend.app.application.delivery.delivery_service.NotificationService") as mock_notif_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            mock_notif = AsyncMock()
            mock_notif_cls.return_value = mock_notif

            await service.cancel(
                tenant_id=tenant_id,
                delivery_id=delivery.id,
                cancelled_by=user_id,
            )

        # Verify DISPATCH_REVERSAL transaction was created
        from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
        tx_models = [obj for obj in added_objects if isinstance(obj, InventoryTransactionModel)]
        assert len(tx_models) == 1
        tx = tx_models[0]
        assert tx.transaction_type == "DISPATCH_REVERSAL"
        assert float(tx.quantity) == 5.0  # positive quantity
        assert tx.material_id == variant_id
        assert tx.reference_type == "delivery"
        assert tx.reference_id == delivery.id

    @pytest.mark.asyncio
    async def test_cancel_updates_so_line_dispatched_quantity(self):
        """Cancellation subtracts cancelled quantities from SO line dispatched_quantity (Req 33.3)."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        service = DeliveryService(session)

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        so_line_id = uuid.uuid4()
        variant_id = uuid.uuid4()

        so_line = _make_sales_order_line(line_id=so_line_id, product_id=variant_id, dispatched_quantity=8.0)
        order = _make_sales_order(tenant_id=tenant_id, lines=[so_line])
        dl = _make_delivery_line(sales_order_line_id=so_line_id, variant_id=variant_id, quantity=5.0)
        delivery = _make_delivery(tenant_id=tenant_id, sales_order_id=order.id, status="DRAFT", lines=[dl])

        service.get = AsyncMock(return_value=delivery)
        service._sales_order_or_error = AsyncMock(return_value=order)

        with patch("backend.app.application.delivery.delivery_service.AuditLogService") as mock_audit_cls, \
             patch("backend.app.application.delivery.delivery_service.NotificationService") as mock_notif_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            mock_notif = AsyncMock()
            mock_notif_cls.return_value = mock_notif

            await service.cancel(
                tenant_id=tenant_id,
                delivery_id=delivery.id,
                cancelled_by=user_id,
            )

        # dispatched_quantity should be reduced by 5 (from 8 to 3)
        assert so_line.dispatched_quantity == 3.0

    @pytest.mark.asyncio
    async def test_cancel_dispatched_quantity_does_not_go_below_zero(self):
        """dispatched_quantity should not go below zero after cancellation."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        service = DeliveryService(session)

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        so_line_id = uuid.uuid4()
        variant_id = uuid.uuid4()

        # dispatched_quantity is 2 but delivery line has 5 — shouldn't go below 0
        so_line = _make_sales_order_line(line_id=so_line_id, product_id=variant_id, dispatched_quantity=2.0)
        order = _make_sales_order(tenant_id=tenant_id, lines=[so_line])
        dl = _make_delivery_line(sales_order_line_id=so_line_id, variant_id=variant_id, quantity=5.0)
        delivery = _make_delivery(tenant_id=tenant_id, sales_order_id=order.id, status="DRAFT", lines=[dl])

        service.get = AsyncMock(return_value=delivery)
        service._sales_order_or_error = AsyncMock(return_value=order)

        with patch("backend.app.application.delivery.delivery_service.AuditLogService") as mock_audit_cls, \
             patch("backend.app.application.delivery.delivery_service.NotificationService") as mock_notif_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            mock_notif = AsyncMock()
            mock_notif_cls.return_value = mock_notif

            await service.cancel(
                tenant_id=tenant_id,
                delivery_id=delivery.id,
                cancelled_by=user_id,
            )

        # dispatched_quantity should be 0, not negative
        assert so_line.dispatched_quantity == 0.0

    @pytest.mark.asyncio
    async def test_cancel_handles_multiple_delivery_lines(self):
        """Cancellation with multiple lines creates one DISPATCH_REVERSAL per line."""
        session = AsyncMock()
        session.flush = AsyncMock()

        service = DeliveryService(session)

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        so_line_id_1 = uuid.uuid4()
        so_line_id_2 = uuid.uuid4()
        variant_id_1 = uuid.uuid4()
        variant_id_2 = uuid.uuid4()

        so_line_1 = _make_sales_order_line(line_id=so_line_id_1, product_id=variant_id_1, dispatched_quantity=10.0)
        so_line_2 = _make_sales_order_line(line_id=so_line_id_2, product_id=variant_id_2, dispatched_quantity=6.0)
        order = _make_sales_order(tenant_id=tenant_id, lines=[so_line_1, so_line_2])

        dl_1 = _make_delivery_line(sales_order_line_id=so_line_id_1, variant_id=variant_id_1, quantity=4.0)
        dl_2 = _make_delivery_line(sales_order_line_id=so_line_id_2, variant_id=variant_id_2, quantity=3.0)
        delivery = _make_delivery(tenant_id=tenant_id, sales_order_id=order.id, status="PACKING", lines=[dl_1, dl_2])

        service.get = AsyncMock(return_value=delivery)
        service._sales_order_or_error = AsyncMock(return_value=order)

        added_objects = []
        session.add = lambda obj: added_objects.append(obj)

        with patch("backend.app.application.delivery.delivery_service.AuditLogService") as mock_audit_cls, \
             patch("backend.app.application.delivery.delivery_service.NotificationService") as mock_notif_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            mock_notif = AsyncMock()
            mock_notif_cls.return_value = mock_notif

            await service.cancel(
                tenant_id=tenant_id,
                delivery_id=delivery.id,
                cancelled_by=user_id,
            )

        from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
        tx_models = [obj for obj in added_objects if isinstance(obj, InventoryTransactionModel)]
        assert len(tx_models) == 2
        assert float(tx_models[0].quantity) == 4.0
        assert float(tx_models[1].quantity) == 3.0
        assert so_line_1.dispatched_quantity == 6.0  # 10 - 4
        assert so_line_2.dispatched_quantity == 3.0  # 6 - 3


class TestDeliveryCancellationAuditAndNotification:
    """Req 33.6, 33.7: Create audit_log entry and notification."""

    @pytest.mark.asyncio
    async def test_cancel_creates_audit_log_entry(self):
        """Cancellation creates an audit_log entry (Req 33.6)."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        service = DeliveryService(session)

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        so_line_id = uuid.uuid4()
        variant_id = uuid.uuid4()

        so_line = _make_sales_order_line(line_id=so_line_id, product_id=variant_id, dispatched_quantity=5.0)
        order = _make_sales_order(tenant_id=tenant_id, lines=[so_line])
        dl = _make_delivery_line(sales_order_line_id=so_line_id, variant_id=variant_id, quantity=5.0)
        delivery = _make_delivery(tenant_id=tenant_id, sales_order_id=order.id, status="DRAFT", lines=[dl])

        service.get = AsyncMock(return_value=delivery)
        service._sales_order_or_error = AsyncMock(return_value=order)

        with patch("backend.app.application.delivery.delivery_service.AuditLogService") as mock_audit_cls, \
             patch("backend.app.application.delivery.delivery_service.NotificationService") as mock_notif_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            mock_notif = AsyncMock()
            mock_notif_cls.return_value = mock_notif

            await service.cancel(
                tenant_id=tenant_id,
                delivery_id=delivery.id,
                cancelled_by=user_id,
                reason="Out of stock",
            )

            # Verify audit log was called
            mock_audit.log_action.assert_called_once()
            call_kwargs = mock_audit.log_action.call_args[1]
            assert call_kwargs["tenant_id"] == tenant_id
            assert call_kwargs["user_id"] == user_id
            assert call_kwargs["action_type"] == "cancel_delivery"
            assert call_kwargs["entity_type"] == "delivery"
            assert call_kwargs["entity_id"] == delivery.id
            assert call_kwargs["reason"] == "Out of stock"
            assert "sales_order_id" in call_kwargs["metadata"]

    @pytest.mark.asyncio
    async def test_cancel_creates_notification(self):
        """Cancellation creates delivery_cancelled notification (Req 33.7)."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        service = DeliveryService(session)

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        so_line_id = uuid.uuid4()
        variant_id = uuid.uuid4()

        so_line = _make_sales_order_line(line_id=so_line_id, product_id=variant_id, dispatched_quantity=5.0)
        order = _make_sales_order(tenant_id=tenant_id, order_number="SO-000042", lines=[so_line])
        dl = _make_delivery_line(sales_order_line_id=so_line_id, variant_id=variant_id, quantity=5.0)
        delivery = _make_delivery(
            tenant_id=tenant_id,
            sales_order_id=order.id,
            delivery_number="DO-000007",
            status="DRAFT",
            lines=[dl],
        )

        service.get = AsyncMock(return_value=delivery)
        service._sales_order_or_error = AsyncMock(return_value=order)

        with patch("backend.app.application.delivery.delivery_service.AuditLogService") as mock_audit_cls, \
             patch("backend.app.application.delivery.delivery_service.NotificationService") as mock_notif_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            mock_notif = AsyncMock()
            mock_notif_cls.return_value = mock_notif

            await service.cancel(
                tenant_id=tenant_id,
                delivery_id=delivery.id,
                cancelled_by=user_id,
            )

            # Verify notification was sent
            mock_notif.notify_delivery_cancelled.assert_called_once_with(
                tenant_id=tenant_id,
                delivery_id=delivery.id,
                delivery_number="DO-000007",
                order_number="SO-000042",
            )
