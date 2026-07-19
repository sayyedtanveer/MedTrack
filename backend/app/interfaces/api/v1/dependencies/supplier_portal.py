from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from backend.app.interfaces.api.v1.dependencies.auth import get_current_user_payload
from backend.app.infrastructure.security.jwt_claim_validator import parse_supplier_claim


async def require_supplier_id(
    payload: dict = Depends(get_current_user_payload),
) -> uuid.UUID:
    """Safely parse supplier_id from JWT payload using centralized validator."""
    sid = parse_supplier_claim(payload)
    if not sid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supplier portal: user must be linked to a supplier",
        )
    return sid
