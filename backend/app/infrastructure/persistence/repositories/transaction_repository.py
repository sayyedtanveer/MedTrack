from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.inventory.entities.inventory_transaction import InventoryTransaction, ReferenceType, TransactionType
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class TransactionRepository(BaseRepository[InventoryTransaction, InventoryTransactionModel]):

    def _model_class(self) -> Type[InventoryTransactionModel]:
        return InventoryTransactionModel

    def _to_entity(self, model: InventoryTransactionModel) -> InventoryTransaction:
        return InventoryTransaction(
            id=model.id,
            tenant_id=model.tenant_id,
            material_id=model.material_id,
            transaction_type=TransactionType(model.transaction_type),
            quantity=Decimal(str(model.quantity)),
            unit_id=model.unit_id,
            batch_id=model.batch_id,
            from_location_id=model.from_location_id,
            to_location_id=model.to_location_id,
            reference_type=ReferenceType(model.reference_type),
            reference_id=model.reference_id,
            remarks=model.remarks,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: InventoryTransaction) -> InventoryTransactionModel:
        return InventoryTransactionModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            material_id=entity.material_id,
            transaction_type=entity.transaction_type.value,
            quantity=float(entity.quantity),
            unit_id=entity.unit_id,
            batch_id=entity.batch_id,
            from_location_id=entity.from_location_id,
            to_location_id=entity.to_location_id,
            reference_type=entity.reference_type.value,
            reference_id=entity.reference_id,
            remarks=entity.remarks,
            created_by=entity.created_by,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def list_by_material(
        self,
        material_id: uuid.UUID,
        tenant_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> List[InventoryTransaction]:
        offset = (page - 1) * page_size
        stmt = (
            select(InventoryTransactionModel)
            .where(
                InventoryTransactionModel.material_id == material_id,
                InventoryTransactionModel.tenant_id == tenant_id,
                InventoryTransactionModel.is_deleted.is_(False),
            )
            .offset(offset)
            .limit(page_size)
            .order_by(InventoryTransactionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(
        self,
        tenant_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> List[InventoryTransaction]:
        offset = (page - 1) * page_size
        stmt = (
            select(InventoryTransactionModel)
            .where(
                InventoryTransactionModel.tenant_id == tenant_id,
                InventoryTransactionModel.is_deleted.is_(False),
            )
            .offset(offset)
            .limit(page_size)
            .order_by(InventoryTransactionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]
