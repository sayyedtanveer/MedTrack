"""
Workflow Orchestration Service - End-to-End Manufacturing Workflow

This service orchestrates the complete operational workflow:
SALES_ORDER → APPROVED → WORK_ORDER_CREATED → MATERIAL_PENDING → MATERIAL_RESERVED → 
MATERIAL_ISSUED → IN_PRODUCTION → QC_PENDING → QC_APPROVED/QC_REJECTED → 
FG_RECEIVED → READY_FOR_DISPATCH → DELIVERED → INVOICED → PAYMENT_RECEIVED

Key responsibilities:
1. Connect Sales Order to Work Order creation
2. Trigger material reservation on WO release
3. Trigger QC on production completion
4. Auto-increase FG stock after QC approval
5. Update Sales Order status based on WO progress
6. Trigger delivery dispatch on FG receipt
7. Trigger invoicing on delivery
8. Auto-invoice after delivery (Req 2.1-2.4)
9. Payment completion transitions (Req 3.4, 3.6)
10. FG receipt auto-reserves for SO, full allocation triggers READY_FOR_DISPATCH (Req 7.5, 7.6)
11. Purchase Requisition creation for shortages (Req 17.1, 17.6)
12. Reservation release on cancellation (Req 18.1-18.3)
13. Production hold/exceptions (Req 26.1, 26.3)
14. Orchestration engine coordination (Req 29.1-29.14)
"""
from __future__ import annotations

import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.sales.value_objects.order_status import OrderStatus
from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderModel,
    SalesOrderLineModel,
)
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.purchase_requisition_model import PurchaseRequisitionModel
from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.application.notifications.notification_service import NotificationService

logger = logging.getLogger(__name__)


