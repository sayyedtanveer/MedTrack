"""MRP service for persistent material requirement suggestions."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import cast, delete, func, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.supply_chain.po_number_service import PONumberService
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.mrp_model import MRPSuggestionModel
from backend.app.infrastructure.persistence.models.purchase_order_model import (
    PurchaseOrderLineModel,
    PurchaseOrderModel,
)
from backend.app.infrastructure.persistence.models.supplier_model import (
    SupplierModel,
    SupplierPriceHistoryModel,
)
from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderMaterialModel,
    WorkOrderModel,
)
# Register all models that participate in cross-table relationships so SQLAlchemy's
# mapper can resolve string-based relationship references (e.g. "OperationModel",
# "MaterialModel") before any query executes. In the full application the DI container
# imports all models at startup; these services need the same guarantee when called
# in isolation or from background tasks.
from backend.app.infrastructure.persistence.models.operation_model import OperationModel as _OperationModel  # noqa: F401
from backend.app.infrastructure.persistence.models.workstation_model import WorkstationModel as _WorkstationModel  # noqa: F401
from backend.app.infrastructure.persistence.models.material_model import MaterialModel as _MaterialModel  # noqa: F401
from backend.app.infrastructure.persistence.models.bom_model import BOMModel as _BOMModel, BOMLineModel as _BOMLineModel  # noqa: F401
from backend.app.infrastructure.persistence.models.bom_operation_model import BOMOperationModel as _BOMOperationModel  # noqa: F401
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel as _ItemTemplateModel  # noqa: F401
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel as _ItemVariantModel  # noqa: F401


def _cast_status(column):
    """Cast the work_order_status PostgreSQL enum column to Text for string comparisons.

    The work_orders.status column is a native PostgreSQL enum type. SQLAlchemy
    binds Python string values as VARCHAR, which PostgreSQL rejects with:
      'operator does not exist: work_order_status = character varying'
    Casting to String (TEXT) tells PostgreSQL to compare as text, which works
    for both IN and != comparisons.
    """
    return cast(column, String)


class MRPService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def run(self, tenant_id: uuid.UUID) -> dict:
        """Run MRP and persist fresh non-converted suggestions for the tenant.

        For each material with a net shortage:
        - Calculates gross requirement from open Work Order materials
        - Adds safety stock
        - Subtracts available stock (current + open POs - reserved)
        - Looks up the preferred supplier (price-history based, matching MaterialPlanningService)
        - Persists suggestion with supplier_id and supplier_name populated
        """
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

        # Build a supplier lookup map for all materials at once to avoid N+1 queries
        supplier_by_material = await self._build_supplier_map(tenant_id)

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

            # Resolve preferred supplier for this material
            supplier_info = self._get_supplier_for_material(material_key, supplier_by_material)
            supplier_id = supplier_info["id"] if supplier_info else None
            supplier_name = supplier_info["name"] if supplier_info else "No Supplier"

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
                    supplier_id=supplier_id,
                    supplier_name=supplier_name,
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
                # Cast enum column to String so PostgreSQL can compare with VARCHAR params
                _cast_status(WorkOrderModel.status).in_(
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

    async def _build_supplier_map(self, tenant_id: uuid.UUID) -> dict[str, dict]:
        """Return a dict mapping material_id (str) → {id, name} for the preferred supplier.

        Preference order (mirrors MaterialPlanningService._choose_supplier_for_material):
        1. Supplier with most recent price history entry for the material
        2. Fallback: oldest active supplier for the tenant (no price history required)

        A single batch query is used to avoid N+1 per material.
        """
        # Step 1: materials that have price-history entries — pick the most recent
        price_stmt = (
            select(
                SupplierPriceHistoryModel.material_id,
                SupplierModel.id.label("supplier_id"),
                SupplierModel.name.label("supplier_name"),
                func.max(SupplierPriceHistoryModel.effective_from).label("latest"),
            )
            .join(SupplierModel, SupplierModel.id == SupplierPriceHistoryModel.supplier_id)
            .where(
                SupplierPriceHistoryModel.tenant_id == tenant_id,
                SupplierModel.tenant_id == tenant_id,
                SupplierModel.is_active.is_(True),
                SupplierModel.is_deleted.is_(False),
            )
            .group_by(
                SupplierPriceHistoryModel.material_id,
                SupplierModel.id,
                SupplierModel.name,
            )
            .order_by(func.max(SupplierPriceHistoryModel.effective_from).desc())
        )
        price_rows = (await self._session.execute(price_stmt)).all()

        supplier_map: dict[str, dict] = {}
        for row in price_rows:
            mat_key = str(row.material_id)
            # Keep only the first (most-recent) entry per material
            if mat_key not in supplier_map:
                supplier_map[mat_key] = {"id": row.supplier_id, "name": row.supplier_name}

        # Step 2: fallback supplier for any material without a price-history match
        fallback_stmt = (
            select(SupplierModel)
            .where(
                SupplierModel.tenant_id == tenant_id,
                SupplierModel.is_active.is_(True),
                SupplierModel.is_deleted.is_(False),
            )
            .order_by(SupplierModel.created_at.asc())
            .limit(1)
        )
        fallback = (await self._session.execute(fallback_stmt)).scalar_one_or_none()
        self._fallback_supplier = (
            {"id": fallback.id, "name": fallback.name} if fallback else None
        )

        return supplier_map

    def _get_supplier_for_material(self, material_id: str, supplier_map: dict[str, dict]) -> Optional[dict]:
        """Return supplier info for a material, falling back to the tenant-level default."""
        return supplier_map.get(material_id) or getattr(self, "_fallback_supplier", None)

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
