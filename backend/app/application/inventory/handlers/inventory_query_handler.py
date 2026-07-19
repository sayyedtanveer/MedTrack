from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from backend.app.application.inventory.commands.inventory_commands import (
    AddStockCommand, RemoveStockCommand, AdjustStockCommand,
    CreateMaterialCommand, UpdateMaterialCommand,
)
from backend.app.application.inventory.handlers.inventory_handlers import (
    AddStockHandler, AdjustStockHandler, CreateMaterialHandler,
    MaterialResult, RemoveStockHandler, UpdateMaterialHandler, _to_result,
)
from backend.app.application.inventory.queries.inventory_queries import (
    GetMaterialQuery, GetStockQuery, GetTransactionsQuery, ListMaterialsQuery,
)
from backend.app.domain.inventory.entities.inventory_transaction import InventoryTransaction
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.infrastructure.persistence.repositories.transaction_repository import TransactionRepository


@dataclass
class StockInfo:
    material_id: uuid.UUID
    material_code: str
    material_name: str
    current_stock: Decimal
    reserved_stock: Decimal
    available_stock: Decimal
    base_unit_id: Optional[uuid.UUID]
    is_low_stock: bool
    reorder_level: Optional[Decimal]


@dataclass
class TransactionResult:
    id: uuid.UUID
    material_id: uuid.UUID
    transaction_type: str
    quantity: Decimal
    unit_id: Optional[uuid.UUID]
    from_location_id: Optional[uuid.UUID]
    to_location_id: Optional[uuid.UUID]
    reference_type: str
    reference_id: Optional[uuid.UUID]
    remarks: Optional[str]
    created_by: uuid.UUID
    created_at: str


@dataclass
class PaginatedMaterials:
    items: List[MaterialResult]
    total: int
    page: int
    page_size: int


class InventoryQueryHandler:
    def __init__(self, material_repo: MaterialRepository, tx_repo: TransactionRepository):
        self._material_repo = material_repo
        self._tx_repo = tx_repo

    async def list_materials(self, query: ListMaterialsQuery) -> PaginatedMaterials:
        items = await self._material_repo.search(
            tenant_id=query.tenant_id,
            query=query.query,
            category=query.category,
            material_type=query.material_type,
            is_active=query.is_active,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self._material_repo.count(
            tenant_id=query.tenant_id,
            query=query.query,
            category=query.category,
            material_type=query.material_type,
            is_active=query.is_active,
        )
        return PaginatedMaterials(
            items=[_to_result(m) for m in items],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_material(self, query: GetMaterialQuery) -> Optional[MaterialResult]:
        material = await self._material_repo.get_by_id(query.id, query.tenant_id)
        return _to_result(material) if material else None

    async def get_stock(self, query: GetStockQuery) -> Optional[StockInfo]:
        material = await self._material_repo.get_by_id(query.material_id, query.tenant_id)
        if not material:
            return None
        return StockInfo(
            material_id=material.id,
            material_code=material.code,
            material_name=material.name,
            current_stock=material.current_stock,
            reserved_stock=material.reserved_stock,
            available_stock=material.get_available_stock(),
            base_unit_id=material.base_unit_id,
            is_low_stock=material.is_low_stock(),
            reorder_level=material.reorder_level,
        )

    async def get_transactions(self, query: GetTransactionsQuery) -> List[TransactionResult]:
        if query.material_id:
            txs = await self._tx_repo.list_by_material(
                material_id=query.material_id,
                tenant_id=query.tenant_id,
                page=query.page,
                page_size=query.page_size,
            )
        else:
            txs = await self._tx_repo.list_all(
                tenant_id=query.tenant_id,
                page=query.page,
                page_size=query.page_size,
            )
        return [
            TransactionResult(
                id=tx.id,
                material_id=tx.material_id,
                transaction_type=tx.transaction_type.value,
                quantity=tx.quantity,
                unit_id=tx.unit_id,
                from_location_id=tx.from_location_id,
                to_location_id=tx.to_location_id,
                reference_type=tx.reference_type.value,
                reference_id=tx.reference_id,
                remarks=tx.remarks,
                created_by=tx.created_by,
                created_at=tx.created_at.isoformat(),
            )
            for tx in txs
        ]
