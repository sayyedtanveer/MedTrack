from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """
    Centralized error logging middleware.
    
    Wraps every request in a try/except to capture:
    1. All unhandled exceptions (those not caught by specific handlers)
    2. All handled exceptions (before they're converted to responses)
    
    For each exception:
    - Generates a trace_id (UUID) for end-to-end tracking
    - Calls ErrorLogger to capture and persist error details
    - Returns clean JSON error response with trace_id
    
    Response format:
    {
        "success": false,
        "error": {
            "message": "Human-readable error description",
            "code": "ERROR_CODE",
            "trace_id": "uuid-string"
        }
    }
    
    Placement: At TOP of middleware stack (outermost) to wrap entire pipeline.
    Integration: Accesses error_logger via request.app.state.container.error_logger
    
    Design philosophy:
    - Never blocks user response (silent failures with fallback)
    - Always returns trace_id for support ticket correlation
    - Respects existing status code mapping logic
    - Integrates with background queue if DB fails
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Wrap request with exception handling.
        
        Flow:
        1. Generate trace_id
        2. Try to process request normally (call_next)
        3. If any exception: log it, return clean error response
        4. Otherwise: return normal response
        """
        trace_id = str(uuid.uuid4())

        try:
            # Process request through entire middleware stack
            response = await call_next(request)
            return response

        except Exception as exc:
            # Capture exception details
            await self._handle_error(request, exc, trace_id)

            # Get mapped status code and error code
            from backend.app.infrastructure.logging.error_logger import ErrorLogger

            error_logger = getattr(getattr(request.app, "state", None), "container", None)
            if error_logger is None:
                status_code, error_code = (500, None)
            else:
                error_logger = error_logger.error_logger
                status_code, error_code = error_logger._map_exception_to_status_and_code(exc)

            # Build clean error response
            code_value = "INTERNAL_ERROR"
            if error_code is not None:
                code_value = getattr(error_code, "value", None) or "INTERNAL_ERROR"

            return JSONResponse(
                status_code=status_code,
                content={
                    "success": False,
                    "error": {
                        "message": self._get_user_friendly_message(exc, status_code),
                        "code": code_value,
                        "trace_id": trace_id,
                    },
                },
            )

    async def _handle_error(self, request: Request, exception: Exception, trace_id: str) -> None:
        """
        Delegate to ErrorLogger for detailed error capture.
        
        Implements fire-and-forget pattern:
        - Logs error asynchronously
        - Never blocks response
        - Errors in logging are silently caught
        """
        try:
            container = getattr(getattr(request.app, "state", None), "container", None)
            if container is None:
                return
            error_logger = getattr(container, "error_logger", None)
            if error_logger is None:
                return
            await error_logger.log_error(request, exception, trace_id)
        except Exception as logging_exc:
            # Error logger itself must never crash the request
            logger.error(
                "Error logging failed",
                extra={
                    "error": str(logging_exc),
                    "trace_id": trace_id,
                    "original_exception": type(exception).__name__,
                },
            )

    @staticmethod
    def _get_user_friendly_message(exc: Exception, status_code: int) -> str:
        """
        Convert exception to user-friendly message.
        
        Avoids exposing internal implementation details.
        """
        exc_type = type(exc).__name__
        exc_msg = str(exc)

        # Map by status code first
        if status_code == 400:
            return "Invalid request. Please check your input and try again."
        elif status_code == 401:
            if "auth" in exc_type.lower():
                return "Authentication failed. Please check your credentials."
            return "You are not authenticated. Please log in."
        elif status_code == 403:
            return "You do not have permission to access this resource."
        elif status_code == 404:
            return "The requested resource was not found."
        elif status_code == 409:
            return "A conflict occurred. Please check your data and try again."
        elif status_code >= 500:
            return "An unexpected error occurred. Please try again later."

        # Fallback: use exception message if safe, else generic
        if exc_msg and len(exc_msg) < 200 and is_safe_message(exc_msg):
            return exc_msg
        return "An error occurred processing your request."


def is_safe_message(msg: str) -> bool:
    """
    Check if exception message is safe to show to user.
    
    Filters out messages containing sensitive patterns like:
    - File paths
    - Database connection strings
    - Internal implementation details
    """
    unsafe_patterns = [
        "password",
        "secret",
        "token",
        "api_key",
        "database",
        "connection",
        "/home/",
        "/usr/",
        "/opt/",
        "C:\\",
    ]
    
    msg_lower = msg.lower()
    return not any(pattern in msg_lower for pattern in unsafe_patterns)
