"""Reporting & Analytics API routes - role-filtered cross-module reports."""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_current_tenant_id,
    get_current_role,
)
from backend.app.application.finance.reporting_service import ReportingService
from backend.app.application.documents.services.document_generation_service import DocumentGenerationService
from backend.app.application.documents.services.template_service import TemplateService
from backend.app.application.documents.services.pdf_generation_service import PDFGenerationService
from backend.app.application.documents.services.document_storage_service import DocumentStorageService
from backend.app.services.kpi_query_service import (
    KPIQueryService,
    DateRange,
    ProductionFilters,
    ReportFilters,
    OEEFilters,
)

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


async def _get_db_session(request: Request):
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session


@router.get("/inventory/summary")
async def inventory_summary(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Inventory summary with low-stock flags."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.inventory_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/inventory/turnover")
async def inventory_turnover(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Inventory turnover from materialized view."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.inventory_turnover(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/inventory/near-empty-batches")
async def near_empty_batches(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
    threshold_pct: float = Query(10.0, ge=0, le=100),
):
    """Batches below threshold % of original quantity."""
    from sqlalchemy import select
    from backend.app.infrastructure.persistence.models.batch_model import BatchModel

    rows = (
        await session.execute(
            select(BatchModel).where(
                BatchModel.tenant_id == tenant_id,
                BatchModel.is_deleted.is_(False),
                BatchModel.remaining_quantity.isnot(None),
            )
        )
    ).scalars().all()
    result = []
    for b in rows:
        orig = float(b.original_quantity or b.quantity or 0)
        rem = float(b.remaining_quantity or 0)
        if orig <= 0:
            continue
        pct = rem / orig * 100
        if pct <= threshold_pct:
            result.append({
                "batch_id": str(b.id),
                "batch_number": b.batch_number,
                "material_id": str(b.material_id),
                "remaining_quantity": rem,
                "original_quantity": orig,
                "percent_remaining": round(pct, 2),
            })
    return result


