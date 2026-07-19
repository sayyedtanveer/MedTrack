import uuid
from typing import Type

from sqlalchemy import func, select

from backend.app.domain.inventory.entities.material_category import MaterialCategory
from backend.app.infrastructure.persistence.models.material_category_model import MaterialCategoryModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class MaterialCategoryRepository(BaseRepository[MaterialCategory, MaterialCategoryModel]):
    def _model_class(self) -> Type[MaterialCategoryModel]:
        return MaterialCategoryModel

    def _to_entity(self, model: MaterialCategoryModel) -> MaterialCategory:
        entity = MaterialCategory(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            code_prefix=model.code_prefix,
            description=model.description,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        entity._is_deleted = model.is_deleted
        entity._deleted_at = model.deleted_at
        return entity

    def _to_model(self, entity: MaterialCategory) -> MaterialCategoryModel:
        return MaterialCategoryModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            name=entity.name,
            code_prefix=entity.code_prefix,
            description=entity.description,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
        )

    # BaseRepository.get_by_id already provides tenant-scoped lookup with
    # is_deleted filtering — no need to override it here.

    async def update(self, category: MaterialCategory) -> None:
        """Persist changes to an existing category using merge (upsert by PK)."""
        model = self._to_model(category)
        await self._session.merge(model)
        await self._session.flush()

    async def count_material_references(self, category_id: uuid.UUID) -> int:
        """Return the number of active (non-deleted) materials that reference this category."""
        stmt = select(func.count(MaterialModel.id)).where(
            MaterialModel.category_id == category_id,
            MaterialModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
