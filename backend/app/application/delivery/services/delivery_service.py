"""
Delivery Service - Queue-First Operational Workspace for Delivery Team

Provides operational queue-first dashboard for delivery team with:
- Dispatch Queue: Orders ready for dispatch
- Delivery Queue: Orders in transit
- Completed Queue: Recently delivered orders
- Integration with WorkflowOrchestrationService for sales order updates
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.delivery_model import DeliveryOrderModel
from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel
from backend.app.application.manufacturing.services.workflow_orchestration_service import WorkflowOrchestrationService

logger = logging.getLogger(__name__)


class DeliveryService:
    """
    Service for Delivery operational workspace with queue-first design.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.workflow_service = WorkflowOrchestrationService(session)
    
    async def get_delivery_dashboard(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get comprehensive delivery dashboard with all operational queues.
        
        Returns:
        - Dispatch Queue: Orders ready for dispatch
        - In Transit Queue: Orders currently being delivered
        - Completed Queue: Recently delivered orders
        - Delivery metrics
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dispatch_queue": await self._get_dispatch_queue(tenant_id),
            "in_transit_queue": await self._get_in_transit_queue(tenant_id),
            "completed_queue": await self._get_completed_queue(tenant_id),
            "metrics": await self._get_delivery_metrics(tenant_id),
        }
    
    async def _get_dispatch_queue(self, tenant_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get orders ready for dispatch."""
        
        # Get delivery orders ready to ship
        stmt = select(DeliveryOrderModel).where(
            and_(
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.status.in_(["READY_TO_SHIP", "PACKING"]),
                DeliveryOrderModel.is_deleted.is_(False),
            )
        ).order_by(DeliveryOrderModel.created_at.asc()).limit(20)
        
        result = await self.session.execute(stmt)
        delivery_orders = result.scalars().all()
        
        # Get linked sales orders for additional context
        queue_data = []
        for do in delivery_orders:
            sales_order = None
            if do.sales_order_id:
                so_stmt = select(SalesOrderModel).where(
                    SalesOrderModel.id == do.sales_order_id,
                    SalesOrderModel.is_deleted.is_(False),
                )
                so_result = await self.session.execute(so_stmt)
                sales_order = so_result.scalar_one_or_none()
            
            queue_data.append({
                "delivery_order_id": str(do.id),
                "delivery_number": do.delivery_number,
                "sales_order_id": str(do.sales_order_id) if do.sales_order_id else None,
                "sales_order_number": sales_order.order_number if sales_order else None,
                "status": do.status,
                "client_id": str(do.client_id) if do.client_id else None,
                "shipping_address": do.shipping_address,
                "created_at": do.created_at.isoformat() if do.created_at else None,
                "priority": do.priority if hasattr(do, 'priority') else "NORMAL",
            })
        
        return queue_data
    
    async def _get_in_transit_queue(self, tenant_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get orders currently in transit."""
        
        stmt = select(DeliveryOrderModel).where(
            and_(
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.status == "IN_TRANSIT",
                DeliveryOrderModel.is_deleted.is_(False),
            )
        ).order_by(DeliveryOrderModel.shipped_at.asc()).limit(20)
        
        result = await self.session.execute(stmt)
        delivery_orders = result.scalars().all()
        
        queue_data = []
        for do in delivery_orders:
            sales_order = None
            if do.sales_order_id:
                so_stmt = select(SalesOrderModel).where(
                    SalesOrderModel.id == do.sales_order_id,
                    SalesOrderModel.is_deleted.is_(False),
                )
                so_result = await self.session.execute(so_stmt)
                sales_order = so_result.scalar_one_or_none()
            
            queue_data.append({
                "delivery_order_id": str(do.id),
                "delivery_number": do.delivery_number,
                "sales_order_id": str(do.sales_order_id) if do.sales_order_id else None,
                "sales_order_number": sales_order.order_number if sales_order else None,
                "status": do.status,
                "client_id": str(do.client_id) if do.client_id else None,
                "tracking_number": do.tracking_number,
                "shipped_at": do.shipped_at.isoformat() if do.shipped_at else None,
                "estimated_delivery": do.estimated_delivery.isoformat() if hasattr(do, 'estimated_delivery') and do.estimated_delivery else None,
            })
        
        return queue_data
    
    async def _get_completed_queue(self, tenant_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get recently completed deliveries (last 30 days)."""
        
        since = datetime.now(timezone.utc) - timedelta(days=30)
        
        stmt = select(DeliveryOrderModel).where(
            and_(
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.status == "DELIVERED",
                DeliveryOrderModel.delivery_date >= since,
                DeliveryOrderModel.is_deleted.is_(False),
            )
        ).order_by(DeliveryOrderModel.delivery_date.desc()).limit(20)
        
        result = await self.session.execute(stmt)
        delivery_orders = result.scalars().all()
        
        queue_data = []
        for do in delivery_orders:
            sales_order = None
            if do.sales_order_id:
                so_stmt = select(SalesOrderModel).where(
                    SalesOrderModel.id == do.sales_order_id,
                    SalesOrderModel.is_deleted.is_(False),
                )
                so_result = await self.session.execute(so_stmt)
                sales_order = so_result.scalar_one_or_none()
            
            queue_data.append({
                "delivery_order_id": str(do.id),
                "delivery_number": do.delivery_number,
                "sales_order_id": str(do.sales_order_id) if do.sales_order_id else None,
                "sales_order_number": sales_order.order_number if sales_order else None,
                "status": do.status,
                "client_id": str(do.client_id) if do.client_id else None,
                "delivery_date": do.delivery_date.isoformat() if do.delivery_date else None,
            })
        
        return queue_data
    
    async def _get_delivery_metrics(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        """Get delivery performance metrics."""
        
        # Total deliveries this month
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        total_deliveries_stmt = select(func.count(DeliveryOrderModel.id)).where(
            and_(
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.status == "DELIVERED",
                DeliveryOrderModel.delivery_date >= month_start,
                DeliveryOrderModel.is_deleted.is_(False),
            )
        )
        
        total_deliveries = (await self.session.execute(total_deliveries_stmt)).scalar() or 0
        
        # Pending dispatch
        pending_dispatch_stmt = select(func.count(DeliveryOrderModel.id)).where(
            and_(
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.status.in_(["READY_TO_SHIP", "PACKING"]),
                DeliveryOrderModel.is_deleted.is_(False),
            )
        )
        
        pending_dispatch = (await self.session.execute(pending_dispatch_stmt)).scalar() or 0
        
        # In transit
        in_transit_stmt = select(func.count(DeliveryOrderModel.id)).where(
            and_(
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.status == "IN_TRANSIT",
                DeliveryOrderModel.is_deleted.is_(False),
            )
        )
        
        in_transit = (await self.session.execute(in_transit_stmt)).scalar() or 0
        
        # Overdue deliveries
        overdue_stmt = select(func.count(DeliveryOrderModel.id)).where(
            and_(
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.status == "IN_TRANSIT",
                DeliveryOrderModel.estimated_delivery < datetime.now(timezone.utc).date(),
                DeliveryOrderModel.is_deleted.is_(False),
            )
        )
        
        overdue = (await self.session.execute(overdue_stmt)).scalar() or 0
        
        return {
            "total_deliveries_this_month": total_deliveries,
            "pending_dispatch": pending_dispatch,
            "in_transit": in_transit,
            "overdue_deliveries": overdue,
        }
    
    async def dispatch_order(
        self,
        tenant_id: uuid.UUID,
        delivery_order_id: uuid.UUID,
        tracking_number: str,
        dispatched_by: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Dispatch a delivery order.
        
        Transition: READY_TO_SHIP → IN_TRANSIT
        Action: Update delivery order status, trigger sales order SHIPPED status
        """
        stmt = select(DeliveryOrderModel).where(
            and_(
                DeliveryOrderModel.id == delivery_order_id,
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.is_deleted.is_(False),
            )
        )
        
        result = await self.session.execute(stmt)
        do = result.scalar_one_or_none()
        
        if not do:
            raise ValueError(f"Delivery order {delivery_order_id} not found")
        
        if do.status not in ["READY_TO_SHIP", "PACKING"]:
            raise ValueError(f"Cannot dispatch order in {do.status} status")
        
        do.status = "IN_TRANSIT"
        do.shipped_at = datetime.now(timezone.utc)
        do.tracking_number = tracking_number
        do.updated_at = datetime.now(timezone.utc)
        
        # Update linked sales order to SHIPPED if exists
        if do.sales_order_id:
            so_stmt = select(SalesOrderModel).where(
                and_(
                    SalesOrderModel.id == do.sales_order_id,
                    SalesOrderModel.tenant_id == tenant_id,
                    SalesOrderModel.is_deleted.is_(False),
                )
            )
            so_result = await self.session.execute(so_stmt)
            sales_order = so_result.scalar_one_or_none()
            if sales_order and sales_order.status not in ("SHIPPED", "DELIVERED", "INVOICED", "PAYMENT_RECEIVED", "COMPLETED"):
                sales_order.status = "SHIPPED"
                sales_order.updated_at = datetime.now(timezone.utc)
        
        return {
            "delivery_order_id": str(delivery_order_id),
            "status": do.status,
            "tracking_number": tracking_number,
            "message": "Order dispatched successfully",
        }
    
    async def confirm_delivery(
        self,
        tenant_id: uuid.UUID,
        delivery_order_id: uuid.UUID,
        delivery_notes: str,
        confirmed_by: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Confirm delivery of an order.
        
        Transition: IN_TRANSIT → DELIVERED
        Action: Update delivery order status, trigger sales order DELIVERED status
        """
        stmt = select(DeliveryOrderModel).where(
            and_(
                DeliveryOrderModel.id == delivery_order_id,
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.is_deleted.is_(False),
            )
        )
        
        result = await self.session.execute(stmt)
        do = result.scalar_one_or_none()
        
        if not do:
            raise ValueError(f"Delivery order {delivery_order_id} not found")
        
        if do.status != "IN_TRANSIT":
            raise ValueError(f"Cannot confirm delivery for order in {do.status} status")
        
        do.status = "DELIVERED"
        do.delivery_date = datetime.now(timezone.utc)
        do.remarks = delivery_notes
        do.updated_at = datetime.now(timezone.utc)
        
        # Update linked sales order to DELIVERED, then trigger auto-invoice (Gap #7)
        if do.sales_order_id:
            so_stmt = select(SalesOrderModel).where(
                and_(
                    SalesOrderModel.id == do.sales_order_id,
                    SalesOrderModel.tenant_id == tenant_id,
                    SalesOrderModel.is_deleted.is_(False),
                )
            )
            so_result = await self.session.execute(so_stmt)
            sales_order = so_result.scalar_one_or_none()
            if sales_order and sales_order.status not in ("DELIVERED", "INVOICED", "PAYMENT_RECEIVED", "COMPLETED"):
                sales_order.status = "DELIVERED"
                sales_order.updated_at = datetime.now(timezone.utc)
            # Flush so on_order_delivered sees SO in DELIVERED state
            await self.session.flush()
            # Trigger auto-invoice via WorkflowOrchestrationService (Req 36.3, 37.1–37.5)
            await self.workflow_service.on_order_delivered(
                tenant_id=tenant_id,
                sales_order_id=do.sales_order_id,
            )
        
        return {
            "delivery_order_id": str(delivery_order_id),
            "status": do.status,
            "delivery_date": do.delivery_date.isoformat(),
            "message": "Delivery confirmed successfully",
        }
