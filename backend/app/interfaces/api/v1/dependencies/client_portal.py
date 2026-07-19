from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from backend.app.interfaces.api.v1.dependencies.auth import get_current_user_payload
from backend.app.infrastructure.security.jwt_claim_validator import parse_client_claim


async def require_client_role(
    payload: dict = Depends(get_current_user_payload),
) -> dict:
    if str(payload.get("role", "")).lower() != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client portal access requires a client account",
        )
    return payload


async def require_client_id(
    payload: dict = Depends(require_client_role),
) -> uuid.UUID:
    """Safely parse client_id from JWT payload using centralized validator."""
    cid = parse_client_claim(payload)
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client portal: user must be linked to a client",
        )
    return cid
