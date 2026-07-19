"""Inventory Reservation Service - domain service for reservation lifecycle."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.domain.inventory.entities.inventory_reservation import (
    InventoryReservation,
    ReservationStatus,
)
from backend.app.domain.inventory.entities.material_shortage import (
    MaterialShortage,
    ShortageStatus,
)


class InventoryReservationService:
    """Domain service for inventory reservation lifecycle management.

    Responsibilities:
    - Handle partial reservations
    - Track reservation states
    - Create shortage records when needed
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._inventory = InventoryService(session)

    async def reserve_for_work_order(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        required_quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
    ) -> tuple[Decimal, Decimal, Optional[uuid.UUID]]:
        """Reserve material for work order with partial reservation handling.

        Returns: (reserved_qty, shortage_qty, shortage_record_id)
        """
        # Reserve available stock
        reserved_qty, shortage_qty = await self._inventory.reserve_for_work_order(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=required_quantity,
            work_order_id=work_order_id,
            unit_id=unit_id,
            created_by=created_by,
        )

        shortage_record_id = None

        # Create shortage record if shortage exists
        if shortage_qty > 0:
            await self._inventory.create_shortage_record(
                tenant_id=tenant_id,
                work_order_id=work_order_id,
                material_id=material_id,
                required_quantity=required_quantity,
                shortage_quantity=shortage_qty,
                created_by=created_by,
            )
            # Note: We would return the actual shortage record ID after model creation
            # For now, we'll return None as placeholder
            shortage_record_id = None

        return reserved_qty, shortage_qty, shortage_record_id

    async def get_reservation_audit_trail(
        self,
        *,
        tenant_id: uuid.UUID,
        reference_type: str,
        reference_id: uuid.UUID,
    ) -> list[InventoryReservation]:
        """Get full reservation audit trail for a reference."""
        from backend.app.infrastructure.persistence.models.inventory_reservation_model import (
            InventoryReservationModel,
        )

        stmt = (
            select(InventoryReservationModel)
            .where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.reference_type == reference_type,
                InventoryReservationModel.reference_id == reference_id,
            )
            .order_by(InventoryReservationModel.created_at)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        reservations = []
        for model in models:
            reservations.append(
                InventoryReservation(
                    id=model.id,
                    tenant_id=model.tenant_id,
                    reference_type=model.reference_type,
                    reference_id=model.reference_id,
                    material_id=model.material_id,
                    batch_id=model.batch_id,
                    quantity=Decimal(str(model.quantity)),
                    status=ReservationStatus(model.status),
                    unit_id=model.unit_id,
                    issued_quantity=Decimal(str(model.issued_quantity or 0)),
                    consumed_quantity=Decimal(str(model.consumed_quantity or 0)),
                    returned_quantity=Decimal(str(model.returned_quantity or 0)),
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                )
            )
        return reservations

    async def get_shortages_for_work_order(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
    ) -> list[MaterialShortage]:
        """Get all shortage records for a work order."""
        return await self._inventory.get_shortages_for_work_order(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
        )
