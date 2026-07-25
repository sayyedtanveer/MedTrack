"""Sales order command handlers (application orchestration)."""

from typing import Optional
from uuid import uuid4, UUID
from datetime import date

from backend.app.domain.sales.entities import SalesOrder, SalesOrderLine, Client
from backend.app.domain.sales.value_objects import OrderNumber, OrderStatus, Money
from backend.app.domain.sales.services import (
    PricingService,
    CreditValidationService,
    InventoryReservationService,
)
from backend.app.domain.sales.repositories import (
    SalesOrderRepository,
    ClientRepository,
    PriceListRepository,
)
from backend.app.application.sales.commands import (
    CreateSalesOrderCommand,
    AddLineToSalesOrderCommand,
    RemoveLineFromSalesOrderCommand,
    ApplyDiscountToOrderCommand,
    SubmitSalesOrderForApprovalCommand,
    ApproveSalesOrderCommand,
    RejectSalesOrderCommand,
    ConfirmSalesOrderCommand,
    CancelSalesOrderCommand,
    TransitionOrderToProductionCommand,
    TransitionOrderToReadyCommand,
    ShipOrderCommand,
    DeliverOrderCommand,
    RecordPaymentCommand,
    CreateClientCommand,
    UpdateClientCommand,
    DeactivateClientCommand,
    CreatePriceListCommand,
    AddPriceListLineCommand,
    UpdatePriceListLineCommand,
    RemovePriceListLineCommand,
)


class CreateSalesOrderCommandHandler:
    """Handler for creating new sales orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,  # Unit of Work for managing transactions
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: CreateSalesOrderCommand) -> UUID:
        """
        Create a new sales order.
        
        Args:
            command: Create command
            
        Returns:
            Order ID
        """
        # Generate order number
        sequence = await self.sales_order_repo.get_next_sequence(
            tenant_id=command.tenant_id,
            date=command.order_date,
        )
        order_number = OrderNumber.generate(sequence)
        
        # Create order aggregate
        order_id = uuid4()
        order = SalesOrder(
            id=order_id,
            tenant_id=command.tenant_id,
            order_number=order_number,
            client_id=command.client_id,
            order_date=command.order_date,
            delivery_date=command.delivery_date,
            approver_id=command.approver_id,
        )
        order.created_by = command.created_by
        order.notes = command.notes
        
        # Persist order
        await self.sales_order_repo.save(order)
        
        # Dispatch domain events (handled in Unit of Work post-commit)
        await self.uow.work()
        
        return order_id


class AddLineToSalesOrderCommandHandler:
    """Handler for adding lines to sales orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        pricing_service: PricingService,
        uow,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.pricing_service = pricing_service
        self.uow = uow

    async def handle(self, command: AddLineToSalesOrderCommand) -> UUID:
        """
        Add a line to a sales order.
        
        Args:
            command: Add line command
            
        Returns:
            Line ID
            
        Raises:
            ValueError: If order not found or not in DRAFT status
        """
        # Fetch order
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        # Resolve unit price: use manual override if provided, else call PricingService
        # REQ-SP-004 AC4: if unit_price override supplied, skip PricingService entirely
        if command.unit_price is not None:
            unit_price = command.unit_price
        else:
            unit_price = await self.pricing_service.get_price(
                tenant_id=command.tenant_id,
                product_id=command.product_id,
                product_type=command.product_type,
                client_id=order.client_id,
                price_date=order.order_date,
            )
        
        # Create line entity
        line_id = uuid4()
        line = SalesOrderLine(
            id=line_id,
            order_id=order.id,
            product_id=command.product_id,
            product_type=command.product_type,
            uom_id=command.uom_id,
            quantity=command.quantity,
            unit_price=unit_price,
            tax_rate=command.tax_rate,
        )
        
        # Add line to order aggregate
        order.add_line(line)
        
        # Persist changes
        await self.sales_order_repo.save(order)
        await self.uow.work()
        
        return line_id


class RemoveLineFromSalesOrderCommandHandler:
    """Handler for removing lines from sales orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: RemoveLineFromSalesOrderCommand) -> None:
        """
        Remove a line from a sales order.
        
        Args:
            command: Remove line command
        """
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        order.remove_line(command.line_id)
        
        await self.sales_order_repo.save(order)
        await self.uow.work()


class ApplyDiscountToOrderCommandHandler:
    """Handler for applying discounts to orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: ApplyDiscountToOrderCommand) -> None:
        """Apply discount to order."""
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        order.apply_discount(command.discount_amount)
        
        await self.sales_order_repo.save(order)
        await self.uow.work()


