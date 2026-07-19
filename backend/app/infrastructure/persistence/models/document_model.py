"""Document ORM model for tracking generated PDFs with versioning and audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class DocumentModel(Base):
    """Generated document with versioning and audit trail."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_tenant_id", "tenant_id"),
        Index("ix_documents_entity", "document_type", "entity_id"),
        Index("ix_documents_is_deleted", "is_deleted"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    
    # Document type and entity reference
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # work_order, purchase_order, invoice, etc.
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)  # Reference to the entity
    
    # Versioning
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # File storage
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)  # Storage path on filesystem
    
    # Audit trail
    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    
    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<DocumentModel id={self.id} type={self.document_type} entity_id={self.entity_id} version={self.version_number}>"
