"""
Unit and integration tests for centralized error logging system.

Tests cover:
- Traceback extraction and parsing
- Sensitive header/field filtering
- Request body truncation at 5KB
- Exception to error_code mapping
- Error logger service functionality
- Middleware response format
- Repository persistence
- Background queue operations
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.infrastructure.logging.error_logger import ErrorLogger
from backend.app.infrastructure.logging.models import ErrorLogModel, ErrorCode
from backend.app.infrastructure.logging.repository import ErrorLogRepository
from backend.app.infrastructure.logging.error_queue import ErrorLogQueue, ErrorLogPayload
from backend.app.interfaces.api.v1.middleware.error_logging_middleware import ErrorLoggingMiddleware


class TestErrorExtraction:
    """Test error information extraction from exceptions."""

    @pytest.mark.asyncio
    async def test_extract_traceback_gets_file_and_line(self):
        """Verify traceback extraction correctly parses file_name and line_number."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        try:
            raise ValueError("Test error")
        except ValueError as exc:
            file_name, line_number, stack_trace = await error_logger._extract_traceback(exc)

            assert file_name is not None
            assert file_name.endswith(".py")
            assert line_number is not None
            assert isinstance(line_number, int)
            assert stack_trace is not None
            assert "ValueError" in stack_trace
            assert "Test error" in stack_trace

    @pytest.mark.asyncio
    async def test_extract_traceback_limits_stack_to_5_lines(self):
        """Verify stack trace is limited to 3-5 lines."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        try:
            raise RuntimeError("Deep error")
        except RuntimeError as exc:
            _, _, stack_trace = await error_logger._extract_traceback(exc)

            # Count lines
            lines = [l for l in stack_trace.split("\n") if l.strip()]
            assert len(lines) <= 5


class TestSensitiveDataFiltering:
    """Test filtering of sensitive headers and fields."""

    def test_filter_sensitive_headers(self):
        """Verify sensitive headers (Authorization, Cookie, X-API-Key) are removed."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        # Create mock request with sensitive headers
        request = Mock()
        request.headers = {
            "user-agent": "test-agent",
            "authorization": "Bearer token123",
            "cookie": "session=abc",
            "x-api-key": "secret-key",
            "content-type": "application/json",
        }

        filtered = error_logger._extract_headers(request)

        assert filtered is not None
        assert "user-agent" in filtered
        assert "content-type" in filtered
        assert "authorization" not in filtered
        assert "cookie" not in filtered
        assert "x-api-key" not in filtered

    def test_filter_sensitive_body_fields(self):
        """Verify sensitive body fields (password, token, etc.) are redacted."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        data = {
            "email": "user@example.com",
            "password": "secret123",
            "confirm_password": "secret123",
            "token": "jwt-token-here",
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "secret": "api-secret",
            "api_key": "key-123",
        }

        filtered = error_logger._filter_sensitive_fields(data)

        assert filtered["email"] == "user@example.com"
        assert filtered["password"] == "[REDACTED]"
        assert filtered["confirm_password"] == "[REDACTED]"
        assert filtered["token"] == "[REDACTED]"
        assert filtered["access_token"] == "[REDACTED]"
        assert filtered["refresh_token"] == "[REDACTED]"
        assert filtered["secret"] == "[REDACTED]"
        assert filtered["api_key"] == "[REDACTED]"

    def test_filter_sensitive_fields_in_nested_structure(self):
        """Verify filtering works recursively on nested dicts and lists."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        data = {
            "user": {
                "name": "John",
                "password": "secret",
                "settings": [
                    {"config_key": "token", "config_value": "token123"},
                    {"config_key": "api_key", "config_value": "key-456"},
                    {"token": "jwt-token-here"},
                    {"access_token": "access-token-here"},
                ],
            }
        }

        filtered = error_logger._filter_sensitive_fields(data)

        assert filtered["user"]["name"] == "John"
        assert filtered["user"]["password"] == "[REDACTED]"
        assert filtered["user"]["settings"][0]["config_key"] == "token"
        assert filtered["user"]["settings"][0]["config_value"] == "token123"
        assert filtered["user"]["settings"][1]["config_value"] == "key-456"
        assert filtered["user"]["settings"][2]["token"] == "[REDACTED]"
        assert filtered["user"]["settings"][3]["access_token"] == "[REDACTED]"


