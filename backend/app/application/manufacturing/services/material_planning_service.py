"""Material planning on work order release (reservation + procurement)."""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.inventory.services.inventory_reservation_service import (
    InventoryReservationService,
)
from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.application.supply_chain.po_number_service import PONumberService
from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.material_request_model import MaterialRequestModel
from backend.app.infrastructure.persistence.models.purchase_order_model import (
    PurchaseOrderLineModel,
    PurchaseOrderModel,
)
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderMaterialModel,
    WorkOrderModel,
)

logger = logging.getLogger(__name__)


class MaterialPlanningService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._inventory = InventoryService(session)
        self._reservation = InventoryReservationService(session)

    async def plan_for_release(self, wo: WorkOrderModel) -> None:
        """Reserve available BOM material and procure net shortage for this WO."""
        rows = (
            await self._session.execute(
                select(WorkOrderMaterialModel, MaterialModel)
                .join(MaterialModel, MaterialModel.id == WorkOrderMaterialModel.material_id)
                .where(
                    WorkOrderMaterialModel.work_order_id == wo.id,
                    MaterialModel.tenant_id == wo.tenant_id,
                    MaterialModel.is_deleted.is_(False),
                )
            )
        ).all()
        if not rows:
            wo.status = WorkOrderStatus.MATERIAL_RESERVED.value
            wo.updated_at = datetime.now(timezone.utc)
            return

        shortage_lines: list[tuple[WorkOrderMaterialModel, MaterialModel, Decimal]] = []
        for requirement, material in rows:
            required_qty = Decimal(str(requirement.required_quantity or 0))
            issued_qty = Decimal(str(requirement.issued_quantity or 0))
            remaining_qty = required_qty - issued_qty
            if remaining_qty <= 0:
                continue

            already_reserved = await self._inventory.get_existing_reservation_qty_for_wo(
                tenant_id=wo.tenant_id,
                work_order_id=wo.id,
                material_id=material.id,
            )
            need_to_reserve = max(Decimal("0"), remaining_qty - already_reserved)
            if need_to_reserve <= 0:
                shortage_qty = Decimal("0")
            else:
                _reserved_qty, shortage_qty, _ = await self._reservation.reserve_for_work_order(
                    tenant_id=wo.tenant_id,
                    work_order_id=wo.id,
                    material_id=material.id,
                    required_quantity=need_to_reserve,
                    unit_id=requirement.unit_id,
                    created_by=wo.created_by,
                )

            incoming_qty = await self._open_po_quantity(wo.tenant_id, material.id)
            net_shortage_qty = shortage_qty - incoming_qty
            if net_shortage_qty > 0:
                shortage_lines.append((requirement, material, net_shortage_qty))

        if not shortage_lines:
            wo.status = WorkOrderStatus.MATERIAL_RESERVED.value
            wo.updated_at = datetime.now(timezone.utc)
            return

        for _requirement, material, shortage_qty in shortage_lines:
            existing_request = (
                await self._session.execute(
                    select(MaterialRequestModel).where(
                        MaterialRequestModel.tenant_id == wo.tenant_id,
                        MaterialRequestModel.item_id == material.id,
                        MaterialRequestModel.item_type == "material",
                        MaterialRequestModel.source_ref_type == "work_order",
                        MaterialRequestModel.source_ref_id == wo.id,
                        MaterialRequestModel.status == "open",
                        MaterialRequestModel.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()

            if existing_request is None:
                self._session.add(
                    MaterialRequestModel(
                        id=uuid.uuid4(),
                        tenant_id=wo.tenant_id,
                        item_id=material.id,
                        item_type="material",
                        required_quantity=float(shortage_qty),
                        fulfilled_quantity=0,
                        required_by=wo.due_date,
                        status="open",
                        source_ref_type="work_order",
                        source_ref_id=wo.id,
                    )
                )
            elif shortage_qty > Decimal(str(existing_request.required_quantity or 0)):
                existing_request.required_quantity = float(shortage_qty)
                existing_request.required_by = wo.due_date

        supplier_groups: dict[
            uuid.UUID,
            tuple[SupplierModel, list[tuple[WorkOrderMaterialModel, MaterialModel, Decimal]]],
        ] = {}
        for requirement, material, shortage_qty in shortage_lines:
            supplier = await self._choose_supplier_for_material(wo.tenant_id, material.id)
            if supplier is None:
                logger.warning(
                    "WO %s has material shortage for %s but no active supplier is available.",
                    wo.id,
                    material.id,
                )
                continue
            _, grouped_lines = supplier_groups.setdefault(supplier.id, (supplier, []))
            grouped_lines.append((requirement, material, shortage_qty))

        for supplier, grouped_lines in supplier_groups.values():
            po_total = Decimal("0")
            po_number = await PONumberService(self._session).generate(wo.tenant_id)
            po = PurchaseOrderModel(
                id=uuid.uuid4(),
                tenant_id=wo.tenant_id,
                po_number=po_number,
                supplier_id=supplier.id,
                order_date=date.today(),
                expected_delivery=wo.due_date,
                status="sent",
                total_amount=0,
                notes=f"Auto-created for WO {wo.id} raw-material shortage.",
                created_by=wo.created_by,
            )
            self._session.add(po)
            await self._session.flush()

            for _, material, shortage_qty in grouped_lines:
                unit_price = Decimal(str(material.current_cost or 0))
                line_total = shortage_qty * unit_price
                po_total += line_total
                self._session.add(
                    PurchaseOrderLineModel(
                        id=uuid.uuid4(),
                        tenant_id=wo.tenant_id,
                        purchase_order_id=po.id,
                        material_id=material.id,
                        quantity=float(shortage_qty),
                        received_quantity=0,
                        unit_price=float(unit_price),
                        line_total=float(line_total),
                    )
                )
            po.total_amount = float(po_total)

    async def _open_po_quantity(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> Decimal:
        result = await self._session.execute(
            select(
                func.coalesce(
                    func.sum(PurchaseOrderLineModel.quantity - PurchaseOrderLineModel.received_quantity),
                    0,
                )
            )
            .join(PurchaseOrderModel, PurchaseOrderModel.id == PurchaseOrderLineModel.purchase_order_id)
            .where(
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
                PurchaseOrderLineModel.material_id == material_id,
                PurchaseOrderModel.status.in_(["sent", "partially_received", "approved"]),
            )
        )
        return Decimal(str(result.scalar() or 0))

    async def _choose_supplier_for_material(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID
    ) -> SupplierModel | None:
        result = await self._session.execute(
            select(SupplierModel)
            .where(
                SupplierModel.tenant_id == tenant_id,
                SupplierModel.is_active.is_(True),
                SupplierModel.is_deleted.is_(False),
            )
            .order_by(SupplierModel.created_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()
