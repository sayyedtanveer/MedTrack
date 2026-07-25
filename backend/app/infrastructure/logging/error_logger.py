from __future__ import annotations

import json
import traceback
import uuid
from typing import Optional, Any, Dict
from urllib.parse import parse_qs

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.infrastructure.context.request_context import get_request_context
from backend.app.infrastructure.logging.logger import get_logger
from backend.app.infrastructure.logging.models import ErrorLogModel, ErrorCode
from backend.app.infrastructure.logging.repository import ErrorLogRepository

logger = get_logger(__name__)

# Sensitive fields to filter from request body and query parameters
SENSITIVE_BODY_FIELDS = {
    "password",
    "confirm_password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
}

# Sensitive headers to filter
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "x-api-key",
}

# Maximum request body size to log (5KB)
MAX_REQUEST_BODY_SIZE = 5 * 1024


class ErrorLogger:
    """
    Centralized error logging service.
    
    Captures all exceptions with:
    - Traceback extraction (file name, line number, short stack)
    - Request details (method, path, body, headers, query params)
    - Sensitive data filtering (passwords, tokens, authorization)
    - Body truncation (5KB limit with flag)
    - Context enrichment (tenant_id, user_id, correlation_id)
    - Status code mapping to ErrorCode enum
    
    Implements hybrid async logging:
    1. Try immediate DB save
    2. If DB fails, queue to background task for retry
    
    Never blocks user response (silent failure + fallback queue).
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """
        Initialize error logger.
        
        Args:
            session_factory: AsyncSessionMaker from create_session_factory()
        """
        self._session_factory = session_factory
        self._repository = ErrorLogRepository(session_factory)

    async def log_error(
        self, request: Request, exception: Exception, trace_id: str
    ) -> None:
        """
        Capture and persist an error to database.
        
        Orchestrates:
        1. Extract traceback (file_name, line_number, stack_trace)
        2. Extract request data (path, method, headers, body, query_params)
        3. Extract context (tenant_id, user_id, correlation_id)
        4. Determine status_code and error_code
        5. Filter sensitive data
        6. Truncate body if needed
        7. Save to database (with fallback queue on failure)
        
        Args:
            request: FastAPI Request object
            exception: Exception that was caught
            trace_id: Unique trace ID for this error (UUID string)
        """
        try:
            # Extract traceback information
            file_name, line_number, stack_trace = await self._extract_traceback(exception)

            # Extract request information
            path = request.url.path
            method = request.method
            ip_address = request.client.host if request.client else "unknown"

            # Extract and filter request body
            request_body, request_body_truncated = await self._extract_request_body(
                request
            )

            # Extract and filter query parameters
            query_params = await self._extract_query_params(request)

            # Extract and filter headers
            headers = self._extract_headers(request)

            # Extract context from ContextVars
            ctx = get_request_context()
            tenant_id = uuid.UUID(ctx.tenant_id) if ctx.tenant_id else None
            user_id = uuid.UUID(ctx.user_id) if ctx.user_id else None

            # Determine status code and error code
            status_code, error_code = self._map_exception_to_status_and_code(exception)

            # For 5xx, print full traceback to logs to make debugging possible in dev/tests
            if status_code >= 500:
                logger.error(
                    "INTERNAL_ERROR captured",
                    extra={
                        "trace_id": trace_id,
                        "error_type": type(exception).__name__,
                        "error_message": str(exception),
                        "stack_trace": stack_trace,
                    },
                )

            # Build error log model
            error_log = ErrorLogModel(
                id=uuid.uuid4(),
                trace_id=uuid.UUID(trace_id),
                correlation_id=ctx.correlation_id,
                tenant_id=tenant_id,
                user_id=user_id,
                ip_address=ip_address,
                path=path,
                method=method,
                status_code=status_code,
                error_code=error_code.value,
                error_type=type(exception).__name__,
                error_message=str(exception)[:500],  # Limit to 500 chars
                file_name=file_name,
                line_number=line_number,
                stack_trace=stack_trace,
                request_body=request_body,
                request_body_truncated=request_body_truncated,
                query_params=query_params,
                headers=headers,
                timestamp=None,  # Will use default (now)
            )

            # Save to database with async fallback
            saved = await self._repository.save_error(error_log)
            if not saved:
                # DB write failed - queue for retry
                await self._enqueue_error_log(error_log)

        except Exception as exc:
            # CRITICAL: Error logger itself must never crash
            # Log the failure and continue
            logger.error(
                "Failed to log error",
                extra={
                    "error": str(exc),
                    "trace_id": trace_id,
                    "original_exception": type(exception).__name__,
                },
            )

    async def _extract_traceback(self, exception: Exception) -> tuple[Optional[str], Optional[int], Optional[str]]:
        """
        Extract file name, line number, and short stack trace from exception.
        
        Returns tuple of (file_name, line_number, stack_trace_string)
        where stack_trace is limited to 3-5 lines.
        """
        try:
            tb = traceback.format_exc()
            
            # Parse traceback to get file_name and line_number
            tb_lines = tb.split("\n")
            file_name = None
            line_number = None
            
            # Find the last frame (where exception occurred)
            for line in reversed(tb_lines):
                if line.startswith("  File "):
                    # Extract file and line info
                    try:
                        # Format: '  File "/path/to/file.py", line 123, in function'
                        parts = line.split(", ")
                        file_part = parts[0].replace('  File "', "").strip('"')
                        line_part = parts[1].replace("line ", "").strip()
                        
                        # Extract just filename from full path
                        file_name = file_part.split("\\")[-1].split("/")[-1]
                        line_number = int(line_part)
                        break
                    except (ValueError, IndexError):
                        continue

            # Build short stack trace (last 3-5 lines)
            stack_lines = tb_lines[-5:]  # Last 5 lines
            stack_trace = "\n".join(line for line in stack_lines if line.strip())
            
            return file_name, line_number, stack_trace if stack_trace else None

        except Exception as exc:
            logger.error("Failed to extract traceback", extra={"error": str(exc)})
            return None, None, None

    async def _extract_request_body(self, request: Request) -> tuple[Optional[str], bool]:
        """
        Extract request body from POST/PUT/PATCH requests.
        
        Returns:
            Tuple of (request_body_string, was_truncated)
            where request_body is JSON string limited to 5KB
        """
        try:
            # Only extract body for requests that typically have one
            if request.method not in ("POST", "PUT", "PATCH"):
                return None, False

            # Read body (can only be read once)
            try:
                body = await request.body()
            except Exception as exc:
                # If some middleware/handler already consumed the stream,
                # do not treat it as an error here.
                if "Stream consumed" in str(exc):
                    return None, False
                raise
            
            if not body:
                return None, False

            # Convert to string
            body_str = body.decode("utf-8", errors="ignore")
            
            # Check size
            body_bytes = body_str.encode("utf-8")
            if len(body_bytes) > MAX_REQUEST_BODY_SIZE:
                # Truncate to 5KB
                body_str = body_str[:MAX_REQUEST_BODY_SIZE]
                truncated = True
            else:
                truncated = False

            # Try to parse and filter if JSON
            try:
                body_dict = json.loads(body_str)
                filtered = self._filter_sensitive_fields(body_dict)
                return json.dumps(filtered, default=str), truncated
            except json.JSONDecodeError:
                # Not JSON, return as-is (but still apply truncation)
                return body_str, truncated

        except Exception as exc:
            logger.error("Failed to extract request body", extra={"error": str(exc)})
            return None, False

    async def _extract_query_params(self, request: Request) -> Optional[dict]:
        """
        Extract and filter query parameters.
        
        Returns JSON dict of query params with sensitive fields filtered out.
        """
        try:
            if not request.query_params:
                return None

            params_dict = dict(request.query_params)
            filtered = self._filter_sensitive_fields(params_dict)
            
            return filtered if filtered else None

        except Exception as exc:
            logger.error("Failed to extract query params", extra={"error": str(exc)})
            return None

    def _extract_headers(self, request: Request) -> Optional[dict]:
        """
        Extract and filter headers.
        
        Removes: Authorization, Cookie, X-API-Key
        Returns JSON dict of remaining headers.
        """
        try:
            if not request.headers:
                return None

            headers = dict(request.headers)
            filtered = {
                k: v
                for k, v in headers.items()
                if k.lower() not in SENSITIVE_HEADERS
            }
            
            return filtered if filtered else None

        except Exception as exc:
            logger.error("Failed to extract headers", extra={"error": str(exc)})
            return None

    def _filter_sensitive_fields(self, data: Any) -> Any:
        """
        Recursively filter sensitive fields from dict/list structures.
        
        Removes: password, token, secret, api_key, access_token, 
                 refresh_token, confirm_password
        Also handles key/value pair dicts where key's value is a sensitive word.
        """
        if isinstance(data, dict):
            # Check for key/value pair pattern: {"key": "token", "value": "..."}
            # If this dict has a "key" (or "name") field whose value is sensitive,
            # redact the corresponding "value" field
            key_field = data.get("key") or data.get("name") or data.get("field")
            if key_field and isinstance(key_field, str) and key_field.lower() in SENSITIVE_BODY_FIELDS:
                result = {}
                for k, v in data.items():
                    if k.lower() in ("value", "val", "data", "content"):
                        result[k] = "[REDACTED]"
                    elif k.lower() in SENSITIVE_BODY_FIELDS:
                        result[k] = "[REDACTED]"
                    else:
                        result[k] = self._filter_sensitive_fields(v)
                return result
            return {
                k: self._filter_sensitive_fields(v)
                if k.lower() not in SENSITIVE_BODY_FIELDS
                else "[REDACTED]"
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._filter_sensitive_fields(item) for item in data]
        else:
            return data

    def _map_exception_to_status_and_code(
        self, exception: Exception
    ) -> tuple[int, ErrorCode]:
        """
        Map exception type to HTTP status code and ErrorCode enum.

        Supports common exception types:
        - ValueError → 400 (VALIDATION_ERROR) unless auth-related
        - KeyError → 400 (VALIDATION_ERROR) unless auth-related
        - AttributeError → 400 (VALIDATION_ERROR) unless auth-related
        - PermissionError → 403 (FORBIDDEN)
        - FileNotFoundError → 404 (NOT_FOUND)
        - HTTPException with status_code → use that status code
        - All others → 500 (INTERNAL_ERROR)
        """
        from fastapi import HTTPException

        # Check for HTTPException first (highest priority)
        if isinstance(exception, HTTPException):
            status_code = exception.status_code
            # Map status code to ErrorCode
            if status_code == 400:
                return status_code, ErrorCode.VALIDATION_ERROR
            elif status_code == 401:
                return status_code, ErrorCode.AUTH_FAILED
            elif status_code == 403:
                return status_code, ErrorCode.FORBIDDEN
            elif status_code == 404:
                return status_code, ErrorCode.NOT_FOUND
            elif status_code == 409:
                return status_code, ErrorCode.CONFLICT
            else:
                return status_code, ErrorCode.INTERNAL_ERROR

        # Check exception type and message
        exc_type = type(exception).__name__
        exc_msg = str(exception).lower()

        # Only treat clearly auth-related exceptions as 401.
        auth_keywords = ["auth", "jwt", "token", "credential"]
        is_auth_related = any(keyword in exc_type.lower() or keyword in exc_msg for keyword in auth_keywords)

        # Business-rule and validation exceptions should not be misclassified as auth failures.
        if is_auth_related:
            return 401, ErrorCode.AUTH_FAILED

        if isinstance(exception, ValueError):
            return 400, ErrorCode.VALIDATION_ERROR
        elif isinstance(exception, KeyError):
            return 400, ErrorCode.VALIDATION_ERROR
        elif isinstance(exception, AttributeError):
            return 400, ErrorCode.VALIDATION_ERROR
        elif isinstance(exception, PermissionError):
            return 403, ErrorCode.FORBIDDEN
        elif isinstance(exception, FileNotFoundError):
            return 404, ErrorCode.NOT_FOUND

        # Default: unhandled exception
        return 500, ErrorCode.INTERNAL_ERROR

    async def _enqueue_error_log(self, error_log: ErrorLogModel) -> None:
        """
        Queue error log for background retry when DB save fails.
        
        This is called when the repository.save_error() returns None.
        Can integrate with background task system or in-memory queue.
        
        For now, just log the fallback event.
        Future: integrate with error_queue.py background task.
        """
        try:
            logger.warning(
                "Error log queued for retry",
                extra={
                    "trace_id": str(error_log.trace_id),
                    "status_code": error_log.status_code,
                    "error_code": error_log.error_code,
                },
            )
            # TODO: Integrate with ErrorLogQueue when available
            # await error_queue.enqueue(error_log)
        except Exception as exc:
            logger.error(
                "Failed to queue error log",
                extra={
                    "error": str(exc),
                    "trace_id": str(error_log.trace_id),
                },
            )
