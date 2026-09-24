import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Integer,
    Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from backend.app.infrastructure.persistence.database import Base

class FileAttachmentModel(Base):
    __tablename__ = "file_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    cloudinary_public_id: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)


class TechnicalDocumentModel(Base):
    __tablename__ = "technical_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    document_number: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_category: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "Drawing", "SOP", "Datasheet"
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    revisions: Mapped[list["DocumentRevisionModel"]] = relationship(
        "DocumentRevisionModel", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "document_number", name="uq_technical_doc_tenant_number"),
    )


class DocumentRevisionModel(Base):
    __tablename__ = "document_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("technical_documents.id", ondelete="CASCADE"), nullable=False
    )
    file_attachment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_attachments.id", ondelete="RESTRICT"), nullable=False
    )
    
    revision_code: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT") # DRAFT, APPROVED, OBSOLETE
    notes: Mapped[str] = mapped_column(String(1000), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    document: Mapped["TechnicalDocumentModel"] = relationship("TechnicalDocumentModel", back_populates="revisions")
    file_attachment: Mapped["FileAttachmentModel"] = relationship("FileAttachmentModel")

    __table_args__ = (
        UniqueConstraint("tenant_id", "document_id", "revision_code", name="uq_doc_revision_code"),
    )


class DocumentAssociationModel(Base):
    __tablename__ = "document_associations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    
    # Target Entities
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=True
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("item_variants.id", ondelete="CASCADE"), nullable=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("item_templates.id", ondelete="CASCADE"), nullable=True
    )

    is_print_package_included: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    revision: Mapped["DocumentRevisionModel"] = relationship("DocumentRevisionModel")

    __table_args__ = (
        CheckConstraint(
            "(work_order_id IS NOT NULL AND variant_id IS NULL AND template_id IS NULL) OR "
            "(work_order_id IS NULL AND variant_id IS NOT NULL AND template_id IS NULL) OR "
            "(work_order_id IS NULL AND variant_id IS NULL AND template_id IS NOT NULL)",
            name="ck_document_association_target_exactly_one"
        ),
    )
