"""
Centralized JWT Claim Validation Utility

Provides safe, enterprise-grade validation for JWT claims with proper error handling.
Prevents UUID parsing errors from bubbling up as generic 400 VALIDATION_ERROR.

All authentication dependencies should use these utilities instead of direct
uuid.UUID() calls on payload data.
"""

from __future__ import annotations

import uuid
from typing import Optional, Dict, Any

from fastapi import HTTPException, status

from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class JWTClaimValidationError(Exception):
    """Raised when JWT claim validation fails."""
    def __init__(self, message: str, error_code: str = "INVALID_TOKEN_CLAIMS"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


def validate_jwt_claims(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that required JWT claims exist and have valid structure.
    
    Required claims:
    - sub (subject/user_id): Must be a valid UUID string
    - tid (tenant_id): Must be a valid UUID string
    - role: Must be a non-empty string
    
    Optional claims:
    - sid (supplier_id): If present, must be a valid UUID string
    - cid (client_id): If present, must be a valid UUID string
    
    Args:
        payload: Decoded JWT payload dictionary
        
    Returns:
        Validated payload dictionary
        
    Raises:
        HTTPException: With 401 status for invalid/missing claims
    """
    # Validate required claims exist
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: empty payload"
        )
    
    # Validate sub (user_id)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id (sub) claim"
        )
    
    # Validate tid (tenant_id)
    tid = payload.get("tid")
    if not tid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing tenant_id (tid) claim"
        )
    
    # Validate role
    role = payload.get("role")
    if not role or not isinstance(role, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing or invalid role claim"
        )
    
    # Validate UUID formats (this is where the original bug was)
    try:
        uuid.UUID(str(sub))
    except (ValueError, AttributeError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: user_id (sub) is not a valid UUID"
        ) from exc
    
    try:
        uuid.UUID(str(tid))
    except (ValueError, AttributeError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: tenant_id (tid) is not a valid UUID"
        ) from exc
    
    # Validate optional claims if present
    sid = payload.get("sid")
    if sid:
        try:
            uuid.UUID(str(sid))
        except (ValueError, AttributeError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: supplier_id (sid) is not a valid UUID"
            ) from exc
    
    cid = payload.get("cid")
    if cid:
        try:
            uuid.UUID(str(cid))
        except (ValueError, AttributeError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: client_id (cid) is not a valid UUID"
            ) from exc
    
    return payload


def parse_user_claim(payload: Dict[str, Any]) -> uuid.UUID:
    """
    Safely parse user_id (sub) claim from JWT payload.
    
    Args:
        payload: Decoded JWT payload dictionary
        
    Returns:
        user_id as UUID
        
    Raises:
        HTTPException: With 401 status for invalid/missing sub claim
    """
    sub = payload.get("sub")
    if not sub:
        logger.warning("JWT validation failed: missing sub claim", extra={"payload_keys": list(payload.keys())})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id (sub) claim"
        )
    
    try:
        user_id = uuid.UUID(str(sub))
        logger.debug("Successfully parsed user_id from JWT", extra={"user_id": str(user_id)})
        return user_id
    except (ValueError, AttributeError, TypeError) as exc:
        logger.warning("JWT validation failed: invalid sub claim format", extra={"sub": sub, "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: user_id (sub) is not a valid UUID"
        ) from exc


def parse_tenant_claim(payload: Dict[str, Any]) -> uuid.UUID:
    """
    Safely parse tenant_id (tid) claim from JWT payload.
    
    Args:
        payload: Decoded JWT payload dictionary
        
    Returns:
        tenant_id as UUID
        
    Raises:
        HTTPException: With 401 status for invalid/missing tid claim
    """
    tid = payload.get("tid")
    if not tid:
        logger.warning("JWT validation failed: missing tid claim", extra={"payload_keys": list(payload.keys())})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing tenant_id (tid) claim"
        )
    
    try:
        tenant_id = uuid.UUID(str(tid))
        logger.debug("Successfully parsed tenant_id from JWT", extra={"tenant_id": str(tenant_id)})
        return tenant_id
    except (ValueError, AttributeError, TypeError) as exc:
        logger.warning("JWT validation failed: invalid tid claim format", extra={"tid": tid, "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: tenant_id (tid) is not a valid UUID"
        ) from exc


def parse_role_claim(payload: Dict[str, Any]) -> str:
    """
    Safely parse role claim from JWT payload.
    
    Args:
        payload: Decoded JWT payload dictionary
        
    Returns:
        role as string
        
    Raises:
        HTTPException: With 401 status for invalid/missing role claim
    """
    role = payload.get("role")
    if not role or not isinstance(role, str):
        logger.warning("JWT validation failed: missing or invalid role claim", extra={"role": role, "role_type": type(role).__name__})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing or invalid role claim"
        )
    
    logger.debug("Successfully parsed role from JWT", extra={"role": role})
    return role


def parse_supplier_claim(payload: Dict[str, Any]) -> Optional[uuid.UUID]:
    """
    Safely parse optional supplier_id (sid) claim from JWT payload.
    
    Args:
        payload: Decoded JWT payload dictionary
        
    Returns:
        supplier_id as UUID, or None if not present
        
    Raises:
        HTTPException: With 401 status if sid is present but invalid
    """
    sid = payload.get("sid")
    if not sid:
        return None
    
    try:
        return uuid.UUID(str(sid))
    except (ValueError, AttributeError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: supplier_id (sid) is not a valid UUID"
        ) from exc


def parse_client_claim(payload: Dict[str, Any]) -> Optional[uuid.UUID]:
    """
    Safely parse optional client_id (cid) claim from JWT payload.
    
    Args:
        payload: Decoded JWT payload dictionary
        
    Returns:
        client_id as UUID, or None if not present
        
    Raises:
        HTTPException: With 401 status if cid is present but invalid
    """
    cid = payload.get("cid")
    if not cid:
        return None
    
    try:
        return uuid.UUID(str(cid))
    except (ValueError, AttributeError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: client_id (cid) is not a valid UUID"
        ) from exc


def parse_all_claims(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse all standard claims from JWT payload into validated types.
    
    Returns dictionary with:
    - user_id: UUID
    - tenant_id: UUID
    - role: str
    - supplier_id: Optional[UUID]
    - client_id: Optional[UUID]
    
    Args:
        payload: Decoded JWT payload dictionary
        
    Returns:
        Dictionary with parsed claims
        
    Raises:
        HTTPException: With 401 status for invalid/missing claims
    """
    return {
        "user_id": parse_user_claim(payload),
        "tenant_id": parse_tenant_claim(payload),
        "role": parse_role_claim(payload),
        "supplier_id": parse_supplier_claim(payload),
        "client_id": parse_client_claim(payload),
    }
