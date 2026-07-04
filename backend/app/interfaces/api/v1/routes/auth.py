from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel

from backend.app.application.tenant.commands.register_tenant import RegisterTenantCommand
from backend.app.application.tenant.commands.login_user import LoginUserCommand
from backend.app.application.tenant.handlers.register_tenant_handler import RegisterTenantHandler
from backend.app.application.tenant.handlers.login_user_handler import LoginUserHandler
from backend.app.application.rbac.service import get_effective_role_permissions
from backend.app.infrastructure.persistence.repositories.tenant_repository import TenantRepository
from backend.app.infrastructure.persistence.repositories.user_repository import UserRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_user_payload,
    get_current_tenant_id,
    get_current_user_id,
    get_current_role,
)
from backend.app.interfaces.api.v1.schemas.auth_schemas import (
    LoginRequest,
    LoginResponse,
    RegisterTenantRequest,
    RegisterTenantResponse,
    UserProfileResponse,
    UserInMeResponse,
    TenantInMeResponse,
)
from backend.app.infrastructure.tasks.sample_tasks import SendWelcomeEmailTask
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register-tenant",
    response_model=RegisterTenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new tenant + admin user",
)
async def register_tenant(
    body: RegisterTenantRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    container = get_container(request)
    async with container.session_factory() as session:
        tenant_repo = TenantRepository(session)
        user_repo = UserRepository(session)
        uow = SQLAlchemyUnitOfWork(
            session=session,
            event_dispatcher=container.event_dispatcher,
        )
        handler = RegisterTenantHandler(
            uow=uow,
            tenant_repo=tenant_repo,
            user_repo=user_repo,
            password_hasher=container.password_hasher,
            jwt_handler=container.jwt_handler,
        )
        command = RegisterTenantCommand(
            name=body.name,
            slug=body.slug,
            admin_email=body.admin_email,
            admin_password=body.admin_password,
            admin_first_name=body.admin_first_name,
            admin_last_name=body.admin_last_name,
            plan=body.plan,
        )
        result = await handler.handle(command)

    # Enqueue welcome email as background task
    container.task_service.enqueue(
        SendWelcomeEmailTask(
            email=result.email,
            tenant_name=result.tenant_name,
            first_name=body.admin_first_name,
        ),
        bg_tasks=background_tasks,
    )

    return RegisterTenantResponse(
        tenant_id=result.tenant_id,
        tenant_name=result.tenant_name,
        slug=result.slug,
        user_id=result.user_id,
        email=result.email,
        role=result.role,
        access_token=result.access_token,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate and get JWT token",
)
async def login(body: LoginRequest, request: Request):
    container = get_container(request)
    async with container.session_factory() as session:
        user_repo = UserRepository(session)
        handler = LoginUserHandler(
            user_repo=user_repo,
            password_hasher=container.password_hasher,
            jwt_handler=container.jwt_handler,
        )
        try:
            tenant_id = uuid.UUID(body.tenant_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tenant_id format")

        command = LoginUserCommand(
            email=body.email,
            password=body.password,
            tenant_id=tenant_id,
        )
        result = await handler.handle(command)

    return LoginResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        user_id=result.user_id,
        tenant_id=result.tenant_id,
        email=result.email,
        role=result.role,
        full_name=result.full_name,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current authenticated user profile + tenant info",
)
async def me(
    request: Request,
    payload: dict = Depends(get_current_user_payload),
):
    container = get_container(request)
    tenant_id_str = payload.get("tid", "")
    user_id_str = payload.get("sub", "")

    try:
        tenant_id = uuid.UUID(tenant_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: bad tenant_id")
    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: bad user_id")

    async with container.session_factory() as session:
        tenant_repo = TenantRepository(session)
        user_repo = UserRepository(session)
        tenant = await tenant_repo.get_by_tenant_id(tenant_id)
        user = await user_repo.get_by_id(user_id, tenant_id)
        effective_role = await get_effective_role_permissions(session, tenant_id, user.role) if user else None

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserProfileResponse(
        user=UserInMeResponse(
            id=str(user.id),
            email=str(user.email),
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            tenant_id=str(user.tenant_id),
            is_active=user.is_active,
            supplier_id=str(user.supplier_id) if user.supplier_id else None,
            client_id=str(user.client_id) if user.client_id else None,
        ),
        tenant=TenantInMeResponse(
            id=str(tenant.id),
            name=tenant.name,
            slug=tenant.slug,
            plan=tenant.plan,
            is_active=tenant.is_active,
        ),
        permissions=sorted(effective_role.permissions) if effective_role else [],
    )


# ── Change Password ────────────────────────────────────────────────────────────


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    success: bool
    message: str


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    summary="Change current user's password",
)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """
    Change the authenticated user's password.

    Requires providing the current password for verification.
    New password must be at least 8 characters.
    """
    container = get_container(request)

    # Validate new password length
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long.",
        )

    async with container.session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id, tenant_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Verify current password
        if not container.password_hasher.verify(body.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect.",
            )

        # Hash and save new password
        user.hashed_password = container.password_hasher.hash(body.new_password)
        await session.commit()

    logger.info("Password changed successfully", extra={"user_id": str(user_id)})

    return ChangePasswordResponse(
        success=True,
        message="Password changed successfully.",
    )
