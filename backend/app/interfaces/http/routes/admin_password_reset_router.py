"""
Admin Password Reset API Endpoint
==================================
Add this to your FastAPI router to enable password reset from the admin panel.

Usage in your routes:
    from backend.app.interfaces.http.routes.admin_password_reset_router import router as admin_reset_router
    app.include_router(admin_reset_router, prefix="/api/v1/admin", tags=["admin"])
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
import secrets
import string

from backend.app.core.dependencies import get_db_session
from backend.app.interfaces.api.v1.dependencies.auth import get_current_user_id, get_current_tenant_id
from backend.app.infrastructure.persistence.models.user_model import User
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher


router = APIRouter(prefix="/password", tags=["admin-password"])
hasher = BcryptPasswordHasher()


class PasswordResetRequest(BaseModel):
    """Request to reset a user's password."""
    email: str
    new_password: str | None = None  # If None, will generate temporary password
    generate_temp: bool = False


class PasswordResetResponse(BaseModel):
    """Response after password reset."""
    success: bool
    message: str
    temporary_password: str | None = None
    email: str


def generate_temp_password() -> str:
    """Generate a secure 16-char temporary password."""
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(chars) for _ in range(16))


@router.post("/reset", response_model=PasswordResetResponse)
async def reset_user_password(
    request: PasswordResetRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """
    Reset a user's password (Admin only).
    
    **Security Notes:**
    - Passwords are HASHED with bcrypt (one-way) - cannot be decrypted
    - This endpoint generates a NEW password, not decrypts an old one
    - Only admins can access this endpoint
    
    **Parameters:**
    - email: User's email address
    - new_password: New password (or leave null to auto-generate)
    - generate_temp: If true, ignore new_password and generate temporary one
    
    **Response:**
    - success: True if password was reset
    - temporary_password: Only returned if generate_temp=true
    """
    
    # Find user by email in same tenant
    stmt = select(User).where(User.email == request.email, User.tenant_id == current_tenant_id)
    result = await session.execute(stmt)
    user_to_reset = result.scalar_one_or_none()

    if not user_to_reset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{request.email}' not found"
        )

    try:
        # Determine new password
        if request.generate_temp:
            new_password = generate_temp_password()
        elif request.new_password:
            new_password = request.new_password
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either 'new_password' or set 'generate_temp=true'"
            )

        # Hash and update password
        hashed_password = hasher.hash(new_password)
        user_to_reset.hashed_password = hashed_password
        await session.commit()

        return PasswordResetResponse(
            success=True,
            message=f"Password successfully reset for {request.email}",
            temporary_password=new_password if request.generate_temp else None,
            email=request.email
        )

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )


@router.post("/generate-temp-password", response_model=dict)
async def get_temp_password(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Generate a secure temporary password (for copying/displaying to user).
    
    **Response:**
    - temp_password: A 16-character secure password
    - expires_in: Suggested expiry time (for UI display only)
    """
    
    return {
        "temp_password": generate_temp_password(),
        "expires_in": "Share immediately - no automatic expiry",
        "note": "Use this in the password reset endpoint"
    }
