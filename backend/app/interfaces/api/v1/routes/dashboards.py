"""
Role-based dashboard endpoints providing KPI views for each user role.

Dashboards are role-specific and tenant-scoped:
- Admin: System-wide KPIs
- Supplier: Self-only purchase orders and quotations
- Storekeeper: Inventory management KPIs
- Worker: Work order tracking
- Client: Sales order tracking and delivery status
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, func
from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel
from backend.app.infrastructure.persistence.models.grn_model import GoodsReceiptNoteModel
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.models.sales_models import ClientModel, SalesOrderModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel as InventoryModel
from backend.app.infrastructure.persistence.models.quality_model import (
    NonConformanceReportModel,
    QualityInspectionModel,
    SupplierQuotationModel,
)
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.user_model import UserModel

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_role,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.application.rbac.service import get_effective_role_permissions
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission

router = APIRouter(tags=["Dashboards"])


@router.get(
    "/dashboards/admin",
    dependencies=[Depends(require_permission("admin:read"))],
)
@router.get(
    "/dashboard/admin",
    dependencies=[Depends(require_permission("admin:read"))],
    include_in_schema=False,
)
async def admin_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """
    Admin system-wide KPI dashboard.
    
    Shows:
    - Purchase order metrics (count by status)
    - GRN reception metrics
    - Inventory levels and alerts
    - Work order status distribution
    - Sales order status distribution
    - Production completion percentage
    """
    container = get_container(request)
    async with container.session_factory() as session:
        # PO metrics
        po_stmt = select(
            PurchaseOrderModel.status,
            func.count(PurchaseOrderModel.id).label("count")
        ).where(
            PurchaseOrderModel.tenant_id == tenant_id,
            PurchaseOrderModel.is_deleted.is_(False),
        ).group_by(PurchaseOrderModel.status)
        
        po_result = await session.execute(po_stmt)
        po_by_status = {row[0]: row[1] for row in po_result}
        total_pos = sum(po_by_status.values())
        
        # GRN metrics
        grn_stmt = select(func.count(GoodsReceiptNoteModel.id)).where(
            GoodsReceiptNoteModel.tenant_id == tenant_id,
            GoodsReceiptNoteModel.is_deleted.is_(False),
        )
        grn_count = (await session.execute(grn_stmt)).scalar() or 0
        
        # Inventory metrics (low stock alerts)
        low_stock_stmt = select(func.count(MaterialModel.id)).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.reorder_level.isnot(None),
            MaterialModel.current_stock <= MaterialModel.reorder_level,
            MaterialModel.is_deleted.is_(False),
        )
        low_stock_count = (await session.execute(low_stock_stmt)).scalar() or 0
        
        # WO metrics
        wo_stmt = select(
            WorkOrderModel.status,
            func.count(WorkOrderModel.id).label("count")
        ).where(
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        ).group_by(WorkOrderModel.status)
        
        wo_result = await session.execute(wo_stmt)
        wo_by_status = {row[0]: row[1] for row in wo_result}
        total_wos = sum(wo_by_status.values())
        
        # SO metrics
        so_stmt = select(
            SalesOrderModel.status,
            func.count(SalesOrderModel.id).label("count")
        ).where(
            SalesOrderModel.tenant_id == tenant_id,
            SalesOrderModel.is_deleted.is_(False),
        ).group_by(SalesOrderModel.status)
        
        so_result = await session.execute(so_stmt)
        so_by_status = {row[0]: row[1] for row in so_result}
        total_sos = sum(so_by_status.values())

        revenue = await session.scalar(
            select(func.coalesce(func.sum(SalesOrderModel.grand_total), 0)).where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.status.in_(["DELIVERED", "COMPLETED"]),
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        open_orders = await session.scalar(
            select(func.count(SalesOrderModel.id)).where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.status.in_(
                    ["PENDING_APPROVAL", "APPROVED", "CONFIRMED", "PRODUCTION", "READY", "SHIPPED"]
                ),
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        
        # Production completion %
        completed_wos = wo_by_status.get("COMPLETED", 0)
        production_completion_pct = (
            (completed_wos / total_wos * 100) if total_wos > 0 else 0
        )
        
        # Total inventory value (estimated)
        inv_value_stmt = select(
            func.sum(InventoryModel.quantity * MaterialModel.current_cost)
        ).join(
            MaterialModel, InventoryModel.material_id == MaterialModel.id
        ).where(
            MaterialModel.tenant_id == tenant_id,
            InventoryModel.is_deleted.is_(False),
        )
        
        inv_value = (await session.execute(inv_value_stmt)).scalar() or Decimal("0")
    
    return {
        "dashboard_type": "admin",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "purchase_orders": {
            "total": total_pos,
            "by_status": po_by_status,
        },
        "goods_receipts": {
            "total": grn_count,
        },
        "inventory": {
            "low_stock_alerts": low_stock_count,
            "estimated_value": float(inv_value),
        },
        "revenue": float(revenue or 0),
        "open_orders": int(open_orders or 0),
        "open_work_orders": int(total_wos - completed_wos),
        "production_target_progress": round(production_completion_pct, 1),
        "work_orders": {
            "total": total_wos,
            "by_status": wo_by_status,
            "completion_percentage": round(production_completion_pct, 1),
        },
        "sales_orders": {
            "total": total_sos,
            "by_status": so_by_status,
        },
    }


@router.get(
    "/dashboards/supplier",
    dependencies=[Depends(require_permission("supplier:read"))],
)
@router.get(
    "/dashboard/supplier",
    dependencies=[Depends(require_permission("supplier:read"))],
    include_in_schema=False,
)
async def supplier_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Supplier portal dashboard.
    
    Shows:
    - My purchase orders (filtered by supplier_id from JWT)
    - My quotations by status
    - My performance rating
    - Quotes awaiting response
    """
    container = get_container(request)
    async with container.session_factory() as session:
        # Get user's supplier_id
        user = await session.get(UserModel, user_id)
        if not user or user.supplier_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User must be associated with a supplier",
            )
        
        supplier_id = user.supplier_id
        
        # My POs
        po_stmt = select(
            PurchaseOrderModel.status,
            func.count(PurchaseOrderModel.id).label("count")
        ).where(
            PurchaseOrderModel.tenant_id == tenant_id,
            PurchaseOrderModel.supplier_id == supplier_id,
            PurchaseOrderModel.is_deleted.is_(False),
        ).group_by(PurchaseOrderModel.status)
        
        po_result = await session.execute(po_stmt)
        po_by_status = {row[0]: row[1] for row in po_result}
        total_pos = sum(po_by_status.values())
        
        # My quotations
        quotation_stmt = select(
            SupplierQuotationModel.status,
            func.count(SupplierQuotationModel.id).label("count")
        ).where(
            SupplierQuotationModel.tenant_id == tenant_id,
            SupplierQuotationModel.supplier_id == supplier_id,
            SupplierQuotationModel.is_deleted.is_(False),
        ).group_by(SupplierQuotationModel.status)
        
        quotation_result = await session.execute(quotation_stmt)
        quotation_by_status = {row[0]: row[1] for row in quotation_result}
        total_quotations = sum(quotation_by_status.values())
        
        # Pending quotations (DRAFT or SUBMITTED)
        pending_quotations = (
            quotation_by_status.get("DRAFT", 0) +
            quotation_by_status.get("SUBMITTED", 0)
        )
        
        # Supplier performance rating
        supplier = await session.get(SupplierModel, supplier_id)
        supplier_rating = supplier.performance_rating if supplier else None
    
    return {
        "dashboard_type": "supplier",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "purchase_orders": {
            "total": total_pos,
            "by_status": po_by_status,
        },
        "quotations": {
            "total": total_quotations,
            "by_status": quotation_by_status,
            "pending_action": pending_quotations,
        },
        "performance": {
            "rating": supplier_rating,
        },
    }


