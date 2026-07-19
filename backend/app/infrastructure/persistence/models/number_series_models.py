"""Number Series Engine database models.

These models support the generic Number Series Engine for configurable code generation
across all ERP entity types (material, product, purchase_order, sales_order, invoice,
grn, work_order, batch, customer, supplier).

Tables:
- number_series_config: Per-entity-type configuration per tenant
- number_series_prefixes: Sub-type to prefix mappings per tenant per entity
- number_series_sequences: Generic sequence counters with row-level locking support
- number_series_audit_log: Audit trail for generation events and config changes
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class NumberSeriesConfigModel(Base):
    """Per-entity-type number series configuration per tenant.

    Supports: material, product, purchase_order, sales_order, invoice, grn,
    work_order, batch, customer, supplier.
    Path: Settings → Business Configuration → Number Series → {Entity} Configuration
    """

    __tablename__ = "number_series_config"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_type", name="uq_number_series_config_tenant_entity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    auto_generate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    manual_override: Mapped[str] = mapped_column(String(20), nullable=False, default="never")
    prefix: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    include_abbreviation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    abbreviation_length: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    sequence_length: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    separator: Mapped[str] = mapped_column(String(5), nullable=False, default="-")
    lock_after_save: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class NumberSeriesPrefixModel(Base):
    """Configurable entity sub-type prefix mapping per tenant.

    For materials: maps material_type (raw, finished, etc.) to prefix (RM, FG, etc.)
    For other entities: maps sub_type to prefix (if applicable).
    """

    __tablename__ = "number_series_prefixes"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "entity_type", "sub_type",
            name="uq_ns_prefix_tenant_entity_subtype",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    sub_type: Mapped[str] = mapped_column(String(30), nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), nullable=False)
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


class NumberSeriesSequenceModel(Base):
    """Generic sequence counter for all ERP entities.

    Replaces the material-only item_code_sequences scope for new-format codes.
    Supports concurrent access via SELECT FOR UPDATE row-level locking.
    """

    __tablename__ = "number_series_sequences"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_type", "prefix", name="uq_ns_sequence_scope"),
        Index("ix_ns_sequences_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class NumberSeriesAuditLogModel(Base):
    """Audit trail for number series generation and configuration changes.

    Event types: "generated", "manual_override", "config_changed", "prefix_changed"
    """

    __tablename__ = "number_series_audit_log"
    __table_args__ = (
        Index("ix_ns_audit_log_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    generated_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    old_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(String, nullable=True)
