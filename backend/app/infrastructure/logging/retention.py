from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.infrastructure.logging.logger import get_logger
from backend.app.infrastructure.logging.models import ErrorLogModel

logger = get_logger(__name__)


class ErrorLogRetentionManager:
    """
    Manages error log retention and cleanup.
    
    Supports configurable retention policies:
    - Default: 30 days
    - Configurable via settings
    
    Can be invoked as:
    - Scheduled task (APScheduler) on startup + periodic runs
    - Manual CLI command
    - Background worker task
    
    Design philosophy:
    - Never blocks request processing
    - Runs asynchronously
    - Logs failures but doesn't raise
    - Tracks stats for monitoring
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        retention_days: int = 30,
    ) -> None:
        """
        Initialize retention manager.
        
        Args:
            session_factory: AsyncSessionMaker for DB access
            retention_days: Number of days to keep logs (default: 30)
        """
        self._session_factory = session_factory
        self._retention_days = retention_days
        self._stats = {"last_run": None, "deleted_count": 0, "errors": 0}

    async def cleanup_old_logs(self) -> int:
        """
        Delete error logs older than retention period.
        
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=self._retention_days
            )

            async with self._session_factory() as session:
                # Query to get count first (optional, for logging)
                stmt = select(ErrorLogModel).where(
                    ErrorLogModel.timestamp < cutoff_date
                )
                result = await session.execute(stmt)
                old_logs = result.scalars().all()
                count = len(old_logs)

                # Delete old logs
                delete_stmt = delete(ErrorLogModel).where(
                    ErrorLogModel.timestamp < cutoff_date
                )
                await session.execute(delete_stmt)
                await session.commit()

            logger.info(
                "Error log cleanup completed",
                extra={
                    "deleted_count": count,
                    "retention_days": self._retention_days,
                    "cutoff_date": cutoff_date.isoformat(),
                },
            )

            self._stats["last_run"] = datetime.now(timezone.utc).isoformat()
            self._stats["deleted_count"] = count
            return count

        except Exception as exc:
            logger.error(
                "Error log cleanup failed",
                extra={
                    "error": str(exc),
                    "retention_days": self._retention_days,
                },
            )
            self._stats["errors"] += 1
            return 0

    def get_stats(self) -> dict:
        """Return cleanup statistics."""
        return self._stats.copy()

    async def cleanup_by_tenant(self, tenant_id: str, retention_days: int) -> int:
        """
        Delete error logs for specific tenant.
        
        Useful for tenant offboarding or GDPR compliance.
        
        Args:
            tenant_id: UUID string of tenant
            retention_days: Age threshold for this tenant
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=retention_days
            )

            async with self._session_factory() as session:
                delete_stmt = delete(ErrorLogModel).where(
                    (ErrorLogModel.tenant_id == tenant_id)
                    & (ErrorLogModel.timestamp < cutoff_date)
                )
                result = await session.execute(delete_stmt)
                await session.commit()
                count = result.rowcount

            logger.info(
                "Error log cleanup by tenant completed",
                extra={
                    "tenant_id": tenant_id,
                    "deleted_count": count,
                    "retention_days": retention_days,
                },
            )
            return count

        except Exception as exc:
            logger.error(
                "Error log cleanup by tenant failed",
                extra={
                    "error": str(exc),
                    "tenant_id": tenant_id,
                    "retention_days": retention_days,
                },
            )
            return 0
