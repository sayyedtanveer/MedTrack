import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.domain.bom.entities.workstation import Workstation
from backend.app.infrastructure.persistence.models.workstation_model import WorkstationModel
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


class WorkstationRepository:
    def __init__(self, uow: SQLAlchemyUnitOfWork):
        self._uow = uow

    @property
    def _session(self):
        return self._uow._session

    def _to_entity(self, model: WorkstationModel) -> Workstation:
        return Workstation(
            id=model.id,
            tenant_id=model.tenant_id,
            code=model.code,
            name=model.name,
            capacity_hours_per_day=float(model.capacity_hours_per_day),
            hourly_rate=float(model.hourly_rate),
            is_active=model.is_active,
            is_deleted=model.is_deleted,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Workstation) -> WorkstationModel:
        return WorkstationModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            code=entity.code,
            name=entity.name,
            capacity_hours_per_day=entity.capacity_hours_per_day,
            hourly_rate=entity.hourly_rate,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
        )

    async def get_by_id(self, workstation_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Workstation]:
        stmt = select(WorkstationModel).where(
            WorkstationModel.id == workstation_id,
            WorkstationModel.tenant_id == tenant_id,
            WorkstationModel.is_deleted.is_(False)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_workstations(self, tenant_id: uuid.UUID) -> List[Workstation]:
        stmt = select(WorkstationModel).where(
            WorkstationModel.tenant_id == tenant_id,
            WorkstationModel.is_deleted.is_(False)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    def save(self, workstation: Workstation) -> None:
        model = self._to_model(workstation)
        self._session.add(model)
