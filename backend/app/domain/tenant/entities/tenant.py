from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity
from backend.app.domain.shared.exceptions.business_rule_violation import BusinessRuleViolationException
from backend.app.domain.tenant.value_objects.tenant_status import TenantStatus


class Tenant(BaseEntity):
    """
    Tenant aggregate root.

    A tenant represents one manufacturing company using the ERP.
    All other entities are scoped to a tenant.
    """

    def __init__(
        self,
        name: str,
        slug: str,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,  # same as id for Tenant itself
        plan: str = "starter",
        is_active: bool = True, # Deprecated, keeping for backwards compatibility initially
        status: TenantStatus | str = TenantStatus.PENDING,
        is_system_tenant: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
        timezone: Optional[str] = None,
        default_warehouse_name: Optional[str] = None,
    ) -> None:
        # Tenant's own id IS its tenant_id
        resolved_id = id or uuid.uuid4()
        super().__init__(
            id=resolved_id,
            tenant_id=tenant_id or resolved_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )
        self._name = name
        self._slug = slug
        self._plan = plan
        self._is_active = is_active
        self._status = TenantStatus.from_string(status) if isinstance(status, str) else status
        self._is_system_tenant = is_system_tenant
        self._timezone = timezone
        self._default_warehouse_name = default_warehouse_name

        self._validate()

    # ── Properties ────────────────────────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def slug(self) -> str:
        return self._slug

    @property
    def plan(self) -> str:
        return self._plan

    @property
    def is_active(self) -> bool:
        return self._status == TenantStatus.ACTIVE

    @property
    def status(self) -> TenantStatus:
        return self._status

    @property
    def is_system_tenant(self) -> bool:
        return self._is_system_tenant

    @property
    def timezone(self) -> Optional[str]:
        return self._timezone

    @property
    def default_warehouse_name(self) -> Optional[str]:
        return self._default_warehouse_name

    # ── Invariants ────────────────────────────────────────────────────────
    def _validate(self) -> None:
        if not self._name or len(self._name.strip()) < 2:
            raise BusinessRuleViolationException(
                rule="Tenant name must be at least 2 characters"
            )
        if not self._slug or not self._slug.replace("-", "").isalnum():
            raise BusinessRuleViolationException(
                rule="Tenant slug must be alphanumeric (hyphens allowed)"
            )

    # ── Behaviour ─────────────────────────────────────────────────────────
    def activate(self) -> None:
        self._is_active = True
        self._status = TenantStatus.ACTIVE
        self._touch()

    def deactivate(self) -> None:
        self._is_active = False
        self._status = TenantStatus.ARCHIVED
        self._touch()
        
    def approve(self) -> None:
        if self._status != TenantStatus.PENDING:
            raise BusinessRuleViolationException(rule="Can only approve pending tenants.")
        self._status = TenantStatus.ACTIVE
        self._is_active = True
        self._touch()
        
    def reject(self) -> None:
        if self._status != TenantStatus.PENDING:
            raise BusinessRuleViolationException(rule="Can only reject pending tenants.")
        self._status = TenantStatus.REJECTED
        self._touch()
        
    def suspend(self) -> None:
        self._status = TenantStatus.SUSPENDED
        self._is_active = False
        self._touch()
        
    def reactivate(self) -> None:
        if self._status != TenantStatus.SUSPENDED:
            raise BusinessRuleViolationException(rule="Can only reactivate suspended tenants.")
        self._status = TenantStatus.ACTIVE
        self._is_active = True
        self._touch()

    def change_plan(self, new_plan: str) -> None:
        allowed = {"starter", "professional", "enterprise"}
        if new_plan not in allowed:
            raise BusinessRuleViolationException(
                rule=f"Plan must be one of {allowed}", details=f"Got: {new_plan}"
            )
        self._plan = new_plan
        self._touch()