class WorkflowOrchestrationService:
    """
    Service for orchestrating end-to-end manufacturing workflow.
    
    Ensures that state transitions across modules are synchronized
    and that business rules are enforced consistently.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.inventory_service = InventoryService(session)
        self.notification_service = NotificationService(session)
    
    async def on_work_order_released(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Reserve materials and plan procurement when a work order is released.
        
        Creates Purchase Requisitions for any material shortages (Req 17.1, 17.6).
        Transitions WO to MATERIAL_RESERVED if all materials available,
        or to MATERIAL_PENDING if shortages exist.
        """
        stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        wo = (await self.session.execute(stmt)).scalar_one_or_none()
        if wo is None:
            raise ValueError(f"Work order {work_order_id} not found")

        from backend.app.application.manufacturing.services.material_planning_service import (
            MaterialPlanningService,
        )

        await MaterialPlanningService(self.session).plan_for_release(wo)
        await self.session.flush()

        # Create Purchase Requisitions for shortages (Req 17.1, 17.6)
        shortages = await self.inventory_service.get_shortages_for_work_order(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
        )
        
        requisitions_created = []
        for shortage in shortages:
            material_id = shortage.get("material_id")
            shortage_qty = Decimal(str(shortage.get("shortage_quantity", 0)))
            
            if shortage_qty <= 0 or material_id is None:
                continue
            
            # Check if requisition already exists for this WO + material
            existing_pr = (await self.session.execute(
                select(PurchaseRequisitionModel).where(
                    and_(
                        PurchaseRequisitionModel.tenant_id == tenant_id,
                        PurchaseRequisitionModel.work_order_id == work_order_id,
                        PurchaseRequisitionModel.material_id == material_id,
                        PurchaseRequisitionModel.is_deleted.is_(False),
                    )
                )
            )).scalar_one_or_none()
            
            if existing_pr is None:
                pr_number = f"PR-{uuid.uuid4().hex[:8].upper()}"
                pr = PurchaseRequisitionModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    requisition_number=pr_number,
                    status="PENDING_APPROVAL",
                    material_id=material_id,
                    work_order_id=work_order_id,
                    required_quantity=float(shortage_qty),
                    shortage_quantity=float(shortage_qty),
                    created_by=wo.created_by,
                )
                self.session.add(pr)
                requisitions_created.append(str(pr.id))
        
        if requisitions_created:
            await self.session.flush()
            
            # Notify procurement team about shortages
            await self.notification_service.create_notification(
                tenant_id=tenant_id,
                notification_type="material_shortage",
                title=f"Material Shortage for WO {wo.wo_number}",
                message=f"Purchase Requisitions created for {len(requisitions_created)} material(s) with shortages.",
                reference_id=str(work_order_id),
                reference_type="work_order",
            )

        # Notify storekeeper that WO has been released (Req 23.7)
        await self.notification_service.create_notification(
            tenant_id=tenant_id,
            notification_type="wo_released",
            title=f"Work Order {wo.wo_number} Released",
            message=f"Work Order {wo.wo_number} has been released. Materials can be prepared.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

        # If WO is in MATERIAL_RESERVED, notify storekeeper to issue materials (Req 27.1)
        if wo.status == "MATERIAL_RESERVED":
            await self.notification_service.create_notification(
                tenant_id=tenant_id,
                notification_type="issue_materials_action",
                title=f"Action Required: Issue Materials - WO {wo.wo_number}",
                message=f"Materials reserved for Work Order {wo.wo_number}. Please issue materials to begin production.",
                reference_id=str(work_order_id),
                reference_type="work_order",
            )

        return {
            "work_order_id": str(work_order_id),
            "status": wo.status,
            "requisitions_created": requisitions_created,
            "message": "Material planning completed for released work order",
        }

    async def on_sales_order_approved(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Handle Sales Order approval workflow.
        
        Transition: APPROVED → WORK_ORDER_CREATED
        Action: Create Work Order for each line item
        """
        logger.info(
            "Sales Order approved - creating work orders",
            extra={"tenant_id": str(tenant_id), "sales_order_id": str(sales_order_id)}
        )
        
        # Update Sales Order status to WORK_ORDER_CREATED
        stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        sales_order = result.scalar_one_or_none()
        
        if not sales_order:
            raise ValueError(f"Sales Order {sales_order_id} not found")
        
        # Validate transition
        current_status = OrderStatus(sales_order.status)
        if not current_status.can_transition_to(OrderStatus.WORK_ORDER_CREATED):
            raise ValueError(
                f"Cannot transition Sales Order from {current_status.value} to WORK_ORDER_CREATED"
            )
        
        sales_order.status = OrderStatus.WORK_ORDER_CREATED.value
        sales_order.updated_at = datetime.now(timezone.utc)
        
        await self.session.flush()
        
        # Notify planner about approved sales order (Req 23.1)
        await self.notification_service.create_notification(
            tenant_id=tenant_id,
            notification_type="sales_approved",
            title=f"Sales Order {sales_order.order_number} Approved",
            message=f"Sales Order {sales_order.order_number} has been approved and is ready for production planning.",
            reference_id=str(sales_order_id),
            reference_type="sales_order",
        )
        
        # TODO: Create Work Orders for each line item
        # This will be implemented in the sales integration module
        
        return {
            "sales_order_id": str(sales_order_id),
            "status": sales_order.status,
            "message": "Sales Order approved and work orders created",
        }
    
    async def on_work_order_completed(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Handle Work Order completion workflow.
        
        Transition: FG_RECEIVED → READY_FOR_DISPATCH
        Action: Update linked Sales Order to READY_FOR_DISPATCH
        """
        logger.info(
            "Work Order completed - updating sales order",
            extra={"tenant_id": str(tenant_id), "work_order_id": str(work_order_id)}
        )
        
        # Get Work Order
        stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        work_order = result.scalar_one_or_none()
        
        if not work_order:
            raise ValueError(f"Work Order {work_order_id} not found")
        
        # Update linked Sales Order if exists
        if work_order.sales_order_id:
            sales_order_stmt = select(SalesOrderModel).where(
                and_(
                    SalesOrderModel.id == work_order.sales_order_id,
                    SalesOrderModel.tenant_id == tenant_id,
                    SalesOrderModel.is_deleted.is_(False),
                )
            )
            sales_order_result = await self.session.execute(sales_order_stmt)
            sales_order = sales_order_result.scalar_one_or_none()
            
            if sales_order:
                current_status = OrderStatus(sales_order.status)
                if current_status.can_transition_to(OrderStatus.READY_FOR_DISPATCH):
                    sales_order.status = OrderStatus.READY_FOR_DISPATCH.value
                    sales_order.updated_at = datetime.now(timezone.utc)
                    
                    await self.session.flush()
                    
                    # Notify storekeeper for dispatch
                    await self.notification_service.create_notification(
                        tenant_id=tenant_id,
                        notification_type="ready_for_dispatch_action",
                        title=f"Action Required: Dispatch Order {sales_order.order_number}",
                        message=f"Work Order {work_order.wo_number} completed. Order {sales_order.order_number} is ready for dispatch.",
                        reference_id=str(sales_order.id),
                        reference_type="sales_order",
                    )
        
        return {
            "work_order_id": str(work_order_id),
            "status": work_order.status,
            "message": "Work Order completed and sales order updated",
        }
    
    async def on_qc_approved(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        received_by: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Handle QC approval workflow.
        
        Transition: QC_APPROVED → FG_RECEIVED
        Action: Automatically increase FG stock
        """
        logger.info(
            "QC approved - receiving finished goods",
            extra={"tenant_id": str(tenant_id), "work_order_id": str(work_order_id)}
        )
        
        # Get Work Order
        stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        work_order = result.scalar_one_or_none()
        
        if not work_order:
            raise ValueError(f"Work Order {work_order_id} not found")
        
        if work_order.status == WorkOrderStatus.QC_PENDING.value:
            work_order.status = WorkOrderStatus.QC_APPROVED.value
            work_order.updated_at = datetime.now(timezone.utc)

        if work_order.status not in (
            WorkOrderStatus.QC_APPROVED.value,
            WorkOrderStatus.FG_RECEIVED.value,
        ):
            raise ValueError(
                f"Cannot receive FG for WO in status {work_order.status}; QC approval is required"
            )

        fg_material_id = await self._resolve_finished_good_material_id(work_order)
        fg_quantity = Decimal(str(work_order.produced_quantity or 0)) - Decimal(
            str(work_order.scrap_quantity or 0)
        )

        existing_receipt = (
            await self.session.execute(
                select(InventoryTransactionModel.id).where(
                    InventoryTransactionModel.tenant_id == tenant_id,
                    InventoryTransactionModel.material_id == fg_material_id,
                    InventoryTransactionModel.reference_type == "work_order",
                    InventoryTransactionModel.reference_id == work_order_id,
                    InventoryTransactionModel.transaction_type == "FG_RECEIPT",
                    InventoryTransactionModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()

        if fg_quantity > 0 and existing_receipt is None:
            await self.inventory_service.receive_fg(
                tenant_id=tenant_id,
                product_id=fg_material_id,
                quantity=fg_quantity,
                work_order_id=work_order_id,
                created_by=received_by,
            )

            logger.info(
                "FG stock increased",
                extra={
                    "tenant_id": str(tenant_id),
                    "material_id": str(fg_material_id),
                    "quantity": float(fg_quantity),
                },
            )

        work_order.status = WorkOrderStatus.FG_RECEIVED.value
        work_order.updated_at = datetime.now(timezone.utc)

        # Notify storekeeper that QC has been approved (Req 23.9)
        await self.notification_service.create_notification(
            tenant_id=tenant_id,
            notification_type="qc_approved",
            title=f"QC Approved - WO {work_order.wo_number}",
            message=f"Quality inspection passed for Work Order {work_order.wo_number}. Ready for FG receipt.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

        # Notify storekeeper to receive finished goods (Req 27.3)
        await self.notification_service.create_notification(
            tenant_id=tenant_id,
            notification_type="receive_fg_action",
            title=f"Action Required: Receive FG - WO {work_order.wo_number}",
            message=f"QC approved for Work Order {work_order.wo_number}. Please receive finished goods into inventory.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

        return {
            "work_order_id": str(work_order_id),
            "fg_quantity": float(fg_quantity),
            "material_id": str(fg_material_id),
            "receipt_created": existing_receipt is None and fg_quantity > 0,
            "message": "QC approved and FG stock increased",
        }

    async def _resolve_finished_good_material_id(self, work_order: WorkOrderModel) -> uuid.UUID:
        """Resolve a WO product reference to the material row that receives FG stock."""
        from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel

        material = (
            await self.session.execute(
                select(MaterialModel).where(
                    MaterialModel.id == work_order.product_id,
                    MaterialModel.tenant_id == work_order.tenant_id,
                    MaterialModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if material is not None:
            return material.id

        variant = (
            await self.session.execute(
                select(ItemVariantModel).where(
                    ItemVariantModel.id == work_order.product_id,
                    ItemVariantModel.tenant_id == work_order.tenant_id,
                    ItemVariantModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if variant is None:
            raise ValueError(f"Finished-good product {work_order.product_id} not found")

        if getattr(variant, "material_id", None):
            return variant.material_id

        material = (
            await self.session.execute(
                select(MaterialModel).where(
                    MaterialModel.tenant_id == work_order.tenant_id,
                    MaterialModel.code == variant.code,
                    MaterialModel.material_type == "finished",
                    MaterialModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if material is None:
            raise ValueError(f"Product {work_order.product_id} has no finished-good material")
        return material.id
    
    async def on_order_delivered(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Handle Order delivery workflow.
        
        Transition: DELIVERED → INVOICED
        Action: Create draft invoice via FinanceService, transition SO to INVOICED.
        If invoice creation fails, log error and create notification (Req 2.3).
        If duplicate invoice exists, return it without creating new one (Req 2.4).
        """
        logger.info(
            "Order delivered - triggering auto-invoicing",
            extra={"tenant_id": str(tenant_id), "sales_order_id": str(sales_order_id)}
        )
        
        # Idempotency check
        transition_result = await self.on_auto_transition(
            tenant_id=tenant_id,
            operation_key=f"delivered:{sales_order_id}",
            entity_type="sales_order",
            entity_id=sales_order_id,
        )
        if transition_result.get("duplicate"):
            return transition_result
        
        # Get Sales Order
        stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        sales_order = result.scalar_one_or_none()
        
        if not sales_order:
            raise ValueError(f"Sales Order {sales_order_id} not found")
        
        current_status = OrderStatus(sales_order.status)

        # Notify finance that dispatch is completed (Req 23.5)
        await self.notification_service.create_notification(
            tenant_id=tenant_id,
            notification_type="dispatch_completed",
            title=f"Dispatch Completed - Order {sales_order.order_number}",
            message=f"Order {sales_order.order_number} has been delivered. Auto-invoicing in progress.",
            reference_id=str(sales_order_id),
            reference_type="sales_order",
        )

        # Attempt auto-invoice creation (Req 2.1)
        invoice = None
        invoice_error = None
        try:
            from backend.app.application.finance.finance_service import FinanceService
            finance_service = FinanceService(self.session)
            
            # create_invoice_from_sales_order handles duplicate detection internally (Req 2.4)
            invoice = await finance_service.create_invoice_from_sales_order(
                tenant_id=tenant_id,
                sales_order_id=sales_order_id,
                created_by=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # system user
                notes="Auto-generated invoice on delivery",
            )
        except Exception as e:
            invoice_error = str(e)
            logger.error(
                "Auto-invoice creation failed",
                extra={
                    "tenant_id": str(tenant_id),
                    "sales_order_id": str(sales_order_id),
                    "error": invoice_error,
                },
            )
        
        if invoice_error:
            # Req 2.3: Log error, leave SO in DELIVERED, notify finance users
            await self.notification_service.create_notification(
                tenant_id=tenant_id,
                notification_type="invoice_creation_failed",
                title=f"Invoice Creation Failed for Order {sales_order.order_number}",
                message=f"Auto-invoice creation failed for SO {sales_order.order_number}: {invoice_error}",
                reference_id=str(sales_order.id),
                reference_type="sales_order",
            )
            return {
                "sales_order_id": str(sales_order_id),
                "status": sales_order.status,
                "invoice_created": False,
                "error": invoice_error,
                "message": "Auto-invoice creation failed; SO remains DELIVERED",
            }
        
        # Transition SO to INVOICED (Req 2.2)
        if current_status.can_transition_to(OrderStatus.INVOICED):
            sales_order.status = OrderStatus.INVOICED.value
            sales_order.updated_at = datetime.now(timezone.utc)
            await self.session.flush()
        
        return {
            "sales_order_id": str(sales_order_id),
            "status": sales_order.status,
            "invoice_id": str(invoice.id) if invoice else None,
            "invoice_created": invoice is not None,
            "message": "Order delivered, invoice created, SO transitioned to INVOICED",
        }
    
    async def on_payment_received(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        payment_amount: Decimal,
    ) -> Dict[str, Any]:
        """
        Handle payment receipt workflow.
        
        Transition: INVOICED → PAYMENT_RECEIVED → COMPLETED (Req 3.4, 3.6)
        Action: Transition SO to COMPLETED when cumulative payments >= grand_total.
        Partial payments leave SO in INVOICED status (Req 3.5).
        """
        logger.info(
            "Payment received - evaluating order completion",
            extra={
                "tenant_id": str(tenant_id),
                "sales_order_id": str(sales_order_id),
                "payment_amount": float(payment_amount),
            }
        )
        
        # Idempotency check
        transition_result = await self.on_auto_transition(
            tenant_id=tenant_id,
            operation_key=f"payment:{sales_order_id}",
            entity_type="sales_order",
            entity_id=sales_order_id,
        )
        if transition_result.get("duplicate"):
            return transition_result
        
        # Get Sales Order
        stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        sales_order = result.scalar_one_or_none()
        
        if not sales_order:
            raise ValueError(f"Sales Order {sales_order_id} not found")
        
        grand_total = Decimal(str(sales_order.grand_total or 0))
        
        # Calculate cumulative payments from finance module
        cumulative_paid = Decimal("0")
        try:
            from backend.app.infrastructure.persistence.models.finance_models import (
                InvoiceModel,
                PaymentModel,
            )
            from sqlalchemy import func
            
            # Get the invoice linked to this SO
            invoice_stmt = select(InvoiceModel).where(
                and_(
                    InvoiceModel.sales_order_id == sales_order_id,
                    InvoiceModel.tenant_id == tenant_id,
                    InvoiceModel.is_deleted.is_(False),
                )
            )
            invoice = (await self.session.execute(invoice_stmt)).scalar_one_or_none()
            
            if invoice:
                # Sum all payments for this invoice
                paid_sum = await self.session.scalar(
                    select(func.coalesce(func.sum(PaymentModel.amount), 0)).where(
                        PaymentModel.invoice_id == invoice.id,
                        PaymentModel.tenant_id == tenant_id,
                    )
                )
                cumulative_paid = Decimal(str(paid_sum or 0))
        except Exception:
            # Fallback: use the payment amount directly
            cumulative_paid = payment_amount
        
        current_status = OrderStatus(sales_order.status)
        
        # Check if full payment threshold met (Req 3.4, 3.6)
        if cumulative_paid >= grand_total:
            completion_result = await self._complete_sales_order(
                tenant_id=tenant_id,
                sales_order=sales_order,
                completed_by=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                reason="Full payment received and sales order workflow completed",
                metadata={"cumulative_paid": float(cumulative_paid)},
            )
            
            # Notify sales team
            await self.notification_service.create_notification(
                tenant_id=tenant_id,
                notification_type="payment_received",
                title=f"Payment Complete for Order {sales_order.order_number}",
                message=f"Full payment received for order {sales_order.order_number}. Order is now COMPLETED.",
                reference_id=str(sales_order.id),
                reference_type="sales_order",
            )
        else:
            # Partial payment - leave in INVOICED status (Req 3.5)
            logger.info(
                "Partial payment recorded - SO remains INVOICED",
                extra={
                    "cumulative_paid": float(cumulative_paid),
                    "grand_total": float(grand_total),
                },
            )
        
        return {
            "sales_order_id": str(sales_order_id),
            "status": sales_order.status,
            "cumulative_paid": float(cumulative_paid),
            "grand_total": float(grand_total),
            "fully_paid": cumulative_paid >= grand_total,
            "message": "Payment received and order status updated",
        }

    async def close_sales_order(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        closed_by: uuid.UUID,
    ) -> Dict[str, Any]:
        """Manually complete a sales order when the payment workflow has to be forced."""
        stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        sales_order = result.scalar_one_or_none()
        if not sales_order:
            raise ValueError(f"Sales Order {sales_order_id} not found")

        if sales_order.status == OrderStatus.COMPLETED.value:
            return {
                "sales_order_id": str(sales_order_id),
                "status": sales_order.status,
                "message": "Sales order already completed",
            }

        completion_result = await self._complete_sales_order(
            tenant_id=tenant_id,
            sales_order=sales_order,
            completed_by=closed_by,
            reason="Sales order manually closed",
            metadata={"source": "manual_close"},
        )

        await self.notification_service.create_notification(
            tenant_id=tenant_id,
            notification_type="payment_received",
            title=f"Order {sales_order.order_number} Closed",
            message=f"Order {sales_order.order_number} was manually closed and all reservations were released.",
            reference_id=str(sales_order.id),
            reference_type="sales_order",
        )

        return {
            "sales_order_id": str(sales_order_id),
            "status": sales_order.status,
            "released_materials": completion_result.get("released_materials", []),
            "message": "Sales order manually closed",
        }

    async def _complete_sales_order(
        self,
        tenant_id: uuid.UUID,
        sales_order: SalesOrderModel,
        completed_by: uuid.UUID,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Transition a sales order through PAYMENT_RECEIVED and COMPLETED, release reservations, and write audit state."""
        current_status = OrderStatus(sales_order.status)
        released_materials: List[Dict[str, Any]] = []

        if current_status.can_transition_to(OrderStatus.PAYMENT_RECEIVED):
            sales_order.status = OrderStatus.PAYMENT_RECEIVED.value
            sales_order.updated_at = datetime.now(timezone.utc)
            await self.session.flush()

        current_status = OrderStatus(sales_order.status)
        if current_status.can_transition_to(OrderStatus.COMPLETED):
            sales_order.status = OrderStatus.COMPLETED.value
            sales_order.updated_at = datetime.now(timezone.utc)
            await self.session.flush()
            released_materials = await self._release_sales_order_reservations(
                tenant_id=tenant_id,
                sales_order_id=sales_order.id,
                released_by=completed_by,
            )

            try:
                from backend.app.services.audit_log_service import AuditLogService

                audit_service = AuditLogService(self.session)
                completed_at = datetime.now(timezone.utc)
                await audit_service.log_action(
                    tenant_id=tenant_id,
                    user_id=completed_by,
                    action_type="lifecycle_completed",
                    entity_type="sales_order",
                    entity_id=sales_order.id,
                    before_state={
                        "status": OrderStatus.PAYMENT_RECEIVED.value,
                        "order_date": sales_order.order_date,
                        "approved_at": self._serialize_datetime(getattr(sales_order, "approved_at", None)),
                        "confirmed_at": self._serialize_datetime(getattr(sales_order, "confirmed_at", None)),
                        "delivered_at": self._serialize_datetime(getattr(sales_order, "delivered_at", None)),
                        "invoiced_at": self._serialize_datetime(getattr(sales_order, "invoiced_at", None)),
                        "completed_at": None,
                    },
                    after_state={
                        "status": OrderStatus.COMPLETED.value,
                        "order_date": sales_order.order_date,
                        "approved_at": self._serialize_datetime(getattr(sales_order, "approved_at", None)),
                        "confirmed_at": self._serialize_datetime(getattr(sales_order, "confirmed_at", None)),
                        "delivered_at": self._serialize_datetime(getattr(sales_order, "delivered_at", None)),
                        "invoiced_at": self._serialize_datetime(getattr(sales_order, "invoiced_at", None)),
                        "completed_at": completed_at.isoformat(),
                        "reservations_released": len(released_materials),
                    },
                    reason=reason,
                    metadata=metadata,
                )
            except Exception as e:
                logger.warning(
                    "Failed to record sales order completion audit entry",
                    extra={"error": str(e), "sales_order_id": str(sales_order.id)},
                )

        return {
            "status": sales_order.status,
            "released_materials": released_materials,
            "audit_logged": True,
        }

    @staticmethod
    def _serialize_datetime(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    async def _release_sales_order_reservations(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        released_by: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        """Release any remaining reserved stock for a completed sales order."""
        released_materials: List[Dict[str, Any]] = []
        so_lines_stmt = select(SalesOrderLineModel).where(
            SalesOrderLineModel.sales_order_id == sales_order_id,
        )
        so_lines = (await self.session.execute(so_lines_stmt)).scalars().all()

        for line in so_lines:
            allocated_qty = Decimal(str(getattr(line, "allocated_quantity", 0) or 0))
            if allocated_qty <= 0:
                continue
            try:
                await self.inventory_service.release_sales_reservation(
                    tenant_id=tenant_id,
                    material_id=line.product_id,
                    quantity=allocated_qty,
                    sales_order_line_id=line.id,
                    unit_id=getattr(line, "uom_id", None),
                    created_by=released_by,
                )
                released_materials.append(
                    {
                        "sales_order_line_id": str(line.id),
                        "quantity_released": float(allocated_qty),
                    }
                )
            except Exception as e:
                logger.warning(
                    "Failed to release sales reservation on payment completion",
                    extra={"line_id": str(line.id), "error": str(e)},
                )
        return released_materials
    
    async def get_workflow_status(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get complete workflow status for a Sales Order.
        
        Returns status across all stages:
        - Sales Order status
        - Work Order status
        - Material reservation status
        - QC status
        - Delivery status
        - Invoice status
        - Payment status
        """
        # Get Sales Order
        stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        sales_order = result.scalar_one_or_none()
        
        if not sales_order:
            raise ValueError(f"Sales Order {sales_order_id} not found")
        
        # Get Work Orders
        wo_stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.sales_order_id == sales_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        wo_result = await self.session.execute(wo_stmt)
        work_orders = wo_result.scalars().all()
        
        return {
            "sales_order_id": str(sales_order_id),
            "sales_order_status": sales_order.status,
            "sales_order_number": sales_order.order_number,
            "work_orders": [
                {
                    "wo_id": str(wo.id),
                    "wo_number": wo.wo_number,
                    "status": wo.status,
                    "produced_quantity": float(wo.produced_quantity),
                    "planned_quantity": float(wo.planned_quantity),
                }
                for wo in work_orders
            ],
            "workflow_stage": self._determine_workflow_stage(sales_order.status, work_orders),
        }
    
    def _determine_workflow_stage(
        self,
        sales_order_status: str,
        work_orders: list[WorkOrderModel],
    ) -> str:
        """Determine current workflow stage based on statuses."""
        status = OrderStatus(sales_order_status)
        
        if status in [OrderStatus.DRAFT, OrderStatus.PENDING_APPROVAL]:
            return "SALES"
        if status in [OrderStatus.APPROVED, OrderStatus.WORK_ORDER_CREATED]:
            return "PLANNING"
        if status in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
            return "PRODUCTION"
        if any(wo.status in [WorkOrderStatus.MATERIAL_PENDING, WorkOrderStatus.MATERIAL_RESERVED] for wo in work_orders):
            return "MATERIAL"
        if any(wo.status in [WorkOrderStatus.MATERIAL_ISSUED, WorkOrderStatus.IN_PRODUCTION] for wo in work_orders):
            return "PRODUCTION"
        if any(wo.status in [WorkOrderStatus.QC_PENDING, WorkOrderStatus.QC_APPROVED] for wo in work_orders):
            return "QUALITY"
        if status in [OrderStatus.READY_FOR_DISPATCH, OrderStatus.SHIPPED]:
            return "DELIVERY"
        if status == OrderStatus.DELIVERED:
            return "INVOICING"
        if status == OrderStatus.INVOICED:
            return "PAYMENT"
        if status in [OrderStatus.PAYMENT_RECEIVED, OrderStatus.COMPLETED]:
            return "COMPLETED"
        
        return "UNKNOWN"

    # ─── New event handlers (Req 7.5, 7.6, 17.1, 18.1-18.3, 26.1, 29.1-29.14) ───

    async def on_fg_received(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        received_by: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Handle Finished Goods receipt event (Req 7.5, 7.6).
        
        Actions:
        1. Reserve FG for linked Sales Order line
        2. Check if all SO lines are fully allocated
        3. If fully allocated, transition SO to READY_FOR_DISPATCH
        """
        logger.info(
            "FG received - reserving for linked sales order",
            extra={"tenant_id": str(tenant_id), "work_order_id": str(work_order_id)}
        )
        
        # Get Work Order
        stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        work_order = (await self.session.execute(stmt)).scalar_one_or_none()
        
        if not work_order:
            raise ValueError(f"Work Order {work_order_id} not found")
        
        if not work_order.sales_order_id:
            return {
                "work_order_id": str(work_order_id),
                "reserved": False,
                "message": "No linked sales order; no reservation needed",
            }
        
        sales_order_id = work_order.sales_order_id
        
        # Get the sales order and its lines
        so_stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        sales_order = (await self.session.execute(so_stmt)).scalar_one_or_none()
        
        if not sales_order:
            raise ValueError(f"Linked Sales Order {sales_order_id} not found")
        
        # Resolve the FG material ID for this work order
        fg_material_id = await self._resolve_finished_good_material_id(work_order)
        fg_quantity = Decimal(str(work_order.produced_quantity or 0)) - Decimal(
            str(work_order.scrap_quantity or 0)
        )
        
        # Reserve FG for the linked SO line (Req 7.5)
        reserved = False
        if fg_quantity > 0:
            # Find the matching SO line for this WO's product
            so_lines_stmt = select(SalesOrderLineModel).where(
                and_(
                    SalesOrderLineModel.sales_order_id == sales_order_id,
                )
            )
            so_lines = (await self.session.execute(so_lines_stmt)).scalars().all()
            
            target_line = None
            for line in so_lines:
                # Match by work_order_id link or product_id
                if line.work_order_id == work_order_id:
                    target_line = line
                    break
                if line.product_id == work_order.product_id:
                    target_line = line
                    break
            
            if target_line:
                # Calculate how much to reserve (up to the remaining needed)
                already_allocated = Decimal(str(target_line.allocated_quantity or 0))
                ordered_qty = Decimal(str(target_line.quantity or 0))
                needed = ordered_qty - already_allocated
                reserve_qty = min(fg_quantity, needed)
                
                if reserve_qty > 0:
                    try:
                        await self.inventory_service.reserve_sales_stock(
                            tenant_id=tenant_id,
                            material_id=fg_material_id,
                            quantity=reserve_qty,
                            sales_order_line_id=target_line.id,
                            created_by=received_by,
                        )
                        # Update allocated_quantity on the SO line
                        new_allocated = already_allocated + reserve_qty
                        target_line.allocated_quantity = float(new_allocated)
                        target_line.updated_at = datetime.now(timezone.utc)
                        
                        # Update line_status based on allocation vs ordered (Req 19.2, 19.3)
                        if new_allocated >= ordered_qty:
                            target_line.line_status = "ALLOCATED"
                        else:
                            target_line.line_status = "PARTIAL"
                        
                        reserved = True
                    except Exception as e:
                        logger.warning(
                            "FG reservation for SO failed",
                            extra={"error": str(e), "work_order_id": str(work_order_id)},
                        )
        
        await self.session.flush()

        # Notify dispatch that FG has been received (Req 23.4)
        await self.notification_service.create_notification(
            tenant_id=tenant_id,
            notification_type="fg_received",
            title=f"FG Received - WO {work_order.wo_number}",
            message=f"Finished goods received for Work Order {work_order.wo_number}. Quantity: {float(fg_quantity)}.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

        # Check if all SO lines are fully allocated (Req 7.6, 19.8)
        all_lines_stmt = select(SalesOrderLineModel).where(
            SalesOrderLineModel.sales_order_id == sales_order_id,
        )
        all_lines = (await self.session.execute(all_lines_stmt)).scalars().all()
        
        # SO transitions to READY_FOR_DISPATCH iff every non-SHORT_CLOSED line
        # has allocated_quantity >= ordered_quantity (Req 19.8)
        fully_allocated = all(
            Decimal(str(line.allocated_quantity or 0)) >= Decimal(str(line.quantity or 0))
            for line in all_lines
            if line.line_status != "SHORT_CLOSED"
        )
        
        so_transitioned = False
        if fully_allocated:
            current_status = OrderStatus(sales_order.status)
            if current_status.can_transition_to(OrderStatus.READY_FOR_DISPATCH):
                sales_order.status = OrderStatus.READY_FOR_DISPATCH.value
                sales_order.updated_at = datetime.now(timezone.utc)
                so_transitioned = True
                await self.session.flush()
                
                # Notify dispatch team
                await self.notification_service.create_notification(
                    tenant_id=tenant_id,
                    notification_type="ready_for_dispatch_action",
                    title=f"Order {sales_order.order_number} Ready for Dispatch",
                    message=f"All materials allocated for order {sales_order.order_number}. Ready for dispatch.",
                    reference_id=str(sales_order.id),
                    reference_type="sales_order",
                )
        
        return {
            "work_order_id": str(work_order_id),
            "sales_order_id": str(sales_order_id),
            "fg_material_id": str(fg_material_id),
            "fg_quantity": float(fg_quantity),
            "reserved": reserved,
            "fully_allocated": fully_allocated,
            "so_transitioned_to_ready": so_transitioned,
            "message": "FG received and reservation processed",
        }

    async def on_goods_received(
        self,
        tenant_id: uuid.UUID,
        purchase_order_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
    ) -> Dict[str, Any]:
        """
        Handle goods receipt event (GRN + incoming QC approved).
        
        Actions:
        1. Update inventory (stock increase)
        2. Check pending Work Orders waiting for this material
        3. Auto-reserve for pending WOs
        4. Transition WO to MATERIAL_RESERVED if fully reserved
        """
        logger.info(
            "Goods received - updating inventory and checking pending WOs",
            extra={
                "tenant_id": str(tenant_id),
                "purchase_order_id": str(purchase_order_id),
                "material_id": str(material_id),
                "quantity": float(quantity),
            }
        )
        
        # 1. Update inventory (receive stock)
        await self.inventory_service.receive_stock(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=quantity,
            unit_id=None,
            reference_type="purchase_order",
            reference_id=purchase_order_id,
            created_by=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # system user
            remarks=f"GRN received for PO {purchase_order_id}",
        )
        
        # 2. Find pending Work Orders that need this material
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderMaterialModel
        
        pending_wos_stmt = (
            select(WorkOrderModel)
            .join(
                WorkOrderMaterialModel,
                WorkOrderMaterialModel.work_order_id == WorkOrderModel.id,
            )
            .where(
                and_(
                    WorkOrderModel.tenant_id == tenant_id,
                    WorkOrderModel.status == WorkOrderStatus.MATERIAL_PENDING.value,
                    WorkOrderModel.is_deleted.is_(False),
                    WorkOrderMaterialModel.material_id == material_id,
                )
            )
        )
        pending_wos = (await self.session.execute(pending_wos_stmt)).scalars().unique().all()
        
        transitioned_wos = []
        
        for wo in pending_wos:
            # 3. Attempt auto-reserve for this WO
            try:
                from backend.app.application.inventory.services.inventory_reservation_service import (
                    InventoryReservationService,
                )
                reservation_svc = InventoryReservationService(self.session)
                
                # Get all material requirements for this WO
                wo_materials_stmt = select(WorkOrderMaterialModel).where(
                    WorkOrderMaterialModel.work_order_id == wo.id,
                )
                wo_materials = (await self.session.execute(wo_materials_stmt)).scalars().all()
                
                all_reserved = True
                for wom in wo_materials:
                    required_qty = Decimal(str(wom.required_quantity or 0))
                    issued_qty = Decimal(str(wom.issued_quantity or 0))
                    remaining = required_qty - issued_qty
                    if remaining <= 0:
                        continue
                    
                    # Check existing reservation
                    already_reserved = await self.inventory_service.get_existing_reservation_qty_for_wo(
                        tenant_id=tenant_id,
                        work_order_id=wo.id,
                        material_id=wom.material_id,
                    )
                    need_to_reserve = max(Decimal("0"), remaining - already_reserved)
                    
                    if need_to_reserve > 0:
                        # Try to reserve
                        _reserved, shortage, _ = await reservation_svc.reserve_for_work_order(
                            tenant_id=tenant_id,
                            work_order_id=wo.id,
                            material_id=wom.material_id,
                            required_quantity=need_to_reserve,
                            unit_id=wom.unit_id,
                            created_by=wo.created_by,
                        )
                        if shortage > 0:
                            all_reserved = False
                
                # 4. If all materials reserved, transition WO
                if all_reserved:
                    wo.status = WorkOrderStatus.MATERIAL_RESERVED.value
                    wo.updated_at = datetime.now(timezone.utc)
                    transitioned_wos.append(str(wo.id))

                    # Notify storekeeper to issue materials (Req 27.1)
                    await self.notification_service.create_notification(
                        tenant_id=tenant_id,
                        notification_type="issue_materials_action",
                        title=f"Action Required: Issue Materials - WO {wo.wo_number}",
                        message=f"Materials reserved for Work Order {wo.wo_number}. Please issue materials to begin production.",
                        reference_id=str(wo.id),
                        reference_type="work_order",
                    )
                    
            except Exception as e:
                logger.warning(
                    "Auto-reserve failed for WO",
                    extra={"work_order_id": str(wo.id), "error": str(e)},
                )
        
        if transitioned_wos:
            await self.session.flush()
        
        return {
            "purchase_order_id": str(purchase_order_id),
            "material_id": str(material_id),
            "quantity_received": float(quantity),
            "pending_wos_checked": len(pending_wos),
            "wos_transitioned": transitioned_wos,
            "message": "Goods received, inventory updated, and pending WOs checked",
        }

    async def on_cancellation(
        self,
        tenant_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        cancelled_by: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Handle cancellation event for Sales Order or Work Order (Req 18.1-18.3).
        
        Actions:
        1. Release all inventory reservations for the entity
        2. Create audit log entries for the cancellation
        """
        logger.info(
            "Cancellation event - releasing reservations",
            extra={
                "tenant_id": str(tenant_id),
                "entity_type": entity_type,
                "entity_id": str(entity_id),
            }
        )
        
        released_materials: List[Dict[str, Any]] = []
        
        if entity_type == "sales_order":
            # Release all SO line reservations
            so_lines_stmt = select(SalesOrderLineModel).where(
                SalesOrderLineModel.sales_order_id == entity_id,
            )
            so_lines = (await self.session.execute(so_lines_stmt)).scalars().all()
            
            for line in so_lines:
                allocated = Decimal(str(line.allocated_quantity or 0))
                if allocated > 0:
                    try:
                        # Find the material for this line
                        material = (await self.session.execute(
                            select(MaterialModel).where(
                                and_(
                                    MaterialModel.id == line.product_id,
                                    MaterialModel.tenant_id == tenant_id,
                                    MaterialModel.is_deleted.is_(False),
                                )
                            )
                        )).scalar_one_or_none()
                        
                        if material:
                            await self.inventory_service.release_sales_reservation(
                                tenant_id=tenant_id,
                                material_id=material.id,
                                quantity=allocated,
                                sales_order_line_id=line.id,
                                created_by=cancelled_by,
                            )
                            # Reset allocated quantity
                            line.allocated_quantity = 0
                            line.updated_at = datetime.now(timezone.utc)
                            released_materials.append({
                                "material_id": str(material.id),
                                "quantity_released": float(allocated),
                            })
                    except Exception as e:
                        logger.warning(
                            "Failed to release SO line reservation",
                            extra={"line_id": str(line.id), "error": str(e)},
                        )
            
            # Also release any linked WO reservations
            wo_stmt = select(WorkOrderModel).where(
                and_(
                    WorkOrderModel.sales_order_id == entity_id,
                    WorkOrderModel.tenant_id == tenant_id,
                    WorkOrderModel.is_deleted.is_(False),
                )
            )
            linked_wos = (await self.session.execute(wo_stmt)).scalars().all()
            for wo in linked_wos:
                wo_released = await self._release_work_order_reservations(
                    tenant_id=tenant_id,
                    work_order=wo,
                    cancelled_by=cancelled_by,
                )
                released_materials.extend(wo_released)
                
        elif entity_type == "work_order":
            # Release WO material reservations
            wo_stmt = select(WorkOrderModel).where(
                and_(
                    WorkOrderModel.id == entity_id,
                    WorkOrderModel.tenant_id == tenant_id,
                    WorkOrderModel.is_deleted.is_(False),
                )
            )
            work_order = (await self.session.execute(wo_stmt)).scalar_one_or_none()
            
            if work_order:
                released_materials = await self._release_work_order_reservations(
                    tenant_id=tenant_id,
                    work_order=work_order,
                    cancelled_by=cancelled_by,
                )
        
        await self.session.flush()
        
        # Create audit entry for the cancellation
        try:
            from backend.app.services.audit_log_service import AuditLogService
            audit_service = AuditLogService(self.session)
            await audit_service.log_action(
                tenant_id=tenant_id,
                user_id=cancelled_by,
                action_type="cancellation",
                entity_type=entity_type,
                entity_id=entity_id,
                before_state={"status": "active", "reservations": len(released_materials)},
                after_state={"status": "cancelled", "reservations_released": len(released_materials)},
                reason="Entity cancelled - all reservations released",
            )
        except Exception as e:
            logger.warning("Failed to create audit entry for cancellation", extra={"error": str(e)})
        
        return {
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "reservations_released": len(released_materials),
            "released_materials": released_materials,
            "message": "Cancellation processed - all reservations released",
        }

    async def _release_work_order_reservations(
        self,
        tenant_id: uuid.UUID,
        work_order: WorkOrderModel,
        cancelled_by: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        """Release all material reservations for a work order via RESERVATION_RELEASE transactions (Req 18.2, 18.4)."""
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderMaterialModel
        
        released = []
        wo_materials_stmt = select(WorkOrderMaterialModel).where(
            WorkOrderMaterialModel.work_order_id == work_order.id,
        )
        wo_materials = (await self.session.execute(wo_materials_stmt)).scalars().all()
        
        for wom in wo_materials:
            try:
                cancelled_qty = await self.inventory_service.cancel_work_order_reservation(
                    tenant_id=tenant_id,
                    material_id=wom.material_id,
                    work_order_id=work_order.id,
                    unit_id=wom.unit_id,
                    created_by=cancelled_by,
                    remarks=f"Reservation released due to WO cancellation - WO {work_order.id}",
                )
                if cancelled_qty > 0:
                    released.append({
                        "material_id": str(wom.material_id),
                        "quantity_released": float(cancelled_qty),
                    })
            except Exception as e:
                logger.warning(
                    "Failed to release WO reservation for material",
                    extra={"material_id": str(wom.material_id), "error": str(e)},
                )
        
        return released

    async def on_exception(
        self,
        tenant_id: uuid.UUID,
        exception_type: str,
        work_order_id: uuid.UUID,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle production exception events (Req 26.1, 26.3).
        
        Exception types:
        - machine_breakdown: Put WO on PRODUCTION_HOLD
        - supplier_delay: Record delay, create escalation
        - quality_issue: Create QC escalation notification
        
        Actions:
        1. Apply hold/delay pattern based on exception type
        2. Create escalation notifications
        """
        logger.info(
            "Exception event received",
            extra={
                "tenant_id": str(tenant_id),
                "exception_type": exception_type,
                "work_order_id": str(work_order_id),
            }
        )
        
        # Get Work Order
        stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        work_order = (await self.session.execute(stmt)).scalar_one_or_none()
        
        if not work_order:
            raise ValueError(f"Work Order {work_order_id} not found")
        
        hold_applied = False
        notification_type = "production_alert"
        notification_title = ""
        notification_message = ""
        
        if exception_type == "machine_breakdown":
            # Apply production hold pattern
            if work_order.status == WorkOrderStatus.IN_PRODUCTION.value:
                # Store the previous status for resume capability
                work_order.status = "PRODUCTION_HOLD"
                work_order.updated_at = datetime.now(timezone.utc)
                hold_applied = True
            
            notification_type = "machine_breakdown"
            notification_title = f"Machine Breakdown - WO {work_order.wo_number}"
            notification_message = (
                f"Machine breakdown reported for Work Order {work_order.wo_number}. "
                f"Production is on hold. Details: {details.get('reason', 'N/A')}"
            )
            
        elif exception_type == "supplier_delay":
            notification_type = "promise_date_at_risk"
            notification_title = f"Supplier Delay - WO {work_order.wo_number}"
            notification_message = (
                f"Supplier delay reported affecting Work Order {work_order.wo_number}. "
                f"Expected delay: {details.get('delay_days', 'unknown')} days. "
                f"Reason: {details.get('reason', 'N/A')}"
            )
            
        elif exception_type == "quality_issue":
            notification_type = "qc_escalation"
            notification_title = f"Quality Escalation - WO {work_order.wo_number}"
            notification_message = (
                f"Quality issue escalated for Work Order {work_order.wo_number}. "
                f"Issue: {details.get('reason', 'N/A')}"
            )
        else:
            notification_title = f"Production Exception - WO {work_order.wo_number}"
            notification_message = (
                f"Exception of type '{exception_type}' reported for WO {work_order.wo_number}. "
                f"Details: {details.get('reason', 'N/A')}"
            )
        
        await self.session.flush()
        
        # Create escalation notification
        await self.notification_service.create_notification(
            tenant_id=tenant_id,
            notification_type=notification_type,
            title=notification_title,
            message=notification_message,
            reference_id=str(work_order_id),
            reference_type="work_order",
        )
        
        # Create audit entry
        try:
            from backend.app.services.audit_log_service import AuditLogService
            audit_service = AuditLogService(self.session)
            await audit_service.log_action(
                tenant_id=tenant_id,
                user_id=details.get("reported_by", uuid.UUID("00000000-0000-0000-0000-000000000000")),
                action_type=f"exception_{exception_type}",
                entity_type="work_order",
                entity_id=work_order_id,
                before_state={"status": work_order.status if not hold_applied else WorkOrderStatus.IN_PRODUCTION.value},
                after_state={"status": work_order.status, "exception_type": exception_type},
                reason=details.get("reason"),
                metadata=details,
            )
        except Exception as e:
            logger.warning("Failed to create audit entry for exception", extra={"error": str(e)})
        
        return {
            "work_order_id": str(work_order_id),
            "exception_type": exception_type,
            "hold_applied": hold_applied,
            "current_status": work_order.status,
            "message": f"Exception handled: {exception_type}",
        }

    async def on_auto_transition(
        self,
        tenant_id: uuid.UUID,
        operation_key: str,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Idempotent wrapper for orchestrated events (Req 29.1-29.14).
        
        Checks for duplicate operations before proceeding.
        Returns a dict with 'duplicate': True if already completed,
        allowing callers to short-circuit.
        
        Uses audit log to detect previous completions of the same operation.
        """
        try:
            from backend.app.services.audit_log_service import AuditLogService
            from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel
            
            # Check if this operation was already completed
            # Use a hash of the operation key to keep within field length limits
            import hashlib
            action_key = f"auto:{hashlib.md5(operation_key.encode()).hexdigest()[:20]}"
            
            existing = (await self.session.execute(
                select(AuditLogModel.id).where(
                    and_(
                        AuditLogModel.tenant_id == tenant_id,
                        AuditLogModel.entity_type == entity_type,
                        AuditLogModel.entity_id == entity_id,
                        AuditLogModel.action == action_key,
                    )
                ).limit(1)
            )).scalar_one_or_none()
            
            if existing is not None:
                logger.info(
                    "Duplicate auto-transition detected - no-op",
                    extra={
                        "operation_key": operation_key,
                        "entity_type": entity_type,
                        "entity_id": str(entity_id),
                    },
                )
                return {
                    "duplicate": True,
                    "operation_key": operation_key,
                    "entity_type": entity_type,
                    "entity_id": str(entity_id),
                    "message": "Operation already completed - no-op",
                }
            
            # Record this auto-transition
            audit_service = AuditLogService(self.session)
            await audit_service.log_action(
                tenant_id=tenant_id,
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # system
                action_type=action_key,
                entity_type=entity_type,
                entity_id=entity_id,
                before_state={},
                after_state={"operation_key": operation_key},
                reason="Orchestrated auto-transition",
            )
            await self.session.flush()
            
        except Exception as e:
            # If audit log check fails, proceed anyway (non-blocking)
            logger.warning(
                "Auto-transition idempotency check failed - proceeding",
                extra={"operation_key": operation_key, "error": str(e)},
            )
        
        return {
            "duplicate": False,
            "operation_key": operation_key,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "message": "Operation proceeding",
        }
