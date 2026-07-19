from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Type

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.product.entities.item_variant import ItemVariant
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class ItemVariantRepository(BaseRepository[ItemVariant, ItemVariantModel]):

    def _model_class(self) -> Type[ItemVariantModel]:
        return ItemVariantModel

    def _to_entity(self, model: ItemVariantModel) -> ItemVariant:
        return ItemVariant(
            id=model.id,
            tenant_id=model.tenant_id,
            template_id=model.template_id,
            # These are only needed when building from scratch; for rehydration
            # we pass pre-computed code/name/variant_key directly.
            template_code="",
            template_name="",
            attribute_keys_ordered=[],
            attribute_values=model.attribute_values or {},
            base_unit_id=model.base_unit_id,
            material_id=model.material_id,
            standard_cost=Decimal(str(model.standard_cost)) if model.standard_cost is not None else Decimal("0"),
            selling_price=Decimal(str(model.selling_price)) if model.selling_price is not None else None,
            code=model.code,
            name=model.name,
            variant_key=model.variant_key,
            is_active=model.is_active,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: ItemVariant) -> ItemVariantModel:
        return ItemVariantModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            template_id=entity.template_id,
            code=entity.code,
            name=entity.name,
            variant_key=entity.variant_key,
            attribute_values=entity.attribute_values,
            base_unit_id=entity.base_unit_id,
            material_id=entity.material_id,
            standard_cost=float(entity.standard_cost),
            selling_price=float(entity.selling_price) if entity.selling_price is not None else None,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    # ── Custom query methods ──────────────────────────────────────────────────

    async def get_by_variant_key(
        self,
        variant_key: str,
        template_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[ItemVariant]:
        stmt = select(ItemVariantModel).where(
            ItemVariantModel.tenant_id == tenant_id,
            ItemVariantModel.template_id == template_id,
            ItemVariantModel.variant_key == variant_key,
            ItemVariantModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_variants(
        self,
        template_id: uuid.UUID,
        tenant_id: uuid.UUID,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[ItemVariant], int]:
        base_stmt = select(ItemVariantModel).where(
            ItemVariantModel.tenant_id == tenant_id,
            ItemVariantModel.template_id == template_id,
            ItemVariantModel.is_deleted.is_(False),
        )
        if is_active is not None:
            base_stmt = base_stmt.where(ItemVariantModel.is_active == is_active)
        if search:
            from sqlalchemy import or_
            like = f"%{search}%"
            base_stmt = base_stmt.where(
                or_(
                    ItemVariantModel.name.ilike(like),
                    ItemVariantModel.code.ilike(like),
                )
            )

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        paged = (
            base_stmt
            .order_by(ItemVariantModel.code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self._session.execute(paged)).scalars().all()
        return [self._to_entity(r) for r in rows], total

    async def list_all_variants(
        self,
        tenant_id: uuid.UUID,
        search: Optional[str] = None,
        is_active: Optional[bool] = True,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ItemVariant], int]:
        """All variants for tenant (search by code/name)."""
        base_stmt = select(ItemVariantModel).where(
            ItemVariantModel.tenant_id == tenant_id,
            ItemVariantModel.is_deleted.is_(False),
        )
        if is_active is not None:
            base_stmt = base_stmt.where(ItemVariantModel.is_active == is_active)
        if search:
            from sqlalchemy import or_

            like = f"%{search}%"
            base_stmt = base_stmt.where(
                or_(
                    ItemVariantModel.name.ilike(like),
                    ItemVariantModel.code.ilike(like),
                )
            )

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        paged = (
            base_stmt.order_by(ItemVariantModel.code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self._session.execute(paged)).scalars().all()
        return [self._to_entity(r) for r in rows], total
