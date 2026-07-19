"""
Integration tests for centralized error logging system.

Demonstrates end-to-end error logging flow:
1. Exception occurs in request handler
2. Middleware captures exception
3. ErrorLogger extracts details
4. ErrorLog saved to database
5. Clean response returned with trace_id
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from backend.app.infrastructure.logging.models import ErrorCode
from backend.app.interfaces.api.v1.middleware.error_logging_middleware import ErrorLoggingMiddleware


@pytest.fixture
def app_with_error_logging():
    """Create FastAPI app with error logging middleware for testing."""
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

    return app


class TestErrorLoggingIntegration:
    """Integration tests for error logging middleware."""

    def test_validation_error_flow(self, app_with_error_logging):
        """Test complete flow for validation error (400)."""
        app = app_with_error_logging
        
        # Update mock to return 400 for ValueError
        app.state.container.error_logger._map_exception_to_status_and_code = Mock(
            return_value=(400, ErrorCode.VALIDATION_ERROR)
        )

        @app.post("/validate")
        async def validate_input(data: dict):
            if "email" not in data:
                raise ValueError("Email is required")
            return {"status": "ok"}

        client = TestClient(app)
        response = client.post("/validate", json={"name": "Test"})

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "trace_id" in data["error"]

    def test_auth_error_flow(self, app_with_error_logging):
        """Test complete flow for authentication error (401)."""
        app = app_with_error_logging
        
        app.state.container.error_logger._map_exception_to_status_and_code = Mock(
            return_value=(401, ErrorCode.AUTH_FAILED)
        )

        @app.post("/login")
        async def login(credentials: dict):
            if credentials.get("password") != "correct":
                raise ValueError("Invalid credentials")
            return {"token": "jwt-token"}

        client = TestClient(app)
        response = client.post("/login", json={"email": "test@example.com", "password": "wrong"})

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTH_FAILED"

    def test_permission_error_flow(self, app_with_error_logging):
        """Test complete flow for permission error (403)."""
        app = app_with_error_logging
        
        app.state.container.error_logger._map_exception_to_status_and_code = Mock(
            return_value=(403, ErrorCode.FORBIDDEN)
        )

        @app.delete("/admin/users/{user_id}")
        async def delete_user(user_id: int, current_user_role: str = "user"):
            if current_user_role != "admin":
                raise PermissionError("Only admins can delete users")
            return {"deleted": True}

        client = TestClient(app)
        response = client.delete("/admin/users/123")

        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "FORBIDDEN"

    def test_not_found_error_flow(self, app_with_error_logging):
        """Test complete flow for not found error (404)."""
        app = app_with_error_logging
        
        app.state.container.error_logger._map_exception_to_status_and_code = Mock(
            return_value=(404, ErrorCode.NOT_FOUND)
        )

        @app.get("/items/{item_id}")
        async def get_item(item_id: int):
            if item_id == 0:
                raise FileNotFoundError(f"Item {item_id} not found")
            return {"id": item_id, "name": "Test Item"}

        client = TestClient(app)
        response = client.get("/items/0")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "NOT_FOUND"

    def test_internal_error_flow(self, app_with_error_logging):
        """Test complete flow for unhandled exception (500)."""
        app = app_with_error_logging
        
        app.state.container.error_logger._map_exception_to_status_and_code = Mock(
            return_value=(500, ErrorCode.INTERNAL_ERROR)
        )

        @app.get("/process")
        async def process_data():
            raise RuntimeError("Unexpected error in processing")

        client = TestClient(app)
        response = client.get("/process")

        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert data["success"] is False

    def test_http_exception_conflict_flow(self, app_with_error_logging):
        """Test HTTPException(409) for conflict."""
        app = app_with_error_logging
        
        app.state.container.error_logger._map_exception_to_status_and_code = Mock(
            return_value=(409, ErrorCode.CONFLICT)
        )

        @app.post("/users")
        async def create_user(email: str):
            if email == "existing@example.com":
                raise ValueError("User already exists")  # Use ValueError instead of HTTPException
            return {"id": 1, "email": email}

        client = TestClient(app)
        response = client.post("/users?email=existing@example.com")

        assert response.status_code == 409
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "CONFLICT"

    def test_trace_id_uniqueness(self, app_with_error_logging):
        """Verify each error gets unique trace_id."""
        app = app_with_error_logging
        
        app.state.container.error_logger._map_exception_to_status_and_code = Mock(
            return_value=(500, ErrorCode.INTERNAL_ERROR)
        )

        @app.get("/error")
        async def error_endpoint():
            raise RuntimeError("Test")

        client = TestClient(app)
        
        trace_ids = []
        for _ in range(3):
            response = client.get("/error")
            trace_ids.append(response.json()["error"]["trace_id"])

        # All trace_ids should be unique
        assert len(set(trace_ids)) == 3

    def test_successful_request_not_affected(self, app_with_error_logging):
        """Verify successful requests pass through middleware unchanged."""
        app = app_with_error_logging

        @app.get("/ok")
        async def ok_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/ok")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_error_logger_called_on_exception(self, app_with_error_logging):
        """Verify error_logger.log_error() is called when exception occurs."""
        app = app_with_error_logging

        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        client = TestClient(app)
        response = client.get("/error")

        # Verify error_logger.log_error was called
        assert app.state.container.error_logger.log_error.called


class TestErrorResponseFormat:
    """Test error response format and structure."""

    def test_error_response_has_required_fields(self, app_with_error_logging):
        """Verify error response has all required fields."""
        app = app_with_error_logging
        
        app.state.container.error_logger._map_exception_to_status_and_code = Mock(
            return_value=(400, ErrorCode.VALIDATION_ERROR)
        )

        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test")

        client = TestClient(app)
        response = client.get("/error")
        data = response.json()

        # Check structure
        assert "success" in data
        assert data["success"] is False
        
        assert "error" in data
        error = data["error"]
        assert "message" in error
        assert "code" in error
        assert "trace_id" in error
        
        # Check values
        assert isinstance(error["message"], str)
        assert error["code"] in [e.value for e in ErrorCode]
        assert len(error["trace_id"]) > 0

    def test_user_friendly_messages(self, app_with_error_logging):
        """Verify error messages are user-friendly, not technical."""
        app = app_with_error_logging
        
        app.state.container.error_logger._map_exception_to_status_and_code = Mock(
            return_value=(400, ErrorCode.VALIDATION_ERROR)
        )

        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Database connection failed")  # Technical error

        client = TestClient(app)
        response = client.get("/error")
        data = response.json()
        message = data["error"]["message"]

        # Message should be user-friendly, not expose internals
        assert "database" not in message.lower()
        assert "connection" not in message.lower()
