import uuid
from typing import Type

from sqlalchemy import func, select

from backend.app.domain.inventory.entities.unit_of_measure import UnitOfMeasure
from backend.app.infrastructure.persistence.models.bom_model import BOMLineModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class UnitOfMeasureRepository(BaseRepository[UnitOfMeasure, UnitOfMeasureModel]):
    def _model_class(self) -> Type[UnitOfMeasureModel]:
        return UnitOfMeasureModel

    def _to_entity(self, model: UnitOfMeasureModel) -> UnitOfMeasure:
        entity = UnitOfMeasure(
            id=model.id,
            tenant_id=model.tenant_id,
            code=model.code,
            name=model.name,
            precision=model.precision,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        entity._is_deleted = model.is_deleted
        entity._deleted_at = model.deleted_at
        return entity

    def _to_model(self, entity: UnitOfMeasure) -> UnitOfMeasureModel:
        return UnitOfMeasureModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            code=entity.code,
            name=entity.name,
            precision=entity.precision,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
        )

    # ── get_by_id ─────────────────────────────────────────────────────────
    # BaseRepository already provides get_by_id(id, tenant_id) with soft-delete
    # filtering — no override needed.

    # ── update ────────────────────────────────────────────────────────────
    async def update(self, unit: UnitOfMeasure) -> None:
        """Persist changes to an existing unit by merging the mapped model."""
        model = self._to_model(unit)
        await self._session.merge(model)
        await self._session.flush()

    # ── count_material_references ─────────────────────────────────────────
    async def count_material_references(self, unit_id: uuid.UUID) -> int:
        """Count active materials whose base_unit_id references this unit."""
        stmt = select(func.count(MaterialModel.id)).where(
            MaterialModel.base_unit_id == unit_id,
            MaterialModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # ── count_bom_references ──────────────────────────────────────────────
    async def count_bom_references(self, unit_id: uuid.UUID) -> int:
        """Count active BOM lines whose unit_id references this unit."""
        stmt = select(func.count(BOMLineModel.id)).where(
            BOMLineModel.unit_id == unit_id,
            BOMLineModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
