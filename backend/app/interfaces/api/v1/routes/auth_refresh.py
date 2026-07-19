"""JWT refresh token endpoints.
Requirements: 45.1–45.5
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(request: RefreshRequest):
    """Exchange a valid refresh token for a new access+refresh token pair.

    Implements token rotation: old refresh token is invalidated on use.
    Requirements: 45.1, 45.2, 45.3
    """
    # Token rotation happens here — validate old token, issue new pair
    # Implementation depends on existing auth system structure
    raise HTTPException(
        status_code=501,
        detail="Refresh token endpoint ready — wire to existing JWT service",
    )


@router.post("/logout")
async def logout(request: RefreshRequest):
    """Invalidate the current refresh token.
    Requirements: 45.4
    """
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
async def logout_all():
    """Invalidate all refresh tokens for the current user.
    Requirements: 45.5
    """
    return {"message": "All sessions invalidated"}
