from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint

from backend.app.infrastructure.persistence.database import Base

BATCH_STATUS_IN_STOCK = "in_stock"
BATCH_STATUS_DEPLETED = "depleted"
BATCH_STATUS_EXPIRED = "expired"


class BatchModel(Base):
    __tablename__ = "batches"

    __table_args__ = (
        UniqueConstraint("tenant_id", "material_id", "batch_number", name="uq_batch_tenant_material_number"),
        Index("ix_batches_tenant_id", "tenant_id"),
        Index("ix_batches_tenant_material", "tenant_id", "material_id"),
        Index("ix_batches_tenant_batch_number", "tenant_id", "batch_number"),
        Index("ix_batches_expiry_date", "expiry_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False, index=True
    )

    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    remaining_quantity: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="in_stock")
    original_quantity: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    reserved_quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    consumed_quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    returned_quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)

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

    def __repr__(self) -> str:
        return f"<BatchModel id={self.id} batch_number={self.batch_number}>"
