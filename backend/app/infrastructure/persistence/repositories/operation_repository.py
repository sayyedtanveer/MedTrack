"""Repository for Operation Master persistence."""

from __future__ import annotations

import uuid
from typing import Optional, List

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.manufacturing.entities.operation import Operation, OperationType
from backend.app.infrastructure.persistence.models.operation_model import OperationModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class OperationRepository(BaseRepository[Operation, OperationModel]):
    """Repository for Operation Master CRUD operations."""

    def _model_class(self) -> type[OperationModel]:
        return OperationModel

    def _to_entity(self, model: Optional[OperationModel]) -> Optional[Operation]:
        if not model:
            return None
        return Operation(
            id=model.id,
            tenant_id=model.tenant_id,
            operation_code=model.operation_code,
            name=model.name,
            operation_type=OperationType(model.operation_type),
            description=model.description,
            default_sequence=model.default_sequence,
            estimated_time_minutes=model.estimated_time_minutes,
            qc_required=model.qc_required,
            is_active=model.is_active,
            color=model.color,
            icon_code=model.icon_code,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: Operation) -> OperationModel:
        return OperationModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            operation_code=entity.operation_code,
            name=entity.name,
            operation_type=entity.operation_type.value,
            description=entity.description,
            default_sequence=entity.default_sequence,
            estimated_time_minutes=entity.estimated_time_minutes,
            qc_required=entity.qc_required,
            is_active=entity.is_active,
            color=entity.color,
            icon_code=entity.icon_code,
            created_by=entity.created_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
        )

    async def get_by_code(
        self, 
        tenant_id: uuid.UUID, 
        operation_code: str
    ) -> Optional[Operation]:
        """Fetch operation by business code (never UUID in UI)."""
        stmt = select(OperationModel).where(
            OperationModel.tenant_id == tenant_id,
            OperationModel.operation_code == operation_code,
            OperationModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return self._to_entity(result.scalar_one_or_none())

    async def code_exists(
        self,
        tenant_id: uuid.UUID,
        operation_code: str,
        exclude_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Check if operation code already exists."""
        stmt = select(OperationModel.id).where(
            OperationModel.tenant_id == tenant_id,
            OperationModel.operation_code == operation_code,
            OperationModel.is_deleted.is_(False),
        )
        if exclude_id:
            stmt = stmt.where(OperationModel.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_active(
        self,
        tenant_id: uuid.UUID,
        query: Optional[str] = None,
        operation_type: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[Operation]:
        """List operations with optional filtering and search."""
        stmt = select(OperationModel).where(
            OperationModel.tenant_id == tenant_id,
            OperationModel.is_deleted.is_(False),
        )

        if not include_inactive:
            stmt = stmt.where(OperationModel.is_active.is_(True))

        # Search by code or name
        if query:
            stmt = stmt.where(
                or_(
                    OperationModel.operation_code.ilike(f"%{query}%"),
                    OperationModel.name.ilike(f"%{query}%"),
                )
            )

        # Filter by type
        if operation_type:
            stmt = stmt.where(OperationModel.operation_type == operation_type)

        # Sort by sequence
        stmt = stmt.order_by(OperationModel.default_sequence.asc())

        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_for_bom(
        self,
        tenant_id: uuid.UUID,
    ) -> List[Operation]:
        """List active operations available for BOM attachment."""
        return await self.list_active(
            tenant_id=tenant_id,
            include_inactive=False,
        )

    async def count_by_tenant(
        self,
        tenant_id: uuid.UUID,
        include_inactive: bool = True,
    ) -> int:
        """Count operations for a tenant."""
        stmt = select(func.count()).select_from(OperationModel).where(
            OperationModel.tenant_id == tenant_id,
            OperationModel.is_deleted.is_(False),
        )
        if not include_inactive:
            stmt = stmt.where(OperationModel.is_active.is_(True))
        return (await self._session.execute(stmt)).scalar() or 0

    async def soft_deactivate(
        self,
        tenant_id: uuid.UUID,
        operation_id: uuid.UUID,
    ) -> None:
        """Deactivate operation without deleting."""
        stmt = select(OperationModel).where(
            OperationModel.id == operation_id,
            OperationModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.is_active = False
            self._session.add(model)

    async def soft_reactivate(
        self,
        tenant_id: uuid.UUID,
        operation_id: uuid.UUID,
    ) -> None:
        """Reactivate a deactivated operation."""
        stmt = select(OperationModel).where(
            OperationModel.id == operation_id,
            OperationModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.is_active = True
            self._session.add(model)

    async def check_operation_in_use(
        self,
        tenant_id: uuid.UUID,
        operation_id: uuid.UUID,
    ) -> bool:
        """Check if operation is currently attached to any BOM."""
        from backend.app.infrastructure.persistence.models.bom_operation_model import BOMOperationModel
        
        stmt = select(func.count()).select_from(BOMOperationModel).where(
            BOMOperationModel.operation_id == operation_id,
        )
        count = (await self._session.execute(stmt)).scalar() or 0
        return count > 0

    async def get_by_id(self, operation_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Operation]:
        stmt = select(OperationModel).where(
            OperationModel.id == operation_id,
            OperationModel.tenant_id == tenant_id,
            OperationModel.is_deleted.is_(False)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_operations(self, tenant_id: uuid.UUID) -> List[Operation]:
        stmt = select(OperationModel).where(
            OperationModel.tenant_id == tenant_id,
            OperationModel.is_deleted.is_(False)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    def save(self, operation: Operation) -> None:
        model = self._to_model(operation)
        self._session.add(model)
