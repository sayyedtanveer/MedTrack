"""Error logging infrastructure.

Exports:
- ErrorCode: Enum of standardized error codes
- ErrorLogModel: ORM model for error logs table
- ErrorLogger: Main service for capturing and logging errors
- ErrorLogRepository: Persistence layer for error logs
- ErrorLogQueue: Background queue for fallback persistence
- ErrorLogRetentionManager: Cleanup manager for retention policy
"""

from backend.app.infrastructure.logging.models import ErrorCode, ErrorLogModel
from backend.app.infrastructure.logging.error_logger import ErrorLogger
from backend.app.infrastructure.logging.repository import ErrorLogRepository
from backend.app.infrastructure.logging.error_queue import (
    ErrorLogQueue,
    ErrorLogPayload,
    get_error_log_queue,
)
from backend.app.infrastructure.logging.retention import ErrorLogRetentionManager

__all__ = [
    "ErrorCode",
    "ErrorLogModel",
    "ErrorLogger",
    "ErrorLogRepository",
    "ErrorLogQueue",
    "ErrorLogPayload",
    "get_error_log_queue",
    "ErrorLogRetentionManager",
]


