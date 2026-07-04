"""
Notification Service for WebSocket-based operational alerts.
Broadcasts real-time alerts for key manufacturing events.

Extended to support:
- 20+ notification types for end-to-end manufacturing workflow
- deep_link field for direct entity navigation
- Role-based notification targeting
- Integration with WorkflowOrchestrationService event handlers
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class NotificationPayload:
    """Standard notification payload structure."""
    id: str
    type: str
    title: str
    message: str
    data: dict
    timestamp: str
    priority: str = "info"  # info, warning, error, success
    deep_link: Optional[str] = None
    target_role: Optional[str] = None


# ─── Notification Type Constants ───────────────────────────────────────────────

# Workflow state transition notifications
NOTIFICATION_TYPE_SALES_APPROVED = "sales_approved"
NOTIFICATION_TYPE_MATERIAL_SHORTAGE = "material_shortage"
NOTIFICATION_TYPE_QC_FAILED = "qc_failed"
NOTIFICATION_TYPE_FG_RECEIVED = "fg_received"
NOTIFICATION_TYPE_DISPATCH_COMPLETED = "dispatch_completed"
NOTIFICATION_TYPE_PAYMENT_RECEIVED = "payment_received"
NOTIFICATION_TYPE_WO_RELEASED = "wo_released"
NOTIFICATION_TYPE_MATERIAL_ISSUED = "material_issued"
NOTIFICATION_TYPE_QC_APPROVED = "qc_approved"

# Action-required notifications
NOTIFICATION_TYPE_ISSUE_MATERIALS_ACTION = "issue_materials_action"
NOTIFICATION_TYPE_START_PRODUCTION_ACTION = "start_production_action"
NOTIFICATION_TYPE_RECEIVE_FG_ACTION = "receive_fg_action"
NOTIFICATION_TYPE_READY_FOR_DISPATCH_ACTION = "ready_for_dispatch_action"

# Error/exception notifications
NOTIFICATION_TYPE_INVOICE_CREATION_FAILED = "invoice_creation_failed"
NOTIFICATION_TYPE_MACHINE_BREAKDOWN = "machine_breakdown"
NOTIFICATION_TYPE_PROMISE_DATE_AT_RISK = "promise_date_at_risk"
NOTIFICATION_TYPE_QC_ESCALATION = "qc_escalation"
NOTIFICATION_TYPE_DELIVERY_CANCELLED = "delivery_cancelled"
NOTIFICATION_TYPE_INCOMING_QC_FAILED = "incoming_qc_failed"
NOTIFICATION_TYPE_REQUISITION_REJECTED = "requisition_rejected"
NOTIFICATION_TYPE_PRODUCTION_SCRAP_FAILED = "production_scrap_failed"
NOTIFICATION_TYPE_DOCUMENT_GENERATED = "document_generated"
NOTIFICATION_TYPE_FG_RECEIPT_FAILED = "fg_receipt_failed"


# ─── Notification Type → Target Role Mapping ──────────────────────────────────

NOTIFICATION_ROUTING: Dict[str, str] = {
    NOTIFICATION_TYPE_SALES_APPROVED: "planner",
    NOTIFICATION_TYPE_MATERIAL_SHORTAGE: "procurement",
    NOTIFICATION_TYPE_QC_FAILED: "production_supervisor",
    NOTIFICATION_TYPE_FG_RECEIVED: "dispatch",
    NOTIFICATION_TYPE_DISPATCH_COMPLETED: "finance",
    NOTIFICATION_TYPE_PAYMENT_RECEIVED: "sales",
    NOTIFICATION_TYPE_WO_RELEASED: "storekeeper",
    NOTIFICATION_TYPE_MATERIAL_ISSUED: "operator",
    NOTIFICATION_TYPE_QC_APPROVED: "storekeeper",
    NOTIFICATION_TYPE_ISSUE_MATERIALS_ACTION: "storekeeper",
    NOTIFICATION_TYPE_START_PRODUCTION_ACTION: "operator",
    NOTIFICATION_TYPE_RECEIVE_FG_ACTION: "storekeeper",
    NOTIFICATION_TYPE_READY_FOR_DISPATCH_ACTION: "dispatch",
    NOTIFICATION_TYPE_INVOICE_CREATION_FAILED: "finance",
    NOTIFICATION_TYPE_MACHINE_BREAKDOWN: "maintenance",
    NOTIFICATION_TYPE_PROMISE_DATE_AT_RISK: "sales",
    NOTIFICATION_TYPE_QC_ESCALATION: "quality_manager",
    NOTIFICATION_TYPE_DELIVERY_CANCELLED: "sales",
    NOTIFICATION_TYPE_INCOMING_QC_FAILED: "procurement",
    NOTIFICATION_TYPE_REQUISITION_REJECTED: "planner",
    NOTIFICATION_TYPE_PRODUCTION_SCRAP_FAILED: "sales",
    NOTIFICATION_TYPE_FG_RECEIPT_FAILED: "finance",
}

# All valid notification types
ALL_NOTIFICATION_TYPES = list(NOTIFICATION_ROUTING.keys())


def build_deep_link(entity_type: str, entity_id: str) -> str:
    """
    Build a deep link URL for direct navigation to the relevant entity.
    
    Returns a frontend route path that the UI can use for navigation.
    """
    entity_routes = {
        "sales_order": f"/sales/orders/{entity_id}",
        "work_order": f"/manufacturing/work-orders/{entity_id}",
        "delivery": f"/delivery/deliveries/{entity_id}",
        "invoice": f"/finance/invoices/{entity_id}",
        "purchase_requisition": f"/procurement/requisitions/{entity_id}",
        "purchase_order": f"/procurement/purchase-orders/{entity_id}",
        "material": f"/inventory/materials/{entity_id}",
    }
    return entity_routes.get(entity_type, f"/{entity_type}/{entity_id}")


class NotificationService:
    """
    Service for creating and broadcasting operational notifications.
    
    Supports 21 notification types covering the full manufacturing workflow:
    - State transition notifications (sales_approved, wo_released, qc_approved, etc.)
    - Action-required notifications (issue_materials_action, start_production_action, etc.)
    - Error/exception notifications (invoice_creation_failed, machine_breakdown, etc.)
    
    Each notification includes:
    - notification_type: Identifies the event category
    - target_role: The role that should receive this notification
    - deep_link: Direct navigation URL to the relevant entity
    - reference_type/id: Entity reference for programmatic access
    """

    def __init__(self, session: AsyncSession, connection_manager=None):
        self._session = session
        self._connection_manager = connection_manager

    async def create_notification(
        self,
        *,
        tenant_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        deep_link: Optional[str] = None,
        target_role: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> uuid.UUID:
        """
        Create a notification and persist it to the database.
        
        If target_role is not specified, it's looked up from NOTIFICATION_ROUTING.
        If deep_link is not specified, it's auto-generated from reference_type/id.
        
        Args:
            tenant_id: Tenant owning this notification
            notification_type: One of the defined notification type constants
            title: Human-readable notification title
            message: Detailed notification message
            reference_id: Entity ID this notification relates to
            reference_type: Entity type (sales_order, work_order, etc.)
            deep_link: Frontend route for direct navigation (auto-generated if not provided)
            target_role: Role that should see this notification (auto-resolved if not provided)
            user_id: Specific user to notify (optional, for role-based notifications)
            
        Returns:
            UUID of the created notification
        """
        from backend.app.infrastructure.persistence.models.notification_model import NotificationModel

        # Auto-resolve target role from routing table if not provided
        if target_role is None:
            target_role = NOTIFICATION_ROUTING.get(notification_type)

        # Auto-generate deep_link if not provided but reference info is available
        if deep_link is None and reference_type and reference_id:
            deep_link = build_deep_link(reference_type, str(reference_id))

        # Parse reference_id to UUID if it's a string
        ref_id_uuid = None
        if reference_id:
            try:
                ref_id_uuid = uuid.UUID(str(reference_id))
            except (ValueError, AttributeError):
                ref_id_uuid = None

        notification = NotificationModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            reference_type=reference_type,
            reference_id=ref_id_uuid,
            deep_link=deep_link,
            target_role=target_role,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(notification)
        await self._session.flush()

        # Best-effort WebSocket broadcast for real-time delivery
        if self._connection_manager:
            try:
                payload = {
                    "id": str(notification.id),
                    "type": notification_type,
                    "title": title,
                    "message": message,
                    "reference_type": reference_type,
                    "reference_id": str(reference_id) if reference_id else None,
                    "deep_link": deep_link,
                    "target_role": target_role,
                    "is_read": False,
                    "created_at": notification.created_at.isoformat(),
                }
                await self._connection_manager.broadcast_to_tenant(
                    tenant_id=tenant_id,
                    message_type="notification",
                    payload=payload,
                )
            except Exception:
                pass  # WebSocket failure must not affect persistence

        return notification.id

    # ─── Convenience Methods for Specific Notification Types ───────────────────

    async def notify_sales_approved(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        order_number: str,
    ) -> uuid.UUID:
        """Notify planner that a sales order has been approved."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_SALES_APPROVED,
            title=f"Sales Order {order_number} Approved",
            message=f"Sales Order {order_number} has been approved and is ready for production planning.",
            reference_id=str(sales_order_id),
            reference_type="sales_order",
        )

    async def notify_material_shortage(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
        shortage_count: int = 1,
    ) -> uuid.UUID:
        """Notify procurement about material shortage for a work order."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_MATERIAL_SHORTAGE,
            title=f"Material Shortage for WO {wo_number}",
            message=f"Material shortage detected for Work Order {wo_number}. {shortage_count} material(s) require procurement.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

    async def notify_qc_failed(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
        reason: str = "",
    ) -> uuid.UUID:
        """Notify production supervisor about QC failure."""
        msg = f"Quality inspection failed for Work Order {wo_number}."
        if reason:
            msg += f" Reason: {reason}"
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_QC_FAILED,
            title=f"QC Failed - WO {wo_number}",
            message=msg,
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

    async def notify_fg_received(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
        quantity: float = 0,
    ) -> uuid.UUID:
        """Notify dispatch that finished goods have been received."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_FG_RECEIVED,
            title=f"FG Received - WO {wo_number}",
            message=f"Finished goods received for Work Order {wo_number}. Quantity: {quantity}.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

    async def notify_dispatch_completed(
        self,
        tenant_id: uuid.UUID,
        delivery_id: uuid.UUID,
        delivery_number: str,
        sales_order_number: str = "",
    ) -> uuid.UUID:
        """Notify finance that dispatch is completed (delivery marked DELIVERED)."""
        msg = f"Delivery {delivery_number} has been completed."
        if sales_order_number:
            msg += f" Related to order {sales_order_number}."
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_DISPATCH_COMPLETED,
            title=f"Dispatch Completed - {delivery_number}",
            message=msg,
            reference_id=str(delivery_id),
            reference_type="delivery",
        )

    async def notify_payment_received(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        order_number: str,
    ) -> uuid.UUID:
        """Notify sales team that full payment has been received."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_PAYMENT_RECEIVED,
            title=f"Payment Complete - Order {order_number}",
            message=f"Full payment received for order {order_number}. Order is now COMPLETED.",
            reference_id=str(sales_order_id),
            reference_type="sales_order",
        )

    async def notify_wo_released(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
    ) -> uuid.UUID:
        """Notify storekeeper that a work order has been released."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_WO_RELEASED,
            title=f"Work Order {wo_number} Released",
            message=f"Work Order {wo_number} has been released. Materials can be prepared.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

    async def notify_material_issued(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
    ) -> uuid.UUID:
        """Notify operator that all materials have been issued."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_MATERIAL_ISSUED,
            title=f"Materials Issued - WO {wo_number}",
            message=f"All BOM materials have been issued for Work Order {wo_number}. Production can begin.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

    async def notify_qc_approved(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
    ) -> uuid.UUID:
        """Notify storekeeper that QC has been approved."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_QC_APPROVED,
            title=f"QC Approved - WO {wo_number}",
            message=f"Quality inspection passed for Work Order {wo_number}. Ready for FG receipt.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

    async def notify_issue_materials_action(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
    ) -> uuid.UUID:
        """Notify storekeeper to issue materials (WO is MATERIAL_RESERVED)."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_ISSUE_MATERIALS_ACTION,
            title=f"Action Required: Issue Materials - WO {wo_number}",
            message=f"Materials reserved for Work Order {wo_number}. Please issue materials to begin production.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

    async def notify_start_production_action(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
    ) -> uuid.UUID:
        """Notify operator to start production (all materials issued)."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_START_PRODUCTION_ACTION,
            title=f"Action Required: Start Production - WO {wo_number}",
            message=f"All materials issued for Work Order {wo_number}. Production can now begin.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

    async def notify_receive_fg_action(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
    ) -> uuid.UUID:
        """Notify storekeeper to receive finished goods (WO QC approved)."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_RECEIVE_FG_ACTION,
            title=f"Action Required: Receive FG - WO {wo_number}",
            message=f"QC approved for Work Order {wo_number}. Please receive finished goods into inventory.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

    async def notify_ready_for_dispatch_action(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        order_number: str,
    ) -> uuid.UUID:
        """Notify dispatch team that an order is ready for dispatch."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_READY_FOR_DISPATCH_ACTION,
            title=f"Action Required: Dispatch Order {order_number}",
            message=f"Order {order_number} is ready for dispatch. Please create a delivery note.",
            reference_id=str(sales_order_id),
            reference_type="sales_order",
        )

    async def notify_document_generated(
        self,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        document_type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        entity_number: str,
        user_id: uuid.UUID,
    ) -> uuid.UUID:
        """Notify a user that a document has been generated."""
        title = document_type.replace("_", " ").title() + " Generated"
        return await self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=NOTIFICATION_TYPE_DOCUMENT_GENERATED,
            title=title,
            message=f"{title}: {entity_number} has been generated successfully.",
            reference_type=entity_type,
            reference_id=str(entity_id),
            deep_link=build_deep_link(entity_type, str(entity_id)),
        )

    async def notify_invoice_creation_failed(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        order_number: str,
        error: str = "",
    ) -> uuid.UUID:
        """Notify finance that auto-invoice creation failed."""
        msg = f"Auto-invoice creation failed for Sales Order {order_number}."
        if error:
            msg += f" Error: {error}"
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_INVOICE_CREATION_FAILED,
            title=f"Invoice Creation Failed - Order {order_number}",
            message=msg,
            reference_id=str(sales_order_id),
            reference_type="sales_order",
        )

    async def notify_machine_breakdown(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
        reason: str = "",
    ) -> uuid.UUID:
        """Notify maintenance about a machine breakdown."""
        msg = f"Machine breakdown reported for Work Order {wo_number}. Production is on hold."
        if reason:
            msg += f" Details: {reason}"
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_MACHINE_BREAKDOWN,
            title=f"Machine Breakdown - WO {wo_number}",
            message=msg,
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

    async def notify_promise_date_at_risk(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        order_number: str,
        delay_days: int = 0,
    ) -> uuid.UUID:
        """Notify sales that a promise date is at risk."""
        msg = f"Promise date at risk for order {order_number}."
        if delay_days:
            msg += f" Estimated delay: {delay_days} day(s)."
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_PROMISE_DATE_AT_RISK,
            title=f"Promise Date at Risk - Order {order_number}",
            message=msg,
            reference_id=str(sales_order_id),
            reference_type="sales_order",
        )

    async def notify_qc_escalation(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
        rejection_count: int = 3,
    ) -> uuid.UUID:
        """Notify quality manager about QC escalation (3+ rejections)."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_QC_ESCALATION,
            title=f"QC Escalation - WO {wo_number}",
            message=f"Work Order {wo_number} has been rejected {rejection_count} time(s). Quality manager review required.",
            reference_id=str(work_order_id),
            reference_type="work_order",
        )

    async def notify_delivery_cancelled(
        self,
        tenant_id: uuid.UUID,
        delivery_id: uuid.UUID,
        delivery_number: str,
        order_number: str = "",
    ) -> uuid.UUID:
        """Notify sales team about a cancelled delivery."""
        msg = f"Delivery {delivery_number} has been cancelled."
        if order_number:
            msg += f" Related to order {order_number}."
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_DELIVERY_CANCELLED,
            title=f"Delivery Cancelled - {delivery_number}",
            message=msg,
            reference_id=str(delivery_id),
            reference_type="delivery",
        )

    async def notify_incoming_qc_failed(
        self,
        tenant_id: uuid.UUID,
        purchase_order_id: uuid.UUID,
        material_name: str = "",
    ) -> uuid.UUID:
        """Notify procurement that incoming QC has rejected goods."""
        msg = "Incoming QC has rejected received goods."
        if material_name:
            msg += f" Material: {material_name}."
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_INCOMING_QC_FAILED,
            title="Incoming QC Failed",
            message=msg,
            reference_id=str(purchase_order_id),
            reference_type="purchase_order",
        )

    async def notify_requisition_rejected(
        self,
        tenant_id: uuid.UUID,
        requisition_id: uuid.UUID,
        requisition_number: str,
    ) -> uuid.UUID:
        """Notify planner that a purchase requisition has been rejected."""
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_REQUISITION_REJECTED,
            title=f"Requisition Rejected - {requisition_number}",
            message=f"Purchase Requisition {requisition_number} has been rejected.",
            reference_id=str(requisition_id),
            reference_type="purchase_requisition",
        )

    async def notify_production_scrap_failed(
        self,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
        sales_order_number: str = "",
    ) -> uuid.UUID:
        """Notify sales that a WO has been scrapped with a linked sales order."""
        msg = f"Work Order {wo_number} has been scrapped."
        if sales_order_number:
            msg += f" Linked Sales Order {sales_order_number} may be affected."
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type=NOTIFICATION_TYPE_PRODUCTION_SCRAP_FAILED,
            title=f"Production Scrapped - WO {wo_number}",
            message=msg,
            reference_id=str(work_order_id),
            reference_type="work_order",
        )