@router.get(
    "/dashboards/manager",
    dependencies=[Depends(require_permission("sales:approve_order"))],
)
@router.get(
    "/dashboard/manager",
    dependencies=[Depends(require_permission("sales:approve_order"))],
    include_in_schema=False,
)
async def manager_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
):
    """Manager operational workspace dashboard with queue-first design."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.manufacturing.services.manager_service import ManagerService
        manager_service = ManagerService(session)
        
        # Get comprehensive manager dashboard
        dashboard_data = await manager_service.get_manager_dashboard(
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        # Add legacy pending approvals for backward compatibility
        pending_query = select(SalesOrderModel).where(
            SalesOrderModel.tenant_id == tenant_id,
            SalesOrderModel.status == "PENDING_APPROVAL",
            SalesOrderModel.is_deleted.is_(False),
        )
        effective_role = await get_effective_role_permissions(session, tenant_id, role)
        if not effective_role.has_all:
            pending_query = pending_query.where(
                (SalesOrderModel.approver_id == user_id) | (SalesOrderModel.approver_id.is_(None))
            )

        pending_orders = (
            await session.execute(
                pending_query.order_by(SalesOrderModel.submitted_at.asc()).limit(25)
            )
        ).scalars().all()

        dashboard_data["legacy_pending_approvals"] = {
            "count": len(pending_orders),
            "items": [
                {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "client_id": str(order.client_id),
                    "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                    "grand_total": float(order.grand_total or 0),
                }
                for order in pending_orders
            ],
        }

    return dashboard_data


@router.get(
    "/dashboards/planner",
    dependencies=[Depends(require_permission("manufacturing:read"))],
)
@router.get(
    "/dashboard/planner",
    dependencies=[Depends(require_permission("manufacturing:read"))],
    include_in_schema=False,
)
async def planner_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Planner dashboard with open work orders, capacity load, and MRP-style shortage signals."""
    container = get_container(request)
    async with container.session_factory() as session:
        wo_result = await session.execute(
            select(WorkOrderModel.status, func.count(WorkOrderModel.id))
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
            .group_by(WorkOrderModel.status)
        )
        wo_by_status = {row[0]: row[1] for row in wo_result}
        open_work_orders = sum(
            wo_by_status.get(status_key, 0)
            for status_key in ["DRAFT", "PLANNED", "RELEASED", "IN_PROGRESS", "ON_HOLD"]
        )
        completed = wo_by_status.get("COMPLETED", 0)
        total = open_work_orders + completed

        shortages = await session.scalar(
            select(func.count(MaterialModel.id)).where(
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.current_stock <= MaterialModel.reorder_level,
                MaterialModel.is_deleted.is_(False),
            )
        )

        open_pos = await session.scalar(
            select(func.count(PurchaseOrderModel.id)).where(
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.status.in_(["draft", "sent", "acknowledged", "partial", "partially_received"]),
                PurchaseOrderModel.is_deleted.is_(False),
            )
        )

    return {
        "dashboard_type": "planner",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "open_work_orders": int(open_work_orders),
        "capacity_load": round((open_work_orders / total * 100), 1) if total else 0,
        "mrp_suggestions": {
            "shortage_items": int(shortages or 0),
            "open_purchase_orders": int(open_pos or 0),
        },
        "work_orders": wo_by_status,
    }


