"""MRP service for persistent material requirement suggestions."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.supply_chain.po_number_service import PONumberService
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.mrp_model import MRPSuggestionModel
from backend.app.infrastructure.persistence.models.purchase_order_model import (
    PurchaseOrderLineModel,
    PurchaseOrderModel,
)
from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderMaterialModel,
    WorkOrderModel,
)


class MRPService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._schema_checked = False

    async def run(self, tenant_id: uuid.UUID) -> dict:
        """Run MRP and persist fresh non-converted suggestions for the tenant."""
        await self._ensure_schema()
        suggestions: list[MRPSuggestionModel] = []

        materials = (
            await self._session.execute(
                select(MaterialModel).where(
                    MaterialModel.tenant_id == tenant_id,
                    MaterialModel.is_deleted.is_(False),
                    MaterialModel.is_active.is_(True),
                )
            )
        ).scalars().all()

        open_po_qty = await self._open_po_qty(tenant_id)
        gross_from_wo = await self._gross_from_work_orders(tenant_id)

        for material in materials:
            material_key = str(material.id)
            gross = Decimal(str(gross_from_wo.get(material_key, 0)))
            gross += Decimal(str(material.safety_stock or 0))

            current = Decimal(str(material.current_stock or 0))
            reserved = Decimal(str(material.reserved_stock or 0))
            incoming = Decimal(str(open_po_qty.get(material_key, 0)))
            available = current + incoming - reserved
            net = gross - available

            if net <= Decimal("0"):
                continue

            reorder = Decimal(str(material.reorder_level or 0))
            suggested_qty = max(net, reorder)
            lead_time = material.lead_time_days or 7
            order_by = date.today()
            need_by = order_by + timedelta(days=lead_time)

            suggestions.append(
                MRPSuggestionModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    material_id=material.id,
                    material_code=material.code,
                    material_name=material.name,
                    gross_requirement=gross,
                    current_stock=current,
                    open_po_qty=incoming,
                    reserved_stock=reserved,
                    net_requirement=net,
                    suggested_qty=suggested_qty,
                    lead_time_days=lead_time,
                    order_by_date=order_by,
                    need_by_date=need_by,
                    supplier_id=None,
                    supplier_name="Unknown",
                    status="pending",
                )
            )

        await self._session.execute(
            delete(MRPSuggestionModel).where(
                MRPSuggestionModel.tenant_id == tenant_id,
                MRPSuggestionModel.status != "converted",
            )
        )
        for suggestion in suggestions:
            self._session.add(suggestion)

        await self._session.commit()
        return {"run_at": datetime.now(timezone.utc).isoformat(), "suggestions_count": len(suggestions)}

    async def get_suggestions(self, tenant_id: uuid.UUID, status_filter: Optional[str] = None) -> List[dict]:
        await self._ensure_schema()
        stmt = select(MRPSuggestionModel).where(MRPSuggestionModel.tenant_id == tenant_id)
        if status_filter:
            stmt = stmt.where(MRPSuggestionModel.status == status_filter)
        stmt = stmt.order_by(MRPSuggestionModel.created_at.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._serialize(row) for row in rows]

    async def approve_suggestion(self, tenant_id: uuid.UUID, suggestion_id: str) -> dict:
        return await self._set_status(tenant_id, suggestion_id, "approved")

    async def reject_suggestion(self, tenant_id: uuid.UUID, suggestion_id: str) -> dict:
        return await self._set_status(tenant_id, suggestion_id, "rejected")

    async def bulk_approve(self, tenant_id: uuid.UUID, suggestion_ids: List[str]) -> dict:
        await self._ensure_schema()
        count = 0
        for suggestion_id in suggestion_ids:
            try:
                await self._set_status(tenant_id, suggestion_id, "approved", commit=False)
                count += 1
            except ValueError:
                continue
        await self._session.commit()
        return {"approved": count}

    async def convert_to_po(
        self,
        tenant_id: uuid.UUID,
        suggestion_ids: Optional[List[str]] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> List[dict]:
        """Batch approved suggestions into draft POs, grouped by supplier."""
        await self._ensure_schema()
        stmt = select(MRPSuggestionModel).where(
            MRPSuggestionModel.tenant_id == tenant_id,
            MRPSuggestionModel.status == "approved",
        )
        if suggestion_ids is not None:
            parsed_ids = [uuid.UUID(value) for value in suggestion_ids if _is_valid_uuid(value)]
            if not parsed_ids:
                return []
            stmt = stmt.where(MRPSuggestionModel.id.in_(parsed_ids))

        to_convert = (await self._session.execute(stmt)).scalars().all()
        if not to_convert:
            return []

        by_supplier: dict[str, list[MRPSuggestionModel]] = {}
        for suggestion in to_convert:
            key = str(suggestion.supplier_id) if suggestion.supplier_id else "unknown"
            by_supplier.setdefault(key, []).append(suggestion)

        created_pos: list[dict] = []
        po_svc = PONumberService(self._session)

        for supplier_key, items in by_supplier.items():
            po = PurchaseOrderModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                po_number=await po_svc.generate(tenant_id),
                supplier_id=uuid.UUID(supplier_key) if _is_valid_uuid(supplier_key) else None,
                order_date=date.today(),
                status="draft",
                total_amount=0,
                created_by=created_by or uuid.uuid4(),
            )
            self._session.add(po)
            await self._session.flush()

            for item in items:
                self._session.add(
                    PurchaseOrderLineModel(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        purchase_order_id=po.id,
                        material_id=item.material_id,
                        quantity=float(item.suggested_qty),
                        received_quantity=0,
                        unit_price=0,
                        line_total=0,
                    )
                )
                item.status = "converted"
                item.po_id = po.id
                item.updated_at = datetime.now(timezone.utc)

            await self._session.flush()
            created_pos.append({"po_id": str(po.id), "po_number": po.po_number, "lines": len(items)})

        await self._session.commit()
        return created_pos

    async def _open_po_qty(self, tenant_id: uuid.UUID) -> dict[str, float]:
        stmt = (
            select(
                PurchaseOrderLineModel.material_id,
                func.sum(PurchaseOrderLineModel.quantity - PurchaseOrderLineModel.received_quantity),
            )
            .join(PurchaseOrderModel, PurchaseOrderLineModel.purchase_order_id == PurchaseOrderModel.id)
            .where(
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
                PurchaseOrderModel.status.in_(["draft", "sent", "acknowledged", "partial"]),
                PurchaseOrderLineModel.is_deleted.is_(False),
            )
            .group_by(PurchaseOrderLineModel.material_id)
        )
        rows = (await self._session.execute(stmt)).all()
        return {str(material_id): float(quantity or 0) for material_id, quantity in rows}

    async def _gross_from_work_orders(self, tenant_id: uuid.UUID) -> dict[str, float]:
        stmt = (
            select(
                WorkOrderMaterialModel.material_id,
                func.sum(WorkOrderMaterialModel.required_quantity - WorkOrderMaterialModel.issued_quantity),
            )
            .join(WorkOrderModel, WorkOrderMaterialModel.work_order_id == WorkOrderModel.id)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
                WorkOrderModel.status.in_(
                    [
                        WorkOrderStatus.PLANNED.value,
                        WorkOrderStatus.RELEASED.value,
                        WorkOrderStatus.MATERIAL_PENDING.value,
                        WorkOrderStatus.MATERIAL_RESERVED.value,
                        WorkOrderStatus.MATERIAL_ISSUED.value,
                        WorkOrderStatus.IN_PRODUCTION.value,
                    ]
                ),
            )
            .group_by(WorkOrderMaterialModel.material_id)
        )
        rows = (await self._session.execute(stmt)).all()
        return {str(material_id): float(quantity or 0) for material_id, quantity in rows}

    async def _set_status(
        self,
        tenant_id: uuid.UUID,
        suggestion_id: str,
        new_status: str,
        *,
        commit: bool = True,
    ) -> dict:
        await self._ensure_schema()
        if not _is_valid_uuid(suggestion_id):
            raise ValueError(f"Suggestion {suggestion_id} not found")

        suggestion = await self._session.scalar(
            select(MRPSuggestionModel).where(
                MRPSuggestionModel.id == uuid.UUID(suggestion_id),
                MRPSuggestionModel.tenant_id == tenant_id,
            )
        )
        if suggestion is None:
            raise ValueError(f"Suggestion {suggestion_id} not found")
        if suggestion.status == "converted":
            raise ValueError("Cannot change status of a converted suggestion")

        suggestion.status = new_status
        suggestion.updated_at = datetime.now(timezone.utc)
        if commit:
            await self._session.commit()
            await self._session.refresh(suggestion)
        return self._serialize(suggestion)

    async def _ensure_schema(self) -> None:
        if self._schema_checked:
            return
        connection = await self._session.connection()

        def create_table(sync_connection) -> None:
            MRPSuggestionModel.__table__.create(bind=sync_connection, checkfirst=True)

        await connection.run_sync(create_table)
        self._schema_checked = True

    def _serialize(self, suggestion: MRPSuggestionModel) -> dict:
        return {
            "id": str(suggestion.id),
            "tenant_id": str(suggestion.tenant_id),
            "material_id": str(suggestion.material_id),
            "material_code": suggestion.material_code,
            "material_name": suggestion.material_name,
            "gross_requirement": float(suggestion.gross_requirement or 0),
            "current_stock": float(suggestion.current_stock or 0),
            "open_po_qty": float(suggestion.open_po_qty or 0),
            "reserved_stock": float(suggestion.reserved_stock or 0),
            "net_requirement": float(suggestion.net_requirement or 0),
            "suggested_qty": float(suggestion.suggested_qty or 0),
            "lead_time_days": suggestion.lead_time_days,
            "order_by_date": suggestion.order_by_date.isoformat(),
            "need_by_date": suggestion.need_by_date.isoformat(),
            "supplier_id": str(suggestion.supplier_id) if suggestion.supplier_id else None,
            "supplier_name": suggestion.supplier_name,
            "status": suggestion.status,
            "po_id": str(suggestion.po_id) if suggestion.po_id else None,
            "created_at": suggestion.created_at.isoformat(),
        }


def _is_valid_uuid(value: str | None) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (TypeError, ValueError):
        return False
