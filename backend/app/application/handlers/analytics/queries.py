"""Queries for analytics operations."""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from datetime import datetime


@dataclass
class GetSavedReportQuery:
    """Query to retrieve a saved report."""
    tenant_id: UUID
    report_id: UUID


@dataclass
class ListSavedReportsQuery:
    """Query to list saved reports."""
    tenant_id: UUID
    is_public: Optional[bool] = None
    report_type: Optional[str] = None


@dataclass
class ListReportExecutionsQuery:
    """Query to list report executions."""
    tenant_id: UUID
    report_id: Optional[UUID] = None
    limit: int = 100


@dataclass
class ListReportSchedulesQuery:
    """Query to list report schedules."""
    tenant_id: UUID
    is_active: Optional[bool] = None


@dataclass
class GetDashboardMetricQuery:
    """Query to retrieve a cached metric."""
    tenant_id: UUID
    metric_key: str
    period_start: str
    period_end: str


@dataclass
class GenerateSalesReportQuery:
    """Query to generate sales report."""
    tenant_id: UUID
    start_date: datetime
    end_date: datetime
    grouping: Optional[str] = None
    filters: Optional[dict] = None


@dataclass
class GenerateProductionReportQuery:
    """Query to generate production report."""
    tenant_id: UUID
    start_date: datetime
    end_date: datetime
    grouping: Optional[str] = None
    filters: Optional[dict] = None


@dataclass
class GenerateInventoryReportQuery:
    """Query to generate inventory report."""
    tenant_id: UUID
    start_date: datetime
    end_date: datetime
    grouping: Optional[str] = None
    filters: Optional[dict] = None


@dataclass
class GenerateFinanceReportQuery:
    """Query to generate finance report."""
    tenant_id: UUID
    start_date: datetime
    end_date: datetime
    grouping: Optional[str] = None
    filters: Optional[dict] = None


@dataclass
class GetDashboardSummaryQuery:
    """Query to get dashboard summary with all key metrics."""
    tenant_id: UUID
    period_start: str
    period_end: str
