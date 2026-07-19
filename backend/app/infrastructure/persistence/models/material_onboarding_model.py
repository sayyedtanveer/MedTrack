from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class MaterialOnboardingSessionModel(Base):
    __tablename__ = "material_onboarding_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="UPLOADED")
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    protected_changes_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    original_headers_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    mapping_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class MaterialOnboardingRowModel(Base):
    __tablename__ = "material_onboarding_rows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_onboarding_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    normalized_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    validation_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    protected_changes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    classification: Mapped[str] = mapped_column(String(40), nullable=False, default="invalid")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    result_material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class MaterialImportMappingModel(Base):
    __tablename__ = "material_import_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    mapping_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class MaterialOnboardingProfileModel(Base):
    __tablename__ = "material_onboarding_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    defaults_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
