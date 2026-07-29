from __future__ import annotations

import logging
from backend.app.application.shared.command_handler import ICommandHandler
from backend.app.application.tenant.commands.manage_tenant_status import (
    ApproveTenantCommand,
    RejectTenantCommand,
    SuspendTenantCommand,
    ReactivateTenantCommand,
)
from backend.app.domain.tenant.entities.tenant_audit_log import TenantAuditLog
from backend.app.domain.tenant.repositories.tenant_repository_interface import ITenantRepository
from backend.app.domain.tenant.repositories.tenant_audit_log_repository_interface import ITenantAuditLogRepository
from backend.app.domain.shared.interfaces.unit_of_work_interface import IUnitOfWork
from backend.app.domain.shared.exceptions.domain_exception import DomainException
from backend.app.domain.shared.exceptions.business_rule_violation import BusinessRuleViolationException

logger = logging.getLogger(__name__)


class ApproveTenantHandler(ICommandHandler[ApproveTenantCommand, None]):
    def __init__(self, uow: IUnitOfWork, tenant_repo: ITenantRepository, audit_repo: ITenantAuditLogRepository):
        self._uow = uow
        self._tenant_repo = tenant_repo
        self._audit_repo = audit_repo

    async def handle(self, command: ApproveTenantCommand) -> None:
        tenant = await self._tenant_repo.get_by_tenant_id(command.tenant_id)
        if not tenant:
            raise DomainException("Tenant not found", code="NOT_FOUND")

        tenant.approve()
        audit_log = TenantAuditLog(
            tenant_id=tenant.id,
            action="Approved",
            acted_by=command.acted_by
        )

        async with self._uow:
            await self._tenant_repo.save(tenant)
            await self._audit_repo.save(audit_log)
            await self._uow.commit()


class RejectTenantHandler(ICommandHandler[RejectTenantCommand, None]):
    def __init__(self, uow: IUnitOfWork, tenant_repo: ITenantRepository, audit_repo: ITenantAuditLogRepository):
        self._uow = uow
        self._tenant_repo = tenant_repo
        self._audit_repo = audit_repo

    async def handle(self, command: RejectTenantCommand) -> None:
        if not command.reason or not command.reason.strip():
            raise BusinessRuleViolationException("Reason is required for rejection.")

        tenant = await self._tenant_repo.get_by_tenant_id(command.tenant_id)
        if not tenant:
            raise DomainException("Tenant not found", code="NOT_FOUND")

        tenant.reject()
        audit_log = TenantAuditLog(
            tenant_id=tenant.id,
            action="Rejected",
            reason=command.reason,
            acted_by=command.acted_by
        )

        async with self._uow:
            await self._tenant_repo.save(tenant)
            await self._audit_repo.save(audit_log)
            await self._uow.commit()


class SuspendTenantHandler(ICommandHandler[SuspendTenantCommand, None]):
    def __init__(self, uow: IUnitOfWork, tenant_repo: ITenantRepository, audit_repo: ITenantAuditLogRepository):
        self._uow = uow
        self._tenant_repo = tenant_repo
        self._audit_repo = audit_repo

    async def handle(self, command: SuspendTenantCommand) -> None:
        if not command.reason or not command.reason.strip():
            raise BusinessRuleViolationException("Reason is required for suspension.")

        tenant = await self._tenant_repo.get_by_tenant_id(command.tenant_id)
        if not tenant:
            raise DomainException("Tenant not found", code="NOT_FOUND")

        tenant.suspend()
        audit_log = TenantAuditLog(
            tenant_id=tenant.id,
            action="Suspended",
            reason=command.reason,
            acted_by=command.acted_by
        )

        async with self._uow:
            await self._tenant_repo.save(tenant)
            await self._audit_repo.save(audit_log)
            await self._uow.commit()


class ReactivateTenantHandler(ICommandHandler[ReactivateTenantCommand, None]):
    def __init__(self, uow: IUnitOfWork, tenant_repo: ITenantRepository, audit_repo: ITenantAuditLogRepository):
        self._uow = uow
        self._tenant_repo = tenant_repo
        self._audit_repo = audit_repo

    async def handle(self, command: ReactivateTenantCommand) -> None:
        tenant = await self._tenant_repo.get_by_tenant_id(command.tenant_id)
        if not tenant:
            raise DomainException("Tenant not found", code="NOT_FOUND")

        tenant.reactivate()
        audit_log = TenantAuditLog(
            tenant_id=tenant.id,
            action="Reactivated",
            acted_by=command.acted_by
        )

        async with self._uow:
            await self._tenant_repo.save(tenant)
            await self._audit_repo.save(audit_log)
            await self._uow.commit()