@router.get(
    "/dashboards/sales",
    dependencies=[Depends(require_permission("sales:read"))],
)
@router.get(
    "/dashboard/sales",
    dependencies=[Depends(require_permission("sales:read"))],
    include_in_schema=False,
)
async def sales_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Sales dashboard with approvals, monthly sales value, and top clients."""
    container = get_container(request)
    since = datetime.now(timezone.utc) - timedelta(days=30)
    async with container.session_factory() as session:
        pending_approvals = await session.scalar(
            select(func.count(SalesOrderModel.id)).where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.status == "PENDING_APPROVAL",
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        monthly_sales = await session.scalar(
            select(func.coalesce(func.sum(SalesOrderModel.grand_total), 0)).where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.status.in_(["APPROVED", "CONFIRMED", "READY", "SHIPPED", "DELIVERED", "COMPLETED"]),
                SalesOrderModel.created_at >= since,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        top_result = await session.execute(
            select(
                ClientModel.id,
                ClientModel.name,
                func.coalesce(func.sum(SalesOrderModel.grand_total), 0).label("sales_value"),
            )
            .join(SalesOrderModel, SalesOrderModel.client_id == ClientModel.id)
            .where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
            .group_by(ClientModel.id, ClientModel.name)
            .order_by(func.coalesce(func.sum(SalesOrderModel.grand_total), 0).desc())
            .limit(10)
        )

    return {
        "dashboard_type": "sales",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pending_approvals": int(pending_approvals or 0),
        "monthly_sales": float(monthly_sales or 0),
        "top_clients": [
            {"client_id": str(row[0]), "name": row[1], "sales_value": float(row[2] or 0)}
            for row in top_result
        ],
    }


@router.get(
    "/dashboards/qc",
    dependencies=[Depends(require_permission("quality:read"))],
)
@router.get(
    "/dashboard/qc",
    dependencies=[Depends(require_permission("quality:read"))],
    include_in_schema=False,
)
async def qc_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Operational QC dashboard with actionable queues.
    
    Shows:
    - Inspection queue (WOs in QC_PENDING awaiting inspection)
    - Rejected queue (WOs in QC_REJECTED awaiting disposition)
    - Rework queue (WOs in REWORK awaiting re-inspection)
    - Inspection statistics
    """
    container = get_container(request)
    since = datetime.now(timezone.utc) - timedelta(days=30)
    async with container.session_factory() as session:
        from backend.app.application.quality.services.qc_service import QCService
        qc_service = QCService(session)
        
        # Get operational queues
        inspection_queue = await qc_service.get_inspection_queue(tenant_id=tenant_id)
        rejected_queue = await qc_service.get_rejected_queue(tenant_id=tenant_id)
        rework_queue = await qc_service.get_rework_queue(tenant_id=tenant_id)
        
        # Inspection statistics
        inspection_result = await session.execute(
            select(QualityInspectionModel.result, func.count(QualityInspectionModel.id))
            .where(QualityInspectionModel.tenant_id == tenant_id)
            .group_by(QualityInspectionModel.result)
        )
        inspections_by_result = {row[0]: row[1] for row in inspection_result}
        ncrs_this_month = await session.scalar(
            select(func.count(NonConformanceReportModel.id)).where(
                NonConformanceReportModel.tenant_id == tenant_id,
                NonConformanceReportModel.created_at >= since,
            )
        )

    return {
        "dashboard_type": "qc",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queues": {
            "inspection": {
                "count": len(inspection_queue),
                "items": inspection_queue[:10],  # Top 10
            },
            "rejected": {
                "count": len(rejected_queue),
                "items": rejected_queue[:10],
            },
            "rework": {
                "count": len(rework_queue),
                "items": rework_queue[:10],
            },
        },
        "stats": {
            "pending_inspections": len(inspection_queue),
            "awaiting_disposition": len(rejected_queue),
            "in_rework": len(rework_queue),
            "ncrs_this_month": int(ncrs_this_month or 0),
            "inspections_by_result": inspections_by_result,
        },
    }


