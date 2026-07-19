"""Material Shortage database model."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class MaterialShortageModel(Base):
    __tablename__ = "material_shortages"
    __table_args__ = (
        Index("ix_ms_tenant_wo", "tenant_id", "work_order_id"),
        Index("ix_ms_tenant_material", "tenant_id", "material_id"),
        Index("ix_ms_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False
    )
    required_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    available_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    shortage_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
