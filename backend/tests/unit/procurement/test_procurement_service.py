"""
Unit tests for ProcurementService — procurement recovery loop.

Tests cover:
- PR approval → auto-PO creation (Req 17.3)
- PR rejection → planner notification (Req 17.8)
- Incoming QC pass → triggers on_goods_received (Req 17.4, 17.5, 17.6)
- Incoming QC failure → procurement notification (Req 17.7)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from backend.app.application.procurement.services.procurement_service import (
    ProcurementService,
)


# ─── Fixtures & Helpers ──────────────────────────────────────────────────────


def _make_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


def _make_pr(
    tenant_id=None,
    requisition_id=None,
    status="PENDING_APPROVAL",
    material_id=None,
    work_order_id=None,
    shortage_quantity=50.0,
):
    """Create a mock PurchaseRequisition."""
    pr = MagicMock()
    pr.id = requisition_id or uuid.uuid4()
    pr.tenant_id = tenant_id or uuid.uuid4()
    pr.requisition_number = f"PR-{uuid.uuid4().hex[:8].upper()}"
    pr.status = status
    pr.material_id = material_id or uuid.uuid4()
    pr.work_order_id = work_order_id or uuid.uuid4()
    pr.required_quantity = 100.0
    pr.shortage_quantity = shortage_quantity
    pr.created_by = uuid.uuid4()
    pr.approved_by = None
    pr.linked_po_id = None
    pr.is_deleted = False
    pr.updated_at = datetime.now(timezone.utc)
    return pr


def _make_material(tenant_id=None, material_id=None, preferred_supplier_id=None):
    """Create a mock Material."""
    mat = MagicMock()
    mat.id = material_id or uuid.uuid4()
    mat.tenant_id = tenant_id or uuid.uuid4()
    mat.name = "Test Material"
    mat.preferred_supplier_id = preferred_supplier_id
    return mat


def _make_grn(tenant_id=None, grn_id=None, purchase_order_id=None, status="received"):
    """Create a mock GRN with lines."""
    grn = MagicMock()
    grn.id = grn_id or uuid.uuid4()
    grn.tenant_id = tenant_id or uuid.uuid4()
    grn.purchase_order_id = purchase_order_id or uuid.uuid4()
    grn.grn_number = "GRN-001"
    grn.status = status
    grn.updated_by = None
    grn.updated_at = datetime.now(timezone.utc)

    # Create a GRN line
    line = MagicMock()
    line.id = uuid.uuid4()
    line.material_id = uuid.uuid4()
    line.received_quantity = 50.0
    line.accepted_quantity = 50.0
    line.rejected_quantity = 0
    line.is_deleted = False
    grn.lines = [line]

    return grn


# ─── Tests: PR Approval → Auto-PO Creation (Req 17.3) ───────────────────────


class TestApproveRequisition:
    """Test approve_requisition method — auto-PO creation on approval."""

    @pytest.mark.asyncio
    async def test_approve_creates_po_linked_to_pr(self):
        """PR approval creates a PO and links it back to the PR."""
        tenant_id = uuid.uuid4()
        approved_by = uuid.uuid4()
        supplier_id = uuid.uuid4()
        pr = _make_pr(tenant_id=tenant_id, shortage_quantity=25.0)

        material = _make_material(
            tenant_id=tenant_id,
            material_id=pr.material_id,
            preferred_supplier_id=supplier_id,
        )

        session = _make_session()

        # First execute: fetch PR
        # Second execute: fetch material
        call_count = [0]

        async def mock_execute(stmt, *args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # PR lookup
                result.scalar_one_or_none.return_value = pr
            elif call_count[0] == 2:
                # Material lookup
                result.scalar_one_or_none.return_value = material
            else:
                result.scalar_one_or_none.return_value = None
                result.scalars.return_value.all.return_value = []
            return result

        session.execute = AsyncMock(side_effect=mock_execute)

        service = ProcurementService(session)

        result = await service.approve_requisition(
            tenant_id=tenant_id,
            requisition_id=pr.id,
            approved_by=approved_by,
        )

        # PR should be updated to PO_CREATED
        assert pr.status == "PO_CREATED"
        assert pr.approved_by == approved_by
        assert pr.linked_po_id is not None

        # PO should be created (session.add called for PO and PO line)
        assert session.add.call_count >= 2  # PO + PO line
        assert result["status"] == "PO_CREATED"
        assert "purchase_order_id" in result
        assert result["supplier_id"] == str(supplier_id)

    @pytest.mark.asyncio
    async def test_approve_rejects_non_pending_pr(self):
        """Cannot approve a PR that is not in PENDING_APPROVAL status."""
        tenant_id = uuid.uuid4()
        pr = _make_pr(tenant_id=tenant_id, status="APPROVED")

        session = _make_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = pr
        session.execute = AsyncMock(return_value=result_mock)

        service = ProcurementService(session)

        with pytest.raises(ValueError, match="Cannot approve requisition"):
            await service.approve_requisition(
                tenant_id=tenant_id,
                requisition_id=pr.id,
                approved_by=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_approve_raises_on_not_found(self):
        """Raises ValueError if PR not found."""
        session = _make_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        service = ProcurementService(session)

        with pytest.raises(ValueError, match="not found"):
            await service.approve_requisition(
                tenant_id=uuid.uuid4(),
                requisition_id=uuid.uuid4(),
                approved_by=uuid.uuid4(),
            )


# ─── Tests: PR Rejection → Notification (Req 17.8) ──────────────────────────


class TestRejectRequisition:
    """Test reject_requisition method — notification to planner."""

    @pytest.mark.asyncio
    async def test_reject_updates_status_and_notifies(self):
        """PR rejection updates status and sends notification."""
        tenant_id = uuid.uuid4()
        rejected_by = uuid.uuid4()
        pr = _make_pr(tenant_id=tenant_id)

        session = _make_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = pr
        session.execute = AsyncMock(return_value=result_mock)

        service = ProcurementService(session)
        service.notification_service = AsyncMock()
        service.notification_service.notify_requisition_rejected = AsyncMock(
            return_value=uuid.uuid4()
        )

        result = await service.reject_requisition(
            tenant_id=tenant_id,
            requisition_id=pr.id,
            rejected_by=rejected_by,
            reason="Budget constraints",
        )

        assert pr.status == "REJECTED"
        assert result["status"] == "REJECTED"

        # Verify notification was sent
        service.notification_service.notify_requisition_rejected.assert_awaited_once_with(
            tenant_id=tenant_id,
            requisition_id=pr.id,
            requisition_number=pr.requisition_number,
        )

    @pytest.mark.asyncio
    async def test_reject_fails_for_non_pending(self):
        """Cannot reject a PR that is not PENDING_APPROVAL."""
        tenant_id = uuid.uuid4()
        pr = _make_pr(tenant_id=tenant_id, status="PO_CREATED")

        session = _make_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = pr
        session.execute = AsyncMock(return_value=result_mock)

        service = ProcurementService(session)

        with pytest.raises(ValueError, match="Cannot reject requisition"):
            await service.reject_requisition(
                tenant_id=tenant_id,
                requisition_id=pr.id,
                rejected_by=uuid.uuid4(),
            )


# ─── Tests: Incoming QC Passed → on_goods_received (Req 17.4-17.6) ──────────


class TestHandleIncomingQcPassed:
    """Test handle_incoming_qc_passed — triggers on_goods_received."""

    @pytest.mark.asyncio
    async def test_qc_pass_updates_grn_and_triggers_orchestration(self):
        """QC pass marks GRN as inspected and triggers on_goods_received."""
        tenant_id = uuid.uuid4()
        approved_by = uuid.uuid4()
        grn = _make_grn(tenant_id=tenant_id, status="received")

        session = _make_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = grn
        session.execute = AsyncMock(return_value=result_mock)

        service = ProcurementService(session)

        # Mock the WorkflowOrchestrationService via the import path used inside the method
        with patch(
            "backend.app.application.manufacturing.services.workflow_orchestration_service.WorkflowOrchestrationService"
        ) as MockOrch:
            mock_orch_instance = AsyncMock()
            mock_orch_instance.on_goods_received = AsyncMock(
                return_value={"wos_transitioned": ["wo-1"]}
            )
            MockOrch.return_value = mock_orch_instance

            result = await service.handle_incoming_qc_passed(
                tenant_id=tenant_id,
                grn_id=grn.id,
                approved_by=approved_by,
            )

        assert grn.status == "inspected"
        assert result["status"] == "inspected"
        assert "wo-1" in result["transitioned_wos"]

        # Verify on_goods_received was called for each line
        mock_orch_instance.on_goods_received.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_qc_pass_rejects_invalid_status(self):
        """Cannot approve QC for GRN not in 'received' or 'in_inspection'."""
        tenant_id = uuid.uuid4()
        grn = _make_grn(tenant_id=tenant_id, status="inspected")

        session = _make_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = grn
        session.execute = AsyncMock(return_value=result_mock)

        service = ProcurementService(session)

        with pytest.raises(ValueError, match="Expected 'received' or 'in_inspection'"):
            await service.handle_incoming_qc_passed(
                tenant_id=tenant_id,
                grn_id=grn.id,
                approved_by=uuid.uuid4(),
            )


# ─── Tests: Incoming QC Failure → Notification (Req 17.7) ────────────────────


class TestHandleIncomingQcFailed:
    """Test handle_incoming_qc_failed — notification to procurement."""

    @pytest.mark.asyncio
    async def test_qc_fail_marks_rejected_and_notifies(self):
        """QC failure marks GRN as rejected and sends notification."""
        tenant_id = uuid.uuid4()
        rejected_by = uuid.uuid4()
        grn = _make_grn(tenant_id=tenant_id, status="received")

        session = _make_session()

        call_count = [0]

        async def mock_execute(stmt, *args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # GRN lookup
                result.scalar_one_or_none.return_value = grn
            else:
                # Material name lookup
                result.scalar_one_or_none.return_value = "Raw Material A"
            return result

        session.execute = AsyncMock(side_effect=mock_execute)

        service = ProcurementService(session)
        service.notification_service = AsyncMock()
        service.notification_service.notify_incoming_qc_failed = AsyncMock(
            return_value=uuid.uuid4()
        )

        result = await service.handle_incoming_qc_failed(
            tenant_id=tenant_id,
            grn_id=grn.id,
            rejected_by=rejected_by,
            reason="Material does not meet spec",
        )

        assert grn.status == "rejected"
        assert result["status"] == "rejected"

        # Lines should be marked as rejected
        for line in grn.lines:
            assert line.rejected_quantity == float(line.received_quantity)
            assert line.accepted_quantity == 0

        # Notification should be sent
        service.notification_service.notify_incoming_qc_failed.assert_awaited_once_with(
            tenant_id=tenant_id,
            purchase_order_id=grn.purchase_order_id,
            material_name="Raw Material A",
        )

    @pytest.mark.asyncio
    async def test_qc_fail_rejects_invalid_status(self):
        """Cannot reject QC for GRN not in 'received' or 'in_inspection'."""
        tenant_id = uuid.uuid4()
        grn = _make_grn(tenant_id=tenant_id, status="pending_receipt")

        session = _make_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = grn
        session.execute = AsyncMock(return_value=result_mock)

        service = ProcurementService(session)

        with pytest.raises(ValueError, match="Expected 'received' or 'in_inspection'"):
            await service.handle_incoming_qc_failed(
                tenant_id=tenant_id,
                grn_id=grn.id,
                rejected_by=uuid.uuid4(),
            )
