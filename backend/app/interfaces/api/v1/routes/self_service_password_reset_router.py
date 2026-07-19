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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
import secrets
from datetime import datetime, timedelta, timezone
import hashlib

from backend.app.config import settings
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
    
    **Response:**
    - In development: includes reset_token for testing
    - In production: only returns success message
    """
    
    email = request_body.email
    
    # Email always gets generic response (security: don't confirm email exists)
    response = ForgotPasswordResponse(
        success=True,
        message="If an account exists with this email, a password reset link has been sent."
    )
    
    try:
        # Find user by email (any tenant, any role)
        stmt = select(UserModel).where(UserModel.email == email)
        result = await session.execute(stmt)
        try:
            user = result.scalar_one_or_none()
        except Exception:
            # In case of duplicate rows (e.g. legacy data), fall back to the first active row.
            rows = result.scalars().all()
            user = next((row for row in rows if getattr(row, "is_active", True)), None)
            if user is None and rows:
                user = rows[0]
        
        if not user:
            # Still return generic response (don't leak that user doesn't exist)
            return response
        
        # Expire any existing reset tokens for this user
        stmt = select(PasswordResetTokenModel).where(
            (PasswordResetTokenModel.user_id == user.id) &
            (PasswordResetTokenModel.used_at.is_(None))
        )
        result = await session.execute(stmt)
        old_tokens = result.scalars().all()
        
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
                body=f"You requested a password reset. Use this link to reset your password: {reset_url}\n\nThis link expires in 1 hour.\n\nIf you didn't request this, ignore this email.",
                html_body=f"<h2>Password Reset</h2><p>You requested a password reset for your MedTrack account.</p><p><a href='{reset_url}'>Click here to reset your password</a></p><p>This link expires in 1 hour.</p><p>If you didn't request this, you can safely ignore this email.</p>",
            )
        except Exception as e:
            logger.warning(f"Failed to send password reset email to {email}: {e}")
        
        # In development, return token for testing
        if settings.environment.lower() != "production":
            response.reset_token = reset_token
        
        return response
        
    except Exception as e:
        print(f"Error in request_password_reset: {e}")
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
        
        # Get user
        user = await session.get(UserModel, token_row.user_id)
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
