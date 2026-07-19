"""
2FA API Routes

Endpoints for TOTP setup, verification, backup codes, and device trust management.
"""

from __future__ import annotations

import uuid
import base64
import hashlib
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from backend.app.infrastructure.persistence.repositories.user_repository import UserRepository
from backend.app.infrastructure.persistence.repositories.user_device_repository import UserDeviceRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.infrastructure.security.totp_service import TOTPService
from backend.app.infrastructure.security.jwt_claim_validator import (
    parse_user_claim,
    parse_tenant_claim,
)
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_user_payload,
    get_current_user_id,
    get_current_tenant_id,
)
from backend.app.interfaces.api.v1.schemas.auth_schemas import (
    Enable2FAResponse,
    Verify2FASetupRequest,
    Disable2FARequest,
    TwoFactorLoginRequest,
    BackupCodesResponse,
    LoginResponse,
    TwoFactorRecoveryRequest,
    TwoFactorRecoveryVerifyRequest,
)

router = APIRouter(prefix="/auth/2fa", tags=["2FA - Two-Factor Authentication"])


@router.post(
    "/enable",
    response_model=Enable2FAResponse,
    summary="Enable 2FA - Generate secret and backup codes",
)
async def enable_2fa(
    request: Request,
    payload: dict = Depends(get_current_user_payload),
) -> Enable2FAResponse:
    """
    Generate TOTP secret and backup codes for user.

    Returns QR code (base64 PNG) and backup codes.
    Next step: User scans QR or enters secret, then calls /verify-setup
    """
    container = get_container(request)
    user_id = parse_user_claim(payload)
    tenant_id = parse_tenant_claim(payload)

    async with container.session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.totp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA already enabled. Disable first to re-enable.",
            )

        # Generate TOTP secret
        secret = TOTPService.generate_secret()

        # Generate QR code URI and image
        uri = TOTPService.get_totp_uri(secret, user.email, issuer_name="MedTrack")
        qr_code_bytes = TOTPService.generate_qr_code(uri)
        qr_code_base64 = base64.b64encode(qr_code_bytes).decode("utf-8")

        # Generate backup codes
        backup_codes = TOTPService.generate_backup_codes(count=10)

        user.totp_secret = secret
        user.backup_codes = backup_codes
        user.updated_at = datetime.now(timezone.utc)
        session.add(user)
        await session.flush()

        return Enable2FAResponse(
            totp_secret=secret,
            qr_code_base64=qr_code_base64,
            backup_codes=backup_codes,
        )


