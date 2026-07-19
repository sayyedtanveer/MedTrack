from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi.responses import JSONResponse

from backend.app.infrastructure.context.request_context import set_request_context
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}
_CLIENT_ALLOWED_PREFIXES = ("/api/v1/client",)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Resolves tenant_id from the Authorization JWT or X-Tenant-ID header
    and stores it in ContextVars.

    Does NOT enforce authentication — that's the auth dependency's job.
    Only extracts and stores tenant_id for logging and context purposes.
    
    Security: JWT tid claim takes precedence over X-Tenant-ID header to prevent
    tenant spoofing. X-Tenant-ID header is only used for machine-to-machine calls
    where JWT is not present.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        tenant_id: str | None = None

        # 1. Try to decode from JWT (preferred source of truth)
        payload: dict | None = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                container = request.app.state.container
                payload = container.jwt_handler.decode_token(token)
                # Use JWT tid claim as primary source
                tenant_id = payload.get("tid")
            except Exception:
                pass  # Will fail properly in auth dependency

        # 2. Fall back to X-Tenant-ID header (only for machine-to-machine calls)
        if not tenant_id:
            tenant_id = request.headers.get("X-Tenant-ID")

        # If we decoded a token, expose common identity fields on request.state
        if payload:
            try:
                user_id = payload.get("sub")
                role = payload.get("role")
                supplier_id = payload.get("sid")
                client_id = payload.get("cid")

                # Set ContextVars where possible
                if user_id:
                    set_request_context(user_id=user_id, tenant_id=tenant_id)

                # Expose on request.state for handlers that run before auth dependency
                try:
                    request.state.user = {"id": user_id, "role": role}
                    request.state.role = role
                    request.state.supplier_id = supplier_id
                    request.state.client_id = client_id
                    # keep legacy scope values
                    request.scope.setdefault("user_id", user_id)
                    request.scope.setdefault("tenant_id", tenant_id)
                    request.scope.setdefault("user_role", role)
                except Exception:
                    pass
            except Exception:
                pass

        if payload and str(payload.get("role", "")).lower() == "client":
            if request.url.path.startswith("/api/v1/") and not request.url.path.startswith(_CLIENT_ALLOWED_PREFIXES):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Client users can only access client portal endpoints"},
                )

        if tenant_id:
            set_request_context(tenant_id=tenant_id)
            # expose tenant_id on request.state for handlers that run before auth dependency
            try:
                request.state.tenant_id = tenant_id
            except Exception:
                pass
            logger.debug("Tenant resolved", extra={"tenant_id": tenant_id})

        return await call_next(request)
