"""Commands for analytics operations."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID


@dataclass
class CreateSavedReportCommand:
    """Command to create a new saved report."""
    tenant_id: UUID
    created_by: UUID
    name: str
    description: Optional[str]
    report_type: str
    query_config: Dict[str, Any]
    is_public: bool = False


@dataclass
class UpdateReportConfigCommand:
    """Command to update report configuration."""
    tenant_id: UUID
    report_id: UUID
    actor_id: UUID
    query_config: Dict[str, Any]


@dataclass
class DeleteReportCommand:
    """Command to delete a report."""
    tenant_id: UUID
    report_id: UUID
    actor_id: UUID


@dataclass
class ToggleReportPublicCommand:
    """Command to toggle report public visibility."""
    tenant_id: UUID
    report_id: UUID
    actor_id: UUID


@dataclass
class CreateReportScheduleCommand:
    """Command to schedule automated report generation."""
    tenant_id: UUID
    created_by: UUID
    report_id: UUID
    schedule_type: str
    schedule_time: str
    day_of_week: Optional[str]
    day_of_month: Optional[int]
    recipients: list[str]


@dataclass
class GenerateReportCommand:
    """Command to generate a report."""
    tenant_id: UUID
    report_id: UUID
    executed_by: UUID
    export_format: str = "none"  # 'pdf', 'excel', 'csv', 'json', 'none'


@dataclass
class ScheduleReportExecutionCommand:
    """Command for scheduled report execution."""
    schedule_id: UUID
    executed_by: UUID


@dataclass
class RefreshMetricCacheCommand:
    """Command to refresh dashboard metric cache."""
    tenant_id: UUID
    metric_key: str
    period_start: str
    period_end: str