class SubmitSalesOrderForApprovalCommandHandler:
    """Handler for submitting a draft order into approval workflow."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
    ):
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: SubmitSalesOrderForApprovalCommand) -> None:
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")

        if command.notes:
            order.approval_notes = command.notes
        order.submit_for_approval(command.approver_id)

        await self.sales_order_repo.save(order)
        await self.uow.work()


class ApproveSalesOrderCommandHandler:
    """Handler for manager approval."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
    ):
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: ApproveSalesOrderCommand) -> None:
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")

        order.approve(command.approver_id, command.notes)

        await self.sales_order_repo.save(order)
        # Deferred commit to allow confirm_handler to run in same transaction
        # await self.uow.work()


class RejectSalesOrderCommandHandler:
    """Handler for manager rejection."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
    ):
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: RejectSalesOrderCommand) -> None:
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")

        order.reject(command.approver_id, command.notes)

        await self.sales_order_repo.save(order)
        await self.uow.work()


class ConfirmSalesOrderCommandHandler:
    """Handler for confirming sales orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        client_repo: ClientRepository,
        credit_service: CreditValidationService,
        inventory_service: InventoryReservationService,
        uow,
        *,
        fg_check_service=None,
        notification_service=None,
    ):
        """Initialize handler.

        Args:
            fg_check_service: Optional :class:`FGAvailabilityCheckService` instance.
                When provided it is used in place of ``inventory_service`` for the
                FG check path (Gap #2).  The inventory_service is still kept for
                backward-compat usage (e.g. cancellation release).
            notification_service: Optional :class:`NotificationService` instance.
                When provided, emits ``dispatch_queue_updated`` notification to the
                Dispatch role when the SO transitions to READY_FOR_DISPATCH (Gap #4).
        """
        self.sales_order_repo = sales_order_repo
        self.client_repo = client_repo
        self.credit_service = credit_service
        self.inventory_service = inventory_service
        self.uow = uow
        self.fg_check_service = fg_check_service
        self.notification_service = notification_service

    async def handle(self, command: ConfirmSalesOrderCommand) -> None:
        """
        Confirm a sales order (APPROVED → CONFIRMED).

        Business logic:
        1. Validate order state
        2. Check client credit availability
        3. Allocate credit
        4. FG availability check & reservation via FGAvailabilityCheckService (Gap #2)
        5. Transition to CONFIRMED (and optionally READY_FOR_DISPATCH / PRODUCTION)

        Raises:
            ValueError: If validation fails
            InsufficientStockError: On concurrent reservation conflict (→ 409)
        """
        # Fetch order
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")

        # 1. Validate state. Legacy draft confirmation stays supported, while
        # approved orders enter execution through this same reservation path.
        if order.status not in (OrderStatus.DRAFT, OrderStatus.APPROVED):
            raise ValueError(f"Cannot confirm order in {order.status.value} state")

        # 2. Check credit
        is_valid, reason = await self.credit_service.validate_credit(
            tenant_id=command.tenant_id,
            client_id=order.client_id,
            order_grand_total=order.grand_total,
        )
        if not is_valid:
            raise ValueError(f"Credit validation failed: {reason}")

        # 3. Allocate credit
        await self.credit_service.allocate_credit(
            tenant_id=command.tenant_id,
            client_id=order.client_id,
            amount=order.grand_total,
        )

        # 4. FG availability check & reservation (Req 13, 14, 16 — Gap #2)
        if self.fg_check_service is not None:
            # Preferred path: all-or-nothing per line via FGAvailabilityCheckService.
            # SELECT FOR UPDATE on materials row held inside check_and_reserve().
            await self.fg_check_service.check_and_reserve(
                so_id=order.id,
                tenant_id=command.tenant_id,
                lines=order.lines,
                delivery_date=order.delivery_date,
            )
        else:
            # Legacy fallback: per-line partial allocation via InventoryReservationService.
            for line in order.lines:
                allocated_qty, backorder_qty, work_order_id = (
                    await self.inventory_service.reserve_for_order_line(
                        tenant_id=command.tenant_id,
                        product_id=line.product_id,
                        product_type=line.product_type,
                        uom_id=line.uom_id,
                        quantity=line.quantity,
                        sales_order_id=order.id,
                        sales_order_line_id=line.id,
                        delivery_date=order.delivery_date,
                    )
                )

                # Update line with allocations
                if allocated_qty > 0:
                    line.allocate(allocated_qty)
                if backorder_qty > 0:
                    # Record the FG shortage on the line (Req 16 — Gap #2).
                    # mark_shortage sets shortfall_quantity and production_required=True.
                    line.mark_shortage(backorder_qty)
                    line.backorder(backorder_qty)
                if work_order_id:
                    line.work_order_id = work_order_id

        # 5. Transition order
        order.confirm()
        has_backorder = any(line.backorder_quantity > 0 for line in order.lines)
        all_allocated = bool(order.lines) and all(
            line.allocated_quantity >= line.quantity for line in order.lines
        )
        if has_backorder:
            order.transition_to_production()
        elif all_allocated:
            # Gap #4: all lines fully allocated → READY_FOR_DISPATCH (Req 15)
            order.mark_ready_for_dispatch()

        # Persist all changes
        await self.sales_order_repo.save(order)
        await self.uow.work()

        # Gap #4: emit dispatch_queue_updated notification to Dispatch role (Req 15.3)
        if all_allocated and self.notification_service is not None:
            try:
                await self.notification_service.notify_ready_for_dispatch_action(
                    tenant_id=command.tenant_id,
                    sales_order_id=order.id,
                    order_number=str(order.order_number),
                )
            except Exception:
                import logging
                logging.getLogger(__name__).exception(
                    "Failed to emit dispatch_queue_updated notification for SO %s",
                    order.id,
                )


