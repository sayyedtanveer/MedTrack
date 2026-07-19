"""
User Device Model for 2FA device trust

Tracks trusted devices to implement "Remember device for 30 days" feature.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class UserDeviceModel(Base):
    """
    Trusted device record for 2FA bypass.

    Allows users to skip TOTP on previously verified devices for 30 days.
    """

    __tablename__ = "user_devices"
    __table_args__ = (
        Index("ix_user_devices_user", "user_id"),
        Index("ix_user_devices_tenant", "tenant_id"),
        UniqueConstraint("user_id", "device_fingerprint", name="uq_user_device_fingerprint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Device identification
    device_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    device_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # e.g., "Chrome on Windows"
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Trust period
    trusted_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<UserDeviceModel user_id={self.user_id} device={self.device_name}>"
