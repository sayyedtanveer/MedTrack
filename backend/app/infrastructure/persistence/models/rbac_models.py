from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.infrastructure.persistence.database import Base


class TenantRoleModel(Base):
    """Tenant-managed role definition."""

    __tablename__ = "tenant_roles"

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_role_name"),
        Index("ix_tenant_roles_tenant_id", "tenant_id"),
        Index("ix_tenant_roles_name", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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

    permissions: Mapped[list["TenantRolePermissionModel"]] = relationship(
        "TenantRolePermissionModel",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class TenantRolePermissionModel(Base):
    """Permission assigned to a tenant-managed role."""

    __tablename__ = "tenant_role_permissions"

    __table_args__ = (
        UniqueConstraint("role_id", "permission", name="uq_tenant_role_permission"),
        Index("ix_tenant_role_permissions_role_id", "role_id"),
        Index("ix_tenant_role_permissions_permission", "permission"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_roles.id", ondelete="CASCADE"), nullable=False
    )
    permission: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    role: Mapped[TenantRoleModel] = relationship("TenantRoleModel", back_populates="permissions", lazy="selectin")
