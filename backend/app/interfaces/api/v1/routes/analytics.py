"""Analytics & Advanced Reporting API routes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_current_tenant_id,
    get_current_user_id,
    get_current_role,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission

router = APIRouter(prefix="/analytics", tags=["Analytics & Reporting"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class ReportQueryConfigSchema(BaseModel):
    """Report query configuration."""
    metrics: list[str] = []
    filters: Dict[str, Any] = {}
    grouping: Optional[str] = None
    sort_by: Optional[str] = None
    sort_direction: str = "asc"
    limit: int = 1000


class CreateSavedReportRequest(BaseModel):
    """Request to create a saved report."""
    name: str
    description: Optional[str] = None
    report_type: str  # 'sales', 'production', 'inventory', 'finance'
    query_config: ReportQueryConfigSchema
    is_public: bool = False


class UpdateReportRequest(BaseModel):
    """Request to update a report."""
    name: Optional[str] = None
    description: Optional[str] = None
    query_config: Optional[ReportQueryConfigSchema] = None
    is_public: Optional[bool] = None


class SavedReportResponse(BaseModel):
    """Response for a saved report."""
    id: str
    name: str
    description: Optional[str]
    report_type: str
    query_config: ReportQueryConfigSchema
    is_public: bool
    created_by: str
    created_at: str
    updated_at: str


class ReportExecution(BaseModel):
    """Report execution result."""
    id: str
    report_id: str
    export_format: str
    status: str
    execution_time_ms: int
    row_count: int
    file_url: Optional[str]
    created_at: str


class DashboardSummary(BaseModel):
    """Dashboard summary with key metrics."""
    period: Dict[str, str]
    metrics: Dict[str, float]
    summary: Dict[str, Any]


# ============================================================================
# Endpoints: Saved Reports Management
# ============================================================================

@router.post("/reports", response_model=SavedReportResponse, dependencies=[Depends(require_permission("reports:read"))])
async def create_saved_report(
    request_body: CreateSavedReportRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
    request: Request = None,
):
    """Create a new saved report."""
    try:
        from backend.app.application.handlers.analytics.commands import CreateSavedReportCommand
        from backend.app.application.handlers.analytics.command_handlers import CreateSavedReportHandler

        container = request.app.state.container
        repository = container.analytics_repository
        handler = CreateSavedReportHandler(repository)

        command = CreateSavedReportCommand(
            tenant_id=tenant_id,
            created_by=user_id,
            name=request_body.name,
            description=request_body.description,
            report_type=request_body.report_type,
            query_config=request_body.query_config.dict(),
            is_public=request_body.is_public,
        )

        report = await handler.handle(command)

        return SavedReportResponse(
            id=str(report.id),
            name=report.name,
            description=report.description,
            report_type=report.report_type,
            query_config=ReportQueryConfigSchema(**report.query_config.to_dict()),
            is_public=report.is_public,
            created_by=str(report.created_by),
            created_at=report.created_at.isoformat(),
            updated_at=report.updated_at.isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports", response_model=list[SavedReportResponse])
async def list_saved_reports(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    is_public: Optional[bool] = Query(None),
    request: Request = None,
):
    """List saved reports for tenant."""
    try:
        from backend.app.application.handlers.analytics.queries import ListSavedReportsQuery
        from backend.app.application.handlers.analytics.query_handlers import ListSavedReportsHandler

        container = request.app.state.container
        repository = container.analytics_repository
        handler = ListSavedReportsHandler(repository)

        query = ListSavedReportsQuery(
            tenant_id=tenant_id,
            is_public=is_public,
        )

        reports = await handler.handle(query)
        return [SavedReportResponse(**r) for r in reports]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports/{report_id}", response_model=SavedReportResponse)
async def get_saved_report(
    report_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    request: Request = None,
):
    """Get a saved report."""
    try:
        from backend.app.application.handlers.analytics.queries import GetSavedReportQuery
        from backend.app.application.handlers.analytics.query_handlers import GetSavedReportHandler

        container = request.app.state.container
        repository = container.analytics_repository
        handler = GetSavedReportHandler(repository)

        query = GetSavedReportQuery(
            tenant_id=tenant_id,
            report_id=report_id,
        )

        report = await handler.handle(query)
        return SavedReportResponse(**report)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/reports/{report_id}", dependencies=[Depends(require_permission("reports:read"))])
async def delete_report(
    report_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    request: Request = None,
):
    """Delete a report."""
    try:
        from backend.app.application.handlers.analytics.commands import DeleteReportCommand
        from backend.app.application.handlers.analytics.command_handlers import DeleteReportHandler

        container = request.app.state.container
        repository = container.analytics_repository
        handler = DeleteReportHandler(repository)

        command = DeleteReportCommand(
            tenant_id=tenant_id,
            report_id=report_id,
            actor_id=user_id,
        )

        await handler.handle(command)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Endpoints: Report Generation
# ============================================================================

@router.get("/reports/{report_id}/execute")
async def execute_report(
    report_id: uuid.UUID,
    export_format: str = Query("none", regex="^(pdf|excel|csv|json|none)$"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    request: Request = None,
):
    """Execute a saved report and return data."""
    try:
        from backend.app.application.handlers.analytics.commands import GenerateReportCommand
        from backend.app.application.handlers.analytics.command_handlers import GenerateReportHandler

        container = request.app.state.container
        repository = container.analytics_repository
        handler = GenerateReportHandler(repository)

        command = GenerateReportCommand(
            tenant_id=tenant_id,
            report_id=report_id,
            executed_by=user_id,
            export_format=export_format,
        )

        result = await handler.handle(command)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sales-report", response_model=dict)
async def generate_sales_report(
    start_date: str = Query(...),  # YYYY-MM-DD
    end_date: str = Query(...),  # YYYY-MM-DD
    grouping: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    request: Request = None,
):
    """Generate sales report."""
    try:
        from backend.app.application.handlers.analytics.queries import GenerateSalesReportQuery
        from backend.app.application.handlers.analytics.query_handlers import GenerateSalesReportHandler

        container = request.app.state.container
        repository = container.analytics_repository
        handler = GenerateSalesReportHandler(repository)

        query = GenerateSalesReportQuery(
            tenant_id=tenant_id,
            start_date=datetime.fromisoformat(start_date),
            end_date=datetime.fromisoformat(end_date),
            grouping=grouping,
        )

        return await handler.handle(query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/production-report", response_model=dict)
async def generate_production_report(
    start_date: str = Query(...),
    end_date: str = Query(...),
    grouping: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    request: Request = None,
):
    """Generate production report."""
    try:
        from backend.app.application.handlers.analytics.queries import GenerateProductionReportQuery
        from backend.app.application.handlers.analytics.query_handlers import GenerateProductionReportHandler

        container = request.app.state.container
        repository = container.analytics_repository
        handler = GenerateProductionReportHandler(repository)

        query = GenerateProductionReportQuery(
            tenant_id=tenant_id,
            start_date=datetime.fromisoformat(start_date),
            end_date=datetime.fromisoformat(end_date),
            grouping=grouping,
        )

        return await handler.handle(query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/inventory-report", response_model=dict)
async def generate_inventory_report(
    start_date: str = Query(...),
    end_date: str = Query(...),
    grouping: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    request: Request = None,
):
    """Generate inventory report."""
    try:
        from backend.app.application.handlers.analytics.queries import GenerateInventoryReportQuery
        from backend.app.application.handlers.analytics.query_handlers import GenerateInventoryReportHandler

        container = request.app.state.container
        repository = container.analytics_repository
        handler = GenerateInventoryReportHandler(repository)

        query = GenerateInventoryReportQuery(
            tenant_id=tenant_id,
            start_date=datetime.fromisoformat(start_date),
            end_date=datetime.fromisoformat(end_date),
            grouping=grouping,
        )

        return await handler.handle(query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/finance-report", response_model=dict)
async def generate_finance_report(
    start_date: str = Query(...),
    end_date: str = Query(...),
    grouping: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    request: Request = None,
):
    """Generate finance report."""
    try:
        from backend.app.application.handlers.analytics.queries import GenerateFinanceReportQuery
        from backend.app.application.handlers.analytics.query_handlers import GenerateFinanceReportHandler

        container = request.app.state.container
        repository = container.analytics_repository
        handler = GenerateFinanceReportHandler(repository)

        query = GenerateFinanceReportQuery(
            tenant_id=tenant_id,
            start_date=datetime.fromisoformat(start_date),
            end_date=datetime.fromisoformat(end_date),
            grouping=grouping,
        )

        return await handler.handle(query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Endpoints: Dashboard
# ============================================================================

@router.get("/dashboard-summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    period_start: str = Query(...),  # YYYY-MM-DD
    period_end: str = Query(...),  # YYYY-MM-DD
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    request: Request = None,
):
    """Get dashboard summary with all key metrics."""
    try:
        from backend.app.application.handlers.analytics.queries import GetDashboardSummaryQuery
        from backend.app.application.handlers.analytics.query_handlers import GetDashboardSummaryHandler

        container = request.app.state.container
        repository = container.analytics_repository
        handler = GetDashboardSummaryHandler(repository)

        query = GetDashboardSummaryQuery(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )

        result = await handler.handle(query)
        return DashboardSummary(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/execution-history", response_model=list[ReportExecution])
async def get_execution_history(
    report_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    request: Request = None,
):
    """Get report execution history."""
    try:
        from backend.app.application.handlers.analytics.queries import ListReportExecutionsQuery
        from backend.app.application.handlers.analytics.query_handlers import ListReportExecutionsHandler

        container = request.app.state.container
        repository = container.analytics_repository
        handler = ListReportExecutionsHandler(repository)

        query = ListReportExecutionsQuery(
            tenant_id=tenant_id,
            report_id=report_id,
            limit=limit,
        )

        executions = await handler.handle(query)
        return [ReportExecution(**e) for e in executions]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
