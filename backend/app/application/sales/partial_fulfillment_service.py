"""
Partial Fulfillment Service — Handles partial production and dispatch scenarios.

Provides:
1. Create New WO for Remaining — creates a new work order for unfulfilled SO line quantity (Req 19.5)
2. Short-Close Line — closes a partially fulfilled line and recalculates SO totals (Req 19.6)
3. Partial dispatch validation — ensures dispatch_quantity per line ≤ (allocated - dispatched) (Req 20.1, 20.7)
4. Check full allocation for dispatch readiness (Req 19.8)
"""
from __future__ import annotations

import uuid
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.sales.value_objects.order_status import OrderStatus
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderModel,
    SalesOrderLineModel,
)
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel

logger = logging.getLogger(__name__)


class PartialFulfillmentService:
    """Service handling partial production and dispatch workflows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_wo_for_remaining(
        self,
        *,
        tenant_id: uuid.UUID,
        sales_order_line_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Create a new Work Order for the remaining unfulfilled quantity of a PARTIAL SO line.

        Req 19.5: Creates a new WO with planned_quantity = ordered_quantity - allocated_quantity,
        linked to the same sales order and product.

        Returns:
            Dict with work_order_id and details of the created WO.
        """
        # Get the SO line
        line = await self._get_so_line(tenant_id, sales_order_line_id)

        if line.line_status != "PARTIAL":
            raise ValueError(
                f"Cannot create WO for remaining: line status is '{line.line_status}', "
                f"expected 'PARTIAL'"
            )

        ordered_qty = Decimal(str(line.quantity or 0))
        allocated_qty = Decimal(str(line.allocated_quantity or 0))
        remaining_qty = ordered_qty - allocated_qty

        if remaining_qty <= 0:
            raise ValueError(
                "No remaining quantity to produce. "
                f"Ordered: {ordered_qty}, Allocated: {allocated_qty}"
            )

        # Get the sales order for context
        so_stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == line.sales_order_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        sales_order = (await self.session.execute(so_stmt)).scalar_one_or_none()
        if not sales_order:
            raise ValueError(f"Sales order not found for line {sales_order_line_id}")

        # Use the SalesManufacturingIntegrationService to create the WO
        from backend.app.application.sales.manufacturing_integration import (
            SalesManufacturingIntegrationService,
        )
        from backend.app.application.manufacturing.handlers.work_order_handler import (
            WorkOrderHandler,
        )

        wo_handler = WorkOrderHandler(self.session)
        mfg_service = SalesManufacturingIntegrationService(
            wo_handler,
            created_by=created_by,
        )

        # Parse due_date from the sales order
        from datetime import date as date_type

        due_date = None
        if sales_order.delivery_date:
            if isinstance(sales_order.delivery_date, str):
                due_date = date_type.fromisoformat(sales_order.delivery_date)
            else:
                due_date = sales_order.delivery_date
        if due_date is None:
            due_date = date_type.today()

        wo_id = await mfg_service.create_work_order(
            tenant_id=tenant_id,
            product_id=line.product_id,
            product_type=line.product_type,
            quantity=remaining_qty,
            uom_id=line.uom_id,
            due_date=due_date,
            sales_order_id=sales_order.id,
            sales_order_line_id=line.id,
        )

        if wo_id is None:
            raise ValueError(
                "Failed to create Work Order for remaining quantity. "
                "No active BOM found or creation failed."
            )

        # Update line status to BACKORDER since a new WO is in progress
        line.line_status = "BACKORDER"
        line.work_order_id = wo_id
        line.updated_at = datetime.now(timezone.utc)
        await self.session.flush()

        logger.info(
            "Created WO for remaining quantity",
            extra={
                "work_order_id": str(wo_id),
                "sales_order_line_id": str(sales_order_line_id),
                "remaining_quantity": float(remaining_qty),
            },
        )

        return {
            "work_order_id": str(wo_id),
            "sales_order_line_id": str(sales_order_line_id),
            "remaining_quantity": float(remaining_qty),
            "line_status": line.line_status,
            "message": f"New Work Order created for remaining quantity {float(remaining_qty)}",
        }

    async def short_close_line(
        self,
        *,
        tenant_id: uuid.UUID,
        sales_order_line_id: uuid.UUID,
        closed_by: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Short-close a PARTIAL SO line.

        Req 19.6: Updates line status to SHORT_CLOSED, reduces ordered_quantity to
        allocated_quantity, and recalculates the sales order totals.

        Returns:
            Dict with updated line and SO total details.
        """
        line = await self._get_so_line(tenant_id, sales_order_line_id)

        if line.line_status not in ("PARTIAL", "BACKORDER"):
            raise ValueError(
                f"Cannot short-close line: line status is '{line.line_status}', "
                f"expected 'PARTIAL' or 'BACKORDER'"
            )

        allocated_qty = Decimal(str(line.allocated_quantity or 0))
        original_qty = Decimal(str(line.quantity or 0))

        if allocated_qty <= 0:
            raise ValueError("Cannot short-close a line with zero allocated quantity")

        # Update line: set status and reduce ordered_quantity to allocated_quantity
        line.line_status = "SHORT_CLOSED"
        line.quantity = float(allocated_qty)
        line.updated_at = datetime.now(timezone.utc)

        # Recalculate line_total based on new quantity
        unit_price = Decimal(str(line.unit_price or 0))
        tax_rate = Decimal(str(line.tax_rate or 0))
        new_line_total = allocated_qty * unit_price
        new_tax_amount = new_line_total * tax_rate / Decimal("100")
        line.line_total = float(new_line_total)
        line.tax_amount = float(new_tax_amount)

        await self.session.flush()

        # Recalculate sales order totals (Req 19.6)
        so_stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == line.sales_order_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        sales_order = (await self.session.execute(so_stmt)).scalar_one_or_none()
        if sales_order:
            await self._recalculate_so_totals(sales_order)

            # Check if all lines are now fully allocated or SHORT_CLOSED (Req 19.8)
            await self._check_dispatch_readiness(tenant_id, sales_order)

        logger.info(
            "Short-closed SO line",
            extra={
                "sales_order_line_id": str(sales_order_line_id),
                "original_quantity": float(original_qty),
                "new_quantity": float(allocated_qty),
            },
        )

        return {
            "sales_order_line_id": str(sales_order_line_id),
            "line_status": "SHORT_CLOSED",
            "original_quantity": float(original_qty),
            "new_quantity": float(allocated_qty),
            "new_line_total": float(new_line_total),
            "so_subtotal": float(sales_order.subtotal) if sales_order else None,
            "so_grand_total": float(sales_order.grand_total) if sales_order else None,
            "message": f"Line short-closed. Quantity reduced from {float(original_qty)} to {float(allocated_qty)}",
        }

    async def validate_dispatch_quantities(
        self,
        *,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        line_quantities: Dict[uuid.UUID, Decimal],
    ) -> Dict[str, Any]:
        """
        Validate partial dispatch quantities for a sales order.

        Req 20.1, 20.7: dispatch_quantity per line must be ≤ (allocated - dispatched).
        Raises ValueError if any line exceeds available quantity.

        Args:
            line_quantities: Dict mapping sales_order_line_id → requested dispatch_quantity

        Returns:
            Dict with validated quantities and max available per line.
        """
        so_stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        sales_order = (await self.session.execute(so_stmt)).scalar_one_or_none()
        if not sales_order:
            raise ValueError(f"Sales order {sales_order_id} not found")

        validated_lines = []
        for line in sales_order.lines:
            if line.id not in line_quantities:
                continue

            requested_qty = line_quantities[line.id]
            allocated = Decimal(str(line.allocated_quantity or 0))
            dispatched = Decimal(str(line.dispatched_quantity or 0))
            max_dispatchable = allocated - dispatched

            if requested_qty <= 0:
                raise ValueError(
                    f"Dispatch quantity must be greater than 0 for line {line.id}"
                )

            if requested_qty > max_dispatchable:
                raise ValueError(
                    f"Dispatch quantity {float(requested_qty)} exceeds available "
                    f"{float(max_dispatchable)} for line {line.id} "
                    f"(allocated={float(allocated)}, already dispatched={float(dispatched)})"
                )

            validated_lines.append({
                "sales_order_line_id": str(line.id),
                "requested_quantity": float(requested_qty),
                "max_dispatchable": float(max_dispatchable),
                "allocated": float(allocated),
                "dispatched": float(dispatched),
            })

        return {
            "sales_order_id": str(sales_order_id),
            "validated": True,
            "lines": validated_lines,
        }

    async def update_dispatched_quantities(
        self,
        *,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        line_quantities: Dict[uuid.UUID, Decimal],
    ) -> Dict[str, Any]:
        """
        Update dispatched_quantity for SO lines after delivery creation.

        Req 20.2: Updates dispatched_quantity for each line and checks if SO
        should transition from READY_FOR_DISPATCH.

        Args:
            line_quantities: Dict mapping sales_order_line_id → dispatched quantity for this delivery
        """
        # Validate first
        await self.validate_dispatch_quantities(
            tenant_id=tenant_id,
            sales_order_id=sales_order_id,
            line_quantities=line_quantities,
        )

        so_stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        sales_order = (await self.session.execute(so_stmt)).scalar_one_or_none()

        now = datetime.now(timezone.utc)
        for line in sales_order.lines:
            if line.id not in line_quantities:
                continue
            qty = line_quantities[line.id]
            current_dispatched = Decimal(str(line.dispatched_quantity or 0))
            line.dispatched_quantity = float(current_dispatched + qty)
            line.updated_at = now

        await self.session.flush()

        # Check if all non-SHORT_CLOSED lines are fully dispatched (Req 20.5)
        all_dispatched = all(
            Decimal(str(line.dispatched_quantity or 0)) >= Decimal(str(line.allocated_quantity or 0))
            for line in sales_order.lines
            if line.line_status != "SHORT_CLOSED"
        )

        return {
            "sales_order_id": str(sales_order_id),
            "all_lines_fully_dispatched": all_dispatched,
            "updated_lines": [
                {
                    "sales_order_line_id": str(line_id),
                    "dispatched_quantity": float(line_quantities[line_id]),
                }
                for line_id in line_quantities
            ],
        }

    # ──────────────────────────── Private helpers ────────────────────────────

    async def _get_so_line(
        self, tenant_id: uuid.UUID, line_id: uuid.UUID
    ) -> SalesOrderLineModel:
        """Fetch and validate a sales order line exists."""
        stmt = select(SalesOrderLineModel).where(
            SalesOrderLineModel.id == line_id,
        )
        line = (await self.session.execute(stmt)).scalar_one_or_none()
        if not line:
            raise ValueError(f"Sales order line {line_id} not found")

        # Verify tenant via the parent sales order
        so_stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == line.sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        sales_order = (await self.session.execute(so_stmt)).scalar_one_or_none()
        if not sales_order:
            raise ValueError(f"Sales order not found or access denied for line {line_id}")

        return line

    async def _recalculate_so_totals(self, sales_order: SalesOrderModel) -> None:
        """Recalculate sales order totals from its lines (Req 19.6)."""
        lines_stmt = select(SalesOrderLineModel).where(
            SalesOrderLineModel.sales_order_id == sales_order.id,
        )
        lines = (await self.session.execute(lines_stmt)).scalars().all()

        subtotal = sum(Decimal(str(line.line_total or 0)) for line in lines)
        tax_amount = sum(Decimal(str(line.tax_amount or 0)) for line in lines)
        discount_amount = Decimal(str(sales_order.discount_amount or 0))
        grand_total = subtotal + tax_amount - discount_amount

        sales_order.subtotal = float(subtotal)
        sales_order.tax_amount = float(tax_amount)
        sales_order.grand_total = float(grand_total)
        sales_order.updated_at = datetime.now(timezone.utc)

        await self.session.flush()

    async def _check_dispatch_readiness(
        self, tenant_id: uuid.UUID, sales_order: SalesOrderModel
    ) -> bool:
        """
        Check if all lines are fully allocated or SHORT_CLOSED and transition
        the SO to READY_FOR_DISPATCH if appropriate (Req 19.8).
        """
        lines_stmt = select(SalesOrderLineModel).where(
            SalesOrderLineModel.sales_order_id == sales_order.id,
        )
        lines = (await self.session.execute(lines_stmt)).scalars().all()

        # All non-SHORT_CLOSED lines must be fully allocated
        fully_allocated = all(
            Decimal(str(line.allocated_quantity or 0)) >= Decimal(str(line.quantity or 0))
            for line in lines
            if line.line_status != "SHORT_CLOSED"
        )

        if fully_allocated:
            current_status = OrderStatus(sales_order.status)
            if current_status.can_transition_to(OrderStatus.READY_FOR_DISPATCH):
                sales_order.status = OrderStatus.READY_FOR_DISPATCH.value
                sales_order.updated_at = datetime.now(timezone.utc)
                await self.session.flush()
                return True

        return False
