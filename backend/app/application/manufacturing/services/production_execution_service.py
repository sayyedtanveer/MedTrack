"""Production Execution Service - operational flow for worker dashboard."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderModel,
    JobCardModel,
)
from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
from backend.app.application.manufacturing.services.inventory_service import InventoryService


class ProductionExecutionService:
    """Service for worker operational dashboard and actions.

    Responsibilities:
    - Get worker queue (assigned WOs and operations)
    - Start operation
    - Pause operation
    - Complete operation
    - Report wastage
    - Record production
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._inventory = InventoryService(session)

    @staticmethod
    def _as_decimal(value: object) -> Decimal:
        return Decimal(str(value or 0))

    @staticmethod
    def _yield_percent(produced: Decimal, scrap: Decimal, rejected: Decimal) -> float:
        total_output = produced + scrap + rejected
        if total_output <= 0:
            return 0.0
        return float((produced / total_output) * Decimal("100"))

    @staticmethod
    def _job_card_progress(status: str) -> float:
        if status in ("DONE", "COMPLETED"):
            return 100.0
        if status == "QC_PENDING":
            return 90.0
        if status == "IN_PROGRESS":
            return 50.0
        if status == "PAUSED":
            return 40.0
        if status in ("READY", "PENDING"):
            return 0.0
        return 0.0

    @staticmethod
    def _append_note(existing: Optional[str], note: Optional[str]) -> Optional[str]:
        if not note:
            return existing
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"[{timestamp}] {note}"
        return f"{existing}\n{entry}" if existing else entry

    @staticmethod
    def _elapsed_seconds(start: Optional[datetime], end: Optional[datetime]) -> Optional[float]:
        if start is None or end is None:
            return None
        if start.tzinfo is None and end.tzinfo is not None:
            end = end.replace(tzinfo=None)
        elif start.tzinfo is not None and end.tzinfo is None:
            start = start.replace(tzinfo=None)
        return max(0.0, (end - start).total_seconds())

    async def get_worker_queue(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[dict]:
        """Get assigned work orders and operations for worker dashboard."""
        # Get WOs in MATERIAL_ISSUED or IN_PRODUCTION state
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.status.in_(["MATERIAL_ISSUED", "IN_PRODUCTION"]),
                WorkOrderModel.is_deleted.is_(False),
            )
            .order_by(WorkOrderModel.due_date)
        )
        result = await self._session.execute(stmt)
        wos = result.scalars().all()

        worker_queue = []
        for wo in wos:
            # Get job cards for this WO
            jc_stmt = select(JobCardModel).where(
                JobCardModel.work_order_id == wo.id
            )
            jc_result = await self._session.execute(jc_stmt)
            job_cards = jc_result.scalars().all()

            # Get assigned job cards (assigned to this worker or unassigned)
            assigned_cards = [
                jc for jc in job_cards
                if jc.assigned_to == user_id or jc.assigned_to is None
            ]

            if assigned_cards:
                worker_queue.append({
                    "work_order_id": wo.id,
                    "wo_number": wo.wo_number,
                    "product_id": wo.product_id,
                    "due_date": wo.due_date,
                    "priority": wo.priority,
                    "status": wo.status,
                    "job_cards": [
                        self._serialize_job_card(jc)
                        for jc in assigned_cards
                    ],
                })

        return worker_queue

    def _serialize_job_card(self, jc: JobCardModel) -> dict:
        produced = self._as_decimal(jc.produced_quantity)
        scrap = self._as_decimal(jc.scrap_quantity)
        rejected = self._as_decimal(jc.rejected_quantity)
        actual_end = jc.completed_at or datetime.now(timezone.utc)
        active_duration = self._elapsed_seconds(jc.started_at, actual_end)
        if active_duration is not None:
            active_duration = max(
                0.0,
                active_duration - float(self._as_decimal(jc.total_downtime_seconds)),
            )
        return {
            "job_card_id": jc.id,
            "operation_id": jc.operation_id,
            "operation_name": jc.operation.name if getattr(jc, "operation", None) else None,
            "sequence": jc.sequence,
            "status": jc.status,
            "assigned_to": jc.assigned_to,
            "started_at": jc.started_at,
            "paused_at": jc.paused_at,
            "completed_at": jc.completed_at,
            "total_downtime_seconds": float(self._as_decimal(jc.total_downtime_seconds)),
            "actual_duration_seconds": active_duration,
            "produced_quantity": float(produced),
            "scrap_quantity": float(scrap),
            "rework_quantity": float(self._as_decimal(jc.rework_quantity)),
            "rejected_quantity": float(rejected),
            "yield_percent": round(self._yield_percent(produced, scrap, rejected), 2),
            "progress_percent": self._job_card_progress(jc.status),
            "pause_reason": jc.pause_reason,
            "operator_notes": jc.operator_notes,
        }

    async def start_operation(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        job_card_id: uuid.UUID,
        assigned_to: uuid.UUID,
    ) -> None:
        """Start a job card operation.
        
        Triggers WO transition: MATERIAL_ISSUED → IN_PRODUCTION (if first operation).
        """
        wo_stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        wo_result = await self._session.execute(wo_stmt)
        wo_model = wo_result.scalar_one_or_none()

        if not wo_model:
            raise ValueError("Work Order not found")

        stmt = (
            select(JobCardModel)
            .where(
                JobCardModel.id == job_card_id,
                JobCardModel.work_order_id == work_order_id,
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        jc = result.scalar_one_or_none()

        if not jc:
            raise ValueError("Job card not found")

        if jc.status == "IN_PROGRESS" and jc.assigned_to == assigned_to:
            return
        if jc.status not in ("PENDING", "READY"):
            raise ValueError(f"Job card is already {jc.status}")

        now = datetime.now(timezone.utc)
        jc.status = "IN_PROGRESS"
        jc.started_at = jc.started_at or now
        jc.assigned_to = assigned_to
        jc.paused_at = None
        
        # Check if this is the first operation, transition WO to IN_PRODUCTION
        if wo_model.status == WorkOrderStatus.MATERIAL_ISSUED.value:
            wo_model.status = WorkOrderStatus.IN_PRODUCTION.value
            wo_model.updated_at = now

    async def pause_operation(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        job_card_id: uuid.UUID,
        pause_reason: Optional[str] = None,
        operator_notes: Optional[str] = None,
    ) -> None:
        """Pause a job card operation."""
        await self._lock_work_order(tenant_id=tenant_id, work_order_id=work_order_id)
        stmt = (
            select(JobCardModel)
            .where(
                JobCardModel.id == job_card_id,
                JobCardModel.work_order_id == work_order_id,
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        jc = result.scalar_one_or_none()

        if not jc:
            raise ValueError("Job card not found")

        if jc.status != "IN_PROGRESS":
            raise ValueError(f"Cannot pause job card in {jc.status} status")

        now = datetime.now(timezone.utc)
        jc.status = "PAUSED"
        jc.paused_at = now
        jc.pause_reason = pause_reason
        jc.operator_notes = self._append_note(jc.operator_notes, operator_notes)

    async def resume_operation(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        job_card_id: uuid.UUID,
        operator_notes: Optional[str] = None,
    ) -> None:
        """Resume a paused job card operation and accumulate downtime."""
        await self._lock_work_order(tenant_id=tenant_id, work_order_id=work_order_id)
        stmt = (
            select(JobCardModel)
            .where(
                JobCardModel.id == job_card_id,
                JobCardModel.work_order_id == work_order_id,
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        jc = result.scalar_one_or_none()

        if not jc:
            raise ValueError("Job card not found")

        if jc.status != "PAUSED":
            raise ValueError(f"Cannot resume job card in {jc.status} status")

        now = datetime.now(timezone.utc)
        if jc.paused_at is not None:
            elapsed = self._elapsed_seconds(jc.paused_at, now) or 0.0
            jc.total_downtime_seconds = float(
                self._as_decimal(jc.total_downtime_seconds) + Decimal(str(elapsed))
            )
        jc.status = "IN_PROGRESS"
        jc.paused_at = None
        jc.operator_notes = self._append_note(jc.operator_notes, operator_notes)

    async def complete_operation(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        job_card_id: uuid.UUID,
        remarks: Optional[str] = None,
        operator_notes: Optional[str] = None,
        produced_quantity: Optional[Decimal] = None,
        scrap_quantity: Optional[Decimal] = None,
        rework_quantity: Optional[Decimal] = None,
        rejected_quantity: Optional[Decimal] = None,
    ) -> None:
        """Complete a job card operation."""
        wo = await self._lock_work_order(tenant_id=tenant_id, work_order_id=work_order_id)
        stmt = (
            select(JobCardModel)
            .where(
                JobCardModel.id == job_card_id,
                JobCardModel.work_order_id == work_order_id,
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        jc = result.scalar_one_or_none()

        if not jc:
            raise ValueError("Job card not found")

        if jc.status not in ("IN_PROGRESS", "PAUSED"):
            raise ValueError(f"Cannot complete job card in {jc.status} status")

        now = datetime.now(timezone.utc)
        if jc.status == "PAUSED" and jc.paused_at is not None:
            elapsed = self._elapsed_seconds(jc.paused_at, now) or 0.0
            jc.total_downtime_seconds = float(
                self._as_decimal(jc.total_downtime_seconds) + Decimal(str(elapsed))
            )
            jc.paused_at = None

        metric_updates = {
            "produced_quantity": produced_quantity,
            "scrap_quantity": scrap_quantity,
            "rework_quantity": rework_quantity,
            "rejected_quantity": rejected_quantity,
        }
        for attr, value in metric_updates.items():
            if value is not None:
                if value < 0:
                    raise ValueError(f"{attr} cannot be negative")
                setattr(jc, attr, float(value))

        jc.status = "DONE"
        jc.completed_at = now
        if remarks:
            jc.remarks = remarks
        jc.operator_notes = self._append_note(jc.operator_notes, operator_notes)

        if wo.status == WorkOrderStatus.IN_PRODUCTION.value:
            planned = self._as_decimal(wo.planned_quantity)
            produced = self._as_decimal(wo.produced_quantity)
            if planned > 0 and produced >= planned:
                all_cards = (
                    await self._session.execute(
                        select(JobCardModel).where(JobCardModel.work_order_id == work_order_id)
                    )
                ).scalars().all()
                if all(card.id == jc.id or card.status == "DONE" for card in all_cards):
                    wo.status = WorkOrderStatus.QC_PENDING.value
                    wo.updated_at = now

    async def report_wastage(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        scrap_quantity: Decimal,
        recorded_by: uuid.UUID,
        notes: Optional[str] = None,
    ) -> None:
        """Report scrap/wastage during production.
        
        Inventory impact: CONSUMED → REJECTED.
        Updates WO scrap quantity.
        """
        # Get WO
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == work_order_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        wo_model = result.scalar_one_or_none()
        
        if not wo_model:
            raise ValueError("Work Order not found")
        
        # Update scrap quantity
        current_scrap = Decimal(str(wo_model.scrap_quantity))
        wo_model.scrap_quantity = current_scrap + scrap_quantity
        wo_model.updated_at = datetime.now(timezone.utc)
        
        # Inventory mutation: CONSUMED → REJECTED via InventoryService.reject_stock()
        await self._inventory.reject_stock(
            tenant_id=tenant_id,
            material_id=wo_model.product_id,
            quantity=scrap_quantity,
            work_order_id=work_order_id,
            created_by=recorded_by,
            reason=notes or "Production wastage",
        )

    async def record_production(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        produced_quantity: Decimal,
        scrap_quantity: Decimal,
        job_card_id: Optional[uuid.UUID] = None,
        operation_id: Optional[uuid.UUID] = None,
        recorded_by: uuid.UUID,
        notes: Optional[str] = None,
    ) -> None:
        """Record production quantity.
        
        Triggers WO transition: IN_PRODUCTION → QC_PENDING.
        Inventory impact: ISSUED → CONSUMED.
        """
        # Get WO
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        wo_model = result.scalar_one_or_none()
        
        if not wo_model:
            raise ValueError("Work Order not found")
        
        from backend.app.infrastructure.persistence.models.work_order_model import ProductionRecordModel
        from backend.app.application.manufacturing.services.production_posting_service import (
            ProductionPostingService,
        )

        if produced_quantity < 0 or scrap_quantity < 0:
            raise ValueError("Production quantities cannot be negative")

        prev_produced = Decimal(str(wo_model.produced_quantity))
        prev_scrap = Decimal(str(wo_model.scrap_quantity))
        if produced_quantity < prev_produced:
            raise ValueError("Produced quantity cannot be lower than the existing WO total")
        if scrap_quantity < prev_scrap:
            raise ValueError("Scrap quantity cannot be lower than the existing WO total")

        produced_delta = produced_quantity - prev_produced
        scrap_delta = scrap_quantity - prev_scrap

        if produced_delta <= 0 and scrap_delta <= 0:
            return

        resolved_operation_id = operation_id

        rec = ProductionRecordModel(
            work_order_id=work_order_id,
            produced_quantity=float(produced_delta),
            scrap_quantity=float(scrap_delta),
            recorded_by=recorded_by,
            notes=notes,
        )
        self._session.add(rec)
        await self._session.flush()

        if job_card_id is not None:
            jc = (
                await self._session.execute(
                    select(JobCardModel)
                    .where(
                        JobCardModel.id == job_card_id,
                        JobCardModel.work_order_id == work_order_id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if jc is None:
                raise ValueError("Job card not found")
            if resolved_operation_id is None:
                resolved_operation_id = jc.operation_id
            jc.produced_quantity = float(max(self._as_decimal(jc.produced_quantity), produced_quantity))
            jc.scrap_quantity = float(max(self._as_decimal(jc.scrap_quantity), scrap_quantity))
            jc.operator_notes = self._append_note(jc.operator_notes, notes)

        wo_model.produced_quantity = float(produced_quantity)
        wo_model.scrap_quantity = float(scrap_quantity)
        wo_model.updated_at = datetime.now(timezone.utc)

        await ProductionPostingService(self._session).post_production_consumption(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            produced_delta=max(Decimal("0"), produced_delta),
            scrap_delta=max(Decimal("0"), scrap_delta),
            production_record_id=rec.id,
            recorded_by=recorded_by,
            operation_id=resolved_operation_id,
        )

        if (
            wo_model.status == WorkOrderStatus.IN_PRODUCTION.value
            and produced_quantity >= Decimal(str(wo_model.planned_quantity or 0))
        ):
            wo_model.status = WorkOrderStatus.QC_PENDING.value
            wo_model.updated_at = datetime.now(timezone.utc)

    async def _lock_work_order(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
    ) -> WorkOrderModel:
        result = await self._session.execute(
            select(WorkOrderModel)
            .where(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        wo = result.scalar_one_or_none()
        if wo is None:
            raise ValueError("Work Order not found")
        return wo
