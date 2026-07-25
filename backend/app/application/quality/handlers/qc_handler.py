"""QC Handler for approve/reject/rework operations."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.quality.commands.qc_commands import (
    ApproveInspectionCommand,
    RejectInspectionCommand,
    SendToReworkCommand,
    ScrapBatchCommand,
)
from backend.app.application.quality.services.qc_service import QCService
from backend.app.application.quality.handlers.fg_receive_command_handler import (
    FGReceiveCommandHandler,
)
from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.domain.quality.entities.quality_inspection import (
    QualityInspection,
    InspectionResult,
    InspectionDetail,
)
from backend.app.domain.manufacturing.entities.work_order import (
    WorkOrder,
    WorkOrderStatus,
    InvalidStatusTransitionError,
)
from backend.app.infrastructure.persistence.models.quality_model import (
    QualityInspectionModel,
    InspectionDetailModel,
)
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel


class QCHandler:
    """Handler for QC operational actions.
    
    Responsibilities:
    - Approve inspection (WO: QC_PENDING → QC_APPROVED)
    - Reject inspection (WO: QC_PENDING → QC_REJECTED)
    - Send to rework (WO: QC_REJECTED → REWORK)
    - Scrap batch (WO: QC_REJECTED → REJECTED → CLOSED)
    - Integrate with WO status transitions
    - Trigger FG inventory increase on approval
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._inventory = InventoryService(session)

    async def approve_inspection(self, command: ApproveInspectionCommand) -> QualityInspection:
        """Approve QC inspection and transition WO to QC_APPROVED."""
        # Load WO
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == command.work_order_id,
            WorkOrderModel.tenant_id == command.tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        wo_model = result.scalar_one_or_none()
        
        if not wo_model:
            raise ValueError(f"Work Order {command.work_order_id} not found")
        
        # Validate WO is in QC_PENDING
        if wo_model.status != WorkOrderStatus.QC_PENDING.value:
            raise InvalidStatusTransitionError(
                f"Cannot approve: WO must be in QC_PENDING, current: {wo_model.status}"
            )
        
        # Create domain inspection
        inspection = QualityInspection(
            tenant_id=command.tenant_id,
            reference_type="work_order",
            reference_id=command.work_order_id,
            inspection_date=command.inspection_date,
            inspector_id=command.inspector_id,
            result=InspectionResult.PASSED,
            remarks=command.remarks,
        )
        
        # Add details if provided
        if command.details:
            for detail_data in command.details:
                detail = InspectionDetail(
                    parameter=detail_data.get("parameter", ""),
                    measured_value=detail_data.get("measured_value"),
                    tolerance_min=detail_data.get("tolerance_min"),
                    tolerance_max=detail_data.get("tolerance_max"),
                    is_passed=detail_data.get("is_passed", True),
                )
                inspection.add_detail(detail)
        
        # Persist inspection
        inspection_model = QualityInspectionModel(
            id=inspection.id,
            tenant_id=inspection.tenant_id,
            reference_type=inspection.reference_type,
            reference_id=inspection.reference_id,
            inspection_date=inspection.inspection_date,
            inspector_id=inspection.inspector_id,
            result=inspection.result.value,
            remarks=inspection.remarks,
        )
        self._session.add(inspection_model)
        
        # Persist details
        for detail in inspection.details:
            detail_model = InspectionDetailModel(
                tenant_id=inspection.tenant_id,
                inspection_id=inspection.id,
                parameter=detail.parameter,
                measured_value=detail.measured_value,
                tolerance_min=detail.tolerance_min,
                tolerance_max=detail.tolerance_max,
                is_passed=detail.is_passed,
            )
            self._session.add(detail_model)
        
        # Transition WO to QC_APPROVED, then fire FGReceiveCommandHandler (Gap #3).
        wo_model.status = WorkOrderStatus.QC_APPROVED.value
        wo_model.updated_at = datetime.now(timezone.utc)

        await FGReceiveCommandHandler(self._session).handle(
            wo_id=command.work_order_id,
            tenant_id=command.tenant_id,
            received_by=command.inspector_id,
        )
        
        await self._session.flush()
        return inspection

    async def reject_inspection(self, command: RejectInspectionCommand) -> QualityInspection:
        """Reject QC inspection and transition WO to QC_REJECTED."""
        # Load WO
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == command.work_order_id,
            WorkOrderModel.tenant_id == command.tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        wo_model = result.scalar_one_or_none()
        
        if not wo_model:
            raise ValueError(f"Work Order {command.work_order_id} not found")
        
        # Validate WO is in QC_PENDING
        if wo_model.status != WorkOrderStatus.QC_PENDING.value:
            raise InvalidStatusTransitionError(
                f"Cannot reject: WO must be in QC_PENDING, current: {wo_model.status}"
            )
        
        # Create domain inspection
        inspection = QualityInspection(
            tenant_id=command.tenant_id,
            reference_type="work_order",
            reference_id=command.work_order_id,
            inspection_date=command.inspection_date,
            inspector_id=command.inspector_id,
            result=InspectionResult.FAILED,
            remarks=command.reason,
            defect_details=command.defect_details,
            rework_required=command.rework_required,
            scrap_quantity=command.scrap_quantity,
        )
        
        # Add details if provided
        if command.details:
            for detail_data in command.details:
                detail = InspectionDetail(
                    parameter=detail_data.get("parameter", ""),
                    measured_value=detail_data.get("measured_value"),
                    tolerance_min=detail_data.get("tolerance_min"),
                    tolerance_max=detail_data.get("tolerance_max"),
                    is_passed=detail_data.get("is_passed", False),
                )
                inspection.add_detail(detail)
        
        # Persist inspection
        inspection_model = QualityInspectionModel(
            id=inspection.id,
            tenant_id=inspection.tenant_id,
            reference_type=inspection.reference_type,
            reference_id=inspection.reference_id,
            inspection_date=inspection.inspection_date,
            inspector_id=inspection.inspector_id,
            result=inspection.result.value,
            remarks=inspection.remarks,
        )
        self._session.add(inspection_model)
        
        # Persist details
        for detail in inspection.details:
            detail_model = InspectionDetailModel(
                tenant_id=inspection.tenant_id,
                inspection_id=inspection.id,
                parameter=detail.parameter,
                measured_value=detail.measured_value,
                tolerance_min=detail.tolerance_min,
                tolerance_max=detail.tolerance_max,
                is_passed=detail.is_passed,
            )
            self._session.add(detail_model)
        
        # Transition WO to QC_REJECTED
        wo_model.status = WorkOrderStatus.QC_REJECTED.value
        wo_model.updated_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        return inspection

    async def send_to_rework(self, command: SendToReworkCommand) -> None:
        """Send rejected batch to rework.
        
        Triggers WO transition: QC_REJECTED → REWORK.
        """
        # Load WO
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == command.work_order_id,
            WorkOrderModel.tenant_id == command.tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        wo_model = result.scalar_one_or_none()
        
        if not wo_model:
            raise ValueError(f"Work Order {command.work_order_id} not found")
        
        # Validate WO is in QC_REJECTED
        if wo_model.status != WorkOrderStatus.QC_REJECTED.value:
            raise InvalidStatusTransitionError(
                f"Cannot send to rework: WO must be in QC_REJECTED, current: {wo_model.status}"
            )
        
        # Transition WO to REWORK
        wo_model.status = WorkOrderStatus.REWORK.value
        wo_model.updated_at = datetime.now(timezone.utc)
        
        # TODO: If additional material required, issue more stock
        # This will be handled by Storekeeper flow (Phase 2)
        
        await self._session.flush()

    async def scrap_batch(self, command: ScrapBatchCommand) -> None:
        """Scrap rejected batch.
        
        Triggers WO transition: QC_REJECTED → REJECTED → CLOSED.
        Inventory impact: 
          - ISSUED → REJECTED (via InventoryService)
          - Release remaining unreserved materials (reserved > issued) via RESERVATION_RELEASE (Req 18.3)
        """
        # Load WO
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == command.work_order_id,
            WorkOrderModel.tenant_id == command.tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        wo_model = result.scalar_one_or_none()
        
        if not wo_model:
            raise ValueError(f"Work Order {command.work_order_id} not found")
        
        # Validate WO is in QC_REJECTED
        if wo_model.status != WorkOrderStatus.QC_REJECTED.value:
            raise InvalidStatusTransitionError(
                f"Cannot scrap: WO must be in QC_REJECTED, current: {wo_model.status}"
            )
        
        # Transition WO to REJECTED
        wo_model.status = WorkOrderStatus.REJECTED.value
        wo_model.scrap_quantity = command.scrap_quantity
        wo_model.updated_at = datetime.now(timezone.utc)
        
        # Inventory mutation: ISSUED → REJECTED
        # Note: This rejects the issued materials, not the FG
        # For simplicity, we're rejecting the scrap quantity from the product
        await self._inventory.reject_stock(
            tenant_id=command.tenant_id,
            material_id=wo_model.product_id,
            quantity=command.scrap_quantity,
            work_order_id=command.work_order_id,
            created_by=command.inspector_id,
            reason="QC rejected - batch scrapped",
        )
        
        # Release remaining unreserved raw materials (reserved > issued) - Req 18.3
        # Materials that were reserved but not yet issued should be returned to available stock
        await self._inventory.cancel_work_order_reservation(
            tenant_id=command.tenant_id,
            material_id=wo_model.product_id,
            work_order_id=command.work_order_id,
            unit_id=None,
            created_by=command.inspector_id,
            remarks=f"WO scrapped - releasing remaining unreserved materials",
        )
        
        # Also release reservations for all BOM line materials
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderMaterialModel
        wo_materials_stmt = select(WorkOrderMaterialModel).where(
            WorkOrderMaterialModel.work_order_id == command.work_order_id,
        )
        wo_materials = (await self._session.execute(wo_materials_stmt)).scalars().all()
        for wom in wo_materials:
            await self._inventory.cancel_work_order_reservation(
                tenant_id=command.tenant_id,
                material_id=wom.material_id,
                work_order_id=command.work_order_id,
                unit_id=wom.unit_id,
                created_by=command.inspector_id,
                remarks=f"WO scrapped - releasing remaining unreserved material",
            )
        
        # Close WO after scrap
        wo_model.status = WorkOrderStatus.CLOSED.value
        wo_model.updated_at = datetime.now(timezone.utc)
        
        await self._session.flush()
