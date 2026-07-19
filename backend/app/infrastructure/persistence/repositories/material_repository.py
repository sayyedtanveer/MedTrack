from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional, Type

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.inventory.entities.material import Material, MaterialType
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository

def _normalize_material_type(value: MaterialType | str | None) -> MaterialType:
    return Material.coerce_material_type(value)


def _normalize_material_name(value: str) -> str:
    return " ".join(str(value or "").split()).strip().lower()


class MaterialRepository(BaseRepository[Material, MaterialModel]):

    def _model_class(self) -> Type[MaterialModel]:
        return MaterialModel

    def _to_entity(self, model: MaterialModel) -> Material:
        return Material(
            id=model.id,
            tenant_id=model.tenant_id,
            code=model.code,
            name=model.name,
            material_type=_normalize_material_type(model.material_type),
            description=model.description,
            category_id=model.category_id,
            base_unit_id=model.base_unit_id,
            current_stock=Decimal(str(model.current_stock)),
            reserved_stock=Decimal(str(model.reserved_stock)),
            reorder_level=Decimal(str(model.reorder_level)) if model.reorder_level is not None else None,
            location_id=model.location_id,
            is_batch_tracked=model.is_batch_tracked,
            is_serialized=model.is_serialized,
            code_locked=model.code_locked,
            inspection_required=model.inspection_required,
            inspection_template_id=model.inspection_template_id,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: Material) -> MaterialModel:
        return MaterialModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            code=entity.code,
            name=entity.name,
            description=entity.description,
            material_type=_normalize_material_type(entity.material_type).value,
            category_id=entity.category_id,
            base_unit_id=entity.base_unit_id,
            current_stock=float(entity.current_stock),
            reserved_stock=float(entity.reserved_stock),
            reorder_level=float(entity.reorder_level) if entity.reorder_level is not None else None,
            location_id=entity.location_id,
            is_batch_tracked=entity.is_batch_tracked,
            is_serialized=entity.is_serialized,
            code_locked=entity.code_locked,
            inspection_required=entity.inspection_required,
            inspection_template_id=entity.inspection_template_id,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_code(self, code: str, tenant_id: uuid.UUID) -> Optional[Material]:
        stmt = select(MaterialModel).where(
            MaterialModel.code == code,
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def code_exists(self, code: str, tenant_id: uuid.UUID, exclude_id: Optional[uuid.UUID] = None) -> bool:
        stmt = select(MaterialModel.id).where(
            MaterialModel.code == code,
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted.is_(False),
        )
        if exclude_id:
            stmt = stmt.where(MaterialModel.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def name_exists(
        self,
        name: str,
        tenant_id: uuid.UUID,
        material_type: MaterialType | str | None = None,
        exclude_id: Optional[uuid.UUID] = None,
    ) -> bool:
        normalized_name = _normalize_material_name(name)
        stmt = select(MaterialModel.id).where(
            func.lower(func.trim(MaterialModel.name)) == normalized_name,
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted.is_(False),
        )
        if material_type is not None:
            stmt = stmt.where(
                func.lower(func.trim(MaterialModel.material_type))
                == _normalize_material_type(material_type).value
            )
        if exclude_id:
            stmt = stmt.where(MaterialModel.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def search(
        self,
        tenant_id: uuid.UUID,
        query: Optional[str] = None,
        category: Optional[str] = None,
        material_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[Material]:
        offset = (page - 1) * page_size
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted.is_(False),
        )
        if query:
            stmt = stmt.where(
                or_(
                    MaterialModel.name.ilike(f"%{query}%"),
                    MaterialModel.code.ilike(f"%{query}%"),
                )
            )
        if category:
            pass # TODO: category filter needs to map to material_categories name now, skipping for now
        if material_type:
            stmt = stmt.where(
                func.lower(func.trim(MaterialModel.material_type))
                == _normalize_material_type(material_type).value
            )
        if is_active is not None:
            stmt = stmt.where(MaterialModel.is_active == is_active)

        stmt = stmt.offset(offset).limit(page_size).order_by(MaterialModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(
        self,
        tenant_id: uuid.UUID,
        query: Optional[str] = None,
        category: Optional[str] = None,
        material_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        stmt = select(func.count()).select_from(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted.is_(False),
        )
        if query:
            stmt = stmt.where(
                or_(
                    MaterialModel.name.ilike(f"%{query}%"),
                    MaterialModel.code.ilike(f"%{query}%"),
                )
            )
        if category:
            pass # TODO: handle category filter via join
        if material_type:
            stmt = stmt.where(
                func.lower(func.trim(MaterialModel.material_type))
                == _normalize_material_type(material_type).value
            )
        if is_active is not None:
            stmt = stmt.where(MaterialModel.is_active == is_active)
        result = await self._session.execute(stmt)
        return result.scalar_one()
