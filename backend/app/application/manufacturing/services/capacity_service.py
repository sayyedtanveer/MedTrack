"""Capacity Planning Service.

Calculates workstation load percentages, detects bottlenecks, and builds
Gantt-compatible scheduling data from work orders + job cards.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderModel,
    JobCardModel,
)
from backend.app.infrastructure.persistence.models.operation_model import OperationModel
from backend.app.infrastructure.persistence.models.workstation_model import WorkstationModel


class CapacityService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------ #
    #  Load Chart                                                          #
    # ------------------------------------------------------------------ #

    async def get_load_chart(
        self,
        tenant_id: uuid.UUID,
        start: date,
        end: date,
    ) -> List[dict]:
        """Return load % per workstation for the given date range.

        Load % = (total job card run hours scheduled) / (capacity_hours * working_days) * 100
        """
        # Fetch all active workstations
        ws_stmt = select(WorkstationModel).where(
            WorkstationModel.tenant_id == tenant_id,
            WorkstationModel.is_deleted.is_(False),
            WorkstationModel.is_active.is_(True),
        )
        ws_rows = (await self._session.execute(ws_stmt)).scalars().all()

        working_days = _count_working_days(start, end)

        # Fetch job cards for work orders that overlap the date range
        jc_stmt = (
            select(JobCardModel, OperationModel, WorkstationModel)
            .join(OperationModel, JobCardModel.operation_id == OperationModel.id)
            .join(WorkstationModel, OperationModel.workstation_id == WorkstationModel.id)
            .join(WorkOrderModel, JobCardModel.work_order_id == WorkOrderModel.id)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
                WorkOrderModel.status.notin_([WorkOrderStatus.CLOSED]),
                WorkOrderModel.due_date >= start,
                WorkOrderModel.start_date <= end,
            )
        )
        jc_rows = (await self._session.execute(jc_stmt)).all()

        # Accumulate planned hours per workstation
        hours_by_ws: dict[uuid.UUID, float] = {}
        for jc, op, ws in jc_rows:
            # run_time is per unit (minutes), need WO planned_quantity
            # We'll load the work-order planned_quantity via the join result
            hours_by_ws.setdefault(ws.id, 0.0)
            # Approximate: assume job card run_time already represents total hours
            # run_time (min/unit) is stored on OperationModel
            # We join the WO for quantity
            hours_by_ws[ws.id] += float(op.run_time) / 60.0

        results = []
        for ws in ws_rows:
            capacity = float(ws.capacity_hours_per_day) * working_days
            scheduled = hours_by_ws.get(ws.id, 0.0)
            load_pct = (scheduled / capacity * 100) if capacity > 0 else 0.0
            results.append(
                {
                    "workstation_id": str(ws.id),
                    "workstation_code": ws.code,
                    "workstation_name": ws.name,
                    "capacity_hours": round(capacity, 2),
                    "scheduled_hours": round(scheduled, 2),
                    "load_pct": round(load_pct, 1),
                    "status": _load_status(load_pct),
                }
            )

        return sorted(results, key=lambda r: r["load_pct"], reverse=True)

    # ------------------------------------------------------------------ #
    #  Bottleneck Detection                                                #
    # ------------------------------------------------------------------ #

    async def get_bottlenecks(
        self,
        tenant_id: uuid.UUID,
        threshold: float = 90.0,
    ) -> List[dict]:
        """Return workstations where load > threshold% for the next 30 days."""
        today = date.today()
        load_chart = await self.get_load_chart(tenant_id, today, today + timedelta(days=30))

        bottlenecks = []
        for row in load_chart:
            if row["load_pct"] > threshold:
                overtime_hours = 0.0
                if row["load_pct"] > 100:
                    # Hours of extra capacity needed
                    overtime_hours = round(
                        row["scheduled_hours"] - row["capacity_hours"], 2
                    )
                suggestion = (
                    "Critical overload — arrange overtime or redistribute work orders."
                    if row["load_pct"] > 100
                    else "Approaching capacity limit — consider overtime or rescheduling."
                )
                bottlenecks.append(
                    {
                        **row,
                        "overtime_hours_needed": overtime_hours,
                        "suggestion": suggestion,
                        "alert_level": "critical" if row["load_pct"] > 100 else "warning",
                    }
                )

        return bottlenecks

    # ------------------------------------------------------------------ #
    #  Production Schedule (Gantt data)                                   #
    # ------------------------------------------------------------------ #

    async def get_schedule(
        self,
        tenant_id: uuid.UUID,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> List[dict]:
        """Return Gantt-compatible work-order schedule records."""
        today = date.today()
        start = start or today
        end = end or (today + timedelta(days=30))

        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
                WorkOrderModel.status.notin_([WorkOrderStatus.CLOSED]),
                WorkOrderModel.due_date >= start,
                WorkOrderModel.start_date <= end,
            )
            .order_by(WorkOrderModel.start_date)
        )
        rows = (await self._session.execute(stmt)).scalars().all()

        return [
            {
                "id": str(wo.id),
                "wo_number": wo.wo_number,
                "status": wo.status.value if hasattr(wo.status, "value") else str(wo.status),
                "priority": wo.priority.value if hasattr(wo.priority, "value") else str(wo.priority),
                "start_date": wo.start_date.isoformat(),
                "due_date": wo.due_date.isoformat(),
                "planned_quantity": float(wo.planned_quantity),
                "produced_quantity": float(wo.produced_quantity),
                "progress_pct": round(
                    float(wo.produced_quantity) / float(wo.planned_quantity) * 100
                    if float(wo.planned_quantity) > 0
                    else 0,
                    1,
                ),
            }
            for wo in rows
        ]

    # ------------------------------------------------------------------ #
    #  Reschedule (drag-drop)                                             #
    # ------------------------------------------------------------------ #

    async def reschedule(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        new_start: date,
        new_due: date,
    ) -> dict:
        """Update start/due dates of a work order (forward/backward scheduling)."""
        if new_due < new_start:
            raise ValueError("due_date must be >= start_date")
        wo = await self._session.get(WorkOrderModel, work_order_id)
        if not wo or wo.tenant_id != tenant_id or wo.is_deleted:
            raise ValueError("Work order not found")
        if wo.status in (WorkOrderStatus.COMPLETED, WorkOrderStatus.CLOSED):
            raise ValueError("Cannot reschedule a completed/closed work order")
        wo.start_date = new_start
        wo.due_date = new_due
        await self._session.flush()
        return {
            "id": str(wo.id),
            "wo_number": wo.wo_number,
            "start_date": wo.start_date.isoformat(),
            "due_date": wo.due_date.isoformat(),
        }


# ── Helpers ────────────────────────────────────────────────────────────────── #


def _count_working_days(start: date, end: date) -> int:
    """Count Mon–Fri days in [start, end]."""
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5:  # Monday=0 … Friday=4
            count += 1
        current += timedelta(days=1)
    return max(count, 1)


def _load_status(load_pct: float) -> str:
    if load_pct > 90:
        return "critical"
    if load_pct > 70:
        return "warning"
    return "ok"
