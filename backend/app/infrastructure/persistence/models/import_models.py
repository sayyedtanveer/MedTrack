from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.infrastructure.persistence.database import Base


class ImportSessionModel(Base):
    __tablename__ = "import_sessions"
    __table_args__ = (
        Index("ix_import_sessions_tenant", "tenant_id"),
        Index("ix_import_sessions_status", "status"),
        Index("ix_import_sessions_expires", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    
    module: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "CLIENTS", "SUPPLIERS"
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PREVIEW") # PREVIEW, COMPLETED, FAILED
    duplicate_strategy: Mapped[str] = mapped_column(String(30), nullable=False, default="SKIP") # SKIP, UPDATE, FAIL_IMPORT
    
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) + timedelta(days=1), nullable=False
    )

    rows: Mapped[List["ImportSessionRowModel"]] = relationship(
        "ImportSessionRowModel",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ImportSessionRowModel(Base):
    __tablename__ = "import_session_rows"
    __table_args__ = (
        Index("ix_import_session_rows_session", "session_id"),
        Index("ix_import_session_rows_valid", "is_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("import_sessions.id", ondelete="CASCADE"), nullable=False
    )
    
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    data_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    errors_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    session: Mapped["ImportSessionModel"] = relationship(
        "ImportSessionModel", back_populates="rows", lazy="selectin"
    )
