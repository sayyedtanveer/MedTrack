from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.infrastructure.persistence.database import Base


class OperationModel(Base):
    """Operation Master ORM model for manufacturing routing.
    
    Represents reusable manufacturing operations that can be:
    - Attached to BOMs as routing steps
    - Inherited by work orders
    - Executed on shop floor
    """
    __tablename__ = "operations"

    # Primary Key & Tenant
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    # Business Identity (never expose UUID to users)
    operation_code: Mapped[str] = mapped_column(String(10), nullable=False)  # "10", "20", "30"
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "Cutting", "Assembly"
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False, default="other")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Routing & Sequencing
    default_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    estimated_time_minutes: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    # Quality & Status
    qc_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # UI/UX Metadata
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    icon_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Audit Trail
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    # Soft Delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workstation: Mapped[Optional["WorkstationModel"]] = relationship(
        "WorkstationModel", back_populates="operations", lazy="joined", foreign_keys="OperationModel.workstation_id"
    )
    workstation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workstations.id"), nullable=True, index=True
    )
    bom_operations: Mapped[list["BOMOperationModel"]] = relationship(
        "BOMOperationModel", back_populates="operation", lazy="select"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_operations_tenant_active", tenant_id, is_active),
        Index("ix_operations_tenant_code", tenant_id, operation_code, unique=True),
        Index("ix_operations_sequence", tenant_id, default_sequence),
    )

    def __repr__(self) -> str:
        return f"<OperationModel(code={self.operation_code}, name={self.name})>"
