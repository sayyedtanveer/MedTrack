"""Correlation ID middleware for request tracing.
Requirements: 41.2
"""
from __future__ import annotations
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Extracts or generates a correlation ID and adds it to response headers.

    Reads X-Request-ID from incoming request headers (for client-supplied tracing).
    Falls back to a freshly generated UUID when no header is present.
    The ID is stored on request.state.correlation_id and echoed back in the
    response as X-Request-ID so clients can correlate requests and responses.

    Requirements: 41.2
    """

    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(self.HEADER) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        if HAS_STRUCTLOG:
            import structlog
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        response = await call_next(request)
        response.headers[self.HEADER] = correlation_id
        return response
