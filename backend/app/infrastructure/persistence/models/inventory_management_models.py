from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class StockReservationModel(Base):
    __tablename__ = "stock_reservations"

    __table_args__ = (
        Index("ix_stock_res_tenant_mat", "tenant_id", "material_id"),
        Index("ix_stock_res_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False)
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True) # Optional if reserving generally

    quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE") # ACTIVE, CONSUMED, CANCELLED
    
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # e.g. WORK_ORDER, SALES_ORDER
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class WarehouseZoneModel(Base):
    __tablename__ = "warehouse_zones"

    __table_args__ = (
        Index("ix_wh_zone_tenant_location", "tenant_id", "warehouse_location_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    warehouse_location_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False)
    
    zone_name: Mapped[str] = mapped_column(String(100), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., RECEIVING, STORAGE, QUARANTINE, DISPATCH
    
    capacity: Mapped[Optional[float]] = mapped_column(Numeric(15, 3), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class StockLedgerModel(Base):
    """Immutable ledger history for true running balance."""
    __tablename__ = "stock_ledger_entries"

    __table_args__ = (
        Index("ix_ledger_tenant_material", "tenant_id", "material_id"),
        Index("ix_ledger_tenant_date", "tenant_id", "transaction_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False)
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False) # RECEIPT, ISSUE, ADJUSTMENT, TRANSFER
    
    quantity_change: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    running_balance: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    
    unit_cost: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    total_value: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)

    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
