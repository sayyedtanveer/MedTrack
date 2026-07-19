"""Inventory Reservation database model."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class InventoryReservationModel(Base):
    __tablename__ = "inventory_reservations"
    __table_args__ = (
        Index("ix_ir_tenant_ref", "tenant_id", "reference_type", "reference_id"),
        Index("ix_ir_tenant_material", "tenant_id", "material_id"),
        Index("ix_ir_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    reference_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batches.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RESERVED")
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units_of_measure.id", ondelete="SET NULL"), nullable=True
    )
    issued_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    consumed_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    returned_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
