"""
Manager Workspace Service - Operational Dashboard for Managers

Provides operational queue-first dashboard for managers with:
- Pending approvals (sales orders, purchase orders)
- Work order monitoring
- Production capacity overview
- Critical alerts (shortages, delays, quality issues)
- Team workload distribution
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from decimal import Decimal

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel
from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.quality_model import (
    QualityInspectionModel,
    NonConformanceReportModel,
)

logger = logging.getLogger(__name__)


class ManagerService:
    """
    Service for Manager operational workspace.
    
    Provides queue-first dashboard with actionable items for managers.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_manager_dashboard(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get comprehensive manager dashboard with all operational queues.
        
        Returns:
        - Pending approvals queue
        - Work order monitoring
        - Production capacity
        - Critical alerts
        - Team workload
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pending_approvals": await self._get_pending_approvals(tenant_id, user_id),
            "work_orders": await self._get_work_order_monitoring(tenant_id),
            "production_capacity": await self._get_production_capacity(tenant_id),
            "critical_alerts": await self._get_critical_alerts(tenant_id),
            "team_workload": await self._get_team_workload(tenant_id),
        }
    
    async def _get_pending_approvals(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Get pending approvals queue for managers."""
        
        # Pending Sales Orders
        pending_so_stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.status == "PENDING_APPROVAL",
                SalesOrderModel.is_deleted.is_(False),
            )
        ).order_by(SalesOrderModel.submitted_at.asc()).limit(10)
        
        pending_so_result = await self.session.execute(pending_so_stmt)
        pending_sales_orders = pending_so_result.scalars().all()
        
        # Pending Purchase Orders
        pending_po_stmt = select(PurchaseOrderModel).where(
            and_(
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.status.in_(["draft", "pending"]),
                PurchaseOrderModel.is_deleted.is_(False),
            )
        ).order_by(PurchaseOrderModel.created_at.desc()).limit(10)
        
        pending_po_result = await self.session.execute(pending_po_stmt)
        pending_purchase_orders = pending_po_result.scalars().all()
        
        return {
            "sales_orders": [
                {
                    "id": str(so.id),
                    "order_number": so.order_number,
                    "client_id": str(so.client_id),
                    "grand_total": float(so.grand_total or 0),
                    "submitted_at": so.submitted_at.isoformat() if so.submitted_at else None,
                    "created_by": str(so.created_by),
                }
                for so in pending_sales_orders
            ],
            "purchase_orders": [
                {
                    "id": str(po.id),
                    "po_number": po.po_number,
                    "supplier_id": str(po.supplier_id),
                    "total_amount": float(po.total_amount or 0),
                    "created_at": po.created_at.isoformat() if po.created_at else None,
                    "created_by": str(po.created_by),
                }
                for po in pending_purchase_orders
            ],
            "total_pending": len(pending_sales_orders) + len(pending_purchase_orders),
        }
    
    async def _get_work_order_monitoring(
        self,
        tenant_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Get work order monitoring data."""
        
        # WO status distribution
        wo_status_stmt = select(
            WorkOrderModel.status,
            func.count(WorkOrderModel.id).label("count")
        ).where(
            and_(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        ).group_by(WorkOrderModel.status)
        
        wo_status_result = await self.session.execute(wo_status_stmt)
        wo_by_status = {row[0]: row[1] for row in wo_status_result}
        
        # WOs overdue
        overdue_stmt = select(func.count(WorkOrderModel.id)).where(
            and_(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.due_date < datetime.now(timezone.utc).date(),
                WorkOrderModel.status.in_(["PLANNED", "RELEASED", "MATERIAL_PENDING", "MATERIAL_RESERVED", "MATERIAL_ISSUED", "IN_PRODUCTION"]),
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        
        overdue_count = (await self.session.execute(overdue_stmt)).scalar() or 0
        
        # WOs starting soon (next 7 days)
        soon_start = datetime.now(timezone.utc).date() + timedelta(days=7)
        soon_stmt = select(func.count(WorkOrderModel.id)).where(
            and_(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.start_date <= soon_start,
                WorkOrderModel.start_date >= datetime.now(timezone.utc).date(),
                WorkOrderModel.status == "PLANNED",
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        
        soon_count = (await self.session.execute(soon_stmt)).scalar() or 0
        
        return {
            "by_status": wo_by_status,
            "total": sum(wo_by_status.values()),
            "overdue": overdue_count,
            "starting_soon": soon_count,
        }
    
    async def _get_production_capacity(
        self,
        tenant_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Get production capacity overview."""
        
        # Active WOs
        active_wo_stmt = select(
            func.count(WorkOrderModel.id),
            func.sum(WorkOrderModel.planned_quantity),
            func.sum(WorkOrderModel.produced_quantity),
        ).where(
            and_(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.status.in_(["MATERIAL_ISSUED", "IN_PRODUCTION"]),
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        
        active_result = await self.session.execute(active_wo_stmt)
        active_count, planned_total, produced_total = active_result.one()
        
        # Capacity utilization (simple metric)
        capacity_utilization = 0
        if planned_total and planned_total > 0:
            capacity_utilization = (produced_total / planned_total * 100) if produced_total else 0
        
        return {
            "active_work_orders": active_count or 0,
            "planned_quantity": float(planned_total or 0),
            "produced_quantity": float(produced_total or 0),
            "capacity_utilization": round(capacity_utilization, 1),
        }
    
    async def _get_critical_alerts(
        self,
        tenant_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Get critical alerts for managers."""
        
        # Material shortages
        shortage_stmt = select(
            MaterialModel.id,
            MaterialModel.code,
            MaterialModel.name,
            MaterialModel.current_stock,
            MaterialModel.reorder_level,
        ).where(
            and_(
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.reorder_level.isnot(None),
                MaterialModel.current_stock <= MaterialModel.reorder_level,
                MaterialModel.is_deleted.is_(False),
            )
        ).limit(10)
        
        shortage_result = await self.session.execute(shortage_stmt)
        shortages = [
            {
                "material_id": str(row[0]),
                "code": row[1],
                "name": row[2],
                "current_stock": float(row[3]),
                "reorder_level": float(row[4]),
            }
            for row in shortage_result
        ]
        
        # Recent QC rejections (last 7 days)
        since = datetime.now(timezone.utc) - timedelta(days=7)
        rejected_stmt = select(
            QualityInspectionModel.id,
            QualityInspectionModel.work_order_id,
            QualityInspectionModel.inspection_date,
        ).where(
            and_(
                QualityInspectionModel.tenant_id == tenant_id,
                QualityInspectionModel.result == "REJECTED",
                QualityInspectionModel.inspection_date >= since,
            )
        ).limit(10)
        
        rejected_result = await self.session.execute(rejected_stmt)
        rejections = [
            {
                "inspection_id": str(row[0]),
                "work_order_id": str(row[1]),
                "inspection_date": row[2].isoformat() if row[2] else None,
            }
            for row in rejected_result
        ]
        
        # Open NCRs
        ncr_stmt = select(func.count(NonConformanceReportModel.id)).where(
            and_(
                NonConformanceReportModel.tenant_id == tenant_id,
                NonConformanceReportModel.status.in_(["OPEN", "UNDER_REVIEW"]),
            )
        )
        
        ncr_count = (await self.session.execute(ncr_stmt)).scalar() or 0
        
        return {
            "material_shortages": shortages,
            "shortage_count": len(shortages),
            "qc_rejections": rejections,
            "rejection_count": len(rejections),
            "open_ncrs": ncr_count,
        }
    
    async def _get_team_workload(
        self,
        tenant_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Get team workload distribution."""
        
        # WOs by assigned user (simplified - using created_by for now)
        workload_stmt = select(
            WorkOrderModel.created_by,
            func.count(WorkOrderModel.id).label("count"),
        ).where(
            and_(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.status.in_(["RELEASED", "MATERIAL_PENDING", "MATERIAL_RESERVED", "MATERIAL_ISSUED", "IN_PRODUCTION"]),
                WorkOrderModel.is_deleted.is_(False),
            )
        ).group_by(WorkOrderModel.created_by)
        
        workload_result = await self.session.execute(workload_stmt)
        
        return {
            "by_user": [
                {
                    "user_id": str(row[0]),
                    "active_work_orders": row[1],
                }
                for row in workload_result
            ]
        }
