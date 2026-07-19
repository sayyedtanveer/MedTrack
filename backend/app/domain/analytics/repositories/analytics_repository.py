"""Repository interfaces for analytics domain."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from backend.app.domain.analytics.entities.report import (
    SavedReport,
    ReportSchedule,
    ReportExecution,
    DashboardMetric,
)


class AnalyticsRepository(ABC):
    """Base repository for analytics entities."""

    @abstractmethod
    async def save_report(self, report: SavedReport) -> None:
        """Save a report configuration."""
        pass

    @abstractmethod
    async def get_report(self, tenant_id: UUID, report_id: UUID) -> Optional[SavedReport]:
        """Get a report by ID."""
        pass

    @abstractmethod
    async def list_reports(
        self, tenant_id: UUID, is_public: Optional[bool] = None
    ) -> List[SavedReport]:
        """List reports for a tenant."""
        pass

    @abstractmethod
    async def delete_report(self, tenant_id: UUID, report_id: UUID) -> None:
        """Delete (soft) a report."""
        pass

    @abstractmethod
    async def save_schedule(self, schedule: ReportSchedule) -> None:
        """Save a report schedule."""
        pass

    @abstractmethod
    async def get_schedule(self, tenant_id: UUID, schedule_id: UUID) -> Optional[ReportSchedule]:
        """Get a schedule by ID."""
        pass

    @abstractmethod
    async def list_schedules(self, tenant_id: UUID, is_active: Optional[bool] = None) -> List[ReportSchedule]:
        """List schedules for a tenant."""
        pass

    @abstractmethod
    async def save_execution(self, execution: ReportExecution) -> None:
        """Save a report execution record."""
        pass

    @abstractmethod
    async def list_executions(
        self, tenant_id: UUID, report_id: Optional[UUID] = None, limit: int = 100
    ) -> List[ReportExecution]:
        """List report executions."""
        pass

    @abstractmethod
    async def save_metric(self, metric: DashboardMetric) -> None:
        """Save a dashboard metric."""
        pass

    @abstractmethod
    async def get_metric(
        self, tenant_id: UUID, metric_key: str, period_start: str, period_end: str
    ) -> Optional[DashboardMetric]:
        """Get a cached metric."""
        pass

    @abstractmethod
    async def get_sales_data(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get sales data for report generation."""
        pass

    @abstractmethod
    async def get_work_orders(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get work order data for report generation."""
        pass

    @abstractmethod
    async def get_inventory_data(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get inventory data for report generation."""
        pass

    @abstractmethod
    async def get_finance_data(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get finance data for report generation."""
        pass
