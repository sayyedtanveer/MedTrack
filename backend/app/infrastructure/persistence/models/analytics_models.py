import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, Numeric, JSONB, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from backend.app.infrastructure.persistence.models.base_model import BaseModel


class SavedReport(BaseModel):
    """
    Stores custom report configurations for re-use.
    Users can build reports once and save them for repeated execution.
    """
    __tablename__ = "saved_reports"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    created_by: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    name: str = Column(String(255), nullable=False)  # e.g., "Monthly Revenue by Client"
    description: Optional[str] = Column(Text, nullable=True)
    report_type: str = Column(String(50), nullable=False)  # 'sales', 'production', 'inventory', etc.
    
    # Query configuration stored as JSONB
    query_config: Dict[str, Any] = Column(
        JSONB,
        nullable=False,
        default={
            "metrics": [],
            "filters": {},
            "grouping": None,
            "sort_by": None,
            "sort_direction": "asc",
            "limit": 1000
        }
    )
    
    is_public: bool = Column(Boolean, default=False)  # Can other users see this report?
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted: bool = Column(Boolean, default=False)
    deleted_at: Optional[datetime] = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("TenantModel", foreign_keys=[tenant_id])
    creator = relationship("UserModel", foreign_keys=[created_by])
    schedules = relationship("ReportSchedule", back_populates="report", cascade="all, delete-orphan")
    executions = relationship("ReportExecution", back_populates="report", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SavedReport(id={self.id}, name={self.name}, report_type={self.report_type})>"


class ReportSchedule(BaseModel):
    """
    Schedules automated report generation and email delivery.
    Supports daily, weekly, and monthly cadences.
    """
    __tablename__ = "report_schedules"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    created_by: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    report_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("saved_reports.id"), nullable=False, index=True)
    
    schedule_type: str = Column(String(50), nullable=False)  # 'daily', 'weekly', 'monthly'
    schedule_time: str = Column(String(5), nullable=False)  # HH:MM format (e.g., "08:00")
    day_of_week: Optional[str] = Column(String(20), nullable=True)  # 'monday', 'tuesday', etc. (for weekly)
    day_of_month: Optional[int] = Column(Integer, nullable=True)  # 1-28 (for monthly)
    
    recipients: list = Column(ARRAY(String), default=[])  # Email addresses
    is_active: bool = Column(Boolean, default=True)
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_executed_at: Optional[datetime] = Column(DateTime, nullable=True)
    is_deleted: bool = Column(Boolean, default=False)
    deleted_at: Optional[datetime] = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("TenantModel", foreign_keys=[tenant_id])
    creator = relationship("UserModel", foreign_keys=[created_by])
    report = relationship("SavedReport", back_populates="schedules", foreign_keys=[report_id])

    def __repr__(self):
        return f"<ReportSchedule(id={self.id}, schedule_type={self.schedule_type}, report_id={self.report_id})>"


class ReportExecution(BaseModel):
    """
    Audit trail of all report executions.
    Tracks execution time, output format, file location, and status.
    """
    __tablename__ = "report_executions"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    report_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("saved_reports.id"), nullable=False, index=True)
    executed_by: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    export_format: str = Column(String(20), nullable=False)  # 'pdf', 'excel', 'csv', 'json', 'none'
    execution_time_ms: int = Column(Integer, nullable=False)  # Performance tracking
    row_count: int = Column(Integer, default=0)  # Number of data rows in report
    
    file_url: Optional[str] = Column(String(500), nullable=True)  # Path to exported file
    file_size_kb: Optional[int] = Column(Integer, nullable=True)  # Size of exported file
    
    status: str = Column(String(50), default="success")  # 'success', 'failed', 'queued'
    error_message: Optional[str] = Column(Text, nullable=True)  # If failed
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_deleted: bool = Column(Boolean, default=False)
    deleted_at: Optional[datetime] = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("TenantModel", foreign_keys=[tenant_id])
    report = relationship("SavedReport", back_populates="executions", foreign_keys=[report_id])
    executor = relationship("UserModel", foreign_keys=[executed_by])

    def __repr__(self):
        return f"<ReportExecution(id={self.id}, status={self.status}, format={self.export_format})>"


class DashboardMetric(BaseModel):
    """
    Caches dashboard metrics to improve performance.
    Pre-calculated KPIs are stored with expiry times.
    """
    __tablename__ = "dashboard_metrics"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    metric_key: str = Column(String(100), nullable=False)  # 'sales_revenue_mtd', 'inventory_value', etc.
    metric_value: float = Column(Numeric(18, 2), nullable=False)  # Cached value
    
    period_start: str = Column(String(10), nullable=False)  # YYYY-MM-DD
    period_end: str = Column(String(10), nullable=False)  # YYYY-MM-DD
    
    metadata: Dict[str, Any] = Column(JSONB, nullable=True)  # Additional info (trend, status, etc.)
    
    cached_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: datetime = Column(DateTime, nullable=False)  # When cache becomes invalid
    
    is_deleted: bool = Column(Boolean, default=False)
    deleted_at: Optional[datetime] = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("TenantModel", foreign_keys=[tenant_id])

    def __repr__(self):
        return f"<DashboardMetric(metric_key={self.metric_key}, value={self.metric_value})>"

    def is_expired(self) -> bool:
        """Check if cache has expired."""
        return datetime.utcnow() > self.expires_at
