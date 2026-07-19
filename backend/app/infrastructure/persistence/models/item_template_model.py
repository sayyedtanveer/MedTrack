from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint

from backend.app.infrastructure.persistence.database import Base
from backend.app.domain.product.value_objects.product_status import ProductStatus


class ItemTemplateModel(Base):
    __tablename__ = "item_templates"

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_item_template_tenant_code"),
        Index("ix_item_templates_tenant_id", "tenant_id"),
        Index("ix_item_templates_tenant_code", "tenant_id", "code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    code_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign keys — stored as UUID, no strict FK because categories/units may
    # live in the inventory bounded context. We keep them as loose references.
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    base_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Attribute definitions — list of {key, label} dicts
    attributes: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    # Status lifecycle: DRAFT, ACTIVE, INACTIVE, ARCHIVED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ProductStatus.ACTIVE.value)
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
        return f"<ItemTemplateModel id={self.id} code={self.code}>"
