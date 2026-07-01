"""Number Series Audit Service.

Provides audit logging for the Number Series Engine. Records events for:
- Code generation ("generated")
- Manual code overrides ("manual_override")
- Configuration changes ("config_changed")

All audit entries are tenant-isolated and include the acting user.

Requirements: 13.1, 13.2, 13.3, 13.5
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.number_series_models import (
    NumberSeriesAuditLogModel,
)

logger = logging.getLogger(__name__)


class NumberSeriesAuditService:
    """Tenant-scoped audit logger for Number Series Engine events.

    This service writes audit log entries to the number_series_audit_log table.
    Each entry is scoped to a tenant_id, ensuring tenant isolation (Requirement 13.5).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_generated(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
        generated_code: str,
        user_id: uuid.UUID,
        entity_id: Optional[uuid.UUID] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> uuid.UUID:
        """Log a code generation event.

        Requirement 13.1: Record event_type "generated" with generated code,
        entity_type, and the acting user on each code generation.

        Args:
            tenant_id: The tenant UUID (ensures tenant isolation).
            entity_type: Entity type (material, purchase_order, etc.).
            generated_code: The code that was generated.
            user_id: The user who triggered the generation.
            entity_id: Optional ID of the entity the code was generated for.
            metadata: Optional additional context (sub_type, entity_name, etc.).

        Returns:
            The UUID of the created audit log entry.
        """
        return await self._create_entry(
            tenant_id=tenant_id,
            entity_type=entity_type,
            event_type="generated",
            generated_code=generated_code,
            user_id=user_id,
            entity_id=entity_id,
            metadata=metadata,
        )

    async def log_manual_override(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
        generated_code: str,
        user_id: uuid.UUID,
        entity_id: Optional[uuid.UUID] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> uuid.UUID:
        """Log a manual override event.

        Requirement 13.2: Record event_type "manual_override" with the provided
        code, entity_type, and the acting user.

        Args:
            tenant_id: The tenant UUID (ensures tenant isolation).
            entity_type: Entity type (material, purchase_order, etc.).
            generated_code: The manually provided code.
            user_id: The user who provided the manual code.
            entity_id: Optional ID of the entity the code was assigned to.
            metadata: Optional additional context.

        Returns:
            The UUID of the created audit log entry.
        """
        return await self._create_entry(
            tenant_id=tenant_id,
            entity_type=entity_type,
            event_type="manual_override",
            generated_code=generated_code,
            user_id=user_id,
            entity_id=entity_id,
            metadata=metadata,
        )

    async def log_config_changed(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
        old_value: str,
        new_value: str,
        user_id: uuid.UUID,
        metadata: Optional[dict[str, Any]] = None,
    ) -> uuid.UUID:
        """Log a configuration change event.

        Requirement 13.3: Record event_type "config_changed" with old_value
        and new_value when an administrator changes Number Series configuration.

        Args:
            tenant_id: The tenant UUID (ensures tenant isolation).
            entity_type: Entity type whose config was changed.
            old_value: JSON string or description of previous config value(s).
            new_value: JSON string or description of new config value(s).
            user_id: The administrator who made the change.
            metadata: Optional additional context (field names changed, etc.).

        Returns:
            The UUID of the created audit log entry.
        """
        return await self._create_entry(
            tenant_id=tenant_id,
            entity_type=entity_type,
            event_type="config_changed",
            old_value=old_value,
            new_value=new_value,
            user_id=user_id,
            metadata=metadata,
        )

    async def _create_entry(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
        event_type: str,
        user_id: uuid.UUID,
        generated_code: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> uuid.UUID:
        """Create and persist an audit log entry.

        All entries are scoped to tenant_id for tenant isolation (Requirement 13.5).
        """
        entry_id = uuid.uuid4()
        metadata_json = json.dumps(metadata) if metadata else None

        entry = NumberSeriesAuditLogModel(
            id=entry_id,
            tenant_id=tenant_id,
            entity_type=entity_type,
            event_type=event_type,
            entity_id=entity_id,
            generated_code=generated_code,
            old_value=old_value,
            new_value=new_value,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            metadata_json=metadata_json,
        )
        self._session.add(entry)

        logger.info(
            "Number Series audit: event_type=%s, entity_type=%s, tenant_id=%s, user_id=%s, code=%s",
            event_type,
            entity_type,
            tenant_id,
            user_id,
            generated_code or "(n/a)",
        )

        return entry_id
