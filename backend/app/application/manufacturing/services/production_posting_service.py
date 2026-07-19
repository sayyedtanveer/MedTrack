"""Canonical production inventory posting: BOM consumption without duplicate FG receipt."""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.infrastructure.persistence.models.bom_model import BOMLineModel
from backend.app.infrastructure.persistence.models.material_consumption_model import (
    MaterialConsumptionRecordModel,
)
from backend.app.infrastructure.persistence.models.inventory_reservation_model import (
    InventoryReservationModel,
)
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.work_order_model import (
    ProductionRecordModel,
    WorkOrderMaterialModel,
    WorkOrderModel,
)

logger = logging.getLogger(__name__)


class ProductionPostingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._inventory = InventoryService(session)

    async def post_production_consumption(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        produced_delta: Decimal,
        scrap_delta: Decimal,
        production_record_id: uuid.UUID | None,
        recorded_by: uuid.UUID,
        operation_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Consume materials for incremental production output (no FG receipt here)."""
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
            raise ValueError(f"Work order {work_order_id} not found")

        output_delta = produced_delta + scrap_delta
        if output_delta <= 0:
            return []

        results: list[dict] = []
        if wo.bom_id is None:
            return results

        bl_res = await self._session.execute(
            select(BOMLineModel).where(
                BOMLineModel.bom_id == wo.bom_id,
                BOMLineModel.material_id.isnot(None),
                BOMLineModel.is_deleted.is_(False),
            )
        )
        for line in bl_res.scalars().all():
            per_unit = Decimal(str(line.quantity))
            scrap_factor = Decimal(str(getattr(line, "scrap_percentage", 0) or 0)) / Decimal("100")
            effective_per_unit = per_unit * (Decimal("1") + scrap_factor)
            planned = output_delta * effective_per_unit

            wm = (
                await self._session.execute(
                    select(WorkOrderMaterialModel).where(
                        WorkOrderMaterialModel.work_order_id == wo.id,
                        WorkOrderMaterialModel.material_id == line.material_id,
                    )
                )
            ).scalar_one_or_none()
            if wm is None or line.material_id is None:
                continue

            already_consumed = await self._sum_consumed_for_material(
                tenant_id=tenant_id,
                work_order_id=wo.id,
                material_id=line.material_id,
            )
            total_required = (
                Decimal(str(wo.produced_quantity)) + Decimal(str(wo.scrap_quantity))
            ) * effective_per_unit
            to_consume = total_required - already_consumed
            if to_consume <= 0:
                continue

            issued_unconsumed = await self._sum_issued_unconsumed_for_material(
                tenant_id=tenant_id,
                work_order_id=wo.id,
                material_id=line.material_id,
            )
            if to_consume > issued_unconsumed:
                shortfall = to_consume - issued_unconsumed
                await self._inventory.issue_material_for_wo(
                    tenant_id=tenant_id,
                    work_order_id=wo.id,
                    material_id=line.material_id,
                    quantity=shortfall,
                    unit_id=line.unit_id,
                    created_by=recorded_by,
                    transition_wo_status=False,
                )

            await self._inventory.consume_stock(
                tenant_id=tenant_id,
                material_id=line.material_id,
                quantity=to_consume,
                work_order_id=wo.id,
                unit_id=line.unit_id,
                created_by=recorded_by,
            )

            variance = to_consume - planned
            record = MaterialConsumptionRecordModel(
                tenant_id=tenant_id,
                work_order_id=wo.id,
                material_id=line.material_id,
                production_record_id=production_record_id,
                operation_id=operation_id,
                planned_quantity=float(planned),
                actual_quantity=float(to_consume),
                variance_quantity=float(variance),
                scrap_quantity=float(scrap_delta * effective_per_unit),
                unit_id=line.unit_id,
                recorded_by=recorded_by,
            )
            self._session.add(record)
            results.append(
                {
                    "material_id": str(line.material_id),
                    "planned_quantity": float(planned),
                    "actual_quantity": float(to_consume),
                    "variance_quantity": float(variance),
                    "operation_id": str(operation_id) if operation_id else None,
                }
            )
        return results

    async def _sum_consumed_for_material(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> Decimal:
        from sqlalchemy import func

        stmt = select(func.coalesce(func.sum(MaterialConsumptionRecordModel.actual_quantity), 0)).where(
            MaterialConsumptionRecordModel.tenant_id == tenant_id,
            MaterialConsumptionRecordModel.work_order_id == work_order_id,
            MaterialConsumptionRecordModel.material_id == material_id,
        )
        total = (await self._session.execute(stmt)).scalar()
        return Decimal(str(total or 0))

    async def _sum_issued_unconsumed_for_material(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> Decimal:
        rows = (
            await self._session.execute(
                select(InventoryReservationModel).where(
                    InventoryReservationModel.tenant_id == tenant_id,
                    InventoryReservationModel.reference_type == "work_order",
                    InventoryReservationModel.reference_id == work_order_id,
                    InventoryReservationModel.material_id == material_id,
                    InventoryReservationModel.status.in_(
                        ("ISSUED", "PARTIALLY_ISSUED", "PARTIALLY_CONSUMED", "RESERVED")
                    ),
                )
            )
        ).scalars().all()
        return sum(
            (
                max(
                    Decimal("0"),
                    Decimal(str(row.issued_quantity or 0))
                    - Decimal(str(row.consumed_quantity or 0))
                    - Decimal(str(row.returned_quantity or 0)),
                )
                for row in rows
            ),
            Decimal("0"),
        )
