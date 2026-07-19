"""Handlers for analytics commands."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from backend.app.domain.analytics.entities.report import SavedReport, ReportQueryConfig
from backend.app.domain.analytics.services.report_generator import ReportGenerator


class CreateSavedReportHandler:
    """Handler for creating saved reports."""

    def __init__(self, repository):
        self.repository = repository

    async def handle(self, command: "CreateSavedReportCommand") -> SavedReport:
        """Create and save a new report."""
        query_config = ReportQueryConfig.from_dict(command.query_config)
        
        report = SavedReport(
            id=None,
            tenant_id=command.tenant_id,
            created_by=command.created_by,
            name=command.name,
            description=command.description,
            report_type=command.report_type,
            query_config=query_config,
            is_public=command.is_public,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        await self.repository.save_report(report)
        return report


class UpdateReportConfigHandler:
    """Handler for updating report configuration."""

    def __init__(self, repository):
        self.repository = repository

    async def handle(self, command: "UpdateReportConfigCommand") -> SavedReport:
        """Update report configuration."""
        report = await self.repository.get_report(command.tenant_id, command.report_id)
        if not report:
            raise ValueError(f"Report {command.report_id} not found")

        new_config = ReportQueryConfig.from_dict(command.query_config)
        report.update_config(new_config)
        
        await self.repository.save_report(report)
        return report


class DeleteReportHandler:
    """Handler for deleting reports."""

    def __init__(self, repository):
        self.repository = repository

    async def handle(self, command: "DeleteReportCommand") -> None:
        """Delete (soft) a report."""
        report = await self.repository.get_report(command.tenant_id, command.report_id)
        if not report:
            raise ValueError(f"Report {command.report_id} not found")

        report.soft_delete()
        await self.repository.save_report(report)


class ToggleReportPublicHandler:
    """Handler for toggling report public status."""

    def __init__(self, repository):
        self.repository = repository

    async def handle(self, command: "ToggleReportPublicCommand") -> SavedReport:
        """Toggle report public visibility."""
        report = await self.repository.get_report(command.tenant_id, command.report_id)
        if not report:
            raise ValueError(f"Report {command.report_id} not found")

        report.toggle_public()
        await self.repository.save_report(report)
        return report


class GenerateReportHandler:
    """Handler for generating reports."""

    def __init__(self, repository):
        self.repository = repository
        self.generator = ReportGenerator(repository)

    async def handle(self, command: "GenerateReportCommand") -> dict:
        """Generate a report based on saved configuration."""
        report = await self.repository.get_report(command.tenant_id, command.report_id)
        if not report:
            raise ValueError(f"Report {command.report_id} not found")

        # Generate report based on type
        start_time = datetime.utcnow()
        
        if report.report_type == "sales":
            report_data = await self.generator.generate_sales_report(
                tenant_id=command.tenant_id,
                start_date=datetime.utcnow().replace(day=1),
                end_date=datetime.utcnow(),
                filters=report.query_config.filters,
            )
        elif report.report_type == "production":
            report_data = await self.generator.generate_production_report(
                tenant_id=command.tenant_id,
                start_date=datetime.utcnow().replace(day=1),
                end_date=datetime.utcnow(),
                filters=report.query_config.filters,
            )
        elif report.report_type == "inventory":
            report_data = await self.generator.generate_inventory_report(
                tenant_id=command.tenant_id,
                start_date=datetime.utcnow().replace(day=1),
                end_date=datetime.utcnow(),
                filters=report.query_config.filters,
            )
        elif report.report_type == "finance":
            report_data = await self.generator.generate_finance_report(
                tenant_id=command.tenant_id,
                start_date=datetime.utcnow().replace(day=1),
                end_date=datetime.utcnow(),
                filters=report.query_config.filters,
            )
        else:
            raise ValueError(f"Unknown report type: {report.report_type}")

        end_time = datetime.utcnow()
        execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return {
            "report_id": str(command.report_id),
            "data": report_data,
            "execution_time_ms": execution_time_ms,
            "generated_at": datetime.utcnow().isoformat(),
        }