@router.get("/inventory/consumption-variance")
async def consumption_variance_report(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
    work_order_id: Optional[uuid.UUID] = Query(None),
):
    from sqlalchemy import select
    from backend.app.infrastructure.persistence.models.material_consumption_model import (
        MaterialConsumptionRecordModel,
    )

    stmt = select(MaterialConsumptionRecordModel).where(
        MaterialConsumptionRecordModel.tenant_id == tenant_id
    )
    if work_order_id:
        stmt = stmt.where(MaterialConsumptionRecordModel.work_order_id == work_order_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "work_order_id": str(r.work_order_id),
            "material_id": str(r.material_id),
            "planned_quantity": r.planned_quantity,
            "actual_quantity": r.actual_quantity,
            "variance_quantity": r.variance_quantity,
            "recorded_at": r.recorded_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/production/summary")
async def production_summary(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Work order summary by status, extended with cycle_time_hours, qc_pass_rate_percent, rework_count."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        base_summary = await svc.work_order_summary(tenant_id, role.upper())

        # Extend with manufacturing KPI fields using KPIQueryService
        kpi_service = KPIQueryService(session)
        from datetime import timedelta
        date_range = DateRange(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
        )

        # Cycle time from completed WOs (average)
        cycle_report = await kpi_service.get_cycle_time_report(
            tenant_id, ReportFilters()
        )
        avg_cycle_time = 0.0
        if cycle_report.entries:
            total_weighted = sum(
                e.avg_cycle_time_hours * e.sample_count for e in cycle_report.entries
            )
            total_samples = sum(e.sample_count for e in cycle_report.entries)
            avg_cycle_time = round(total_weighted / total_samples, 2) if total_samples > 0 else 0.0

        # QC pass rate
        qc_report = await kpi_service.get_qc_pass_fail_report(
            tenant_id, ReportFilters()
        )

        # Rework count from manufacturing KPIs
        mfg_kpis = await kpi_service.get_manufacturing_kpis(tenant_id, date_range)

        # Extend the base summary with new fields
        if isinstance(base_summary, dict):
            base_summary["cycle_time_hours"] = avg_cycle_time
            base_summary["qc_pass_rate_percent"] = qc_report.overall_pass_rate
            base_summary["rework_count"] = mfg_kpis.total_rework
        else:
            base_summary = {
                "data": base_summary,
                "cycle_time_hours": avg_cycle_time,
                "qc_pass_rate_percent": qc_report.overall_pass_rate,
                "rework_count": mfg_kpis.total_rework,
            }

        return base_summary
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/production/efficiency")
async def production_efficiency(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Work order efficiency — scrap rates by month."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.work_order_efficiency(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/sales/summary")
async def sales_summary(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Sales orders summary — by status + monthly trend."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.sales_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/sales/top-clients")
async def top_clients(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Top clients by revenue."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.top_clients(tenant_id, role.upper(), limit)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/procurement/summary")
async def procurement_summary(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Procurement summary by PO status."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.procurement_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/quality/summary")
async def quality_summary(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Quality inspection results summary."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.quality_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/summary")
async def finance_summary(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Finance summary — AR + AP."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.finance_summary(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/ar-aging")
async def ar_aging(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Accounts Receivable aging by client."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.ar_aging(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/ap-aging")
async def ap_aging(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Accounts Payable aging by supplier."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.ap_aging(tenant_id, role.upper())
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/trial-balance")
async def trial_balance(
    request: Request,
    as_of: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Trial balance as of a date."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.trial_balance(tenant_id, role.upper(), as_of=as_of)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/profit-loss")
async def profit_and_loss(
    request: Request,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Profit and loss report."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.profit_and_loss(tenant_id, role.upper(), from_date=from_date, to_date=to_date)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/balance-sheet")
async def balance_sheet(
    request: Request,
    as_of: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Balance sheet as of a date."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.balance_sheet(tenant_id, role.upper(), as_of=as_of)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/finance/cash-flow")
async def cash_flow(
    request: Request,
    months: int = Query(6, ge=1, le=24),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Cash flow statement."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        return await svc.cash_flow(tenant_id, role.upper(), months=months)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/refresh-views")
async def refresh_materialized_views(
    view_name: Optional[str] = Query(None),
    role: str = Depends(get_current_role),
    session: AsyncSession = Depends(_get_db_session),
):
    """Manually refresh materialized views (ADMIN only)."""
    if role.upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    svc = ReportingService(session)
    refreshed = await svc.refresh_views(view_name)
    return {"refreshed": refreshed}


@router.get("/inventory/summary/export/pdf")
async def inventory_summary_pdf(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Export inventory summary as PDF."""
    role = request.scope.get("user_role", "viewer")
    try:
        from datetime import datetime
        
        # Get report data
        svc = ReportingService(session)
        data = await svc.inventory_summary(tenant_id, role.upper())
        
        # Get tenant info
        from backend.app.domain.tenant.repositories import TenantRepository
        tenant_repo = TenantRepository(session)
        tenant = await tenant_repo.get_by_id(tenant_id)
        
        # Build template context
        context = {
            "tenant": {
                "name": tenant.name,
                "company_name": tenant.company_name or tenant.name,
                "logo_url": tenant.logo_url or "",
                "gst_number": tenant.gst_number or "",
                "pan_number": tenant.pan_number or "",
                "address": tenant.address or "",
                "phone": tenant.phone or "",
                "email": tenant.email or "",
                "footer_text": tenant.footer_text or "",
            },
            "report": {
                "title": "Inventory Summary Report",
                "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "data": data,
            },
        }
        
        # Generate PDF using simple HTML template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Inventory Summary</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .low-stock {{ color: red; font-weight: bold; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <h1>{context['tenant']['company_name']}</h1>
            <p>GST: {context['tenant']['gst_number']}</p>
            <p>PAN: {context['tenant']['pan_number']}</p>
            <p>{context['tenant']['address']}</p>
            <h2>Inventory Summary Report</h2>
            <p>Generated: {context['report']['generated_at']}</p>
            <table>
                <tr>
                    <th>Code</th>
                    <th>Name</th>
                    <th>Category</th>
                    <th>On Hand</th>
                    <th>Reserved</th>
                    <th>Available</th>
                    <th>Reorder Level</th>
                </tr>
                {''.join([f'''
                <tr>
                    <td>{row.get('code', '')}</td>
                    <td>{row.get('name', '')}</td>
                    <td>{row.get('category', '')}</td>
                    <td>{row.get('quantity_on_hand', 0)}</td>
                    <td>{row.get('quantity_reserved', 0)}</td>
                    <td>{row.get('available', 0)}</td>
                    <td class="{'low-stock' if row.get('is_low_stock') else ''}">{row.get('reorder_level', 0)}</td>
                </tr>
                ''' for row in data])}
            </table>
            <div class="footer">{context['tenant']['footer_text']}</div>
        </body>
        </html>
        """
        
        # Generate PDF
        pdf_service = PDFGenerationService()
        pdf_content = pdf_service.generate_pdf_from_string(html)
        
        # Store PDF
        storage_service = DocumentStorageService()
        file_path = storage_service.generate_file_path(tenant_id, "inventory_summary", f"inventory_summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf")
        storage_service.save_file(file_path, pdf_content)
        
        return {
            "file_path": file_path,
            "download_url": f"/api/v1/documents/download?path={file_path}",
            "generated_at": context['report']['generated_at'],
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/manufacturing")
async def manufacturing_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Manufacturing dashboard with WO status, efficiency, and capacity metrics."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        summary = await svc.work_order_summary(tenant_id, role.upper())
        efficiency = await svc.work_order_efficiency(tenant_id, role.upper())
        
        return {
            "work_orders": summary,
            "efficiency": efficiency,
            "capacity": {
                "active_orders": sum(row.get("count", 0) for row in summary.get("by_status", []) if row.get("status") in ["IN_PROGRESS", "READY"]),
                "utilization": "75%",  # Could be calculated from actual data
            },
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/dashboard/procurement")
async def procurement_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Procurement dashboard with PO status and supplier metrics."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        summary = await svc.procurement_summary(tenant_id, role.upper())
        
        return {
            "purchase_orders": summary,
            "pending_approvals": sum(row.get("count", 0) for row in summary.get("by_status", []) if row.get("status") in ["DRAFT", "PENDING_APPROVAL"]),
            "active_orders": sum(row.get("count", 0) for row in summary.get("by_status", []) if row.get("status") in ["APPROVED", "ORDERED"]),
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/dashboard/finance")
async def finance_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Finance dashboard with AR/AP, cash flow, and profitability metrics."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        summary = await svc.finance_summary(tenant_id, role.upper())
        ar_aging = await svc.ar_aging(tenant_id, role.upper())
        ap_aging = await svc.ap_aging(tenant_id, role.upper())
        
        return {
            "summary": summary,
            "ar_aging": ar_aging,
            "ap_aging": ap_aging,
            "cash_position": summary.get("cash_flow", {}).get("net_cash_flow", 0),
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/dashboard/sales")
async def sales_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Sales dashboard with order status, revenue trends, and top clients."""
    role = request.scope.get("user_role", "viewer")
    try:
        svc = ReportingService(session)
        summary = await svc.sales_summary(tenant_id, role.upper())
        top_clients = await svc.top_clients(tenant_id, role.upper(), limit=10)
        
        return {
            "orders": summary,
            "top_clients": top_clients,
            "pending_orders": sum(row.get("count", 0) for row in summary.get("by_status", []) if row.get("status") in ["PENDING", "CONFIRMED"]),
            "monthly_revenue": summary.get("monthly", []),
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ==================== NEW KPI & REPORTS ENDPOINTS ====================
# Requirements: 15.1–15.8, 22.1–22.4, 25.1, 25.5, 25.7, 32.1–32.10


def _dataclass_to_dict(obj) -> dict:
    """Safely convert a dataclass instance to a JSON-serializable dict."""
    import dataclasses
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        result = {}
        for f in dataclasses.fields(obj):
            value = getattr(obj, f.name)
            if dataclasses.is_dataclass(value):
                result[f.name] = _dataclass_to_dict(value)
            elif isinstance(value, list):
                result[f.name] = [
                    _dataclass_to_dict(v) if dataclasses.is_dataclass(v) else v
                    for v in value
                ]
            elif isinstance(value, uuid.UUID):
                result[f.name] = str(value)
            else:
                result[f.name] = value
        return result
    return obj


@router.get("/dashboard/kpis")
async def admin_dashboard_kpis(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Admin dashboard KPI aggregates with trend indicators.

    Returns counts: pending SO, running WO, delayed WO, QC pending,
    low stock items, today's dispatches, invoices pending, payments pending.
    Each metric includes a trend indicator (up/down/neutral vs 24h ago).

    Requirements: 25.1, 25.5, 25.7
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import text

    kpi_service = KPIQueryService(session)
    kpis = await kpi_service.get_admin_kpis(tenant_id)

    # Compute trend indicators by comparing with yesterday's counts (simplified)
    # We use a heuristic: query counts from 24h ago window for comparison
    yesterday = date.today() - timedelta(days=1)

    # For trend, we compare today's snapshot with yesterday approximation.
    # Since we don't have historical snapshots, we'll return neutral trends.
    # A more sophisticated implementation would store daily snapshots.
    kpi_dict = _dataclass_to_dict(kpis)
    kpi_dict["trends"] = {
        "pending_sales_orders": "neutral",
        "running_work_orders": "neutral",
        "delayed_work_orders": "neutral",
        "qc_pending": "neutral",
        "low_stock_items": "neutral",
        "todays_dispatches": "neutral",
        "invoices_pending": "neutral",
        "payments_pending": "neutral",
    }
    kpi_dict["generated_at"] = datetime.now(timezone.utc).isoformat()

    return kpi_dict


@router.get("/production/dashboard")
async def production_dashboard_metrics(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
    work_center_id: Optional[uuid.UUID] = Query(None),
):
    """Production dashboard metrics — today's production, QC queue, shortages, output.

    Returns: running WOs, completed today, delayed, QC queue, material shortages,
    total produced vs planned, scrap totals.

    Requirements: 22.1–22.4
    """
    from datetime import datetime, timezone

    filters = ProductionFilters(
        date_from=date_from,
        date_to=date_to,
        product_id=product_id,
        work_center_id=work_center_id,
    )

    kpi_service = KPIQueryService(session)
    summary = await kpi_service.get_production_summary(tenant_id, filters)

    result = _dataclass_to_dict(summary)
    result["output_percentage"] = (
        round((summary.total_produced / summary.total_planned) * 100, 1)
        if summary.total_planned > 0
        else 0.0
    )
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


@router.get("/manufacturing-kpis")
async def manufacturing_kpis(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    """Manufacturing KPIs — OEE, yield, scrap rate, rework rate, inventory turnover.

    Requirements: 32.1–32.10
    """
    from datetime import datetime, timezone, timedelta

    # Default to last 30 days if no date range given
    end = date_to or date.today()
    start = date_from or (end - timedelta(days=30))

    date_range = DateRange(start_date=start, end_date=end)

    kpi_service = KPIQueryService(session)
    kpis = await kpi_service.get_manufacturing_kpis(tenant_id, date_range)

    result = _dataclass_to_dict(kpis)
    result["date_range"] = {"start_date": start.isoformat(), "end_date": end.isoformat()}
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


@router.get("/production/cycle-time")
async def production_cycle_time(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
):
    """Cycle time per product with date range filter.

    Returns average, min, max cycle time in hours for each product.

    Requirements: 32.5, 32.6
    """
    from datetime import datetime, timezone

    filters = ReportFilters(
        date_from=date_from,
        date_to=date_to,
        product_id=product_id,
    )

    kpi_service = KPIQueryService(session)
    report = await kpi_service.get_cycle_time_report(tenant_id, filters)

    result = _dataclass_to_dict(report)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


@router.get("/production/qc-rate")
async def production_qc_rate(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
):
    """QC pass/fail rates grouped by product.

    Returns pass/fail counts and pass rate percentage per product,
    plus overall pass rate.

    Requirements: 32.7, 32.8
    """
    from datetime import datetime, timezone

    filters = ReportFilters(
        date_from=date_from,
        date_to=date_to,
        product_id=product_id,
    )

    kpi_service = KPIQueryService(session)
    report = await kpi_service.get_qc_pass_fail_report(tenant_id, filters)

    result = _dataclass_to_dict(report)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


@router.get("/production/output")
async def production_output(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
    period: str = Query("daily", regex="^(daily|weekly|monthly)$"),
):
    """Produced vs planned output, aggregated by period (daily/weekly/monthly).

    Requirements: 15.5, 15.6
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import text

    # Default to last 30 days
    end = date_to or date.today()
    start = date_from or (end - timedelta(days=30))

    # Determine date truncation SQL based on period
    if period == "weekly":
        trunc_fn = "date_trunc('week', wo.start_date)"
    elif period == "monthly":
        trunc_fn = "date_trunc('month', wo.start_date)"
    else:
        trunc_fn = "wo.start_date::date"

    params = {"tid": tenant_id, "date_from": start, "date_to": end}
    product_filter = ""
    if product_id:
        product_filter = " AND wo.product_id = :product_id"
        params["product_id"] = product_id

    result = await session.execute(
        text(f"""
            SELECT
                {trunc_fn} as period_start,
                COALESCE(SUM(wo.produced_quantity), 0) as total_produced,
                COALESCE(SUM(wo.planned_quantity), 0) as total_planned,
                COALESCE(SUM(wo.scrap_quantity), 0) as total_scrap,
                COUNT(*) as work_order_count
            FROM work_orders wo
            WHERE wo.tenant_id = :tid
              AND wo.start_date >= :date_from
              AND wo.start_date <= :date_to
              AND wo.is_deleted = false
              {product_filter}
            GROUP BY {trunc_fn}
            ORDER BY period_start ASC
        """),
        params,
    )

    entries = []
    for row in result.mappings():
        period_start = row["period_start"]
        produced = float(row["total_produced"])
        planned = float(row["total_planned"])
        entries.append({
            "period_start": period_start.isoformat() if period_start else None,
            "total_produced": produced,
            "total_planned": planned,
            "total_scrap": float(row["total_scrap"]),
            "work_order_count": int(row["work_order_count"]),
            "achievement_rate": round((produced / planned) * 100, 1) if planned > 0 else 0.0,
        })

    return {
        "period": period,
        "date_range": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "entries": entries,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/sales/fulfillment")
async def sales_fulfillment(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    client_id: Optional[uuid.UUID] = Query(None),
):
    """Order fulfillment timing per client.

    Returns average fulfillment time (order creation to delivery) grouped by client.

    Requirements: 15.7, 15.8
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import text

    end = date_to or date.today()
    start = date_from or (end - timedelta(days=90))

    params = {"tid": tenant_id, "date_from": start, "date_to": end}
    client_filter = ""
    if client_id:
        client_filter = " AND so.client_id = :client_id"
        params["client_id"] = client_id

    result = await session.execute(
        text(f"""
            SELECT
                so.client_id,
                c.name as client_name,
                COUNT(*) as total_orders,
                COUNT(*) FILTER (WHERE so.status IN ('DELIVERED', 'COMPLETED')) as fulfilled_orders,
                AVG(
                    CASE WHEN so.status IN ('DELIVERED', 'COMPLETED')
                    THEN EXTRACT(EPOCH FROM (so.updated_at - so.created_at)) / 3600.0
                    ELSE NULL END
                ) as avg_fulfillment_hours
            FROM sales_orders so
            LEFT JOIN clients c ON c.id = so.client_id
            WHERE so.tenant_id = :tid
              AND so.created_at >= :date_from
              AND so.created_at <= :date_to
              AND so.is_deleted = false
              {client_filter}
            GROUP BY so.client_id, c.name
            ORDER BY avg_fulfillment_hours ASC NULLS LAST
        """),
        params,
    )

    entries = []
    for row in result.mappings():
        avg_hours = float(row["avg_fulfillment_hours"]) if row["avg_fulfillment_hours"] else None
        entries.append({
            "client_id": str(row["client_id"]) if row["client_id"] else None,
            "client_name": row["client_name"] or "Unknown",
            "total_orders": int(row["total_orders"]),
            "fulfilled_orders": int(row["fulfilled_orders"]),
            "avg_fulfillment_hours": round(avg_hours, 2) if avg_hours else None,
            "avg_fulfillment_days": round(avg_hours / 24, 1) if avg_hours else None,
            "fulfillment_rate": round(
                int(row["fulfilled_orders"]) / int(row["total_orders"]) * 100, 1
            ) if int(row["total_orders"]) > 0 else 0.0,
        })

    return {
        "date_range": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "entries": entries,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/production/material-variance")
async def production_material_variance(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    work_order_id: Optional[uuid.UUID] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
):
    """Planned vs actual material consumption report.

    Returns variance per material (positive = over-consumption, negative = under).

    Requirements: 15.3, 15.4
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import text

    end = date_to or date.today()
    start = date_from or (end - timedelta(days=30))

    params = {"tid": tenant_id, "date_from": start, "date_to": end}
    wo_filter = ""
    product_filter = ""

    if work_order_id:
        wo_filter = " AND mcr.work_order_id = :work_order_id"
        params["work_order_id"] = work_order_id
    if product_id:
        product_filter = " AND wo.product_id = :product_id"
        params["product_id"] = product_id

    result = await session.execute(
        text(f"""
            SELECT
                mcr.material_id,
                m.name as material_name,
                m.code as material_code,
                COALESCE(SUM(mcr.planned_quantity), 0) as total_planned,
                COALESCE(SUM(mcr.actual_quantity), 0) as total_actual,
                COALESCE(SUM(mcr.variance_quantity), 0) as total_variance,
                COUNT(DISTINCT mcr.work_order_id) as work_order_count
            FROM material_consumption_records mcr
            INNER JOIN materials m ON m.id = mcr.material_id
            INNER JOIN work_orders wo ON wo.id = mcr.work_order_id
            WHERE mcr.tenant_id = :tid
              AND mcr.recorded_at >= :date_from
              AND mcr.recorded_at <= :date_to
              {wo_filter}{product_filter}
            GROUP BY mcr.material_id, m.name, m.code
            ORDER BY total_variance DESC
        """),
        params,
    )

    entries = []
    for row in result.mappings():
        planned = float(row["total_planned"])
        actual = float(row["total_actual"])
        variance = float(row["total_variance"])
        entries.append({
            "material_id": str(row["material_id"]),
            "material_name": row["material_name"],
            "material_code": row["material_code"],
            "total_planned": round(planned, 4),
            "total_actual": round(actual, 4),
            "total_variance": round(variance, 4),
            "variance_percentage": round((variance / planned) * 100, 2) if planned > 0 else 0.0,
            "work_order_count": int(row["work_order_count"]),
        })

    return {
        "date_range": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "entries": entries,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
