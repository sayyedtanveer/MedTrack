"""Inventory Traceability Service - full inventory orchestration."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.inventory_management_models import StockLedgerModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.inventory_reservation_model import InventoryReservationModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.batch_model import BatchModel
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel


class InventoryTraceabilityService:
    """Service for inventory traceability and audit trail.

    Responsibilities:
    - Get material traceability (full history)
    - Get stock ledger entries
    - Get audit trail for specific transactions
    - Trace material from receipt to issue
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_material_traceability(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> list[dict]:
        """Get full traceability history for a material."""
        stmt = (
            select(InventoryTransactionModel, MaterialModel, BatchModel)
            .join(MaterialModel, MaterialModel.id == InventoryTransactionModel.material_id)
            .outerjoin(BatchModel, BatchModel.id == InventoryTransactionModel.batch_id)
            .where(
                InventoryTransactionModel.tenant_id == tenant_id,
                InventoryTransactionModel.material_id == material_id,
                InventoryTransactionModel.is_deleted.is_(False),
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.is_deleted.is_(False),
            )
            .order_by(InventoryTransactionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        traceability = []
        for tx, material, batch in rows:
            reservation = None
            work_order = None
            if tx.reference_type == "work_order" and tx.reference_id is not None:
                reservation = (
                    await self._session.execute(
                        select(InventoryReservationModel).where(
                            InventoryReservationModel.tenant_id == tenant_id,
                            InventoryReservationModel.reference_type == "work_order",
                            InventoryReservationModel.reference_id == tx.reference_id,
                            InventoryReservationModel.material_id == tx.material_id,
                            InventoryReservationModel.batch_id == tx.batch_id,
                        )
                    )
                ).scalars().first()
                work_order = (
                    await self._session.execute(
                        select(WorkOrderModel).where(
                            WorkOrderModel.id == tx.reference_id,
                            WorkOrderModel.tenant_id == tenant_id,
                            WorkOrderModel.is_deleted.is_(False),
                        )
                    )
                ).scalar_one_or_none()
            traceability.append({
                "transaction_id": tx.id,
                "transaction_type": tx.transaction_type,
                "material_code": material.code,
                "material_name": material.name,
                "quantity": tx.quantity,
                "unit_id": tx.unit_id,
                "batch_id": tx.batch_id,
                "batch_number": batch.batch_number if batch is not None else None,
                "reference_type": tx.reference_type,
                "reference_id": tx.reference_id,
                "wo_number": work_order.wo_number if work_order is not None else None,
                "reserved_quantity": reservation.quantity if reservation is not None else None,
                "issued_quantity": reservation.issued_quantity if reservation is not None else None,
                "consumed_quantity": reservation.consumed_quantity if reservation is not None else None,
                "returned_quantity": reservation.returned_quantity if reservation is not None else None,
                "created_at": tx.created_at,
                "created_by": tx.created_by,
                "remarks": tx.remarks,
            })

        return traceability

    async def get_stock_ledger(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: Optional[uuid.UUID] = None,
        location_id: Optional[uuid.UUID] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get stock ledger entries."""
        stmt = (
            select(StockLedgerModel)
            .where(StockLedgerModel.tenant_id == tenant_id)
        )
        if material_id:
            stmt = stmt.where(StockLedgerModel.material_id == material_id)
        if location_id:
            stmt = stmt.where(StockLedgerModel.location_id == location_id)
        stmt = stmt.order_by(StockLedgerModel.transaction_date.desc()).limit(limit)
        
        result = await self._session.execute(stmt)
        ledger_entries = result.scalars().all()

        ledger = []
        for entry in ledger_entries:
            ledger.append({
                "ledger_id": entry.id,
                "material_id": entry.material_id,
                "location_id": entry.location_id,
                "transaction_type": entry.transaction_type,
                "quantity_change": entry.quantity_change,
                "transaction_date": entry.transaction_date,
                "reference_type": entry.reference_type,
                "reference_id": entry.reference_id,
            })

        return ledger

    async def get_transaction_audit_trail(
        self,
        *,
        tenant_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> dict:
        """Get full audit trail for a specific transaction."""
        stmt = (
            select(InventoryTransactionModel, MaterialModel, BatchModel)
            .join(MaterialModel, MaterialModel.id == InventoryTransactionModel.material_id)
            .outerjoin(BatchModel, BatchModel.id == InventoryTransactionModel.batch_id)
            .where(
                InventoryTransactionModel.id == transaction_id,
                InventoryTransactionModel.tenant_id == tenant_id,
                MaterialModel.tenant_id == tenant_id,
            )
        )
        result = await self._session.execute(stmt)
        row = result.one_or_none()

        if not row:
            return None
        tx, material, batch = row

        return {
            "transaction_id": tx.id,
            "transaction_type": tx.transaction_type,
            "material_id": tx.material_id,
            "material_code": material.code,
            "material_name": material.name,
            "batch_id": tx.batch_id,
            "batch_number": batch.batch_number if batch is not None else None,
            "quantity": tx.quantity,
            "unit_id": tx.unit_id,
            "reference_type": tx.reference_type,
            "reference_id": tx.reference_id,
            "created_at": tx.created_at,
            "created_by": tx.created_by,
            "remarks": tx.remarks,
            "from_location_id": tx.from_location_id,
            "to_location_id": tx.to_location_id,
        }

    async def trace_material_lifecycle(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        batch_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """Trace material lifecycle from receipt to consumption."""
        # Get all transactions for this material
        stmt = (
            select(InventoryTransactionModel)
            .where(
                InventoryTransactionModel.tenant_id == tenant_id,
                InventoryTransactionModel.material_id == material_id,
                InventoryTransactionModel.is_deleted.is_(False),
            )
        )
        if batch_id is not None:
            stmt = stmt.where(InventoryTransactionModel.batch_id == batch_id)
        stmt = stmt.order_by(InventoryTransactionModel.created_at)
        result = await self._session.execute(stmt)
        transactions = result.scalars().all()

        # Calculate running balance
        running_balance = 0
        lifecycle = {
            "material_id": material_id,
            "initial_balance": 0,
            "current_balance": 0,
            "total_received": 0,
            "total_issued": 0,
            "transactions": [],
        }

        for tx in transactions:
            tx_type = str(tx.transaction_type or "").lower()
            if tx_type in ("in", "receipt", "purchase_receipt", "production_receipt", "transfer_in", "fg_receipt"):
                running_balance += tx.quantity
                lifecycle["total_received"] += tx.quantity
            elif tx_type in ("out", "issue", "transfer_out", "consumption", "consume", "consume_reservation"):
                running_balance -= tx.quantity
                lifecycle["total_issued"] += tx.quantity

            lifecycle["transactions"].append({
                "transaction_id": tx.id,
                "transaction_type": tx.transaction_type,
                "batch_id": tx.batch_id,
                "quantity": tx.quantity,
                "running_balance": running_balance,
                "created_at": tx.created_at,
                "reference_type": tx.reference_type,
                "reference_id": tx.reference_id,
            })

        lifecycle["current_balance"] = running_balance

        return lifecycle