@router.post(
    "/verify-setup",
    response_model=dict,
    summary="Verify 2FA setup with code",
)
async def verify_2fa_setup(
    body: Verify2FASetupRequest,
    request: Request,
    payload: dict = Depends(get_current_user_payload),
) -> dict:
    """
    Verify user can use authenticator app by validating a code.

    After this succeeds, 2FA is enabled and user will be prompted for code on login.
    Backup codes are stored in database.
    """
    container = get_container(request)
    user_id = parse_user_claim(payload)
    tenant_id = parse_tenant_claim(payload)

    async with container.session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.totp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA already enabled",
            )

        if not user.totp_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TOTP secret not initialized. Call /enable first.",
            )

        # Verify the code
        if not TOTPService.verify_totp(user.totp_secret, body.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code")

        # Keep the codes returned during /enable so users do not receive one set
        # on-screen and a different set after verification.
        backup_codes = user.backup_codes or TOTPService.generate_backup_codes(count=10)
        user.totp_enabled = True
        user.backup_codes = backup_codes
        user.updated_at = datetime.now(timezone.utc)

        session.add(user)
        await session.flush()

        return {
            "success": True,
            "message": "2FA enabled successfully",
            "backup_codes": backup_codes,
        }


@router.post(
    "/disable",
    summary="Disable 2FA for user",
)
async def disable_2fa(
    body: Disable2FARequest,
    request: Request,
    payload: dict = Depends(get_current_user_payload),
) -> dict:
    """
    Disable 2FA after password verification.

    Requires user's password for security (similar to account deletion).
    """
    container = get_container(request)
    user_id = parse_user_claim(payload)
    tenant_id = parse_tenant_claim(payload)

    async with container.session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Verify password
        if not container.password_hasher.verify(body.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

        # Disable 2FA
        user.totp_enabled = False
        user.totp_secret = None
        user.backup_codes = []
        user.updated_at = datetime.now(timezone.utc)

        session.add(user)
        await session.flush()

        return {
            "success": True,
            "message": "2FA disabled successfully",
        }


@router.get(
    "/backup-codes",
    response_model=BackupCodesResponse,
    summary="Get unused backup codes",
)
async def get_backup_codes(
    request: Request,
    payload: dict = Depends(get_current_user_payload),
) -> BackupCodesResponse:
    """
    Retrieve current unused backup codes.

    User can regenerate codes by disabling and re-enabling 2FA.
    """
    container = get_container(request)
    user_id = parse_user_claim(payload)

    async with container.session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not user.totp_enabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not enabled")

        return BackupCodesResponse(backup_codes=user.backup_codes or [])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with email, password, and 2FA code",
)
async def login_with_2fa(
    body: TwoFactorLoginRequest,
    request: Request,
) -> LoginResponse:
    """
    Complete login flow with 2FA verification.

    Can provide either:
    - TOTP code (6 digits)
    - Backup code (format: XXXX-XXXX)
    - Nothing if 2FA not enabled (falls back to password-only)
    """
    container = get_container(request)

    try:
        tenant_id = uuid.UUID(body.tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant_id format")

    async with container.session_factory() as session:
        user_repo = UserRepository(session)

        # Find user by email + tenant
        user = await user_repo.get_by_email_and_tenant(body.email, tenant_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Verify password
        if not container.password_hasher.verify(body.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Check if 2FA enabled and code provided
        if user.totp_enabled:
            if not body.code:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="2FA required",
                    headers={"X-Requires-2FA": "true"},
                )

            # Try TOTP code first
            if len(body.code) == 6 and body.code.isdigit():
                if not TOTPService.verify_totp(user.totp_secret, body.code):
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code")
            else:
                # Try backup code
                is_valid, remaining_codes = TOTPService.verify_backup_code(body.code, user.backup_codes)
                if not is_valid:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid backup code")

                # Update backup codes (remove used code)
                user.backup_codes = remaining_codes
                user.updated_at = datetime.now(timezone.utc)
                session.add(user)

        # Generate JWT
        token_data = {
            "sub": str(user.id),
            "tid": str(tenant_id),
            "role": user.role,
        }
        access_token = container.jwt_handler.create_access_token(
            user_id=token_data["sub"],
            tenant_id=token_data["tid"],
            role=token_data["role"],
        )

        # Handle device trust if requested
        if body.remember_device:
            device_repo = UserDeviceRepository(session)
            device_fingerprint = _generate_device_fingerprint(request, body.device_name)

            # Check if device already trusted
            existing_device = await device_repo.get_by_fingerprint(user.id, device_fingerprint)

            if existing_device:
                # Update trust expiry
                existing_device.trusted_until = datetime.now(timezone.utc) + timedelta(days=30)
                existing_device.last_used_at = datetime.now(timezone.utc)
                session.add(existing_device)
            else:
                # Create new trusted device
                device = device_repo.create_user_device(
                    user_id=user.id,
                    tenant_id=tenant_id,
                    device_fingerprint=device_fingerprint,
                    device_name=body.device_name or "Unnamed Device",
                    ip_address=_get_client_ip(request),
                    trusted_until=datetime.now(timezone.utc) + timedelta(days=30),
                )
                session.add(device)

            await session.flush()

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=str(user.id),
            tenant_id=str(tenant_id),
            email=user.email,
            role=user.role,
            full_name=f"{user.first_name} {user.last_name}",
        )


@router.post(
    "/recover",
    summary="Request account recovery via email",
)
async def request_recovery(
    body: TwoFactorRecoveryRequest,
    background_tasks: BackgroundTasks,
    request: Request,
) -> dict:
    """
    Request recovery code sent to registered email.

    Use when user loses access to authenticator app and backup codes.
    Admin will receive request and must approve recovery.
    """
    # This is a placeholder - full implementation requires:
    # 1. Email service for sending recovery codes
    # 2. Admin approval workflow
    # 3. Recovery code storage in DB
    # For MVP: Just acknowledge request

    return {
        "success": True,
        "message": "Recovery request received. Check your email and contact support if needed.",
    }


def _generate_device_fingerprint(request: Request, device_name: Optional[str] = None) -> str:
    """
    Generate a fingerprint for the device based on:
    - User-Agent
    - Accept-Language
    - Device name (if provided)

    This is a simplified approach. Production systems might use more sophisticated
    device fingerprinting libraries.
    """
    user_agent = request.headers.get("user-agent", "")
    accept_language = request.headers.get("accept-language", "")
    name_part = device_name or ""

    fingerprint_str = f"{user_agent}|{accept_language}|{name_part}"
    fingerprint_hash = hashlib.sha256(fingerprint_str.encode()).hexdigest()

    return fingerprint_hash


def _get_client_ip(request: Request) -> str:
    """
    Extract client IP from request, checking for proxy headers.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.client.host if request.client else "unknown"