class CancelSalesOrderCommandHandler:
    """Handler for cancelling sales orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        credit_service: CreditValidationService,
        inventory_service: InventoryReservationService,
        uow,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.credit_service = credit_service
        self.inventory_service = inventory_service
        self.uow = uow

    async def handle(self, command: CancelSalesOrderCommand) -> None:
        """
        Cancel a sales order.
        
        Business logic:
        1. Release reserved inventory
        2. Release allocated credit
        3. Transition to CANCELLED
        """
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        if not order.can_transition_to(OrderStatus.CANCELLED):
            raise ValueError(
                f"Cannot cancel order in {order.status.value} status"
            )
        
        # Release inventory
        await self.inventory_service.release_for_order(
            tenant_id=command.tenant_id,
            sales_order_id=order.id,
            lines=order.lines,
        )
        
        # Release credit (only if order was confirmed and credit was allocated)
        if order.status in (
            OrderStatus.CONFIRMED,
            OrderStatus.PRODUCTION,
            OrderStatus.READY,
            OrderStatus.SHIPPED,
        ):
            await self.credit_service.release_credit(
                tenant_id=command.tenant_id,
                client_id=order.client_id,
                amount=order.grand_total,
            )
        
        # Cancel order
        order.cancel()
        
        await self.sales_order_repo.save(order)
        await self.uow.work()


class ShipOrderCommandHandler:
    """Handler for shipping orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        inventory_service: InventoryReservationService,
        uow,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.inventory_service = inventory_service
        self.uow = uow

    async def handle(self, command: ShipOrderCommand) -> None:
        """
        Record shipment for an order.
        
        Args:
            command: Ship command with line-by-line shipment quantities
        """
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        # Record shipments for each line
        for line in order.lines:
            shipment_key = line.id if line.id in command.line_shipments else str(line.id)
            if shipment_key in command.line_shipments:
                shipped_qty = command.line_shipments[shipment_key]
                
                # Record shipment
                line.ship(shipped_qty)
                
                # Update inventory
                await self.inventory_service.record_shipment(
                    tenant_id=command.tenant_id,
                    sales_order_line_id=line.id,
                    shipped_qty=shipped_qty,
                )
        
        # If all lines shipped, transition order to SHIPPED
        all_shipped = bool(order.lines) and all(
            line.allocated_quantity > 0 and line.shipped_quantity >= line.allocated_quantity
            for line in order.lines
        )
        if all_shipped:
            if order.status in (OrderStatus.CONFIRMED, OrderStatus.PRODUCTION):
                order.transition_to_ready()
            order.ship()
        
        await self.sales_order_repo.save(order)
        await self.uow.work()


class DeliverOrderCommandHandler:
    """Handler for delivering orders."""

    def __init__(
        self,
        sales_order_repo: SalesOrderRepository,
        uow,
    ):
        """Initialize handler."""
        self.sales_order_repo = sales_order_repo
        self.uow = uow

    async def handle(self, command: DeliverOrderCommand) -> None:
        """Record delivery of order."""
        order = await self.sales_order_repo.get_by_id(
            id=command.sales_order_id,
            tenant_id=command.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {command.sales_order_id} not found")
        
        order.deliver()
        
        await self.sales_order_repo.save(order)
        await self.uow.work()

