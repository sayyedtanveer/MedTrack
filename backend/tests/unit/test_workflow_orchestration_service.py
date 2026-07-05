"""
Unit tests for WorkflowOrchestrationService new event handlers.

Tests cover:
- on_fg_received: FG reservation for linked SO, full allocation check
- on_goods_received: Inventory update, pending WO check, auto-reserve
- on_cancellation: Reservation release, audit entries
- on_exception: Hold/delay patterns, escalation notifications
- on_auto_transition: Idempotency checks
- on_order_delivered (extended): Auto-invoice creation, error handling
- on_payment_received (extended): Full/partial payment threshold
- on_work_order_released (extended): Purchase Requisition creation
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import pytest

from backend.app.application.manufacturing.services.workflow_orchestration_service import (
    WorkflowOrchestrationService,
)
from backend.app.domain.sales.value_objects.order_status import OrderStatus
from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus


def _make_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


def _make_service(session=None):
    """Create a service with mocked dependencies."""
    if session is None:
        session = _make_session()

    with patch(
        "backend.app.application.manufacturing.services.workflow_orchestration_service.InventoryService"
    ) as mock_inv, patch(
        "backend.app.application.manufacturing.services.workflow_orchestration_service.NotificationService"
    ) as mock_notif:
        mock_inv_instance = AsyncMock()
        mock_inv.return_value = mock_inv_instance
        mock_notif_instance = AsyncMock()
        mock_notif.return_value = mock_notif_instance

        service = WorkflowOrchestrationService(session)
        # Patch the services back since constructor already ran
        service.inventory_service = mock_inv_instance
        service.notification_service = mock_notif_instance

    return service


def _make_work_order(
    tenant_id=None,
    work_order_id=None,
    sales_order_id=None,
    product_id=None,
    status=WorkOrderStatus.FG_RECEIVED.value,
    produced_quantity=100,
    scrap_quantity=5,
):
    wo = MagicMock()
    wo.id = work_order_id or uuid.uuid4()
    wo.tenant_id = tenant_id or uuid.uuid4()
    wo.sales_order_id = sales_order_id
    wo.product_id = product_id or uuid.uuid4()
    wo.status = status
    wo.produced_quantity = produced_quantity
    wo.scrap_quantity = scrap_quantity
    wo.wo_number = "WO-001"
    wo.created_by = uuid.uuid4()
    wo.due_date = "2025-06-01"
    wo.is_deleted = False
    wo.updated_at = datetime.now(timezone.utc)
    return wo


def _make_sales_order(
    tenant_id=None,
    sales_order_id=None,
    status=OrderStatus.PRODUCTION.value,
    grand_total=1000.0,
):
    so = MagicMock()
    so.id = sales_order_id or uuid.uuid4()
    so.tenant_id = tenant_id or uuid.uuid4()
    so.status = status
    so.order_number = "SO-001"
    so.grand_total = grand_total
    so.is_deleted = False
    so.updated_at = datetime.now(timezone.utc)
    return so


def _make_so_line(
    line_id=None,
    sales_order_id=None,
    product_id=None,
    work_order_id=None,
    quantity=100.0,
    allocated_quantity=0.0,
):
    line = MagicMock()
    line.id = line_id or uuid.uuid4()
    line.sales_order_id = sales_order_id or uuid.uuid4()
    line.product_id = product_id or uuid.uuid4()
    line.work_order_id = work_order_id
    line.quantity = quantity
    line.allocated_quantity = allocated_quantity
    line.updated_at = datetime.now(timezone.utc)
    return line


class TestOnAutoTransition:
    """Test idempotent wrapper for auto-transitions."""

    @pytest.mark.asyncio
    async def test_new_operation_returns_not_duplicate(self):
        """First call for an operation should return duplicate=False."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        # Mock: no existing audit log entry found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.session.execute.return_value = mock_result

        result = await service.on_auto_transition(
            tenant_id=tenant_id,
            operation_key="test_op",
            entity_type="sales_order",
            entity_id=entity_id,
        )

        assert result["duplicate"] is False
        assert result["operation_key"] == "test_op"

    @pytest.mark.asyncio
    async def test_duplicate_operation_returns_noop(self):
        """Second call for same operation should return duplicate=True."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        # Mock: existing audit log entry found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid.uuid4()  # existing ID
        service.session.execute.return_value = mock_result

        result = await service.on_auto_transition(
            tenant_id=tenant_id,
            operation_key="test_op",
            entity_type="sales_order",
            entity_id=entity_id,
        )

        assert result["duplicate"] is True
        assert "no-op" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_audit_check_failure_proceeds_gracefully(self):
        """If audit log check fails, operation proceeds (non-blocking)."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        # Mock: execute raises an exception
        service.session.execute.side_effect = RuntimeError("DB error")

        result = await service.on_auto_transition(
            tenant_id=tenant_id,
            operation_key="test_op",
            entity_type="sales_order",
            entity_id=entity_id,
        )

        # Should proceed (not duplicate) despite error
        assert result["duplicate"] is False