class TestRequestBodyTruncation:
    """Test request body size limiting at 5KB."""

    @pytest.mark.asyncio
    async def test_request_body_truncated_at_5kb(self):
        """Verify request body is truncated at 5KB with flag set."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        # Create mock request with large body
        large_body = "x" * (6 * 1024)  # 6KB
        request = Mock()
        request.method = "POST"
        request.body = AsyncMock(return_value=large_body.encode("utf-8"))

        body_str, truncated = await error_logger._extract_request_body(request)

        assert truncated is True
        assert len(body_str.encode("utf-8")) <= 5 * 1024

    @pytest.mark.asyncio
    async def test_request_body_not_truncated_if_under_5kb(self):
        """Verify request_body_truncated flag is False for small bodies."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        # Create mock request with small body
        small_body = json.dumps({"email": "test@example.com", "name": "Test"})
        request = Mock()
        request.method = "POST"
        request.body = AsyncMock(return_value=small_body.encode("utf-8"))

        body_str, truncated = await error_logger._extract_request_body(request)

        assert truncated is False
        assert body_str == small_body

    @pytest.mark.asyncio
    async def test_request_body_only_extracted_for_post_put_patch(self):
        """Verify request body is only extracted for POST/PUT/PATCH, not GET."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        request = Mock()
        request.method = "GET"
        request.body = AsyncMock()

        body_str, truncated = await error_logger._extract_request_body(request)

        assert body_str is None
        assert truncated is False
        request.body.assert_not_called()


class TestExceptionMapping:
    """Test exception to error_code mapping."""

    def test_value_error_maps_to_validation_error_400(self):
        """Verify ValueError maps to 400 VALIDATION_ERROR."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        status_code, error_code = error_logger._map_exception_to_status_and_code(
            ValueError("Invalid value")
        )

        assert status_code == 400
        assert error_code == ErrorCode.VALIDATION_ERROR

    def test_key_error_maps_to_validation_error_400(self):
        """Verify KeyError maps to 400 VALIDATION_ERROR."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        status_code, error_code = error_logger._map_exception_to_status_and_code(
            KeyError("missing_key")
        )

        assert status_code == 400
        assert error_code == ErrorCode.VALIDATION_ERROR

    def test_permission_error_maps_to_forbidden_403(self):
        """Verify PermissionError maps to 403 FORBIDDEN."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        status_code, error_code = error_logger._map_exception_to_status_and_code(
            PermissionError("Access denied")
        )

        assert status_code == 403
        assert error_code == ErrorCode.FORBIDDEN

    def test_file_not_found_maps_to_not_found_404(self):
        """Verify FileNotFoundError maps to 404 NOT_FOUND."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        status_code, error_code = error_logger._map_exception_to_status_and_code(
            FileNotFoundError("File not found")
        )

        assert status_code == 404
        assert error_code == ErrorCode.NOT_FOUND

    def test_http_exception_401_maps_to_auth_failed(self):
        """Verify HTTPException(401) maps to AUTH_FAILED."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        http_exc = HTTPException(status_code=401, detail="Unauthorized")
        status_code, error_code = error_logger._map_exception_to_status_and_code(http_exc)

        assert status_code == 401
        assert error_code == ErrorCode.AUTH_FAILED

    def test_http_exception_409_maps_to_conflict(self):
        """Verify HTTPException(409) maps to CONFLICT."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        http_exc = HTTPException(status_code=409, detail="Conflict")
        status_code, error_code = error_logger._map_exception_to_status_and_code(http_exc)

        assert status_code == 409
        assert error_code == ErrorCode.CONFLICT

    def test_unhandled_exception_maps_to_internal_error_500(self):
        """Verify unknown exceptions map to 500 INTERNAL_ERROR."""
        error_logger = ErrorLogger(session_factory=AsyncMock())

        status_code, error_code = error_logger._map_exception_to_status_and_code(
            RuntimeError("Unexpected error")
        )

        assert status_code == 500
        assert error_code == ErrorCode.INTERNAL_ERROR


class TestErrorLogQueue:
    """Test background error log queue for fallback persistence."""

    @pytest.mark.asyncio
    async def test_enqueue_adds_payload_to_queue(self):
        """Verify enqueue adds payload to queue."""
        queue = ErrorLogQueue()

        payload = ErrorLogPayload(
            id="550e8400-e29b-41d4-a716-446655440000",
            trace_id="560e8400-e29b-41d4-a716-446655440000",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status_code=500,
            error_code="INTERNAL_ERROR",
            error_type="RuntimeError",
            error_message="Test error",
            file_name="test.py",
            line_number=42,
            stack_trace="line 1",
            path="/api/test",
            method="POST",
            request_body='{"test": "data"}',
            request_body_truncated=False,
            query_params=None,
            headers=None,
            tenant_id=None,
            user_id=None,
            ip_address="127.0.0.1",
            correlation_id=None,
        )

        result = await queue.enqueue(payload)
        assert result is True

        size = await queue.size()
        assert size == 1

    @pytest.mark.asyncio
    async def test_dequeue_retrieves_in_fifo_order(self):
        """Verify dequeue returns items in FIFO order."""
        queue = ErrorLogQueue()

        # Enqueue multiple items
        for i in range(3):
            payload = ErrorLogPayload(
                id=f"{i}50e8400-e29b-41d4-a716-446655440000",
                trace_id=f"{i}60e8400-e29b-41d4-a716-446655440000",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status_code=500,
                error_code="INTERNAL_ERROR",
                error_type="RuntimeError",
                error_message=f"Error {i}",
                file_name="test.py",
                line_number=42,
                stack_trace="line 1",
                path="/api/test",
                method="POST",
                request_body=None,
                request_body_truncated=False,
                query_params=None,
                headers=None,
                tenant_id=None,
                user_id=None,
                ip_address="127.0.0.1",
                correlation_id=None,
            )
            await queue.enqueue(payload)

        # Dequeue batch
        batch = await queue.dequeue_batch(batch_size=2)
        assert len(batch) == 2
        assert batch[0]["error_message"] == "Error 0"
        assert batch[1]["error_message"] == "Error 1"

        # Verify remaining item
        size = await queue.size()
        assert size == 1


class TestErrorLoggingMiddleware:
    """Test error logging middleware response format."""

    def test_middleware_returns_clean_error_response_on_exception(self):
        """Verify middleware returns standardized error response on exception."""
        app = FastAPI()

        # Mock container with error_logger
        mock_container = Mock()
        mock_error_logger = AsyncMock()
        mock_error_logger._map_exception_to_status_and_code = Mock(
            return_value=(500, ErrorCode.INTERNAL_ERROR)
        )
        mock_container.error_logger = mock_error_logger

        app.state.container = mock_container
        app.add_middleware(ErrorLoggingMiddleware)

        @app.get("/error")
        async def error_endpoint():
            raise RuntimeError("Test error")

        client = TestClient(app)
        response = client.get("/error")

        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "message" in data["error"]
        assert "code" in data["error"]
        assert "trace_id" in data["error"]
        assert data["error"]["code"] == "INTERNAL_ERROR"

    def test_middleware_response_includes_trace_id(self):
        """Verify middleware includes trace_id for correlation."""
        app = FastAPI()

        mock_container = Mock()
        mock_error_logger = AsyncMock()
        mock_error_logger._map_exception_to_status_and_code = Mock(
            return_value=(400, ErrorCode.VALIDATION_ERROR)
        )
        mock_container.error_logger = mock_error_logger

        app.state.container = mock_container
        app.add_middleware(ErrorLoggingMiddleware)

        @app.get("/bad-request")
        async def bad_request():
            raise ValueError("Invalid input")

        client = TestClient(app)
        response = client.get("/bad-request")

        data = response.json()
        trace_id = data["error"]["trace_id"]

        # Verify trace_id is valid UUID format
        try:
            uuid.UUID(trace_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        assert is_valid_uuid


class TestErrorLogModel:
    """Test ErrorLog ORM model."""

    def test_error_log_model_all_fields(self):
        """Verify ErrorLogModel can be instantiated with all fields."""
        now = datetime.now(timezone.utc)
        error_log = ErrorLogModel(
            id=uuid.uuid4(),
            trace_id=uuid.uuid4(),
            correlation_id="corr-123",
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            ip_address="192.168.1.1",
            path="/api/v1/users",
            method="POST",
            status_code=400,
            error_code="VALIDATION_ERROR",
            error_type="ValueError",
            error_message="Invalid input",
            file_name="auth_service.py",
            line_number=45,
            stack_trace="  line 45 in validate_user",
            request_body='{"email": "test"}',
            request_body_truncated=False,
            query_params={"filter": "active"},
            headers={"content-type": "application/json"},
            timestamp=now,
        )

        assert error_log.id is not None
        assert error_log.trace_id is not None
        assert error_log.status_code == 400
        assert error_log.error_code == "VALIDATION_ERROR"
        assert error_log.file_name == "auth_service.py"
        assert error_log.request_body_truncated is False


# Integration test fixture (optional, requires full setup)
@pytest.fixture
async def test_client_with_error_logging():
    """Create test client with error logging middleware."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    # Mock container
    mock_container = Mock()
    mock_error_logger = AsyncMock()
    mock_error_logger._map_exception_to_status_and_code = Mock(
        return_value=(500, ErrorCode.INTERNAL_ERROR)
    )
    mock_container.error_logger = mock_error_logger

    app.state.container = mock_container
    app.add_middleware(ErrorLoggingMiddleware)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.get("/error")
    async def error():
        raise RuntimeError("Test error")

    return TestClient(app)
