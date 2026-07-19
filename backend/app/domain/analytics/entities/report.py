"""Domain entity for SavedReport aggregate."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from backend.app.domain.shared.value_objects import AggregateRoot


@dataclass
class ReportQueryConfig:
    """Value object for report query configuration."""
    metrics: list[str] = field(default_factory=list)  # Metric keys to include
    filters: Dict[str, Any] = field(default_factory=dict)  # Filter conditions
    grouping: Optional[str] = None  # Group by field
    sort_by: Optional[str] = None  # Sort field
    sort_direction: str = "asc"  # asc | desc
    limit: int = 1000  # Result limit

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "metrics": self.metrics,
            "filters": self.filters,
            "grouping": self.grouping,
            "sort_by": self.sort_by,
            "sort_direction": self.sort_direction,
            "limit": self.limit,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportQueryConfig":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SavedReport(AggregateRoot):
    """SavedReport aggregate root entity."""
    
    id: UUID
    tenant_id: UUID
    created_by: UUID
    name: str
    description: Optional[str]
    report_type: str  # 'sales', 'production', 'inventory', 'finance'
    query_config: ReportQueryConfig
    is_public: bool
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    def update_config(self, new_config: ReportQueryConfig) -> None:
        """Update report configuration."""
        self.query_config = new_config
        self.updated_at = datetime.utcnow()
        self.add_event("ReportConfigUpdated", {
            "report_id": str(self.id),
            "old_config": self.query_config.to_dict(),
            "new_config": new_config.to_dict(),
        })

    def toggle_public(self) -> None:
        """Toggle public visibility."""
        self.is_public = not self.is_public
        self.updated_at = datetime.utcnow()
        self.add_event("ReportVisibilityToggled", {
            "report_id": str(self.id),
            "is_public": self.is_public,
        })

    def soft_delete(self) -> None:
        """Mark as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.add_event("ReportDeleted", {"report_id": str(self.id)})


@dataclass
class ReportSchedule:
    """ReportSchedule entity for scheduled report generation."""
    
    id: UUID
    tenant_id: UUID
    created_by: UUID
    report_id: UUID
    schedule_type: str  # 'daily', 'weekly', 'monthly'
    schedule_time: str  # HH:MM
    day_of_week: Optional[str]  # For weekly
    day_of_month: Optional[int]  # For monthly
    recipients: list[str]  # Email addresses
    is_active: bool
    created_at: datetime
    last_executed_at: Optional[datetime]
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    def deactivate(self) -> None:
        """Deactivate schedule."""
        self.is_active = False

    def activate(self) -> None:
        """Activate schedule."""
        self.is_active = True

    def update_execution_time(self) -> None:
        """Update last execution time."""
        self.last_executed_at = datetime.utcnow()


@dataclass
class ReportExecution:
    """ReportExecution entity for audit trail."""
    
    id: UUID
    tenant_id: UUID
    report_id: UUID
    executed_by: UUID
    export_format: str  # 'pdf', 'excel', 'csv', 'json', 'none'
    execution_time_ms: int
    row_count: int
    file_url: Optional[str]
    file_size_kb: Optional[int]
    status: str  # 'success', 'failed', 'queued'
    error_message: Optional[str]
    created_at: datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    @property
    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == "success"

    @property
    def duration_seconds(self) -> float:
        """Get execution duration in seconds."""
        return self.execution_time_ms / 1000.0


@dataclass
class DashboardMetric:
    """DashboardMetric entity for cached KPIs."""
    
    id: UUID
    tenant_id: UUID
    metric_key: str
    metric_value: float
    period_start: str  # YYYY-MM-DD
    period_end: str  # YYYY-MM-DD
    metadata: Optional[Dict[str, Any]]
    cached_at: datetime
    expires_at: datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if cache has expired."""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if metric is valid and not deleted."""
        return not self.is_deleted and not self.is_expired()
