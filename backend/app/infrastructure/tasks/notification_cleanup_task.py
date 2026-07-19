"""Notification retention policy — soft-delete notifications older than 90 days.
Requirements: 40.3, 40.4
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

RETENTION_DAYS = 90
BATCH_SIZE = 500


async def cleanup_old_notifications(
    session: AsyncSession,
    tenant_id: Optional[str] = None,
    batch_size: int = BATCH_SIZE,
) -> int:
    """Soft-delete read notifications older than RETENTION_DAYS days.
    
    Runs in batches to avoid lock contention.
    Only deletes is_read=True notifications (preserve unread).
    Returns the total number of notifications soft-deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    total_deleted = 0
    
    while True:
        if tenant_id:
            result = await session.execute(
                text("""
                    UPDATE notifications
                    SET is_deleted = TRUE, updated_at = NOW()
                    WHERE id IN (
                        SELECT id FROM notifications
                        WHERE tenant_id = :tenant_id
                          AND is_deleted = FALSE
                          AND is_read = TRUE
                          AND created_at < :cutoff
                        LIMIT :batch_size
                    )
                    RETURNING id
                """),
                {"tenant_id": tenant_id, "cutoff": cutoff, "batch_size": batch_size}
            )
        else:
            result = await session.execute(
                text("""
                    UPDATE notifications
                    SET is_deleted = TRUE, updated_at = NOW()
                    WHERE id IN (
                        SELECT id FROM notifications
                        WHERE is_deleted = FALSE
                          AND is_read = TRUE
                          AND created_at < :cutoff
                        LIMIT :batch_size
                    )
                    RETURNING id
                """),
                {"cutoff": cutoff, "batch_size": batch_size}
            )
        
        batch_count = len(result.fetchall())
        total_deleted += batch_count
        await session.commit()
        
        if batch_count < batch_size:
            break
    
    logger.info(f"Notification cleanup: {total_deleted} records soft-deleted (cutoff: {cutoff})")
    return total_deleted
