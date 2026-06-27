from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.domain.tenant.value_objects.role import Role
from backend.app.infrastructure.context.request_context import set_request_context

security = HTTPBearer(auto_error=False)


def get_container(request: Request):
    return request.app.state.container


async def get_current_user_payload(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Extract and validate JWT; return decoded payload dict."""
    from backend.app.infrastructure.logging.logger import get_logger
    logger = get_logger(__name__)
    
    # If HTTPBearer doesn't find credentials, try to extract directly from header
    if not credentials:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        else:
            logger.warning(
                "Authentication failed: No credentials provided",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "has_auth_header": "authorization" in (k.lower() for k in request.headers.keys()),
                    "all_headers": {k: (v[:20] + "..." if len(v) > 20 else v) for k, v in request.headers.items()},
                }
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authentication token provided. Please include an Authorization header with a valid Bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    container = get_container(request)
    try:
        payload = container.jwt_handler.decode_token(credentials.credentials)
        logger.debug("JWT decoded successfully", extra={"role": payload.get("role"), "tid": payload.get("tid"), "sub": payload.get("sub")})
    except Exception as e:
        logger.error(f"JWT decode failed: {str(e)}", extra={"token_prefix": credentials.credentials[:20] if credentials else "NO_TOKEN"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update context vars with authenticated user info
    user_id = payload.get("sub")
    tenant_id = payload.get("tid")
    user_role = payload.get("role", "viewer")
    
    # Populate context vars used across async tasks and logging
    set_request_context(
        user_id=user_id,
        tenant_id=tenant_id,
    )

    # Inject easily accessible attributes into request.state for handlers/middleware
    # Keep `request.scope` untouched for compatibility; prefer `request.state` for app logic.
    try:
        # Basic user object (minimal, safe to include)
        request.state.user = {"id": user_id, "role": user_role}
        request.state.tenant_id = tenant_id
        request.state.role = user_role
        # optional supplier/client ids added by login handler as extra claims
        request.state.supplier_id = payload.get("sid")
        request.state.client_id = payload.get("cid")
    except Exception:
        # If request doesn't support state (very unlikely), silently ignore to avoid breaking auth
        pass

    # Backwards-compat: keep lightweight values on scope for middleware that read them
    request.scope["user_id"] = user_id
    request.scope["tenant_id"] = tenant_id
    request.scope["user_role"] = user_role

    return payload


async def get_current_user_id(
    payload: dict = Depends(get_current_user_payload),
) -> uuid.UUID:
    """Parse user_id from JWT payload with fallback for compatibility."""
    from backend.app.infrastructure.logging.logger import get_logger
    logger = get_logger(__name__)
    
    sub = payload.get("sub")
    if not sub:
        logger.warning("Missing sub claim in JWT", extra={"payload_keys": list(payload.keys())})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id (sub) claim"
        )
    
    try:
        return uuid.UUID(str(sub))
    except (ValueError, AttributeError, TypeError) as exc:
        logger.error("Invalid sub claim format", extra={"sub": sub, "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: user_id (sub) is not a valid UUID"
        ) from exc


async def get_current_tenant_id(
    payload: dict = Depends(get_current_user_payload),
) -> uuid.UUID:
    """Parse tenant_id from JWT payload with fallback for compatibility."""
    from backend.app.infrastructure.logging.logger import get_logger
    logger = get_logger(__name__)
    
    tid = payload.get("tid")
    if not tid:
        logger.warning("Missing tid claim in JWT", extra={"payload_keys": list(payload.keys())})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing tenant_id (tid) claim"
        )
    
    try:
        return uuid.UUID(str(tid))
    except (ValueError, AttributeError, TypeError) as exc:
        logger.error("Invalid tid claim format", extra={"tid": tid, "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: tenant_id (tid) is not a valid UUID"
        ) from exc


async def get_current_role(
    payload: dict = Depends(get_current_user_payload),
) -> str:
    """Parse role from JWT payload with fallback for compatibility."""
    from backend.app.infrastructure.logging.logger import get_logger
    logger = get_logger(__name__)
    
    role = payload.get("role")
    if not role or not isinstance(role, str):
        logger.warning("Missing or invalid role claim", extra={"role": role, "role_type": type(role).__name__})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing or invalid role claim"
        )
    
    return role
