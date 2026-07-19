from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.finance.finance_service import FinanceService
from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.application.manufacturing.services.workflow_orchestration_service import WorkflowOrchestrationService
from backend.app.application.notifications.notification_service import NotificationService
from backend.app.application.sales.inventory_integration import SalesInventoryIntegrationService
from backend.app.infrastructure.persistence.models.delivery_model import (
    DeliveryLineModel,
    DeliveryOrderModel,
)
from backend.app.infrastructure.persistence.models.inventory_transaction_model import (
    InventoryTransactionModel,
)
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderLineModel,
    SalesOrderModel,
)
from backend.app.services.audit_log_service import AuditLogService


class DeliveryService:
    """Outbound delivery orchestration over sales and inventory models."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_from_sales_order(
        self,
        *,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        created_by: uuid.UUID,
        lines: Optional[Iterable[dict]] = None,
        carrier: Optional[str] = None,
        tracking_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> DeliveryOrderModel:
        order = await self._sales_order_or_error(tenant_id, sales_order_id)
        requested = {uuid.UUID(str(item["sales_order_line_id"])): Decimal(str(item["quantity"])) for item in lines or []}
        line_models = await self._resolve_delivery_lines(order, requested)
        if not line_models:
            raise ValueError("No allocated quantity is available for delivery")

        delivery = DeliveryOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            delivery_number=await self._next_delivery_number(tenant_id),
            sales_order_id=order.id,
            status="DRAFT",
            carrier=carrier,
            tracking_number=tracking_number,
            notes=notes,
            created_by=created_by,
        )
        self.session.add(delivery)
        await self.session.flush()

        now = datetime.now(timezone.utc)
        for sales_line, quantity in line_models:
            self.session.add(
                DeliveryLineModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    delivery_order_id=delivery.id,
                    sales_order_line_id=sales_line.id,
                    variant_id=sales_line.product_id,
                    quantity=float(quantity),
                )
            )
            # Update dispatched_quantity on the SO line (Req 20.2)
            current_dispatched = Decimal(str(sales_line.dispatched_quantity or 0))
            sales_line.dispatched_quantity = float(current_dispatched + quantity)
            sales_line.updated_at = now

        await self.session.flush()
        return await self.get(tenant_id, delivery.id)

    async def record_sales_shipment_document(
        self,
        *,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        created_by: uuid.UUID,
        line_shipments: dict,
    ) -> DeliveryOrderModel:
        order = await self._sales_order_or_error(tenant_id, sales_order_id)
        requested = {uuid.UUID(str(line_id)): Decimal(str(qty)) for line_id, qty in line_shipments.items()}
        line_models = await self._resolve_delivery_lines(order, requested, allow_already_shipped=True)
        delivery = DeliveryOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            delivery_number=await self._next_delivery_number(tenant_id),
            sales_order_id=order.id,
            status="SHIPPED",
            shipped_at=datetime.now(timezone.utc),
            notes="Created from sales shipment",
            created_by=created_by,
        )
        self.session.add(delivery)
        await self.session.flush()
        for sales_line, quantity in line_models:
            self.session.add(
                DeliveryLineModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    delivery_order_id=delivery.id,
                    sales_order_line_id=sales_line.id,
                    variant_id=sales_line.product_id,
                    quantity=float(quantity),
                )
            )
        await self.session.flush()
        return delivery

    async def ship(
        self,
        *,
        tenant_id: uuid.UUID,
        delivery_id: uuid.UUID,
        shipped_by: uuid.UUID,
        carrier: Optional[str] = None,
        tracking_number: Optional[str] = None,
    ) -> DeliveryOrderModel:
        delivery = await self.get(tenant_id, delivery_id)
        if delivery.status not in {"DRAFT", "PACKING"}:
            raise ValueError(f"Cannot ship delivery in {delivery.status} status")

        order = await self._sales_order_or_error(tenant_id, delivery.sales_order_id)
        lines_by_id = {line.id: line for line in order.lines}
        inventory = SalesInventoryIntegrationService(InventoryService(self.session), created_by=shipped_by)

        for delivery_line in delivery.lines:
            sales_line = lines_by_id.get(delivery_line.sales_order_line_id)
            if sales_line is None:
                raise ValueError(f"Sales line {delivery_line.sales_order_line_id} not found")
            quantity = Decimal(str(delivery_line.quantity))
            allocated = Decimal(str(sales_line.allocated_quantity or 0))
            shipped = Decimal(str(sales_line.shipped_quantity or 0))
            if shipped + quantity > allocated:
                raise ValueError("Delivery quantity exceeds allocated stock")
            await inventory.fulfill_reservation(
                tenant_id=tenant_id,
                reference_type="sales_order_line",
                reference_id=sales_line.id,
                quantity=quantity,
            )
            sales_line.shipped_quantity = float(shipped + quantity)
            sales_line.status = "shipped" if Decimal(str(sales_line.shipped_quantity)) >= allocated else sales_line.status
            sales_line.updated_at = datetime.now(timezone.utc)

        if all(Decimal(str(line.shipped_quantity or 0)) >= Decimal(str(line.allocated_quantity or 0)) for line in order.lines):
            order.status = "SHIPPED"
        order.updated_at = datetime.now(timezone.utc)
        delivery.status = "SHIPPED"
        delivery.carrier = carrier or delivery.carrier
        delivery.tracking_number = tracking_number or delivery.tracking_number
        delivery.shipped_at = datetime.now(timezone.utc)
        delivery.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return delivery

    async def deliver(
        self,
        *,
        tenant_id: uuid.UUID,
        delivery_id: uuid.UUID,
        delivered_by: uuid.UUID,
    ) -> DeliveryOrderModel:
        delivery = await self.get(tenant_id, delivery_id)
        if delivery.status != "SHIPPED":
            raise ValueError(f"Cannot deliver delivery in {delivery.status} status")

        order = await self._sales_order_or_error(tenant_id, delivery.sales_order_id)

        # Mark delivery and sales order as DELIVERED (Req 36.2, 36.3)
        delivery.status = "DELIVERED"
        delivery.delivered_at = datetime.now(timezone.utc)
        delivery.updated_at = datetime.now(timezone.utc)

        should_invoice = all(
            Decimal(str(line.shipped_quantity or 0)) >= Decimal(str(line.quantity or 0)) for line in order.lines
        )
        if should_invoice:
            order.status = "DELIVERED"
            order.updated_at = datetime.now(timezone.utc)
        await self.session.flush()

        # Gap #7: Trigger auto-invoice via WorkflowOrchestrationService.on_order_delivered()
        # This handles: idempotency check, invoice creation, SO → INVOICED transition,
        # failure notification to Finance, and delivery_confirmed_invoice_ready notification.
        # (Req 36.3, 37.1–37.5)
        if should_invoice:
            await WorkflowOrchestrationService(self.session).on_order_delivered(
                tenant_id=tenant_id,
                sales_order_id=order.id,
            )
            return await self.get(tenant_id, delivery_id)

        return delivery

    async def cancel(
        self,
        *,
        tenant_id: uuid.UUID,
        delivery_id: uuid.UUID,
        cancelled_by: uuid.UUID,
        reason: Optional[str] = None,
    ) -> DeliveryOrderModel:
        """Cancel a delivery in DRAFT or PACKING status.

        - Transitions delivery to CANCELLED
        - Creates DISPATCH_REVERSAL inventory transactions (positive quantity) for each line
        - Subtracts cancelled quantities from SO line dispatched_quantity
        - Creates audit_log entry
        - Creates delivery_cancelled notification
        """
        delivery = await self.get(tenant_id, delivery_id)

        # Only allow cancellation for DRAFT/PACKING statuses (Req 33.2, 33.5)
        if delivery.status not in {"DRAFT", "PACKING"}:
            raise ValueError(
                f"Cannot cancel delivery in {delivery.status} status. "
                f"Only DRAFT or PACKING deliveries can be cancelled."
            )

        order = await self._sales_order_or_error(tenant_id, delivery.sales_order_id)
        lines_by_id = {line.id: line for line in order.lines}
        now = datetime.now(timezone.utc)

        # Capture before state for audit
        before_state = {
            "status": delivery.status,
            "delivery_number": delivery.delivery_number,
            "sales_order_id": str(delivery.sales_order_id),
            "lines": [
                {
                    "sales_order_line_id": str(dl.sales_order_line_id),
                    "variant_id": str(dl.variant_id),
                    "quantity": float(dl.quantity),
                }
                for dl in delivery.lines
            ],
        }

        # Create DISPATCH_REVERSAL transactions and update SO line dispatched_quantity (Req 33.3, 33.4)
        restored_quantities = []
        for delivery_line in delivery.lines:
            quantity = Decimal(str(delivery_line.quantity))
            if quantity <= 0:
                continue

            # Create DISPATCH_REVERSAL transaction with positive quantity
            tx = InventoryTransactionModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                material_id=delivery_line.variant_id,
                transaction_type="DISPATCH_REVERSAL",
                quantity=float(quantity),  # positive to restore stock
                reference_type="delivery",
                reference_id=delivery.id,
                remarks=f"Dispatch reversal for cancelled delivery {delivery.delivery_number}",
                created_by=cancelled_by,
            )
            self.session.add(tx)

            # Update SO line dispatched_quantity (Req 33.3)
            sales_line = lines_by_id.get(delivery_line.sales_order_line_id)
            if sales_line is not None:
                current_dispatched = Decimal(str(sales_line.dispatched_quantity or 0))
                new_dispatched = max(Decimal("0"), current_dispatched - quantity)
                sales_line.dispatched_quantity = float(new_dispatched)
                sales_line.updated_at = now

            restored_quantities.append({
                "variant_id": str(delivery_line.variant_id),
                "sales_order_line_id": str(delivery_line.sales_order_line_id),
                "quantity": float(quantity),
            })

        # Transition delivery to CANCELLED (Req 33.3)
        delivery.status = "CANCELLED"
        delivery.cancelled_at = now
        delivery.cancelled_by = cancelled_by
        delivery.cancellation_reason = reason
        delivery.updated_at = now

        # Keep SO in READY_FOR_DISPATCH if it has remaining un-dispatched allocated quantities (Req 33.4)
        # The SO status is not changed here — it stays in READY_FOR_DISPATCH

        await self.session.flush()

        # Capture after state for audit
        after_state = {
            "status": delivery.status,
            "delivery_number": delivery.delivery_number,
            "sales_order_id": str(delivery.sales_order_id),
            "cancelled_at": now.isoformat(),
            "cancelled_by": str(cancelled_by),
            "cancellation_reason": reason,
            "restored_quantities": restored_quantities,
        }

        # Create audit_log entry (Req 33.6)
        audit_service = AuditLogService(self.session)
        await audit_service.log_action(
            tenant_id=tenant_id,
            user_id=cancelled_by,
            action_type="cancel_delivery",
            entity_type="delivery",
            entity_id=delivery.id,
            before_state=before_state,
            after_state=after_state,
            reason=reason,
            metadata={
                "sales_order_id": str(delivery.sales_order_id),
                "restored_quantities": restored_quantities,
            },
        )

        # Create delivery_cancelled notification (Req 33.7)
        notification_service = NotificationService(self.session)
        await notification_service.notify_delivery_cancelled(
            tenant_id=tenant_id,
            delivery_id=delivery.id,
            delivery_number=delivery.delivery_number,
            order_number=order.order_number if hasattr(order, "order_number") else "",
        )

        await self.session.flush()
        return await self.get(tenant_id, delivery.id)

    async def mark_sales_order_delivered_documents(self, tenant_id: uuid.UUID, sales_order_id: uuid.UUID) -> None:
        rows = (
            await self.session.execute(
                select(DeliveryOrderModel).where(
                    DeliveryOrderModel.tenant_id == tenant_id,
                    DeliveryOrderModel.sales_order_id == sales_order_id,
                    DeliveryOrderModel.status == "SHIPPED",
                    DeliveryOrderModel.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        now = datetime.now(timezone.utc)
        for delivery in rows:
            delivery.status = "DELIVERED"
            delivery.delivered_at = now
            delivery.updated_at = now
        await self.session.flush()

    async def get(self, tenant_id: uuid.UUID, delivery_id: uuid.UUID) -> DeliveryOrderModel:
        delivery = (
            await self.session.execute(
                select(DeliveryOrderModel)
                .options(selectinload(DeliveryOrderModel.lines))
                .where(
                    DeliveryOrderModel.id == delivery_id,
                    DeliveryOrderModel.tenant_id == tenant_id,
                    DeliveryOrderModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if delivery is None:
            raise ValueError("Delivery not found")
        return delivery

    async def list(self, tenant_id: uuid.UUID, sales_order_id: Optional[uuid.UUID] = None) -> list[DeliveryOrderModel]:
        query = (
            select(DeliveryOrderModel)
            .options(selectinload(DeliveryOrderModel.lines))
            .where(
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.is_deleted.is_(False),
            )
        )
        if sales_order_id:
            query = query.where(DeliveryOrderModel.sales_order_id == sales_order_id)
        return (await self.session.execute(query.order_by(DeliveryOrderModel.created_at.desc()))).scalars().unique().all()

    async def _sales_order_or_error(self, tenant_id: uuid.UUID, sales_order_id: uuid.UUID) -> SalesOrderModel:
        order = (
            await self.session.execute(
                select(SalesOrderModel)
                .options(selectinload(SalesOrderModel.lines))
                .where(
                    SalesOrderModel.id == sales_order_id,
                    SalesOrderModel.tenant_id == tenant_id,
                    SalesOrderModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if order is None:
            raise ValueError("Sales order not found")
        return order

    async def _resolve_delivery_lines(
        self,
        order: SalesOrderModel,
        requested: dict[uuid.UUID, Decimal],
        *,
        allow_already_shipped: bool = False,
    ) -> list[tuple[SalesOrderLineModel, Decimal]]:
        result: list[tuple[SalesOrderLineModel, Decimal]] = []
        for sales_line in order.lines:
            # Skip SHORT_CLOSED or CANCELLED lines
            if getattr(sales_line, "line_status", "PENDING") in ("SHORT_CLOSED", "CANCELLED"):
                continue

            allocated = Decimal(str(sales_line.allocated_quantity or 0))
            dispatched = Decimal(str(sales_line.dispatched_quantity or 0))
            shipped = Decimal(str(sales_line.shipped_quantity or 0))

            # Partial dispatch: max dispatchable = allocated - dispatched (Req 20.1, 20.7)
            if allow_already_shipped:
                available = allocated
            else:
                available = allocated - dispatched

            if requested:
                if sales_line.id not in requested:
                    continue
                quantity = requested[sales_line.id]
            else:
                quantity = available
            if quantity <= 0:
                continue
            if not allow_already_shipped and quantity > available:
                raise ValueError(
                    f"Dispatch quantity {float(quantity)} exceeds available "
                    f"{float(available)} for line {sales_line.id} "
                    f"(allocated={float(allocated)}, dispatched={float(dispatched)})"
                )
            result.append((sales_line, quantity))
        return result

    async def _next_delivery_number(self, tenant_id: uuid.UUID) -> str:
        count = await self.session.scalar(
            select(func.count(DeliveryOrderModel.id)).where(DeliveryOrderModel.tenant_id == tenant_id)
        )
        return f"DO-{(count or 0) + 1:06d}"
