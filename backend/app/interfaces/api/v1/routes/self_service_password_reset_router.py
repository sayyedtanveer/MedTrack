"""
Self-Service Password Reset for Admin/Internal Users
=====================================================
Allows users to reset their own passwords if they forget them.
Email verification is required for security.

This is different from the admin tool (admin_password_reset.py) which is for:
  - Admins resetting OTHER users' passwords

This endpoint is for:
  - Any user resetting their OWN password (forgot their current password)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import secrets
from datetime import datetime, timedelta, timezone
import hashlib
import uuid

from backend.app.config import settings
from backend.app.domain.shared.exceptions.domain_exception import DomainException
from backend.app.domain.tenant.value_objects.email import Email
from backend.app.infrastructure.persistence.repositories.tenant_repository import TenantRepository
from backend.app.infrastructure.persistence.repositories.user_repository import UserRepository
from backend.app.infrastructure.logging.logger import get_logger
from backend.app.infrastructure.persistence.models.user_model import (
    UserModel,
    PasswordResetTokenModel,
)
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher

router = APIRouter(prefix="/forgot-password", tags=["password-reset"])

logger = get_logger(__name__)


def _get_container(request: Request):
    return request.app.state.container


async def _get_db_session(request: Request):
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session


hasher = BcryptPasswordHasher()


class ForgotPasswordRequest(BaseModel):
    """Request to start password reset process."""
    email: EmailStr
    tenant_id: Optional[str] = None
    workspace_slug: str | None = Field(None, min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")


class ForgotPasswordResponse(BaseModel):
    """Response after requesting password reset."""
    success: bool
    message: str
    reset_token: str | None = None  # Only in development mode


class ResetPasswordRequest(BaseModel):
    """Request to complete password reset."""
    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    """Response after resetting password."""
    success: bool
    message: str


def _hash_token(token: str) -> str:
    """Hash token for safe storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def _utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


@router.post("/request", response_model=ForgotPasswordResponse)
async def request_password_reset(
    request_body: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Request a password reset (self-service).

    **Security Notes:**
    - Sends reset token via email (not exposed in response in production)
    - Token expires in 1 hour
    - Works for all user roles (admin, user, etc.)
    - Does NOT disclose if email exists (prevents user enumeration)
    - When tenant_id is provided the lookup is scoped to that tenant only,
      preventing cross-tenant password reset collisions.

    **Response:**
    - In development: includes reset_token for testing
    - In production: only returns success message
    """

    email = request_body.email

    # Generic response — never reveal whether the email exists
    response = ForgotPasswordResponse(
        success=True,
        message="If an account exists with this email, a password reset link has been sent.",
    )

    try:
        tenant_uuid = None
        try:
            normalized_email = Email(address=email)
            if request_body.tenant_id is not None:
                tenant_uuid = uuid.UUID(request_body.tenant_id)
        except (DomainException, ValueError):
            return response

        tenant_repo = TenantRepository(session)
        if request_body.workspace_slug is not None:
            workspace = await tenant_repo.get_by_slug(request_body.workspace_slug)
            if workspace is None or (tenant_uuid is not None and workspace.id != tenant_uuid):
                return response
            tenant_uuid = workspace.id
        elif tenant_uuid is None:
            tenant_uuid = await UserRepository(session).resolve_unique_workspace(normalized_email)
        if tenant_uuid is None or await tenant_repo.get_by_tenant_id(tenant_uuid) is None:
            return response

        matches = (await session.scalars(select(UserModel).where(
            func.lower(UserModel.email) == str(normalized_email),
            UserModel.tenant_id == tenant_uuid,
            UserModel.is_deleted.is_(False),
        ).limit(2))).all()
        if len(matches) != 1 or not matches[0].is_active:
            return response
        user = matches[0]

        # Expire any existing unused reset tokens for this user
        existing_stmt = select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id,
            PasswordResetTokenModel.tenant_id == tenant_uuid,
            PasswordResetTokenModel.used_at.is_(None),
        )
        existing_result = await session.execute(existing_stmt)
        old_tokens = existing_result.scalars().all()

        for token_row in old_tokens:
            token_row.used_at = _utc_now()

        # Create new reset token
        reset_token = secrets.token_urlsafe(32)
        token_model = PasswordResetTokenModel(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=_hash_token(reset_token),
            expires_at=_utc_now() + timedelta(hours=1),
        )
        session.add(token_model)
        await session.commit()

        # Send password reset email
        email_service = request.app.state.container.email_service
        reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"
        try:
            await email_service.send_email(
                to=user.email,
                subject="MedTrack - Password Reset Request",
                body=(
                    f"You requested a password reset. Use this link to reset your password:\n\n"
                    f"{reset_url}\n\n"
                    f"This link expires in 1 hour.\n\n"
                    f"If you didn't request this, ignore this email."
                ),
                html_body=(
                    f"<h2>Password Reset</h2>"
                    f"<p>You requested a password reset for your MedTrack account.</p>"
                    f"<p><a href='{reset_url}'>Click here to reset your password</a></p>"
                    f"<p>This link expires in 1 hour.</p>"
                    f"<p>If you didn't request this, you can safely ignore this email.</p>"
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to send password reset email to {email}: {e}")

        # In development, return token for testing
        if settings.environment.lower() != "production":
            response.reset_token = reset_token

        return response

    except Exception as e:
        logger.error(f"Error in request_password_reset: {e}")
        # Still return generic response
        return response


@router.post("/reset", response_model=ResetPasswordResponse)
async def reset_password(
    request_body: ResetPasswordRequest,
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Complete the password reset process.
    
    **Parameters:**
    - token: Reset token (from email link)
    - new_password: New password (must be strong)
    
    **Response:**
    - success: True if password was reset
    - message: Result message
    """
    
    try:
        token_hash = _hash_token(request_body.token)
        
        # Find unused, non-expired token
        stmt = select(PasswordResetTokenModel).where(
            (PasswordResetTokenModel.token_hash == token_hash) &
            (PasswordResetTokenModel.used_at.is_(None)) &
            (PasswordResetTokenModel.expires_at > _utc_now())
        )
        result = await session.execute(stmt)
        token_row = result.scalar_one_or_none()
        
        if not token_row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token is invalid or expired"
            )
        
        user = await session.scalar(select(UserModel).where(
            UserModel.id == token_row.user_id,
            UserModel.tenant_id == token_row.tenant_id,
            UserModel.is_deleted.is_(False),
            UserModel.is_active.is_(True),
        ))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        user.hashed_password = hasher.hash(request_body.new_password)
        user.updated_at = _utc_now()
        
        # Mark token as used
        token_row.used_at = _utc_now()
        
        await session.commit()
        
        return ResetPasswordResponse(
            success=True,
            message="Password has been reset successfully. You can now log in."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting password: {str(e)}"
        )
