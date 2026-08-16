"""Integration bridge connecting Sales reservations to canonical Inventory stock."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from backend.app.application.manufacturing.services.inventory_service import (
    InventoryService as StockInventoryService,
)
from backend.app.infrastructure.persistence.models.inventory_reservation_model import (
    InventoryReservationModel,
)
from backend.app.infrastructure.persistence.models.sales_models import SalesOrderLineModel

from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel

logger = logging.getLogger(__name__)


class SalesInventoryIntegrationService:
    """
    Adapter used by the Sales domain reservation service.

    Sales works with product variants, while stock is held as materials. The adapter
    resolves a sellable product to its finished-goods material and delegates all
    mutations to the canonical inventory service.
    """

    def __init__(
        self,
        inventory_service: StockInventoryService,
        *,
        created_by: Optional[UUID] = None,
    ):
        self.inventory_service = inventory_service
        self.created_by = created_by or UUID(int=0)

    async def _resolve_material(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
    ) -> MaterialModel:
        session = self.inventory_service._session

        direct = await session.execute(
            select(MaterialModel).where(
                MaterialModel.id == product_id,
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.is_deleted.is_(False),
            )
        )
        material = direct.scalar_one_or_none()
        if material is not None:
            return material

        if product_type == "variant":
            variant_result = await session.execute(
                select(ItemVariantModel).where(
                    ItemVariantModel.id == product_id,
                    ItemVariantModel.tenant_id == tenant_id,
                    ItemVariantModel.is_deleted.is_(False),
                )
            )
            variant = variant_result.scalar_one_or_none()
            if variant is not None:
                if getattr(variant, "material_id", None):
                    mapped_material_result = await session.execute(
                        select(MaterialModel).where(
                            MaterialModel.id == variant.material_id,
                            MaterialModel.tenant_id == tenant_id,
                            MaterialModel.is_deleted.is_(False),
                        )
                    )
                    mapped_material = mapped_material_result.scalar_one_or_none()
                    if mapped_material is not None:
                        return mapped_material

                material_result = await session.execute(
                    select(MaterialModel).where(
                        MaterialModel.tenant_id == tenant_id,
                        MaterialModel.code == variant.code,
                        MaterialModel.material_type == "finished",
                        MaterialModel.is_deleted.is_(False),
                    )
                )
                material = material_result.scalar_one_or_none()
                if material is not None:
                    return material

        raise ValueError(
            f"No inventory material is linked to {product_type} product {product_id}"
        )

    async def get_available_stock(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
    ) -> Decimal:
        """Get available, unreserved stock for a sales product."""
        material = await self._resolve_material(tenant_id, product_id, product_type)
        return await self.inventory_service.get_available_stock(
            tenant_id=tenant_id,
            material_id=material.id,
        )

    async def reserve_stock(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
        quantity: Decimal,
        uom_id: UUID,
        reference_type: str,
        reference_id: UUID,
        sales_order_id: UUID | None = None,
    ) -> None:
        """Reserve stock for a sales order line without reducing physical stock."""
        if reference_type != "sales_order_line":
            logger.warning("Unexpected sales reservation reference_type=%s", reference_type)
        material = await self._resolve_material(tenant_id, product_id, product_type)
        await self.inventory_service.reserve_sales_stock(
            tenant_id=tenant_id,
            material_id=material.id,
            quantity=quantity,
            sales_order_line_id=reference_id,
            unit_id=uom_id,
            created_by=self.created_by,
            sales_order_id=sales_order_id,
        )

    async def release_stock(
        self,
        tenant_id: UUID,
        reference_type: str,
        reference_id: UUID,
        quantity: Decimal,
    ) -> None:
        """Release reserved sales stock by locating the original reservation."""
        session = self.inventory_service._session
        # First, try to find a reservation made specifically against the line
        reservation_result = await session.execute(
            select(InventoryReservationModel).where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.reference_type == reference_type,
                InventoryReservationModel.reference_id == reference_id,
            )
        )
        reservation = reservation_result.scalars().first()

        if reservation is None and reference_type == "sales_order_line":
            # If not found, try to find the reservation made against the parent sales order
            line_result = await session.execute(
                select(SalesOrderLineModel).where(
                    SalesOrderLineModel.id == reference_id,
                    SalesOrderLineModel.tenant_id == tenant_id,
                    SalesOrderLineModel.is_deleted.is_(False)
                )
            )
            line = line_result.scalar_one_or_none()
            if line is not None:
                reservation_result = await session.execute(
                    select(InventoryReservationModel).where(
                        InventoryReservationModel.tenant_id == tenant_id,
                        InventoryReservationModel.reference_type == "sales_order",
                        InventoryReservationModel.reference_id == line.sales_order_id,
                    )
                )
                reservation = reservation_result.scalars().first()

        if reservation is None:
            logger.warning(f"No reservation found for {reference_type} {reference_id} during release.")
            return

        await self.inventory_service.release_sales_reservation(
            tenant_id=tenant_id,
            material_id=reservation.material_id,
            quantity=quantity,
            sales_order_line_id=reference_id,
            unit_id=reservation.unit_id,
            created_by=self.created_by,
        )

    async def fulfill_reservation(
        self,
        tenant_id: UUID,
        reference_type: str,
        reference_id: UUID,
        quantity: Decimal,
    ) -> None:
        """Convert a reservation into an actual sales shipment."""
        # First, try to find a reservation made specifically against the line
        reservation_result = await session.execute(
            select(InventoryReservationModel).where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.reference_type == reference_type,
                InventoryReservationModel.reference_id == reference_id,
            )
        )
        reservation = reservation_result.scalars().first()

        if reservation is None and reference_type == "sales_order_line":
            # If not found, try to find the reservation made against the parent sales order
            line_result = await session.execute(
                select(SalesOrderLineModel).where(
                    SalesOrderLineModel.id == reference_id,
                    SalesOrderLineModel.tenant_id == tenant_id,
                    SalesOrderLineModel.is_deleted.is_(False)
                )
            )
            line = line_result.scalar_one_or_none()
            if line is not None:
                reservation_result = await session.execute(
                    select(InventoryReservationModel).where(
                        InventoryReservationModel.tenant_id == tenant_id,
                        InventoryReservationModel.reference_type == "sales_order",
                        InventoryReservationModel.reference_id == line.sales_order_id,
                    )
                )
                reservation = reservation_result.scalars().first()

        if reservation is None:
            logger.warning(f"No reservation found for {reference_type} {reference_id}. Falling back to direct stock removal.")
            
            line_result = await session.execute(
                select(SalesOrderLineModel).where(
                    SalesOrderLineModel.id == reference_id,
                    SalesOrderLineModel.tenant_id == tenant_id,
                    SalesOrderLineModel.is_deleted.is_(False)
                )
            )
            line = line_result.scalar_one_or_none()
            if line is None:
                raise ValueError(f"Sales order line {reference_id} not found for fallback fulfillment.")
                
            material = await self._resolve_material(tenant_id, line.product_id, line.product_type)
            await self.inventory_service.remove_stock(
                tenant_id=tenant_id,
                material_id=material.id,
                quantity=quantity,
                unit_id=line.uom_id,
                created_by=self.created_by,
                reference_id=reference_id,
                reference_type="sales_order_line",
                transaction_type="DISPATCH",
                remarks=f"Shipped without prior reservation for sales order line {reference_id}",
            )
            return

        await self.inventory_service.fulfill_sales_reservation(
            tenant_id=tenant_id,
            material_id=reservation.material_id,
            quantity=quantity,
            sales_order_line_id=reference_id,
            unit_id=reservation.unit_id,
            created_by=self.created_by,
        )



from dataclasses import dataclass, field


@dataclass
class FGLineCheckResult:
    """Result of an FG availability check for a single SO line."""

    line_id: UUID
    product_id: UUID
    product_type: str
    ordered_quantity: Decimal
    available_quantity: Decimal
    # True when the full ordered quantity was reserved
    fully_allocated: bool
    # Quantity that could not be fulfilled from existing FG stock
    shortfall_quantity: Decimal
    # UUID of the work order created for the shortage (if any)
    work_order_id: UUID | None = None


@dataclass
class FGCheckResult:
    """Aggregate result of an FG availability check for a whole sales order."""

    so_id: UUID
    all_available: bool
    lines: list[FGLineCheckResult] = field(default_factory=list)


class FGAvailabilityCheckService:
    """
    FG availability check and reservation service — Gap #2.

    Called from ``SalesOrderService.confirm_order()`` after status validation.

    Policy (Req 14, 16 — Cross-Cutting Req A):
    - SELECT FOR UPDATE is held on the ``materials`` row for the entire duration
      of each reservation via ``InventoryService._lock_material``.
    - Full availability (ordered_qty <= available): create one
      ``inventory_reservations`` row (reference_type="sales_order"), increment
      ``materials.reserved_stock``, return allocated_quantity = ordered_quantity.
    - Any shortage: record ``shortfall_quantity`` on the SO line, set
      ``production_required=True``; do NOT create a reservation for that line.
    - On concurrent lock conflict (``InsufficientStockError`` from a second
      simultaneous request): propagate the exception so the route layer can
      return 409 Conflict and roll back the SO confirmation.
    """

    def __init__(
        self,
        inventory_integration: "SalesInventoryIntegrationService",
        manufacturing_service=None,
        *,
        created_by: Optional[UUID] = None,
    ):
        self._inv = inventory_integration
        self._mfg = manufacturing_service
        self.created_by = created_by

    async def check_and_reserve(
        self,
        so_id: UUID,
        tenant_id: UUID,
        lines,  # iterable of SalesOrderLine domain entities
        delivery_date=None,
    ) -> FGCheckResult:
        """
        Check FG availability and reserve stock for each line.

        For each SO line:
          - Read available = current_stock - reserved_stock (under SELECT FOR UPDATE)
          - If available >= ordered_qty: reserve full quantity, set allocated_quantity
          - Else: record shortfall_quantity, set production_required=True
            (do NOT create a partial reservation — Req 16)

        Args:
            so_id: Sales order UUID
            tenant_id: Tenant UUID
            lines: Iterable of SalesOrderLine domain entities (mutated in-place)
            delivery_date: Due date passed to work order creation on shortage

        Returns:
            FGCheckResult with per-line results and overall all_available flag.

        Raises:
            InsufficientStockError: On concurrent reservation conflict (→ 409)
        """
        from backend.app.domain.manufacturing.exceptions import InsufficientStockError

        line_results: list[FGLineCheckResult] = []

        for line in lines:
            ordered_qty = Decimal(str(line.quantity))

            # Read available stock — _lock_material acquires SELECT FOR UPDATE
            available = await self._inv.get_available_stock(
                tenant_id=tenant_id,
                product_id=line.product_id,
                product_type=line.product_type,
            )

            if available >= ordered_qty:
                # Full stock available — reserve the entire line (Req 14.2)
                await self._inv.reserve_stock(
                    tenant_id=tenant_id,
                    product_id=line.product_id,
                    product_type=line.product_type,
                    quantity=ordered_qty,
                    uom_id=line.uom_id,
                    reference_type="sales_order_line",
                    reference_id=line.id,
                    sales_order_id=so_id,
                )
                line.allocate(ordered_qty)
                line_results.append(
                    FGLineCheckResult(
                        line_id=line.id,
                        product_id=line.product_id,
                        product_type=line.product_type,
                        ordered_quantity=ordered_qty,
                        available_quantity=available,
                        fully_allocated=True,
                        shortfall_quantity=Decimal("0"),
                    )
                )
            else:
                # Shortage — do NOT create a partial reservation (Req 16)
                shortfall = ordered_qty - available
                line.mark_shortage(shortfall)
                line.backorder(shortfall)

                work_order_id = None
                if self._mfg is not None:
                    try:
                        work_order_id = await self._mfg.create_work_order(
                            tenant_id=tenant_id,
                            product_id=line.product_id,
                            product_type=line.product_type,
                            quantity=shortfall,
                            uom_id=line.uom_id,
                            due_date=delivery_date,
                            sales_order_id=so_id,
                            sales_order_line_id=line.id,
                        )
                    except Exception:
                        logger.exception(
                            "Failed to create work order for shortage on line %s", line.id
                        )
                if work_order_id:
                    line.work_order_id = work_order_id

                line_results.append(
                    FGLineCheckResult(
                        line_id=line.id,
                        product_id=line.product_id,
                        product_type=line.product_type,
                        ordered_quantity=ordered_qty,
                        available_quantity=available,
                        fully_allocated=False,
                        shortfall_quantity=shortfall,
                        work_order_id=work_order_id,
                    )
                )

        all_available = all(r.fully_allocated for r in line_results)
        return FGCheckResult(so_id=so_id, all_available=all_available, lines=line_results)
