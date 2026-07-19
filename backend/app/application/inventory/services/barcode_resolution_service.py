"""Resolve barcode/QR scan payloads to inventory or manufacturing entities."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.batch_model import BatchModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel


class BarcodeResolutionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(self, *, tenant_id: uuid.UUID, payload: str) -> dict[str, Any]:
        code = (payload or "").strip()
        if not code:
            raise ValueError("Scan payload is required")

        mat = (
            await self._session.execute(
                select(MaterialModel).where(
                    MaterialModel.tenant_id == tenant_id,
                    MaterialModel.is_deleted.is_(False),
                    (MaterialModel.item_code == code) | (MaterialModel.code == code),
                ).limit(1)
            )
        ).scalar_one_or_none()
        if mat:
            return {"type": "material", "id": str(mat.id), "code": mat.item_code or mat.code, "name": mat.name}

        batch = (
            await self._session.execute(
                select(BatchModel).where(
                    BatchModel.tenant_id == tenant_id,
                    BatchModel.batch_number == code,
                    BatchModel.is_deleted.is_(False),
                ).limit(1)
            )
        ).scalar_one_or_none()
        if batch:
            return {
                "type": "batch",
                "id": str(batch.id),
                "batch_number": batch.batch_number,
                "material_id": str(batch.material_id),
            }

        wo = (
            await self._session.execute(
                select(WorkOrderModel).where(
                    WorkOrderModel.tenant_id == tenant_id,
                    WorkOrderModel.wo_number == code,
                    WorkOrderModel.is_deleted.is_(False),
                ).limit(1)
            )
        ).scalar_one_or_none()
        if wo:
            return {"type": "work_order", "id": str(wo.id), "wo_number": wo.wo_number}

        return {"type": "unknown", "payload": code}
