from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint

from backend.app.infrastructure.persistence.database import Base


class ItemVariantModel(Base):
    __tablename__ = "item_variants"

    __table_args__ = (
        # DB-level uniqueness for variant_key per template per tenant
        UniqueConstraint("tenant_id", "template_id", "variant_key", name="uq_item_variant_key"),
        UniqueConstraint("tenant_id", "code", name="uq_item_variant_tenant_code"),
        Index("ix_item_variants_tenant_id", "tenant_id"),
        Index("ix_item_variants_template_id", "template_id"),
        Index("ix_item_variants_variant_key", "tenant_id", "template_id", "variant_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("item_templates.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Auto-generated fields
    code: Mapped[str] = mapped_column(String(255), nullable=False)
    code_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    # Normalized string for uniqueness: "SIZE=SMALL|COLOR=RED"
    variant_key: Mapped[str] = mapped_column(String(500), nullable=False)

    # Attribute values — matches the template's attribute keys
    attribute_values: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)

    base_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    material_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="SET NULL"),
        nullable=True,
    )
    standard_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    selling_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
        return f"<ItemVariantModel id={self.id} code={self.code}>"
