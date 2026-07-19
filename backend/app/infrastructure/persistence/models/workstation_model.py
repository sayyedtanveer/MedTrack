from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.infrastructure.persistence.database import Base


class WorkstationModel(Base):
    __tablename__ = "workstations"

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_workstation_tenant_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    capacity_hours_per_day: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=8.0)
    hourly_rate: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    operations: Mapped[list["OperationModel"]] = relationship(
        "OperationModel", back_populates="workstation", lazy="select"
    )

    # Audit fields
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )
