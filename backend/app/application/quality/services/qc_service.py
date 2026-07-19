"""QC Service - operational flow for QC dashboard."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel


class QCService:
    """Service for QC operational dashboard and actions.

    Responsibilities:
    - Get inspection queue (WOs in QC_PENDING state)
    - Approve inspection
    - Reject inspection
    - Send to rework
    - View inspection history
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_inspection_queue(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get QC inspection queue for QC dashboard."""
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.status == "QC_PENDING",
                WorkOrderModel.is_deleted.is_(False),
            )
            .order_by(WorkOrderModel.due_date)
        )
        result = await self._session.execute(stmt)
        wos = result.scalars().all()

        inspection_queue = []
        for wo in wos:
            inspection_queue.append({
                "work_order_id": wo.id,
                "wo_number": wo.wo_number,
                "product_id": wo.product_id,
                "produced_quantity": wo.produced_quantity,
                "due_date": wo.due_date,
                "priority": wo.priority,
                "status": wo.status,
            })

        return inspection_queue

    async def get_rejected_queue(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get rejected batches for QC dashboard."""
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.status == "QC_REJECTED",
                WorkOrderModel.is_deleted.is_(False),
            )
            .order_by(WorkOrderModel.due_date)
        )
        result = await self._session.execute(stmt)
        wos = result.scalars().all()

        rejected_queue = []
        for wo in wos:
            rejected_queue.append({
                "work_order_id": wo.id,
                "wo_number": wo.wo_number,
                "product_id": wo.product_id,
                "produced_quantity": wo.produced_quantity,
                "due_date": wo.due_date,
                "priority": wo.priority,
                "status": wo.status,
            })

        return rejected_queue

    async def get_rework_queue(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get rework queue for QC dashboard."""
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
                "produced_quantity": wo.produced_quantity,
                "due_date": wo.due_date,
                "priority": wo.priority,
                "status": wo.status,
            })

        return rework_queue
