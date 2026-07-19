"""Handlers for analytics queries."""

from datetime import datetime
from typing import Optional, Dict, Any, List

from backend.app.domain.analytics.services.report_generator import ReportGenerator, MetricsCalculator


class ListSavedReportsHandler:
    """Handler for listing saved reports."""

    def __init__(self, repository):
        self.repository = repository

    async def handle(self, query: "ListSavedReportsQuery") -> List[dict]:
        """List reports for tenant."""
        reports = await self.repository.list_reports(
            tenant_id=query.tenant_id,
            is_public=query.is_public,
        )
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "report_type": r.report_type,
                "is_public": r.is_public,
                "created_by": str(r.created_by),
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in reports
        ]


class GetSavedReportHandler:
    """Handler for retrieving a saved report."""

    def __init__(self, repository):
        self.repository = repository

    async def handle(self, query: "GetSavedReportQuery") -> dict:
        """Get report details."""
        report = await self.repository.get_report(query.tenant_id, query.report_id)
        if not report:
            raise ValueError(f"Report {query.report_id} not found")

        return {
            "id": str(report.id),
            "name": report.name,
            "description": report.description,
            "report_type": report.report_type,
            "query_config": report.query_config.to_dict(),
            "is_public": report.is_public,
            "created_by": str(report.created_by),
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
        }


class ListReportExecutionsHandler:
    """Handler for listing report executions."""

    def __init__(self, repository):
        self.repository = repository

    async def handle(self, query: "ListReportExecutionsQuery") -> List[dict]:
        """List report executions."""
        executions = await self.repository.list_executions(
            tenant_id=query.tenant_id,
            report_id=query.report_id,
            limit=query.limit,
        )
        return [
            {
                "id": str(e.id),
                "report_id": str(e.report_id),
                "export_format": e.export_format,
                "status": e.status,
                "execution_time_ms": e.execution_time_ms,
                "row_count": e.row_count,
                "file_url": e.file_url,
                "created_at": e.created_at.isoformat(),
            }
            for e in executions
        ]


class GenerateSalesReportHandler:
    """Handler for generating sales reports."""

    def __init__(self, repository):
        self.repository = repository
        self.generator = ReportGenerator(repository)

    async def handle(self, query: "GenerateSalesReportQuery") -> dict:
        """Generate sales report."""
        return await self.generator.generate_sales_report(
            tenant_id=query.tenant_id,
            start_date=query.start_date,
            end_date=query.end_date,
            grouping=query.grouping,
            filters=query.filters,
        )


class GenerateProductionReportHandler:
    """Handler for generating production reports."""

    def __init__(self, repository):
        self.repository = repository
        self.generator = ReportGenerator(repository)

    async def handle(self, query: "GenerateProductionReportQuery") -> dict:
        """Generate production report."""
        return await self.generator.generate_production_report(
            tenant_id=query.tenant_id,
            start_date=query.start_date,
            end_date=query.end_date,
            grouping=query.grouping,
            filters=query.filters,
        )


class GenerateInventoryReportHandler:
    """Handler for generating inventory reports."""

    def __init__(self, repository):
        self.repository = repository
        self.generator = ReportGenerator(repository)

    async def handle(self, query: "GenerateInventoryReportQuery") -> dict:
        """Generate inventory report."""
        return await self.generator.generate_inventory_report(
            tenant_id=query.tenant_id,
            start_date=query.start_date,
            end_date=query.end_date,
            grouping=query.grouping,
            filters=query.filters,
        )


class GenerateFinanceReportHandler:
    """Handler for generating finance reports."""

    def __init__(self, repository):
        self.repository = repository
        self.generator = ReportGenerator(repository)

    async def handle(self, query: "GenerateFinanceReportQuery") -> dict:
        """Generate finance report."""
        return await self.generator.generate_finance_report(
            tenant_id=query.tenant_id,
            start_date=query.start_date,
            end_date=query.end_date,
            grouping=query.grouping,
            filters=query.filters,
        )


class GetDashboardSummaryHandler:
    """Handler for getting dashboard summary."""

    def __init__(self, repository):
        self.repository = repository
        self.metrics_calc = MetricsCalculator(repository)

    async def handle(self, query: "GetDashboardSummaryQuery") -> dict:
        """Get dashboard summary with all metrics."""
        start_date = datetime.fromisoformat(query.period_start)
        end_date = datetime.fromisoformat(query.period_end)

        # Calculate key metrics
        metrics = {}
        metric_keys = [
            "sales_revenue_total",
            "sales_orders_count",
            "sales_average_order_value",
            "production_total_qty",
            "production_completion_rate",
            "production_scrap_rate",
            "inventory_value_total",
            "inventory_item_count",
            "inventory_stockouts",
            "finance_ar_total",
            "finance_ap_total",
            "finance_cash_position",
        ]

        for key in metric_keys:
            try:
                value = await self.metrics_calc.calculate_metric(
                    query.tenant_id, key, start_date, end_date
                )
                metrics[key] = value
            except Exception:
                metrics[key] = 0

        return {
            "period": {
                "start": query.period_start,
                "end": query.period_end,
            },
            "metrics": metrics,
            "summary": {
                "sales": {
                    "revenue": metrics.get("sales_revenue_total", 0),
                    "orders": metrics.get("sales_orders_count", 0),
                    "avg_order_value": metrics.get("sales_average_order_value", 0),
                },
                "production": {
                    "total_qty": metrics.get("production_total_qty", 0),
                    "completion_rate": metrics.get("production_completion_rate", 0),
                    "scrap_rate": metrics.get("production_scrap_rate", 0),
                },
                "inventory": {
                    "total_value": metrics.get("inventory_value_total", 0),
                    "item_count": metrics.get("inventory_item_count", 0),
                    "stockouts": metrics.get("inventory_stockouts", 0),
                },
                "finance": {
                    "ar_total": metrics.get("finance_ar_total", 0),
                    "ap_total": metrics.get("finance_ap_total", 0),
                    "cash_position": metrics.get("finance_cash_position", 0),
                },
            },
        }