class TestOnFgReceived:
    """Test FG receipt reservation for linked SO."""

    @pytest.mark.asyncio
    async def test_no_linked_sales_order(self):
        """WO without linked SO returns early."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        wo = _make_work_order(tenant_id=tenant_id, sales_order_id=None)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = wo
        service.session.execute.return_value = mock_result

        result = await service.on_fg_received(
            tenant_id=tenant_id,
            work_order_id=wo.id,
            received_by=uuid.uuid4(),
        )

        assert result["reserved"] is False
        assert "no linked sales order" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_reserves_fg_for_linked_so(self):
        """FG receipt reserves goods for linked SO line."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        so_id = uuid.uuid4()
        product_id = uuid.uuid4()
        wo = _make_work_order(
            tenant_id=tenant_id,
            sales_order_id=so_id,
            product_id=product_id,
            produced_quantity=100,
            scrap_quantity=5,
        )
        so = _make_sales_order(tenant_id=tenant_id, sales_order_id=so_id, status=OrderStatus.PRODUCTION.value)
        so_line = _make_so_line(
            sales_order_id=so_id,
            product_id=product_id,
            work_order_id=wo.id,
            quantity=100.0,
            allocated_quantity=0.0,
        )

        # Mock the sequence of execute calls:
        # 1. Get work order
        # 2. Get sales order
        # 3. Get SO lines (for reservation)
        # 4. Get all SO lines (for full allocation check)
        call_count = [0]
        
        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:  # work order
                result.scalar_one_or_none.return_value = wo
            elif call_count[0] == 2:  # sales order
                result.scalar_one_or_none.return_value = so
            elif call_count[0] == 3:  # SO lines for reservation
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [so_line]
                result.scalars.return_value = scalars_mock
            elif call_count[0] == 4:  # all SO lines for allocation check
                scalars_mock = MagicMock()
                # After reservation, allocated_quantity should be updated
                so_line.allocated_quantity = 95.0  # min(95 fg_qty, 100 needed)
                scalars_mock.all.return_value = [so_line]
                result.scalars.return_value = scalars_mock
            return result

        service.session.execute = mock_execute
        
        # Mock _resolve_finished_good_material_id
        service._resolve_finished_good_material_id = AsyncMock(return_value=product_id)

        result = await service.on_fg_received(
            tenant_id=tenant_id,
            work_order_id=wo.id,
            received_by=uuid.uuid4(),
        )

        assert result["fg_quantity"] == 95.0  # 100 - 5 scrap
        service.inventory_service.reserve_sales_stock.assert_called_once()


