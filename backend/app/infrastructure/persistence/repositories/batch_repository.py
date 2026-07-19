from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.inventory.entities.batch import Batch, BatchStatus
from backend.app.infrastructure.persistence.models.batch_model import BatchModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class BatchRepository(BaseRepository[Batch, BatchModel]):

    def _model_class(self) -> Type[BatchModel]:
        return BatchModel

    def _to_entity(self, model: BatchModel) -> Batch:
        return Batch(
            id=model.id,
            tenant_id=model.tenant_id,
            material_id=model.material_id,
            batch_number=model.batch_number,
            quantity=Decimal(str(model.quantity)),
            remaining_quantity=Decimal(str(model.remaining_quantity)) if model.remaining_quantity is not None else Decimal(str(model.quantity)),
            expiry_date=model.expiry_date,
            location_id=model.location_id,
            status=BatchStatus(model.status) if model.status else BatchStatus.IN_STOCK,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: Batch) -> BatchModel:
        return BatchModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            material_id=entity.material_id,
            batch_number=entity.batch_number,
            quantity=float(entity.quantity),
            remaining_quantity=float(entity.remaining_quantity),
            expiry_date=entity.expiry_date,
            location_id=entity.location_id,
            status=entity.status.value,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_batch_number(
        self,
        batch_number: str,
        material_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[Batch]:
        stmt = select(BatchModel).where(
            BatchModel.tenant_id == tenant_id,
            BatchModel.material_id == material_id,
            BatchModel.batch_number == batch_number,
            BatchModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_material(
        self,
        material_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> List[Batch]:
        stmt = (
            select(BatchModel)
            .where(
                BatchModel.tenant_id == tenant_id,
                BatchModel.material_id == material_id,
                BatchModel.is_deleted.is_(False),
            )
            .order_by(BatchModel.expiry_date.asc().nullslast())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_expiring(
        self,
        tenant_id: uuid.UUID,
        before_date: date,
    ) -> List[Batch]:
        """Returns non-expired batches whose expiry_date is <= before_date."""
        today = date.today()
        stmt = (
            select(BatchModel)
            .where(
                BatchModel.tenant_id == tenant_id,
                BatchModel.is_deleted.is_(False),
                BatchModel.expiry_date.is_not(None),
                BatchModel.expiry_date >= today,
                BatchModel.expiry_date <= before_date,
            )
            .order_by(BatchModel.expiry_date.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def batch_number_exists(
        self,
        batch_number: str,
        material_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        stmt = select(BatchModel.id).where(
            BatchModel.tenant_id == tenant_id,
            BatchModel.material_id == material_id,
            BatchModel.batch_number == batch_number,
            BatchModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