@router.get("/dashboards/storekeeper")
@router.get("/dashboard/storekeeper", include_in_schema=False)
async def storekeeper_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """
    Storekeeper inventory management dashboard.
    
    Shows:
    - Pending GRNs to receive
    - Stock levels and low stock alerts
    - Recent inventory transactions
    - Material requests pending fulfillment
    """
    container = get_container(request)
    async with container.session_factory() as session:
        # Pending GRNs (received but not fully processed)
        pending_grns_stmt = select(func.count(GoodsReceiptNoteModel.id)).where(
            GoodsReceiptNoteModel.tenant_id == tenant_id,
            GoodsReceiptNoteModel.status.in_(["draft", "pending"]),
            GoodsReceiptNoteModel.is_deleted.is_(False),
        )
        pending_grns = (await session.execute(pending_grns_stmt)).scalar() or 0
        
        # Low stock alerts
        low_stock_stmt = select(
            MaterialModel.id,
            MaterialModel.code,
            MaterialModel.name,
            MaterialModel.current_stock,
            MaterialModel.reorder_level,
        ).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.reorder_level.isnot(None),
            MaterialModel.current_stock <= MaterialModel.reorder_level,
            MaterialModel.is_deleted.is_(False),
        ).limit(10)
        
        low_stock_result = await session.execute(low_stock_stmt)
        low_stock_items = [
            {
                "material_id": str(row[0]),
                "code": row[1],
                "name": row[2],
                "current_stock": float(row[3]),
                "minimum_stock": float(row[4] or 0),
            }
            for row in low_stock_result
        ]
        
        # Total inventory value
        inv_value_stmt = select(
            func.sum(InventoryModel.quantity * MaterialModel.current_cost)
        ).join(
            MaterialModel, InventoryModel.material_id == MaterialModel.id
        ).where(
            MaterialModel.tenant_id == tenant_id,
            InventoryModel.is_deleted.is_(False),
        )
        
        inv_value = (await session.execute(inv_value_stmt)).scalar() or Decimal("0")
        
        # Total stock quantity
        total_stock_stmt = select(func.sum(InventoryModel.quantity)).where(
            InventoryModel.tenant_id == tenant_id,
            InventoryModel.is_deleted.is_(False),
        )
        total_stock = (await session.execute(total_stock_stmt)).scalar() or Decimal("0")

        open_pos = await session.scalar(
            select(func.count(PurchaseOrderModel.id)).where(
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.status.in_(["draft", "sent", "acknowledged", "partial", "partially_received"]),
                PurchaseOrderModel.is_deleted.is_(False),
            )
        )

        # Get operational queues using StorekeeperService with error handling
        try:
            from backend.app.application.inventory.services.storekeeper_service import StorekeeperService
            sk_service = StorekeeperService(session)
            issue_queue = await sk_service.get_issue_queue(tenant_id=tenant_id)
            shortage_queue = await sk_service.get_shortage_queue(tenant_id=tenant_id)
            partially_issued = await sk_service.get_partially_issued_wo(tenant_id=tenant_id)
        except Exception as e:
            # Log error but return empty queues to prevent dashboard failure
            from backend.app.infrastructure.logging.logger import get_logger
            logger = get_logger(__name__)
            logger.error("Failed to load storekeeper queues", extra={"error": str(e)})
            issue_queue = []
            shortage_queue = []
            partially_issued = []
    
        return {
            "dashboard_type": "storekeeper",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "queues": {
                "material_issues": {
                    "count": len(issue_queue),
                    "items": issue_queue[:10],
                },
                "shortages": {
                    "count": len(shortage_queue),
                    "items": shortage_queue[:10],
                },
                "partially_issued": {
                    "count": len(partially_issued),
                    "items": partially_issued[:10],
                },
            },
            "stats": {
                "grn_pending": pending_grns,
                "low_stock_count": len(low_stock_items),
                "low_stock_items": low_stock_items,
                "inventory_value": float(inv_value),
                "inventory_quantity": float(total_stock),
                "open_purchase_orders": int(open_pos or 0),
            },
        }


