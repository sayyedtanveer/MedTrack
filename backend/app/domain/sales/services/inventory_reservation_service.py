"""Inventory reservation domain service."""

from decimal import Decimal
from uuid import UUID

from backend.app.domain.manufacturing.exceptions import InsufficientStockError


class InventoryReservationService:
    """
    Inventory reservation service for sales orders.
    
    Responsibilities:
    - Reserve stock when order is confirmed
    - Release stock when order is cancelled
    - Identify shortages and trigger work order creation
    """

    def __init__(self, inventory_service, manufacturing_service):
        """
        Initialize inventory reservation service.
        
        Args:
            inventory_service: External inventory domain service
            manufacturing_service: External manufacturing domain service
        """
        self.inventory_service = inventory_service
        self.manufacturing_service = manufacturing_service

    async def reserve_for_order_line(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
        uom_id: UUID,
        quantity: Decimal,
        sales_order_id: UUID,
        sales_order_line_id: UUID,
        delivery_date,
    ) -> tuple[Decimal, Decimal, UUID | None]:
        """
        Reserve inventory for an order line.
        
        Allocation strategy:
        1. Try to allocate from available stock
        2. If shortage: create work order, allocate what's available
        
        Args:
            tenant_id: Tenant ID
            product_id: Product ID
            product_type: Product type ("variant" or "finished_product")
            uom_id: Unit of measure ID
            quantity: Quantity to reserve
            sales_order_id: Sales order ID
            sales_order_line_id: Sales order line ID (for work order linkage)
            delivery_date: Delivery date (due date for work orders)
            
        Returns:
            Tuple of (allocated_qty: Decimal, backorder_qty: Decimal, work_order_id: UUID | None)
        """
        try:
            # Get available stock from inventory service
            available = await self.inventory_service.get_available_stock(
                tenant_id=tenant_id,
                product_id=product_id,
                product_type=product_type,
            )
            
            allocated_qty = min(available, quantity)
            shortage_qty = quantity - allocated_qty
            
            # Reserve the allocated quantity (Req 14 — Gap #2).
            # SELECT FOR UPDATE is held inside reserve_sales_stock via _lock_material.
            # inventory_reservations row is created with reference_type="sales_order".
            if allocated_qty > 0:
                await self.inventory_service.reserve_stock(
                    tenant_id=tenant_id,
                    product_id=product_id,
                    product_type=product_type,
                    quantity=allocated_qty,
                    uom_id=uom_id,
                    reference_type="sales_order_line",
                    reference_id=sales_order_line_id,
                    sales_order_id=sales_order_id,
                )
            
            # Create work order for shortage if any
            work_order_id = None
            if shortage_qty > 0:
                work_order_id = await self.manufacturing_service.create_work_order(
                    tenant_id=tenant_id,
                    product_id=product_id,
                    product_type=product_type,
                    quantity=shortage_qty,
                    uom_id=uom_id,
                    due_date=delivery_date,
                    sales_order_id=sales_order_id,
                    sales_order_line_id=sales_order_line_id,
                )
            
            return allocated_qty, shortage_qty, work_order_id
            
        except InsufficientStockError:
            # Re-raise directly so the route layer can return a 409 Conflict for
            # concurrent reservation conflicts (Cross-Cutting Req A).
            raise
        except Exception as e:
            # Log and re-raise with context
            raise ValueError(
                f"Failed to reserve inventory for product {product_id}: {str(e)}"
            )

    async def release_for_order(
        self,
        tenant_id: UUID,
        sales_order_id: UUID,
        lines,
    ) -> None:
        """
        Release all reserved inventory for an order (on cancellation).
        
        Args:
            tenant_id: Tenant ID
            sales_order_id: Sales order ID
            lines: List of SalesOrderLine entities
        """
        for line in lines:
            if line.allocated_quantity > 0:
                try:
                    await self.inventory_service.release_stock(
                        tenant_id=tenant_id,
                        reference_type="sales_order_line",
                        reference_id=line.id,
                        quantity=line.allocated_quantity,
                    )
                except Exception as e:
                    # Log but don't fail - best effort
                    print(
                        f"Warning: Failed to release stock for line {line.id}: {str(e)}"
                    )

    async def record_shipment(
        self,
        tenant_id: UUID,
        sales_order_line_id: UUID,
        shipped_qty: Decimal,
    ) -> None:
        """
        Record shipment, converting reservation to actual stock reduction.
        
        Args:
            tenant_id: Tenant ID
            sales_order_line_id: Sales order line ID
            shipped_qty: Quantity shipped
        """
        try:
            await self.inventory_service.fulfill_reservation(
                tenant_id=tenant_id,
                reference_type="sales_order_line",
                reference_id=sales_order_line_id,
                quantity=shipped_qty,
            )
        except Exception as e:
            raise ValueError(
                f"Failed to record shipment for line {sales_order_line_id}: {str(e)}"
            )
