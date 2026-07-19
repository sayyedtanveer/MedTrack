from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # What happened
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # e.g. CREATE, UPDATE, DELETE, LOGIN, LOGOUT, ACCESS_DENIED
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # State capture (before/after for auditable mutations)
    before_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    after_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    correlation_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Additional context
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLogModel id={self.id} action={self.action} entity={self.entity_type}>"
