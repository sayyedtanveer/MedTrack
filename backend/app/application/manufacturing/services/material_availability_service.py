from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.domain.manufacturing.exceptions import BOMNotFoundError
from backend.app.infrastructure.persistence.models.bom_model import BOMLineModel, BOMModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel


class MaterialAvailabilityService:
    """Preview raw-material requirements for a planned work order."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._inventory = InventoryService(session)

    async def check_material_availability(
        self,
        *,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: Decimal,
        bom_id: uuid.UUID | None = None,
    ) -> dict:
        bom = await self._resolve_bom(
            tenant_id=tenant_id,
            product_id=product_id,
            bom_id=bom_id,
        )

        result = await self._session.execute(
            select(BOMLineModel, MaterialModel, UnitOfMeasureModel)
            .join(MaterialModel, MaterialModel.id == BOMLineModel.material_id)
            .outerjoin(UnitOfMeasureModel, UnitOfMeasureModel.id == BOMLineModel.unit_id)
            .where(
                BOMLineModel.tenant_id == tenant_id,
                BOMLineModel.bom_id == bom.id,
                BOMLineModel.material_id.is_not(None),
                BOMLineModel.is_deleted.is_(False),
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.is_deleted.is_(False),
            )
            .order_by(MaterialModel.code.asc(), MaterialModel.name.asc())
        )
        rows = result.all()

        lines: list[dict] = []
        has_shortage = False
        for bom_line, material, unit in rows:
            scrap_factor = Decimal(str(bom_line.scrap_percentage or 0)) / Decimal("100")
            required_qty = Decimal(str(bom_line.quantity or 0)) * quantity * (
                Decimal("1") + scrap_factor
            )
            available_qty = await self._inventory.get_available_stock(
                tenant_id=tenant_id,
                material_id=material.id,
            )
            shortage_qty = max(required_qty - available_qty, Decimal("0"))

            if shortage_qty > 0:
                has_shortage = True
                status = "low" if available_qty > 0 else "shortage"
            else:
                status = "ok"

            lines.append(
                {
                    "material_id": material.id,
                    "material_code": material.code,
                    "material_name": material.name,
                    "unit_id": bom_line.unit_id,
                    "unit_code": unit.code if unit else None,
                    "unit_name": unit.name if unit else None,
                    "required_quantity": required_qty,
                    "available_quantity": available_qty,
                    "shortage_quantity": shortage_qty,
                    "status": status,
                }
            )

        return {
            "product_id": product_id,
            "bom_id": bom.id,
            "planned_quantity": quantity,
            "has_shortage": has_shortage,
            "shortage_count": sum(1 for line in lines if Decimal(str(line["shortage_quantity"])) > 0),
            "message": None if lines else "Selected BOM has no raw material lines.",
            "lines": lines,
        }

    async def _resolve_bom(
        self,
        *,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        bom_id: uuid.UUID | None,
    ) -> BOMModel:
        stmt = select(BOMModel).where(
            BOMModel.tenant_id == tenant_id,
            BOMModel.is_deleted.is_(False),
        )

        if bom_id is not None:
            stmt = stmt.where(BOMModel.id == bom_id)
        else:
            stmt = stmt.where(BOMModel.variant_id == product_id).order_by(
                BOMModel.is_active.desc(),
                BOMModel.updated_at.desc(),
            )

        result = await self._session.execute(stmt.limit(1))
        bom = result.scalar_one_or_none()
        if bom is None and bom_id is None:
            variant = (
                await self._session.execute(
                    select(ItemVariantModel).where(
                        ItemVariantModel.id == product_id,
                        ItemVariantModel.tenant_id == tenant_id,
                        ItemVariantModel.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if variant and variant.template_id:
                template_result = await self._session.execute(
                    select(BOMModel)
                    .where(
                        BOMModel.tenant_id == tenant_id,
                        BOMModel.template_id == variant.template_id,
                        BOMModel.is_deleted.is_(False),
                    )
                    .order_by(
                        BOMModel.is_active.desc(),
                        BOMModel.updated_at.desc(),
                    )
                    .limit(1)
                )
                bom = template_result.scalar_one_or_none()
        if bom is None:
            raise BOMNotFoundError(f"No BOM found for product {product_id}")
        return bom
