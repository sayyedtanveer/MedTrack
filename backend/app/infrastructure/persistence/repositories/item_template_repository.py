from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.product.entities.item_template import ItemTemplate
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class ItemTemplateRepository(BaseRepository[ItemTemplate, ItemTemplateModel]):

    def _model_class(self) -> Type[ItemTemplateModel]:
        return ItemTemplateModel

    def _to_entity(self, model: ItemTemplateModel) -> ItemTemplate:
        from backend.app.domain.product.value_objects.product_status import ProductStatus
        # Convert status string to uppercase to ensure it matches ProductStatus enum values
        status_value = (model.status or 'ACTIVE').upper()
        try:
            status = ProductStatus(status_value)
        except ValueError:
            # Fallback to ACTIVE if status value is invalid
            status = ProductStatus.ACTIVE
        
        return ItemTemplate(
            id=model.id,
            tenant_id=model.tenant_id,
            code=model.code,
            name=model.name,
            description=model.description,
            category_id=model.category_id,
            base_unit_id=model.base_unit_id,
            attributes=model.attributes or [],
            status=status,
            code_locked=model.code_locked,
            is_active=model.is_active,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: ItemTemplate) -> ItemTemplateModel:
        return ItemTemplateModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            code=entity.code,
            code_locked=entity.code_locked,
            name=entity.name,
            description=entity.description,
            category_id=entity.category_id,
            base_unit_id=entity.base_unit_id,
            attributes=entity.attributes,
            status=entity.status.value,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    # ── Custom query methods ──────────────────────────────────────────────────

    async def get_by_code(self, code: str, tenant_id: uuid.UUID) -> Optional[ItemTemplate]:
        stmt = select(ItemTemplateModel).where(
            ItemTemplateModel.tenant_id == tenant_id,
            ItemTemplateModel.code == code.upper(),
            ItemTemplateModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_templates(
        self,
        tenant_id: uuid.UUID,
        category_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ItemTemplate], int]:
        base_stmt = select(ItemTemplateModel).where(
            ItemTemplateModel.tenant_id == tenant_id,
            ItemTemplateModel.is_deleted.is_(False),
        )
        if is_active is not None:
            base_stmt = base_stmt.where(ItemTemplateModel.is_active == is_active)
        if category_id is not None:
            base_stmt = base_stmt.where(ItemTemplateModel.category_id == category_id)
        if search:
            like = f"%{search}%"
            base_stmt = base_stmt.where(
                or_(
                    ItemTemplateModel.name.ilike(like),
                    ItemTemplateModel.code.ilike(like),
                )
            )

        # Count
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Paginate
        paged = (
            base_stmt
            .order_by(ItemTemplateModel.code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self._session.execute(paged)).scalars().all()
        return [self._to_entity(r) for r in rows], total
