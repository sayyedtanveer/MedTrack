from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Boolean, Index, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.domain.inventory.entities.inventory_transaction import ReferenceType, TransactionType
from backend.app.infrastructure.persistence.database import Base


class InventoryTransactionModel(Base):
    __tablename__ = "inventory_transactions"

    __table_args__ = (
        Index("ix_inv_tx_tenant_material", "tenant_id", "material_id"),
        Index("ix_inv_tx_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # type: in, out, transfer, adjustment
    transaction_type = Column(String(20), nullable=False)
    
    quantity = Column(Numeric(15, 3), nullable=False)

    unit_id = Column(UUID(as_uuid=True), ForeignKey("units_of_measure.id"), nullable=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=True)

    from_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    to_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)

    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Soft delete (kept for consistency — transactions are typically never hard-deleted)
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
        return f"<InventoryTransactionModel id={self.id} type={self.transaction_type} qty={self.quantity}>"