class TestOnCancellation:
    """Test cancellation reservation release."""

    @pytest.mark.asyncio
    async def test_sales_order_cancellation_releases_reservations(self):
        """Cancelling an SO releases all line reservations."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        so_id = uuid.uuid4()
        material_id = uuid.uuid4()
        
        so_line = _make_so_line(
            sales_order_id=so_id,
            product_id=material_id,
            allocated_quantity=50.0,
        )
        material = MagicMock()
        material.id = material_id

        call_count = [0]
        
        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:  # SO lines
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [so_line]
                result.scalars.return_value = scalars_mock
            elif call_count[0] == 2:  # material lookup
                result.scalar_one_or_none.return_value = material
            elif call_count[0] == 3:  # linked WOs
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result.scalars.return_value = scalars_mock
            return result

        service.session.execute = mock_execute

        result = await service.on_cancellation(
            tenant_id=tenant_id,
            entity_type="sales_order",
            entity_id=so_id,
            cancelled_by=uuid.uuid4(),
        )

        assert result["reservations_released"] >= 1
        service.inventory_service.release_sales_reservation.assert_called_once()

    @pytest.mark.asyncio
    async def test_work_order_cancellation_releases_reservations(self):
        """Cancelling a WO releases its material reservations."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        wo = _make_work_order(tenant_id=tenant_id)

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:  # work order
                result.scalar_one_or_none.return_value = wo
            elif call_count[0] == 2:  # WO materials
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result.scalars.return_value = scalars_mock
            return result

        service.session.execute = mock_execute
        service.inventory_service.cancel_work_order_reservation = AsyncMock(return_value=Decimal("0"))

        result = await service.on_cancellation(
            tenant_id=tenant_id,
            entity_type="work_order",
            entity_id=wo.id,
            cancelled_by=uuid.uuid4(),
        )

        assert "cancellation processed" in result["message"].lower()


class TestOnException:
    """Test exception handling patterns."""

    @pytest.mark.asyncio
    async def test_machine_breakdown_applies_hold(self):
        """Machine breakdown puts WO on PRODUCTION_HOLD."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        wo = _make_work_order(
            tenant_id=tenant_id,
            status=WorkOrderStatus.IN_PRODUCTION.value,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = wo
        service.session.execute.return_value = mock_result

        result = await service.on_exception(
            tenant_id=tenant_id,
            exception_type="machine_breakdown",
            work_order_id=wo.id,
            details={"reason": "Motor failure", "reported_by": uuid.uuid4()},
        )

        assert result["hold_applied"] is True
        assert wo.status == "PRODUCTION_HOLD"
        service.notification_service.create_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_supplier_delay_creates_notification(self):
        """Supplier delay creates escalation notification without hold."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        wo = _make_work_order(
            tenant_id=tenant_id,
            status=WorkOrderStatus.MATERIAL_PENDING.value,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = wo
        service.session.execute.return_value = mock_result

        result = await service.on_exception(
            tenant_id=tenant_id,
            exception_type="supplier_delay",
            work_order_id=wo.id,
            details={"reason": "Shipment delayed", "delay_days": 5},
        )

        assert result["hold_applied"] is False
        service.notification_service.create_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_quality_issue_creates_escalation(self):
        """Quality issue creates QC escalation notification."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        wo = _make_work_order(
            tenant_id=tenant_id,
            status=WorkOrderStatus.QC_PENDING.value,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = wo
        service.session.execute.return_value = mock_result

        result = await service.on_exception(
            tenant_id=tenant_id,
            exception_type="quality_issue",
            work_order_id=wo.id,
            details={"reason": "Contamination found"},
        )

        assert result["hold_applied"] is False
        service.notification_service.create_notification.assert_called_once()


class TestOnOrderDelivered:
    """Test extended on_order_delivered with auto-invoice."""

    @pytest.mark.asyncio
    async def test_creates_invoice_and_transitions_to_invoiced(self):
        """Successful delivery creates invoice and transitions SO to INVOICED."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        so_id = uuid.uuid4()
        so = _make_sales_order(
            tenant_id=tenant_id,
            sales_order_id=so_id,
            status=OrderStatus.DELIVERED.value,
        )

        # Mock on_auto_transition to pass through
        service.on_auto_transition = AsyncMock(return_value={"duplicate": False})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = so
        service.session.execute.return_value = mock_result

        mock_invoice = MagicMock()
        mock_invoice.id = uuid.uuid4()

        with patch(
            "backend.app.application.finance.finance_service.FinanceService"
        ) as MockFinance:
            mock_finance_instance = AsyncMock()
            mock_finance_instance.create_invoice_from_sales_order.return_value = mock_invoice
            MockFinance.return_value = mock_finance_instance

            result = await service.on_order_delivered(
                tenant_id=tenant_id,
                sales_order_id=so_id,
            )

        assert result["invoice_created"] is True
        assert so.status == OrderStatus.INVOICED.value

    @pytest.mark.asyncio
    async def test_invoice_failure_leaves_so_delivered(self):
        """If invoice creation fails, SO stays DELIVERED and notification is sent."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        so_id = uuid.uuid4()
        so = _make_sales_order(
            tenant_id=tenant_id,
            sales_order_id=so_id,
            status=OrderStatus.DELIVERED.value,
        )

        service.on_auto_transition = AsyncMock(return_value={"duplicate": False})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = so
        service.session.execute.return_value = mock_result

        with patch(
            "backend.app.application.finance.finance_service.FinanceService"
        ) as MockFinance:
            mock_finance_instance = AsyncMock()
            mock_finance_instance.create_invoice_from_sales_order.side_effect = ValueError("Client not found")
            MockFinance.return_value = mock_finance_instance

            result = await service.on_order_delivered(
                tenant_id=tenant_id,
                sales_order_id=so_id,
            )

        assert result["invoice_created"] is False
        assert "error" in result
        assert so.status == OrderStatus.DELIVERED.value  # Unchanged
        # Two notifications: dispatch_completed + invoice_creation_failed
        assert service.notification_service.create_notification.call_count == 2
        call_types = [
            call.kwargs.get("notification_type")
            for call in service.notification_service.create_notification.call_args_list
        ]
        assert "dispatch_completed" in call_types
        assert "invoice_creation_failed" in call_types

    @pytest.mark.asyncio
    async def test_duplicate_delivery_returns_noop(self):
        """Duplicate delivery call returns early."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        so_id = uuid.uuid4()

        service.on_auto_transition = AsyncMock(return_value={
            "duplicate": True,
            "operation_key": f"delivered:{so_id}",
            "entity_type": "sales_order",
            "entity_id": str(so_id),
            "message": "Operation already completed - no-op",
        })

        result = await service.on_order_delivered(
            tenant_id=tenant_id,
            sales_order_id=so_id,
        )

        assert result["duplicate"] is True


