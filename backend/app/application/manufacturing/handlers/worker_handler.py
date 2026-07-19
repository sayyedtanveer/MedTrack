"""Worker Handler - orchestrates worker operational flow."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.manufacturing.commands.worker_commands import (
    StartOperationCommand,
    PauseOperationCommand,
    ResumeOperationCommand,
    CompleteOperationCommand,
    ReportWastageCommand,
    RecordProductionCommand,
)
from backend.app.application.manufacturing.services.production_execution_service import ProductionExecutionService


class WorkerHandler:
    """Handler for worker operational actions."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._production = ProductionExecutionService(session)

    async def handle_start_operation(self, cmd: StartOperationCommand) -> None:
        """Handle starting a job card operation.
        
        Triggers WO transition: MATERIAL_ISSUED → IN_PRODUCTION (if first operation).
        """
        await self._production.start_operation(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            job_card_id=cmd.job_card_id,
            assigned_to=cmd.assigned_to,
        )

    async def handle_pause_operation(self, cmd: PauseOperationCommand) -> None:
        """Handle pausing a job card operation."""
        await self._production.pause_operation(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            job_card_id=cmd.job_card_id,
            pause_reason=cmd.pause_reason,
            operator_notes=cmd.operator_notes,
        )

    async def handle_resume_operation(self, cmd: ResumeOperationCommand) -> None:
        """Handle resuming a paused job card operation."""
        await self._production.resume_operation(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            job_card_id=cmd.job_card_id,
            operator_notes=cmd.operator_notes,
        )

    async def handle_complete_operation(self, cmd: CompleteOperationCommand) -> None:
        """Handle completing a job card operation."""
        await self._production.complete_operation(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            job_card_id=cmd.job_card_id,
            remarks=cmd.remarks,
            operator_notes=cmd.operator_notes,
            produced_quantity=cmd.produced_quantity,
            scrap_quantity=cmd.scrap_quantity,
            rework_quantity=cmd.rework_quantity,
            rejected_quantity=cmd.rejected_quantity,
        )

    async def handle_report_wastage(self, cmd: ReportWastageCommand) -> None:
        """Handle reporting scrap/wastage during production.
        
        Inventory impact: CONSUMED → REJECTED.
        """
        await self._production.report_wastage(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            scrap_quantity=cmd.scrap_quantity,
            recorded_by=cmd.recorded_by,
            notes=cmd.notes,
        )

    async def handle_record_production(self, cmd: RecordProductionCommand) -> None:
        """Handle recording production quantity.
        
        Triggers WO transition: IN_PRODUCTION → QC_PENDING.
        Inventory impact: ISSUED → CONSUMED.
        """
        await self._production.record_production(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            produced_quantity=cmd.produced_quantity,
            scrap_quantity=cmd.scrap_quantity,
            job_card_id=cmd.job_card_id,
            operation_id=cmd.operation_id,
            recorded_by=cmd.recorded_by,
            notes=cmd.notes,
        )