@router.get(
    "/dashboards/worker",
    dependencies=[Depends(require_permission("worker:read"))],
)
@router.get(
    "/dashboard/worker",
    dependencies=[Depends(require_permission("worker:read"))],
    include_in_schema=False,
)
async def worker_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """
    Worker shop floor dashboard.
    
    Shows:
    - Work orders by status
    - Work orders awaiting production
    - Scrap/defect summary
    - Production progress
    """
    container = get_container(request)
    async with container.session_factory() as session:
        # WO metrics
        wo_stmt = select(
            WorkOrderModel.status,
            func.count(WorkOrderModel.id).label("count")
        ).where(
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        ).group_by(WorkOrderModel.status)
        
        wo_result = await session.execute(wo_stmt)
        wo_by_status = {row[0]: row[1] for row in wo_result}
        
        # WOs ready to start (RELEASED status)
        ready_to_start = wo_by_status.get("RELEASED", 0)
        
        # In progress
        in_progress = wo_by_status.get("IN_PROGRESS", 0)
        
        # Recent WOs (last 10)
        recent_wos_stmt = select(
            WorkOrderModel.id,
            WorkOrderModel.wo_number,
            WorkOrderModel.status,
            WorkOrderModel.planned_quantity,
            WorkOrderModel.produced_quantity,
            WorkOrderModel.scrap_quantity,
        ).where(
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        ).order_by(
            WorkOrderModel.created_at.desc()
        ).limit(10)
        
        recent_result = await session.execute(recent_wos_stmt)
        recent_wos = [
            {
                "wo_id": str(row[0]),
                "wo_number": row[1],
                "status": row[2],
                "planned_quantity": float(row[3]),
                "produced_quantity": float(row[4]),
                "scrap_quantity": float(row[5]),
                "progress_pct": (
                    (float(row[4]) / float(row[3]) * 100) if float(row[3]) > 0 else 0
                ),
            }
            for row in recent_result
        ]
    
        # Get operational queue using ProductionExecutionService
        from backend.app.application.manufacturing.services.production_execution_service import ProductionExecutionService
        prod_service = ProductionExecutionService(session)
        # Note: worker queue requires user_id; we'll get all WOs in MATERIAL_ISSUED/IN_PRODUCTION
        worker_queue = await prod_service.get_worker_queue(
            tenant_id=tenant_id,
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # Get all assignable
        )
    
    return {
        "dashboard_type": "worker",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queues": {
            "assigned_operations": {
                "count": len(worker_queue),
                "items": worker_queue[:10],
            },
        },
        "stats": {
            "work_orders_by_status": wo_by_status,
            "ready_to_start": ready_to_start,
            "in_progress": in_progress,
            "awaiting_production": wo_by_status.get("MATERIAL_ISSUED", 0),
            "qc_pending": wo_by_status.get("QC_PENDING", 0),
            "recent_work_orders": recent_wos,
        },
    }