class TestOnPaymentReceived:
    """Test extended payment received logic."""

    @pytest.mark.asyncio
    async def test_full_payment_transitions_to_completed(self):
        """Full payment transitions SO: INVOICED → PAYMENT_RECEIVED → COMPLETED."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        so_id = uuid.uuid4()
        so = _make_sales_order(
            tenant_id=tenant_id,
            sales_order_id=so_id,
            status=OrderStatus.INVOICED.value,
            grand_total=1000.0,
        )

        service.on_auto_transition = AsyncMock(return_value={"duplicate": False})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = so
        service.session.execute.return_value = mock_result
        
        # Mock the payment sum query - use side_effect to handle multiple execute calls
        service.session.scalar = AsyncMock(return_value=1000.0)

        result = await service.on_payment_received(
            tenant_id=tenant_id,
            sales_order_id=so_id,
            payment_amount=Decimal("1000"),
        )

        assert result["fully_paid"] is True
        assert so.status == OrderStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_full_payment_triggers_reservation_release_and_audit_log(self):
        """Full payment completion should release remaining sales reservations."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        so_id = uuid.uuid4()
        so = _make_sales_order(
            tenant_id=tenant_id,
            sales_order_id=so_id,
            status=OrderStatus.INVOICED.value,
            grand_total=1000.0,
        )

        service.on_auto_transition = AsyncMock(return_value={"duplicate": False})
        service._release_sales_order_reservations = AsyncMock(return_value=[{"sales_order_line_id": str(uuid.uuid4()), "quantity_released": 50.0}])

        with patch(
            "backend.app.services.audit_log_service.AuditLogService"
        ) as MockAuditService:
            mock_audit_instance = AsyncMock()
            mock_audit_instance.log_action = AsyncMock()
            MockAuditService.return_value = mock_audit_instance

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = so
            service.session.execute.return_value = mock_result
            service.session.scalar = AsyncMock(return_value=1000.0)

            result = await service.on_payment_received(
                tenant_id=tenant_id,
                sales_order_id=so_id,
                payment_amount=Decimal("1000"),
            )

        assert result["fully_paid"] is True
        assert so.status == OrderStatus.COMPLETED.value
        service._release_sales_order_reservations.assert_awaited_once()
        MockAuditService.return_value.log_action.assert_awaited_once()
        logged_call = MockAuditService.return_value.log_action.await_args.kwargs
        assert logged_call["action_type"] == "lifecycle_completed"

    @pytest.mark.asyncio
    async def test_partial_payment_stays_invoiced(self):
        """Partial payment leaves SO in INVOICED status."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        so_id = uuid.uuid4()
        so = _make_sales_order(
            tenant_id=tenant_id,
            sales_order_id=so_id,
            status=OrderStatus.INVOICED.value,
            grand_total=1000.0,
        )

        service.on_auto_transition = AsyncMock(return_value={"duplicate": False})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = so
        service.session.execute.return_value = mock_result
        
        # Payment query fails (fallback to payment_amount)
        service.session.scalar = AsyncMock(side_effect=Exception("DB error"))

        result = await service.on_payment_received(
            tenant_id=tenant_id,
            sales_order_id=so_id,
            payment_amount=Decimal("500"),
        )

        assert result["fully_paid"] is False
        assert so.status == OrderStatus.INVOICED.value


class TestOnGoodsReceived:
    """Test goods receipt event handler."""

    @pytest.mark.asyncio
    async def test_updates_inventory_on_receipt(self):
        """Goods receipt calls receive_stock."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        po_id = uuid.uuid4()
        material_id = uuid.uuid4()

        # Mock execute to return no pending WOs
        mock_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.unique.return_value = scalars_mock
        scalars_mock.all.return_value = []
        mock_result.scalars.return_value = scalars_mock
        service.session.execute.return_value = mock_result

        result = await service.on_goods_received(
            tenant_id=tenant_id,
            purchase_order_id=po_id,
            material_id=material_id,
            quantity=Decimal("100"),
        )

        service.inventory_service.receive_stock.assert_called_once()
        assert result["quantity_received"] == 100.0
        assert result["pending_wos_checked"] == 0


