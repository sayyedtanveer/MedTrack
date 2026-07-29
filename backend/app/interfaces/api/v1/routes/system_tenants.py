from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from backend.app.application.shared.platform_authorization_service import PlatformAuthorizationService
from backend.app.application.tenant.commands.manage_tenant_status import (
    ApproveTenantCommand,
    RejectTenantCommand,
    SuspendTenantCommand,
    ReactivateTenantCommand,
)
from backend.app.application.tenant.handlers.manage_tenant_status_handler import (
    ApproveTenantHandler,
    RejectTenantHandler,
    SuspendTenantHandler,
    ReactivateTenantHandler,
)
from backend.app.domain.shared.exceptions.business_rule_violation import BusinessRuleViolationException
from backend.app.domain.shared.exceptions.domain_exception import DomainException
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.repositories.tenant_audit_log_repository import TenantAuditLogRepository
from backend.app.infrastructure.persistence.repositories.tenant_repository import TenantRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
    get_current_user_payload,
)
from backend.app.interfaces.api.v1.schemas.system_schemas import SystemTenantResponse, SystemTenantListResponse, TenantActionRequest
from backend.app.infrastructure.logging.logger import get_logger
from backend.app.infrastructure.tasks.sample_tasks import SendWorkspaceApprovedEmailTask

logger = get_logger(__name__)

router = APIRouter(prefix="/system/tenants", tags=["System Administration"])


async def verify_platform_admin(request: Request, payload: dict = Depends(get_current_user_payload)):
    """Dependency to check if current user is a platform admin."""
    container = get_container(request)
    tenant_id_str = payload.get("tid", "")
    role = payload.get("role", "")
    
    try:
        tenant_id = uuid.UUID(tenant_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid tenant ID")

    async with container.session_factory() as session:
        tenant_repo = TenantRepository(session)
        tenant = await tenant_repo.get_by_tenant_id(tenant_id)

    if not tenant or not tenant.is_system_tenant or role != "tenant_admin":
        raise HTTPException(status_code=403, detail="Platform Administrator privileges required")
    
    return True


@router.get(
    "",
    response_model=SystemTenantListResponse,
    dependencies=[Depends(verify_platform_admin)]
)
async def list_all_tenants(request: Request):
    """List all tenants in the system (Platform Admin only)."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(TenantModel).order_by(TenantModel.created_at.desc())
        result = await session.execute(stmt)
        models = result.scalars().all()
        
        tenants = [
            SystemTenantResponse(
                id=m.id,
                name=m.name,
                slug=m.slug,
                plan=m.plan,
                status=m.status,
                is_active=m.is_active,
                is_system_tenant=m.is_system_tenant,
                created_at=m.created_at
            )
            for m in models
        ]
        
    return SystemTenantListResponse(tenants=tenants, total=len(tenants))


@router.post(
    "/{tenant_id}/approve",
    dependencies=[Depends(verify_platform_admin)]
)
async def approve_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session, container.event_dispatcher)
        tenant_repo = TenantRepository(session)
        audit_repo = TenantAuditLogRepository(session)
        handler = ApproveTenantHandler(uow, tenant_repo, audit_repo)
        
        try:
            await handler.handle(ApproveTenantCommand(tenant_id=tenant_id, acted_by=user_id))
        except (DomainException, BusinessRuleViolationException) as e:
            raise HTTPException(status_code=400, detail=str(e))
            
    # Enqueue SendWorkspaceApprovedEmailTask
    # Since we don't have the admin email readily available on Tenant without querying the User repository,
    # and to save time, we will skip sending the email or fetch it. Let's fetch the first admin user.
    async with container.session_factory() as session:
        from backend.app.infrastructure.persistence.models.user_model import UserModel
        stmt = select(UserModel).where(UserModel.tenant_id == tenant_id, UserModel.role == "admin")
        result = await session.execute(stmt)
        admin_user = result.scalars().first()
        
        if admin_user:
            container.task_service.enqueue(
                SendWorkspaceApprovedEmailTask(
                    email=admin_user.email,
                    tenant_name="Workspace",
                    first_name=admin_user.first_name,
                )
            )

    return {"detail": "Tenant approved successfully"}


@router.post(
    "/{tenant_id}/reject",
    dependencies=[Depends(verify_platform_admin)]
)
async def reject_tenant(
    tenant_id: uuid.UUID,
    body: TenantActionRequest,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    if not body.reason:
        raise HTTPException(status_code=400, detail="Reason is required to reject a tenant.")
        
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session, container.event_dispatcher)
        tenant_repo = TenantRepository(session)
        audit_repo = TenantAuditLogRepository(session)
        handler = RejectTenantHandler(uow, tenant_repo, audit_repo)
        
        try:
            await handler.handle(RejectTenantCommand(tenant_id=tenant_id, reason=body.reason, acted_by=user_id))
        except (DomainException, BusinessRuleViolationException) as e:
            raise HTTPException(status_code=400, detail=str(e))
            
    return {"detail": "Tenant rejected successfully"}


@router.post(
    "/{tenant_id}/suspend",
    dependencies=[Depends(verify_platform_admin)]
)
async def suspend_tenant(
    tenant_id: uuid.UUID,
    body: TenantActionRequest,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    if not body.reason:
        raise HTTPException(status_code=400, detail="Reason is required to suspend a tenant.")
        
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session, container.event_dispatcher)
        tenant_repo = TenantRepository(session)
        audit_repo = TenantAuditLogRepository(session)
        handler = SuspendTenantHandler(uow, tenant_repo, audit_repo)
        
        try:
            await handler.handle(SuspendTenantCommand(tenant_id=tenant_id, reason=body.reason, acted_by=user_id))
        except (DomainException, BusinessRuleViolationException) as e:
            raise HTTPException(status_code=400, detail=str(e))
            
    return {"detail": "Tenant suspended successfully"}


@router.post(
    "/{tenant_id}/reactivate",
    dependencies=[Depends(verify_platform_admin)]
)
async def reactivate_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session, container.event_dispatcher)
        tenant_repo = TenantRepository(session)
        audit_repo = TenantAuditLogRepository(session)
        handler = ReactivateTenantHandler(uow, tenant_repo, audit_repo)
        
        try:
            await handler.handle(ReactivateTenantCommand(tenant_id=tenant_id, acted_by=user_id))
        except (DomainException, BusinessRuleViolationException) as e:
            raise HTTPException(status_code=400, detail=str(e))
            
    return {"detail": "Tenant reactivated successfully"}
