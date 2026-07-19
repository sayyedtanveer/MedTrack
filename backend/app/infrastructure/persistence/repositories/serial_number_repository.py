from __future__ import annotations

import uuid
from typing import List, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.inventory.entities.serial_number import SerialNumber, SerialStatus
from backend.app.infrastructure.persistence.models.serial_number_model import SerialNumberModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class SerialNumberRepository(BaseRepository[SerialNumber, SerialNumberModel]):

    def _model_class(self) -> Type[SerialNumberModel]:
        return SerialNumberModel

    def _to_entity(self, model: SerialNumberModel) -> SerialNumber:
        return SerialNumber(
            id=model.id,
            tenant_id=model.tenant_id,
            material_id=model.material_id,
            serial_number=model.serial_number,
            status=SerialStatus(model.status),
            current_location_id=model.current_location_id,
            reference_id=model.reference_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: SerialNumber) -> SerialNumberModel:
        return SerialNumberModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            material_id=entity.material_id,
            serial_number=entity.serial_number,
            status=entity.status.value,
            current_location_id=entity.current_location_id,
            reference_id=entity.reference_id,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_serial(
        self,
        serial_number: str,
        tenant_id: uuid.UUID,
    ) -> Optional[SerialNumber]:
        stmt = select(SerialNumberModel).where(
            SerialNumberModel.tenant_id == tenant_id,
            SerialNumberModel.serial_number == serial_number,
            SerialNumberModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_material(
        self,
        material_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: Optional[str] = None,
    ) -> List[SerialNumber]:
        stmt = select(SerialNumberModel).where(
            SerialNumberModel.tenant_id == tenant_id,
            SerialNumberModel.material_id == material_id,
            SerialNumberModel.is_deleted.is_(False),
        )
        if status:
            stmt = stmt.where(SerialNumberModel.status == status)
        stmt = stmt.order_by(SerialNumberModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def serial_exists(
        self,
        serial_number: str,
        tenant_id: uuid.UUID,
    ) -> bool:
        stmt = select(SerialNumberModel.id).where(
            SerialNumberModel.tenant_id == tenant_id,
            SerialNumberModel.serial_number == serial_number,
            SerialNumberModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