class TestOnWorkOrderReleased:
    """Test extended work order release with Purchase Requisitions."""

    @pytest.mark.asyncio
    async def test_creates_purchase_requisitions_for_shortages(self):
        """WO release creates PRs for material shortages."""
        service = _make_service()
        tenant_id = uuid.uuid4()
        wo_id = uuid.uuid4()
        material_id = uuid.uuid4()
        wo = _make_work_order(
            tenant_id=tenant_id,
            work_order_id=wo_id,
            status=WorkOrderStatus.MATERIAL_PENDING.value,
        )

        # Mock: WO found
        mock_wo_result = MagicMock()
        mock_wo_result.scalar_one_or_none.return_value = wo

        # Mock: no existing PR
        mock_pr_result = MagicMock()
        mock_pr_result.scalar_one_or_none.return_value = None

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_wo_result
            return mock_pr_result

        service.session.execute = mock_execute

        # Mock MaterialPlanningService
        with patch(
            "backend.app.application.manufacturing.services.material_planning_service.MaterialPlanningService"
        ) as MockPlanning:
            mock_planning_instance = AsyncMock()
            MockPlanning.return_value = mock_planning_instance

            # Mock shortages
            service.inventory_service.get_shortages_for_work_order = AsyncMock(
                return_value=[
                    {"material_id": material_id, "shortage_quantity": 50.0}
                ]
            )

            result = await service.on_work_order_released(
                tenant_id=tenant_id,
                work_order_id=wo_id,
            )

        assert len(result["requisitions_created"]) == 1
        service.session.add.assert_called()  # PR was added
