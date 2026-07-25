from __future__ import annotations

import uuid
import enum
from datetime import date, datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, Index,
    Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
from backend.app.infrastructure.persistence.database import Base

# Type hints for forward references
if TYPE_CHECKING:
    from backend.app.infrastructure.persistence.models.material_model import MaterialModel
    from backend.app.infrastructure.persistence.models.operation_model import OperationModel


class WorkOrderPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class WorkOrderModel(Base):
    __tablename__ = "work_orders"

    __table_args__ = (
        UniqueConstraint("tenant_id", "wo_number", name="uq_work_order_tenant_number"),
        Index("ix_work_orders_tenant_status", "tenant_id", "status"),
        Index("ix_work_orders_tenant_due", "tenant_id", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wo_number: Mapped[str] = mapped_column(String(30), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    # Product / BOM snapshot references (immutable after RELEASED)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("item_variants.id", ondelete="RESTRICT"), nullable=False
    )
    bom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("boms.id", ondelete="RESTRICT"), nullable=False
    )
    sales_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    sales_order_line_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Quantities
    planned_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    produced_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    scrap_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)

    # Lifecycle — VARCHAR stores full operational state machine (domain WorkOrderStatus).
    status: Mapped[WorkOrderStatus] = mapped_column(
        SAEnum(WorkOrderStatus, name="work_order_status"), nullable=False, default=WorkOrderStatus.PLANNED
    )
    priority: Mapped[str] = mapped_column(
        SAEnum(WorkOrderPriority, name="work_order_priority"), nullable=False, default=WorkOrderPriority.NORMAL
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Production hold tracking (Req 26.2)
    hold_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    hold_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    materials: Mapped[list["WorkOrderMaterialModel"]] = relationship(
        "WorkOrderMaterialModel", back_populates="work_order", cascade="all, delete-orphan"
    )
    job_cards: Mapped[list["JobCardModel"]] = relationship(
        "JobCardModel",
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="JobCardModel.sequence",
    )
    production_records: Mapped[list["ProductionRecordModel"]] = relationship(
        "ProductionRecordModel", back_populates="work_order", cascade="all, delete-orphan"
    )


class WorkOrderMaterialModel(Base):
    """BOM snapshot — copied from BOM lines at WO creation. Never re-reads live BOM."""
    __tablename__ = "work_order_materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units_of_measure.id"), nullable=False)
    required_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    issued_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)

    work_order: Mapped["WorkOrderModel"] = relationship("WorkOrderModel", back_populates="materials")
    material: Mapped["MaterialModel"] = relationship("MaterialModel", lazy="joined")

    @property
    def material_code(self) -> str | None:
        return self.material.code if getattr(self, "material", None) else None

    @property
    def material_name(self) -> str | None:
        return self.material.name if getattr(self, "material", None) else None


class JobCardModel(Base):
    """Operation snapshot — copied from BOM operation list at WO creation."""
    __tablename__ = "job_cards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")  # PENDING / IN_PROGRESS / DONE
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_downtime_seconds: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    pause_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    operator_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    produced_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    scrap_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    rework_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    rejected_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    work_order: Mapped["WorkOrderModel"] = relationship("WorkOrderModel", back_populates="job_cards")
    operation: Mapped["OperationModel"] = relationship("OperationModel", lazy="joined")

    @property
    def operation_name(self) -> str:
        return self.operation.name if getattr(self, "operation", None) else ""

    @property
    def actual_duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            dur = max(0.0, (self.completed_at - self.started_at).total_seconds())
            dur -= float(self.total_downtime_seconds or 0)
            return dur
        return None

    @property
    def progress_percent(self) -> float:
        if self.status in ("DONE", "COMPLETED"):
            return 100.0
        elif self.status == "IN_PROGRESS":
            return 50.0
        elif self.status == "PAUSED":
            return 40.0
        return 0.0

    @property
    def yield_percent(self) -> float:
        produced = float(self.produced_quantity or 0)
        total = produced + float(self.scrap_quantity or 0) + float(self.rejected_quantity or 0)
        return float((produced / total) * 100) if total > 0 else 0.0


class ProductionRecordModel(Base):
    __tablename__ = "production_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    produced_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    scrap_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    work_order: Mapped["WorkOrderModel"] = relationship("WorkOrderModel", back_populates="production_records")


class WONumberSequenceModel(Base):
    """One row per tenant — atomically incremented to generate WO numbers."""
    __tablename__ = "wo_number_sequences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    current_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

import backend.app.infrastructure.persistence.models.operation_model
