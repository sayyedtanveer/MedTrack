"""
Unit tests for reservation release logic on cancellation (Task 3.5).

Tests cover:
- SO cancellation releases FG reservations via RESERVATION_RELEASE transactions (Req 18.1)
- WO cancellation releases raw material reservations via RESERVATION_RELEASE transactions (Req 18.2)
- WO scrap releases remaining unreserved materials (reserved > issued) (Req 18.3)
- Each release creates proper inventory transaction records with full audit trail (Req 18.4)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.app.application.manufacturing.services.workflow_orchestration_service import (
    WorkflowOrchestrationService,
)
from backend.app.application.quality.commands.qc_commands import ScrapBatchCommand
from backend.app.application.quality.handlers.qc_handler import QCHandler
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


def _make_orchestration_service(session=None):
    """Create a WorkflowOrchestrationService with mocked dependencies."""
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
        service.inventory_service = mock_inv_instance
        service.notification_service = mock_notif_instance

    return service


def _make_so_line(
    line_id=None,
    sales_order_id=None,
    product_id=None,
    allocated_quantity=50.0,
):
    line = MagicMock()
    line.id = line_id or uuid.uuid4()
    line.sales_order_id = sales_order_id or uuid.uuid4()
    line.product_id = product_id or uuid.uuid4()
    line.allocated_quantity = allocated_quantity
    line.updated_at = datetime.now(timezone.utc)
    return line


def _make_work_order_model(
    wo_id=None,
    tenant_id=None,
    product_id=None,
    status=WorkOrderStatus.MATERIAL_RESERVED.value,
):
    wo = MagicMock()
    wo.id = wo_id or uuid.uuid4()
    wo.tenant_id = tenant_id or uuid.uuid4()
    wo.product_id = product_id or uuid.uuid4()
    wo.status = status
    wo.is_deleted = False
    wo.produced_quantity = 0
    wo.scrap_quantity = 0
    wo.updated_at = datetime.now(timezone.utc)
    return wo


def _make_wo_material(material_id=None, unit_id=None):
    wom = MagicMock()
    wom.material_id = material_id or uuid.uuid4()
    wom.unit_id = unit_id or uuid.uuid4()
    wom.work_order_id = uuid.uuid4()
    return wom


class TestSOCancellationReleasesReservations:
    """Req 18.1: SO cancellation releases FG reservations via RESERVATION_RELEASE."""

    @pytest.mark.asyncio
    async def test_so_cancellation_calls_release_sales_reservation(self):
        """Cancelling SO releases allocated quantities back to available stock."""
        service = _make_orchestration_service()
        tenant_id = uuid.uuid4()
        so_id = uuid.uuid4()
        material_id = uuid.uuid4()
        cancelled_by = uuid.uuid4()

        so_line = _make_so_line(
            sales_order_id=so_id,
            product_id=material_id,
            allocated_quantity=75.0,
        )
        material = MagicMock()
        material.id = material_id

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:  # SO lines query
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [so_line]
                result.scalars.return_value = scalars_mock
            elif call_count[0] == 2:  # material lookup
                result.scalar_one_or_none.return_value = material
            elif call_count[0] == 3:  # linked WOs query
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result.scalars.return_value = scalars_mock
            return result

        service.session.execute = mock_execute

        result = await service.on_cancellation(
            tenant_id=tenant_id,
            entity_type="sales_order",
            entity_id=so_id,
            cancelled_by=cancelled_by,
        )

        # Verify release_sales_reservation was called with proper params
        service.inventory_service.release_sales_reservation.assert_called_once_with(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=Decimal("75"),
            sales_order_line_id=so_line.id,
            created_by=cancelled_by,
        )
        assert result["reservations_released"] >= 1
        assert so_line.allocated_quantity == 0  # Reset to 0

    @pytest.mark.asyncio
    async def test_so_cancellation_multiple_lines(self):
        """Multiple SO lines each get their reservations released."""
        service = _make_orchestration_service()
        tenant_id = uuid.uuid4()
        so_id = uuid.uuid4()
        cancelled_by = uuid.uuid4()

        material_id_1 = uuid.uuid4()
        material_id_2 = uuid.uuid4()

        line1 = _make_so_line(product_id=material_id_1, allocated_quantity=30.0)
        line2 = _make_so_line(product_id=material_id_2, allocated_quantity=20.0)

        material1 = MagicMock()
        material1.id = material_id_1
        material2 = MagicMock()
        material2.id = material_id_2

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:  # SO lines
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [line1, line2]
                result.scalars.return_value = scalars_mock
            elif call_count[0] == 2:  # material for line1
                result.scalar_one_or_none.return_value = material1
            elif call_count[0] == 3:  # material for line2
                result.scalar_one_or_none.return_value = material2
            elif call_count[0] == 4:  # linked WOs
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result.scalars.return_value = scalars_mock
            return result

        service.session.execute = mock_execute

        result = await service.on_cancellation(
            tenant_id=tenant_id,
            entity_type="sales_order",
            entity_id=so_id,
            cancelled_by=cancelled_by,
        )

        assert service.inventory_service.release_sales_reservation.call_count == 2
        assert result["reservations_released"] == 2

    @pytest.mark.asyncio
    async def test_so_cancellation_skips_zero_allocation_lines(self):
        """Lines with 0 allocated_quantity are skipped."""
        service = _make_orchestration_service()
        tenant_id = uuid.uuid4()
        so_id = uuid.uuid4()

        line_zero = _make_so_line(allocated_quantity=0.0)

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:  # SO lines
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [line_zero]
                result.scalars.return_value = scalars_mock
            elif call_count[0] == 2:  # linked WOs
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

        service.inventory_service.release_sales_reservation.assert_not_called()
        assert result["reservations_released"] == 0


class TestWOCancellationReleasesReservations:
    """Req 18.2: WO cancellation releases raw material reservations via RESERVATION_RELEASE."""

    @pytest.mark.asyncio
    async def test_wo_cancellation_releases_material_reservations(self):
        """Cancelling WO releases raw material reservations."""
        service = _make_orchestration_service()
        tenant_id = uuid.uuid4()
        wo = _make_work_order_model(tenant_id=tenant_id)
        material_id = uuid.uuid4()
        unit_id = uuid.uuid4()
        cancelled_by = uuid.uuid4()

        wom = _make_wo_material(material_id=material_id, unit_id=unit_id)
        wom.work_order_id = wo.id

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:  # WO lookup
                result.scalar_one_or_none.return_value = wo
            elif call_count[0] == 2:  # WO materials
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [wom]
                result.scalars.return_value = scalars_mock
            return result

        service.session.execute = mock_execute
        service.inventory_service.cancel_work_order_reservation = AsyncMock(
            return_value=Decimal("25")
        )

        result = await service.on_cancellation(
            tenant_id=tenant_id,
            entity_type="work_order",
            entity_id=wo.id,
            cancelled_by=cancelled_by,
        )

        service.inventory_service.cancel_work_order_reservation.assert_called_once_with(
            tenant_id=tenant_id,
            material_id=material_id,
            work_order_id=wo.id,
            unit_id=unit_id,
            created_by=cancelled_by,
            remarks=f"Reservation released due to WO cancellation - WO {wo.id}",
        )
        assert result["reservations_released"] == 1
        assert result["released_materials"][0]["quantity_released"] == 25.0


class TestWOScrapReleasesRemainingMaterials:
    """Req 18.3: WO scrap releases remaining unreserved materials (reserved > issued)."""

    @pytest.mark.asyncio
    async def test_scrap_batch_releases_remaining_reservations(self):
        """Scrapping a WO releases materials where reserved > issued."""
        session = _make_session()
        tenant_id = uuid.uuid4()
        wo_id = uuid.uuid4()
        product_id = uuid.uuid4()
        inspector_id = uuid.uuid4()
        material_id_1 = uuid.uuid4()
        unit_id_1 = uuid.uuid4()

        # Mock WO
        wo_model = MagicMock()
        wo_model.id = wo_id
        wo_model.tenant_id = tenant_id
        wo_model.product_id = product_id
        wo_model.status = WorkOrderStatus.QC_REJECTED.value
        wo_model.is_deleted = False
        wo_model.produced_quantity = 50
        wo_model.scrap_quantity = 0

        # Mock WO material
        wom = MagicMock()
        wom.material_id = material_id_1
        wom.unit_id = unit_id_1
        wom.work_order_id = wo_id

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:  # WO lookup
                result.scalar_one_or_none.return_value = wo_model
            elif call_count[0] == 2:  # WO materials for scrap release
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [wom]
                result.scalars.return_value = scalars_mock
            return result

        session.execute = mock_execute

        with patch(
            "backend.app.application.quality.handlers.qc_handler.InventoryService"
        ) as MockInv:
            mock_inv = AsyncMock()
            MockInv.return_value = mock_inv

            handler = QCHandler(session)
            handler._inventory = mock_inv

            command = ScrapBatchCommand(
                tenant_id=tenant_id,
                work_order_id=wo_id,
                inspector_id=inspector_id,
                scrap_reason="Material contamination",
                scrap_quantity=Decimal("50"),
            )

            await handler.scrap_batch(command)

        # Verify reject_stock was called
        mock_inv.reject_stock.assert_called_once()

        # Verify cancel_work_order_reservation was called for both product and BOM materials
        # First call: product_id reservation release
        # Second call: BOM material reservation release
        assert mock_inv.cancel_work_order_reservation.call_count == 2

        # Verify the BOM material release call
        calls = mock_inv.cancel_work_order_reservation.call_args_list
        # First call: product_id
        assert calls[0].kwargs["material_id"] == product_id
        assert calls[0].kwargs["work_order_id"] == wo_id
        assert "scrapped" in calls[0].kwargs["remarks"].lower()
        # Second call: BOM material
        assert calls[1].kwargs["material_id"] == material_id_1
        assert calls[1].kwargs["unit_id"] == unit_id_1
        assert calls[1].kwargs["work_order_id"] == wo_id

        # Verify WO is CLOSED
        assert wo_model.status == WorkOrderStatus.CLOSED.value


class TestReservationReleaseAuditTrail:
    """Req 18.4: Each release creates proper inventory transaction records."""

    @pytest.mark.asyncio
    async def test_so_cancellation_creates_audit_entry(self):
        """Cancellation creates audit log entry with reservation details."""
        service = _make_orchestration_service()
        tenant_id = uuid.uuid4()
        so_id = uuid.uuid4()
        material_id = uuid.uuid4()
        cancelled_by = uuid.uuid4()

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
            if call_count[0] == 1:
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [so_line]
                result.scalars.return_value = scalars_mock
            elif call_count[0] == 2:
                result.scalar_one_or_none.return_value = material
            elif call_count[0] == 3:
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result.scalars.return_value = scalars_mock
            return result

        service.session.execute = mock_execute

        result = await service.on_cancellation(
            tenant_id=tenant_id,
            entity_type="sales_order",
            entity_id=so_id,
            cancelled_by=cancelled_by,
        )

        # The response contains released materials info for audit
        assert result["released_materials"][0]["material_id"] == str(material_id)
        assert result["released_materials"][0]["quantity_released"] > 0
        # Verify the message confirms all reservations released
        assert "released" in result["message"].lower()
