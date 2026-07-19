from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ── Request schemas ────────────────────────────────────────────────────────────
class RegisterTenantRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Company name")
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$", description="URL-safe identifier")
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, max_length=128)
    admin_first_name: str = Field(..., min_length=1, max_length=100)
    admin_last_name: str = Field(..., min_length=1, max_length=100)
    plan: str = Field(default="starter", pattern=r"^(starter|professional|enterprise)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
    tenant_id: str = Field(..., description="UUID of the tenant to authenticate against")


# ── Response schemas ───────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Nested user object returned inside /auth/me
class UserInMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    tenant_id: str
    is_active: bool
    # Optional portal links (populated from JWT claims when present)
    supplier_id: Optional[str] = None
    client_id: Optional[str] = None


# Nested tenant object returned inside /auth/me
class TenantInMeResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    is_active: bool


# Shape expected by frontend MeResponse type
class UserProfileResponse(BaseModel):
    user: UserInMeResponse
    tenant: TenantInMeResponse
    permissions: List[str] = []


class RegisterTenantResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    slug: str
    user_id: str
    email: str
    role: str
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    tenant_id: str
    email: str
    role: str
    full_name: str


# ── 2FA Setup & Verification ───────────────────────────────────────────────────
class Enable2FARequest(BaseModel):
    """Request to enable 2FA for user"""
    pass  # No parameters needed - just triggers setup


class Enable2FAResponse(BaseModel):
    """Response with QR code and backup codes"""
    totp_secret: str  # Base32 encoded secret (for manual entry)
    qr_code_base64: str  # Base64 encoded PNG image
    backup_codes: list[str]  # One-time backup codes


class Verify2FASetupRequest(BaseModel):
    """Request to verify 2FA setup with code"""
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$", description="6-digit TOTP code")


class Disable2FARequest(BaseModel):
    """Request to disable 2FA - requires password verification"""
    password: str = Field(..., min_length=1, description="User's password for security")


class TwoFactorLoginRequest(BaseModel):
    """Complete login with email, password, and 2FA verification"""
    email: EmailStr
    password: str = Field(..., min_length=1)
    tenant_id: str = Field(..., description="UUID of the tenant")
    code: Optional[str] = Field(None, min_length=6, max_length=6, pattern=r"^\d{6}$|^[A-Z0-9\-]{11}$", description="6-digit TOTP code OR backup code")
    remember_device: bool = Field(False, description="Remember this device for 30 days")
    device_name: Optional[str] = Field(None, max_length=255, description="Friendly name for device (e.g., 'Chrome on Windows')")


class BackupCodesResponse(BaseModel):
    """List of unused backup codes"""
    backup_codes: list[str]


class TwoFactorRecoveryRequest(BaseModel):
    """Request to recover account using email verification"""
    email: EmailStr
    tenant_id: str


class TwoFactorRecoveryVerifyRequest(BaseModel):
    """Verify recovery code sent to email"""
    email: EmailStr
    recovery_code: str = Field(..., min_length=1, description="Recovery code sent to email")
    tenant_id: str
