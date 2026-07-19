"""Storekeeper Handler - orchestrates storekeeper operational flow."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.inventory.commands.storekeeper_commands import (
    ReserveStockCommand,
    IssueMaterialCommand,
    PartialIssueCommand,
    RejectIssueCommand,
    ReturnMaterialCommand,
)
from backend.app.application.inventory.services.storekeeper_service import StorekeeperService


class StorekeeperHandler:
    """Handler for storekeeper operational actions."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._storekeeper = StorekeeperService(session)

    async def handle_reserve_stock(self, cmd: ReserveStockCommand) -> None:
        """Handle stock reservation for work order.
        
        Triggers WO transition: MATERIAL_PENDING → MATERIAL_RESERVED.
        Inventory: AVAILABLE → RESERVED.
        """
        await self._storekeeper.reserve_stock(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            material_id=cmd.material_id,
            quantity=cmd.quantity,
            unit_id=cmd.unit_id,
            batch_id=cmd.batch_id,
            reserved_by=cmd.reserved_by,
        )

    async def handle_issue_material(self, cmd: IssueMaterialCommand) -> None:
        """Handle material issue to work order.
        
        Triggers WO transition: MATERIAL_RESERVED → MATERIAL_ISSUED.
        Inventory: RESERVED → ISSUED.
        """
        await self._storekeeper.issue_material(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            material_id=cmd.material_id,
            quantity=cmd.quantity,
            unit_id=cmd.unit_id,
            batch_id=cmd.batch_id,
            issued_by=cmd.issued_by,
        )

    async def handle_partial_issue(self, cmd: PartialIssueCommand) -> None:
        """Handle partial material issue to work order."""
        await self._storekeeper.partially_issue_material(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            material_id=cmd.material_id,
            quantity=cmd.quantity,
            unit_id=cmd.unit_id,
            batch_id=cmd.batch_id,
            issued_by=cmd.issued_by,
        )

    async def handle_reject_issue(self, cmd: RejectIssueCommand) -> None:
        """Handle rejection of material issue request."""
        await self._storekeeper.reject_issue(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            material_id=cmd.material_id,
            reason=cmd.reason,
            rejected_by=cmd.rejected_by,
        )

    async def handle_return_material(self, cmd: ReturnMaterialCommand) -> None:
        """Handle return of issued material.
        
        Inventory: ISSUED → RESERVED.
        """
        await self._storekeeper.return_material(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            material_id=cmd.material_id,
            quantity=cmd.quantity,
            unit_id=cmd.unit_id,
            batch_id=cmd.batch_id,
            returned_by=cmd.returned_by,
        )
