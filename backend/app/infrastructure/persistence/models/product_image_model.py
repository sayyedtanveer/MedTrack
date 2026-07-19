from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint

from backend.app.infrastructure.persistence.database import Base


class ProductImageModel(Base):
    __tablename__ = "product_images"

    __table_args__ = (
        # Index for querying by template
        Index("ix_product_images_tenant_template", "tenant_id", "template_id"),
        # Index for querying by variant
        Index("ix_product_images_tenant_variant", "tenant_id", "variant_id"),
        # Composite index for listing images for a template/variant
        Index("ix_product_images_order", "template_id", "variant_id", "image_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Foreign keys to product entities
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # File metadata
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)  # S3 URL or local path
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    file_mime_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. 'image/jpeg'

    # Display metadata
    image_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Soft delete
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
        return f"<ProductImageModel id={self.id} file_name={self.file_name}>"
