from __future__ import annotations

import time
import traceback
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.infrastructure.context.request_context import (
    clear_request_context,
    set_request_context,
)
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Outermost middleware — runs first on request, last on response.

    Responsibilities:
    1. Generate correlation_id for the request
    2. Set request context (correlation_id, ip_address) in ContextVars
    3. Log request start and end with timing, user_id, tenant_id
    4. Add X-Duration-Ms response header
    5. Log unhandled exceptions at ERROR with traceback and request context
    6. Clear context vars after response
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = str(uuid.uuid4())
        ip_address = request.client.host if request.client else "unknown"
        start = time.perf_counter()

        # Best-effort extract tenant/user from JWT so logs include identity
        user_id: str | None = None
        tenant_id: str | None = None

        try:
            tenant_id = request.headers.get("X-Tenant-ID")
            logger.info("Request headers Authorization=%s, X-Tenant-ID=%s", request.headers.get("Authorization"), tenant_id)
            payload = None
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                try:
                    # Prefer container's JWT handler when available
                    jwt_handler = None
                    try:
                        container = request.app.state.container
                        jwt_handler = container.jwt_handler
                    except Exception:
                        jwt_handler = None

                    if jwt_handler is None:
                        from backend.app.config import get_settings
                        from backend.app.infrastructure.security.jwt_handler import JWTHandler

                        settings = get_settings()
                        jwt_handler = JWTHandler(
                            secret_key=settings.jwt_secret_key,
                            algorithm=settings.jwt_algorithm,
                            expiry_minutes=settings.jwt_expiry_minutes,
                        )

                    payload = jwt_handler.decode_token(token)
                    # Prefer JWT tid claim over X-Tenant-ID header for security
                    tenant_id = payload.get("tid") or tenant_id
                    logger.info(
                        "Decoded JWT payload tid=%s role=%s sid=%s sub=%s",
                        payload.get("tid"),
                        payload.get("role"),
                        payload.get("sid"),
                        payload.get("sub"),
                    )
                except Exception as exc:
                    logger.exception("JWT decode failed: %s", exc)
                    payload = None

            if payload:
                user_id = payload.get("sub")
                role = payload.get("role")
                supplier_id = payload.get("sid")
                # populate ContextVars and request.state for logging
                if user_id or tenant_id:
                    set_request_context(tenant_id=tenant_id, user_id=user_id)
                try:
                    request.state.tenant_id = tenant_id
                    request.state.user = {"id": user_id, "role": role}
                    request.state.role = role
                    request.state.supplier_id = supplier_id
                    # keep legacy scope values for compatibility
                    request.scope.setdefault("user_id", user_id)
                    request.scope.setdefault("tenant_id", tenant_id)
                    request.scope.setdefault("user_role", role)
                except Exception:
                    pass

        except Exception:
            pass

        # Set context vars — available globally for this request
        set_request_context(
            correlation_id=correlation_id,
            ip_address=ip_address,
        )

        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "ip": ip_address,
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.error(
                "Unhandled exception during request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "traceback": traceback.format_exc(),
                },
            )
            clear_request_context()
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )

        # Inject correlation_id and timing into response headers for client-side tracing
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Duration-Ms"] = str(duration_ms)

        clear_request_context()
        return response
