"""Audit Log Service — immutable before/after state logging for manufacturing actions.

Provides consistent audit trail recording across all modules using:
1. A direct `log_action()` method for explicit audit entries.
2. A `get_entity_audit_trail()` query method with optional filters.
3. An `@auditable` decorator for capturing entity state before/after service method execution.

Requirements: 24.1, 24.2, 24.7
"""
from __future__ import annotations

import functools
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel

logger = logging.getLogger(__name__)


@dataclass
class AuditLogEntry:
    """Domain representation of an audit log record."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    action_type: str
    entity_type: str
    entity_id: Optional[uuid.UUID]
    before_state: Optional[Dict[str, Any]]
    after_state: Optional[Dict[str, Any]]
    reason: Optional[str]
    metadata: Optional[Dict[str, Any]]
    timestamp: datetime


@dataclass
class AuditLogFilters:
    """Optional filters for querying the audit trail."""

    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    user_id: Optional[uuid.UUID] = None
    action_type: Optional[str] = None


class AuditLogService:
    """Tenant-scoped audit log service for immutable action recording.

    Records before/after state snapshots for every auditable manufacturing action.
    All entries are tenant-isolated and immutable once written.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_action(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        action_type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLogEntry:
        """Record an immutable audit log entry.

        Args:
            tenant_id: Tenant scope for multi-tenancy isolation.
            user_id: The user who performed the action.
            action_type: Action identifier (e.g. "release_wo", "issue_material", "qc_approve").
            entity_type: The type of entity acted upon (e.g. "sales_order", "work_order", "delivery").
            entity_id: The unique ID of the entity.
            before_state: JSON-serializable snapshot of key fields before the action.
            after_state: JSON-serializable snapshot of key fields after the action.
            reason: Optional human-readable reason for the action.
            metadata: Optional additional context (e.g. correlation_id, IP, etc.).

        Returns:
            AuditLogEntry domain object representing the persisted record.
        """
        entry_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        model = AuditLogModel(
            id=entry_id,
            tenant_id=tenant_id,
            user_id=user_id,
            action=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            before_value=before_state,
            after_value=after_state,
            extra={
                **({"reason": reason} if reason else {}),
                **(metadata or {}),
            } if reason or metadata else None,
            occurred_at=now,
        )
        self._session.add(model)

        logger.info(
            "Audit log: action=%s entity_type=%s entity_id=%s tenant_id=%s user_id=%s",
            action_type,
            entity_type,
            entity_id,
            tenant_id,
            user_id,
        )

        return AuditLogEntry(
            id=entry_id,
            tenant_id=tenant_id,
            user_id=user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            reason=reason,
            metadata=metadata,
            timestamp=now,
        )

    async def get_entity_audit_trail(
        self,
        tenant_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        filters: Optional[AuditLogFilters] = None,
    ) -> List[AuditLogEntry]:
        """Retrieve the audit trail for a specific entity.

        Args:
            tenant_id: Tenant scope for isolation.
            entity_type: The type of entity (e.g. "sales_order", "work_order").
            entity_id: The entity's unique ID.
            filters: Optional filters for date range, user, or action type.

        Returns:
            Ordered list of AuditLogEntry (most recent first).
        """
        conditions = [
            AuditLogModel.tenant_id == tenant_id,
            AuditLogModel.entity_type == entity_type,
            AuditLogModel.entity_id == entity_id,
        ]

        if filters:
            if filters.date_from is not None:
                conditions.append(AuditLogModel.occurred_at >= filters.date_from)
            if filters.date_to is not None:
                conditions.append(AuditLogModel.occurred_at <= filters.date_to)
            if filters.user_id is not None:
                conditions.append(AuditLogModel.user_id == filters.user_id)
            if filters.action_type is not None:
                conditions.append(AuditLogModel.action == filters.action_type)

        stmt = (
            select(AuditLogModel)
            .where(and_(*conditions))
            .order_by(AuditLogModel.occurred_at.desc())
        )

        result = await self._session.execute(stmt)
        rows: Sequence[AuditLogModel] = result.scalars().all()

        return [self._to_entry(row) for row in rows]

    @staticmethod
    def _to_entry(model: AuditLogModel) -> AuditLogEntry:
        """Convert a persistence model to a domain entry."""
        extra = model.extra or {}
        reason = extra.pop("reason", None) if isinstance(extra, dict) else None
        # Remaining extra fields are treated as metadata
        metadata = extra if extra else None

        return AuditLogEntry(
            id=model.id,
            tenant_id=model.tenant_id,
            user_id=model.user_id,
            action_type=model.action,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            before_state=model.before_value,
            after_state=model.after_value,
            reason=reason,
            metadata=metadata,
            timestamp=model.occurred_at,
        )


# ---------------------------------------------------------------------------
# Entity snapshot helpers for the @auditable decorator
# ---------------------------------------------------------------------------

# Map entity_type to (model_class, id_kwarg_name) for lookup
_ENTITY_REGISTRY: Dict[str, tuple] = {}


def register_auditable_entity(
    entity_type: str,
    model_class: Any,
    id_kwarg: str = "entity_id",
) -> None:
    """Register an entity type for use with the @auditable decorator.

    Args:
        entity_type: String key matching the `entity_type` parameter in `@auditable`.
        model_class: The SQLAlchemy model class to query.
        id_kwarg: The keyword argument name in the decorated function that holds the entity ID.
    """
    _ENTITY_REGISTRY[entity_type] = (model_class, id_kwarg)


def _snapshot(entity: Any) -> Dict[str, Any]:
    """Create a JSON-serializable snapshot of an SQLAlchemy model's column values.

    Captures all mapped column attributes, converting UUIDs, datetimes, and Decimals
    to string representations for JSON compatibility.
    """
    if entity is None:
        return {}

    from sqlalchemy import inspect as sa_inspect

    mapper = sa_inspect(type(entity))
    snapshot: Dict[str, Any] = {}

    for col in mapper.columns:
        key = col.key
        value = getattr(entity, key, None)

        if value is None:
            snapshot[key] = None
        elif isinstance(value, uuid.UUID):
            snapshot[key] = str(value)
        elif isinstance(value, datetime):
            snapshot[key] = value.isoformat()
        elif hasattr(value, "__float__"):
            # Decimal / numeric types
            snapshot[key] = float(value)
        else:
            snapshot[key] = value

    return snapshot


async def _get_entity_for_audit(
    session: AsyncSession,
    entity_type: str,
    kwargs: Dict[str, Any],
) -> Any:
    """Look up the entity instance for snapshotting.

    Uses the _ENTITY_REGISTRY to determine which model class and which
    kwarg holds the entity ID. Falls back to common ID kwarg patterns.
    """
    if entity_type not in _ENTITY_REGISTRY:
        logger.warning(
            "Entity type '%s' not registered for audit. Snapshot will be empty.", entity_type
        )
        return None

    model_class, id_kwarg = _ENTITY_REGISTRY[entity_type]

    # Try the registered kwarg first, then common patterns
    entity_id = kwargs.get(id_kwarg)
    if entity_id is None:
        for fallback_key in ("work_order_id", "sales_order_id", "delivery_id", "id"):
            entity_id = kwargs.get(fallback_key)
            if entity_id is not None:
                break

    if entity_id is None:
        logger.warning(
            "Could not determine entity ID for audit (entity_type=%s, kwargs=%s)",
            entity_type,
            list(kwargs.keys()),
        )
        return None

    entity = await session.get(model_class, entity_id)
    if entity is None:
        logger.warning(
            "Entity not found for audit: type=%s id=%s", entity_type, entity_id
        )
    return entity


# ---------------------------------------------------------------------------
# @auditable decorator
# ---------------------------------------------------------------------------


def auditable(action_type: str, entity_type: str):
    """Decorator that captures entity state before/after a service method.

    The decorated method's owning class must have:
    - `self.audit_service`: An instance of AuditLogService
    - `self.session` (or `self._session`): An AsyncSession for entity lookup

    The decorated function receives `kwargs` that should contain:
    - An entity ID (registered via `register_auditable_entity` or common patterns)
    - `user_id` or `received_by`: The acting user
    - `reason` (optional): Human-readable reason

    Example usage:
        @auditable(action_type="release_wo", entity_type="work_order")
        async def release_work_order(self, *, work_order_id: UUID, user_id: UUID, ...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Resolve session from the service instance
            session = getattr(self, "session", None) or getattr(self, "_session", None)

            # Get entity before execution
            entity = await _get_entity_for_audit(session, entity_type, kwargs) if session else None
            before_state = _snapshot(entity) if entity else {}

            # Execute the actual service method
            result = await func(self, *args, **kwargs)

            # Snapshot the entity post-execution. The entity object in the
            # session identity map already reflects attribute changes made by
            # the service method, so we simply re-snapshot it.
            after_state = _snapshot(entity) if entity else {}

            # Determine user_id from kwargs
            user_id = (
                kwargs.get("user_id")
                or kwargs.get("received_by")
                or kwargs.get("approved_by")
                or kwargs.get("created_by")
            )

            # Determine entity_id
            entity_id = entity.id if entity else None

            # Determine tenant_id
            tenant_id = (
                getattr(entity, "tenant_id", None)
                or kwargs.get("tenant_id")
            )

            # Log the audit entry if we have enough context
            audit_service = getattr(self, "audit_service", None)
            if audit_service and tenant_id and user_id and entity_id:
                try:
                    await audit_service.log_action(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        action_type=action_type,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        before_state=before_state,
                        after_state=after_state,
                        reason=kwargs.get("reason"),
                    )
                except Exception as exc:
                    # Audit logging should never break the primary operation
                    logger.error(
                        "Failed to write audit log: action=%s entity=%s/%s error=%s",
                        action_type,
                        entity_type,
                        entity_id,
                        exc,
                    )
            elif audit_service is None:
                logger.debug(
                    "No audit_service on %s; skipping audit for %s",
                    type(self).__name__,
                    action_type,
                )

            return result

        return wrapper

    return decorator
