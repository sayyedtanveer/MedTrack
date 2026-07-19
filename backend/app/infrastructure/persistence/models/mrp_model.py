from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class MRPSuggestionModel(Base):
    __tablename__ = "mrp_suggestions"

    __table_args__ = (
        Index("ix_mrp_suggestions_tenant_status", "tenant_id", "status"),
        Index("ix_mrp_suggestions_tenant_material", "tenant_id", "material_id"),
        Index("ix_mrp_suggestions_created_at", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False)
    material_code: Mapped[str] = mapped_column(String(100), nullable=False)
    material_name: Mapped[str] = mapped_column(String(255), nullable=False)

    gross_requirement = mapped_column(Numeric(18, 4), nullable=False, default=0)
    current_stock = mapped_column(Numeric(18, 4), nullable=False, default=0)
    open_po_qty = mapped_column(Numeric(18, 4), nullable=False, default=0)
    reserved_stock = mapped_column(Numeric(18, 4), nullable=False, default=0)
    net_requirement = mapped_column(Numeric(18, 4), nullable=False, default=0)
    suggested_qty = mapped_column(Numeric(18, 4), nullable=False, default=0)

    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    order_by_date: Mapped[date] = mapped_column(Date, nullable=False)
    need_by_date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Unknown")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    po_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
