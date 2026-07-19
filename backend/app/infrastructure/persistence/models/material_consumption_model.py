"""Material consumption and variance tracking for production."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class MaterialConsumptionRecordModel(Base):
    __tablename__ = "material_consumption_records"
    __table_args__ = (
        Index("ix_mcr_tenant_wo", "tenant_id", "work_order_id"),
        Index("ix_mcr_material", "tenant_id", "material_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False
    )
    production_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("production_records.id", ondelete="SET NULL"), nullable=True
    )
    operation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    planned_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    actual_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    variance_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    scrap_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)
