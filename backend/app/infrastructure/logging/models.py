from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, Index, String, Text, JSON as SA_JSON
from sqlalchemy.dialects.postgresql import UUID

# Use PostgreSQL JSONB when available, otherwise fall back to SQLAlchemy's generic JSON
JSONB = SA_JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class ErrorCode(str, Enum):
    """Standardized error codes for error logging.
    
    Maps HTTP status codes and exception types to symbolic names
    for easier filtering, grouping, and frontend handling.
    
    Extensible for future modules (add new codes as needed).
    """

    INTERNAL_ERROR = "INTERNAL_ERROR"  # 500 - Unhandled exception
    VALIDATION_ERROR = "VALIDATION_ERROR"  # 400 - Invalid input
    AUTH_FAILED = "AUTH_FAILED"  # 401 - Authentication failed (e.g., invalid credentials)
    UNAUTHORIZED = "UNAUTHORIZED"  # 401 - Missing authentication
    FORBIDDEN = "FORBIDDEN"  # 403 - Permission denied
    NOT_FOUND = "NOT_FOUND"  # 404 - Resource not found
    CONFLICT = "CONFLICT"  # 409 - Constraint violation, duplicate, etc.


class ErrorLogModel(Base):
    """
    Error logging model for centralized error tracking.
    
    Captures all HTTP errors (500, 400, etc.) with:
    - Exception details (type, message, traceback)
    - Request info (method, path, headers, body)
    - Context (tenant_id, user_id, correlation_id)
    - Metadata (file_name, line_number, trace_id)
    
    Sensitive data is filtered during capture:
    - Authorization, Cookie, X-API-Key headers removed
    - password, token, secret, api_key fields removed from body/query_params
    - Request body limited to 5KB
    
    Used for:
    - Debugging (trace_id linkage in support tickets)
    - Monitoring (error trends by type/status)
    - Retention (configurable cleanup policy)
    """

    __tablename__ = "error_logs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Tracing
    trace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )

    # Context
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # HTTP Request Info
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)  # GET, POST, etc.

    # Error Classification
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    error_code: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # INTERNAL_ERROR, VALIDATION_ERROR, etc.
    error_type: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Exception class name
    error_message: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # Human-readable message

    # Stack Trace (limited to 3-5 frames)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Request Details (filtered for sensitive data)
    request_body: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Limited to 5KB
    request_body_truncated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Flag if body exceeded 5KB
    query_params: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Filtered JSON
    headers: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Filtered JSON (no Authorization, Cookie, X-API-Key)

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_error_logs_timestamp_desc", "timestamp"),
        Index("idx_error_logs_tenant_timestamp", "tenant_id", "timestamp"),
        Index("idx_error_logs_status_timestamp", "status_code", "timestamp"),
        Index("idx_error_logs_trace_id", "trace_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ErrorLogModel id={self.id} status={self.status_code} "
            f"error_code={self.error_code} file={self.file_name}>"
        )