@router.get(
    "/dashboards/client",
    dependencies=[Depends(require_permission("client:read"))],
)
@router.get(
    "/dashboard/client",
    dependencies=[Depends(require_permission("client:read"))],
    include_in_schema=False,
)
async def client_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Client sales order dashboard.
    
    Shows:
    - Sales orders by status
    - Pending delivery
    - Shipment tracking
    - Order history
    """
    container = get_container(request)
    async with container.session_factory() as session:
        user = await session.get(UserModel, user_id)
        client_filter = []
        if user and user.client_id:
            client_filter.append(SalesOrderModel.client_id == user.client_id)

        # SO metrics
        so_stmt = select(
            SalesOrderModel.status,
            func.count(SalesOrderModel.id).label("count")
        ).where(
            SalesOrderModel.tenant_id == tenant_id,
            SalesOrderModel.is_deleted.is_(False),
            *client_filter,
        ).group_by(SalesOrderModel.status)
        
        so_result = await session.execute(so_stmt)
        so_by_status = {row[0]: row[1] for row in so_result}
        
        # Pending delivery once stock or production is ready.
        pending_delivery = so_by_status.get("CONFIRMED", 0) + so_by_status.get("READY", 0)
        
        # Shipped
        shipped = so_by_status.get("SHIPPED", 0)
        
        # Recent SOs (last 5)
        recent_sos_stmt = select(
            SalesOrderModel.id,
            SalesOrderModel.order_number,
            SalesOrderModel.status,
            SalesOrderModel.order_date,
            SalesOrderModel.delivery_date,
        ).where(
            SalesOrderModel.tenant_id == tenant_id,
            SalesOrderModel.is_deleted.is_(False),
            *client_filter,
        ).order_by(
            SalesOrderModel.created_at.desc()
        ).limit(5)
        
        recent_result = await session.execute(recent_sos_stmt)
        recent_sos = [
            {
                "so_id": str(row[0]),
                "so_number": row[1],
                "status": row[2],
                "order_date": str(row[3]) if row[3] else None,
                "expected_delivery": str(row[4]) if row[4] else None,
            }
            for row in recent_result
        ]
    
    return {
        "dashboard_type": "client",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sales_orders": so_by_status,
        "pending_delivery": pending_delivery,
        "shipped": shipped,
        "recent_orders": recent_sos,
    }
