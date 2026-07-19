"""Planner Service - operational flow for planner dashboard."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel


class PlannerService:
    """Service for planner operational dashboard and actions.

    Responsibilities:
    - Get planning queue (PLANNED, RELEASED WOs)
    - Get overdue WOs
    - Get WOs with shortages
    - Get WOs in rework
    - View capacity utilization
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_planning_queue(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get planning queue for planner dashboard (PLANNED, RELEASED)."""
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.status.in_(["PLANNED", "RELEASED"]),
                WorkOrderModel.is_deleted.is_(False),
            )
            .order_by(WorkOrderModel.due_date)
        )
        result = await self._session.execute(stmt)
        wos = result.scalars().all()

        planning_queue = []
        for wo in wos:
            planning_queue.append({
                "work_order_id": wo.id,
                "wo_number": wo.wo_number,
                "product_id": wo.product_id,
                "planned_quantity": wo.planned_quantity,
                "due_date": wo.due_date,
                "priority": wo.priority,
                "status": wo.status,
            })

        return planning_queue

    async def get_overdue_queue(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get overdue WOs for planner dashboard."""
        from datetime import datetime, timezone

        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.due_date < datetime.now(timezone.utc),
                WorkOrderModel.status.in_(["PLANNED", "RELEASED", "MATERIAL_PENDING", "MATERIAL_RESERVED", "IN_PRODUCTION"]),
                WorkOrderModel.is_deleted.is_(False),
            )
            .order_by(WorkOrderModel.due_date)
        )
        result = await self._session.execute(stmt)
        wos = result.scalars().all()

        overdue_queue = []
        for wo in wos:
            overdue_queue.append({
                "work_order_id": wo.id,
                "wo_number": wo.wo_number,
                "product_id": wo.product_id,
                "planned_quantity": wo.planned_quantity,
                "due_date": wo.due_date,
                "priority": wo.priority,
                "status": wo.status,
            })

        return overdue_queue

    async def get_shortage_queue(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get WOs with material shortages for planner dashboard."""
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.status == "MATERIAL_PENDING",
                WorkOrderModel.is_deleted.is_(False),
            )
            .order_by(WorkOrderModel.due_date)
        )
        result = await self._session.execute(stmt)
        wos = result.scalars().all()

        shortage_queue = []
        for wo in wos:
            shortage_queue.append({
                "work_order_id": wo.id,
                "wo_number": wo.wo_number,
                "product_id": wo.product_id,
                "planned_quantity": wo.planned_quantity,
                "due_date": wo.due_date,
                "priority": wo.priority,
                "status": wo.status,
            })

        return shortage_queue

    async def get_rework_queue(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get WOs in rework for planner dashboard."""
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.status == "REWORK",
                WorkOrderModel.is_deleted.is_(False),
            )
            .order_by(WorkOrderModel.due_date)
        )
        result = await self._session.execute(stmt)
        wos = result.scalars().all()

        rework_queue = []
        for wo in wos:
            rework_queue.append({
                "work_order_id": wo.id,
                "wo_number": wo.wo_number,
                "product_id": wo.product_id,
                "planned_quantity": wo.planned_quantity,
                "due_date": wo.due_date,
                "priority": wo.priority,
                "status": wo.status,
            })

        return rework_queue

    async def get_capacity_utilization(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Get capacity utilization metrics for planner dashboard."""
        from datetime import datetime, timezone, timedelta

        # Get WOs in production in the next 30 days
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.status.in_(["IN_PRODUCTION", "MATERIAL_ISSUED"]),
                WorkOrderModel.is_deleted.is_(False),
                WorkOrderModel.due_date <= future_date,
            )
        )
        result = await self._session.execute(stmt)
        wos = result.scalars().all()

        total_quantity = sum(wo.quantity for wo in wos)
        
        return {
            "active_wo_count": len(wos),
            "total_planned_quantity": total_quantity,
            "utilization_percent": min(100, int(total_quantity / 1000 * 100)),  # Simplified calculation
        }
