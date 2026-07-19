"""Generate pick lists for work order material issues."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderMaterialModel,
    WorkOrderModel,
)


class PickListService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def generate_from_wo(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> dict:
        from backend.app.infrastructure.persistence.models.pick_list_model import (
            PickListLineModel,
            PickListModel,
        )

        wo = (
            await self._session.execute(
                select(WorkOrderModel).where(
                    WorkOrderModel.id == work_order_id,
                    WorkOrderModel.tenant_id == tenant_id,
                    WorkOrderModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if wo is None:
            raise ValueError("Work order not found")

        pick_list_number = f"PL-{wo.wo_number}"
        pl = PickListModel(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            pick_list_number=pick_list_number,
            status="READY",
            created_by=created_by,
        )
        self._session.add(pl)
        await self._session.flush()

        mats = (
            await self._session.execute(
                select(WorkOrderMaterialModel, MaterialModel)
                .join(MaterialModel, MaterialModel.id == WorkOrderMaterialModel.material_id)
                .where(WorkOrderMaterialModel.work_order_id == work_order_id)
            )
        ).all()

        lines = []
        seq = 0
        for wm, material in mats:
            remaining = Decimal(str(wm.required_quantity)) - Decimal(str(wm.issued_quantity))
            if remaining <= 0:
                continue
            loc_id = material.location_id
            loc_path = ""
            if loc_id:
                loc = (
                    await self._session.execute(
                        select(LocationModel).where(LocationModel.id == loc_id)
                    )
                ).scalar_one_or_none()
                if loc:
                    loc_path = loc.name or str(loc_id)
            seq += 1
            line = PickListLineModel(
                pick_list_id=pl.id,
                material_id=material.id,
                location_id=loc_id,
                quantity=float(remaining),
                sequence=seq,
            )
            self._session.add(line)
            lines.append(
                {
                    "material_id": str(material.id),
                    "material_code": material.item_code or material.code,
                    "quantity": float(remaining),
                    "location": loc_path,
                    "sequence": seq,
                }
            )

        return {
            "pick_list_id": str(pl.id),
            "pick_list_number": pick_list_number,
            "work_order_id": str(work_order_id),
            "lines": lines,
        }
