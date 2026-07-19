from __future__ import annotations

import uuid
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.context.request_context import get_request_context
from backend.app.infrastructure.logging.logger import get_logger
from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel

logger = get_logger(__name__)


class AuditService:
    """
    Writes audit records for all critical ERP operations.

    Called from:
    - AuditMiddleware (all requests)
    - Command handlers (CUD operations)
    - Login/Logout flows
    - Domain event handlers (via EventBus)
    """

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def log_action(
        self,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        before_value: Optional[Dict[str, Any]] = None,
        after_value: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write an audit log entry asynchronously."""
        ctx = get_request_context()
        record = AuditLogModel(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(ctx.tenant_id) if ctx.tenant_id else None,
            user_id=uuid.UUID(ctx.user_id) if ctx.user_id else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_value=before_value,
            after_value=after_value,
            ip_address=ctx.ip_address,
            correlation_id=uuid.UUID(ctx.correlation_id) if ctx.correlation_id else None,
            extra=extra,
            occurred_at=datetime.now(timezone.utc),
        )
        try:
            async with self._session_factory() as session:
                session.add(record)
                await session.commit()
        except Exception as exc:
            # Audit failures must never break the main request
            logger.error("Failed to write audit log", extra={"error": str(exc)})
