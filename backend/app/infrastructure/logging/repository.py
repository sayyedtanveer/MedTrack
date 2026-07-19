from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.infrastructure.logging.models import ErrorLogModel
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class ErrorLogRepository:
    """
    Repository for persisting error logs to the database.
    
    Uses the existing async session factory pattern consistent
    with other repositories in the codebase (e.g., AuditService).
    
    Responsibilities:
    - Save error logs to database
    - Silent failure handling (never block user response)
    - Logging of persistence failures for infrastructure monitoring
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """
        Initialize repository with async session factory.
        
        Args:
            session_factory: AsyncSessionMaker from create_session_factory()
        """
        self._session_factory = session_factory

    async def save_error(self, error_log: ErrorLogModel) -> Optional[ErrorLogModel]:
        """
        Persist an error log to the database asynchronously.
        
        Implements silent failure pattern: if DB write fails, log the error
        without raising (caller should handle queuing to background task).
        
        Args:
            error_log: ErrorLogModel instance with all fields populated
            
        Returns:
            ErrorLogModel if save successful, None if failed
        """
        try:
            async with self._session_factory() as session:
                session.add(error_log)
                await session.commit()
                return error_log
        except Exception as exc:
            # Error log failures must never break the main request
            # Caller (ErrorLogger) will handle queuing to fallback
            logger.error(
                "Failed to persist error log",
                extra={
                    "error": str(exc),
                    "trace_id": str(error_log.trace_id),
                    "status_code": error_log.status_code,
                },
            )
            return None
