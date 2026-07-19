from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from backend.app.domain.shared.domain_event import DomainEvent


class BaseEntity(ABC):
    """
    Abstract base for all domain entities.

    Carries identity (id + tenant_id), timestamps, soft-delete fields,
    and a collection of pending domain events to be dispatched after commit.
    """

    def __init__(
        self,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        self._id: uuid.UUID = id or uuid.uuid4()
        self._tenant_id: uuid.UUID = tenant_id or uuid.uuid4()
        self._created_at: datetime = created_at or datetime.now(timezone.utc)
        self._updated_at: datetime = updated_at or datetime.now(timezone.utc)
        self._is_deleted: bool = is_deleted
        self._deleted_at: Optional[datetime] = deleted_at
        self._domain_events: List["DomainEvent"] = []

    # ── Identity ─────────────────────────────────────────────────────────
    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def tenant_id(self) -> uuid.UUID:
        return self._tenant_id

    # ── Timestamps ───────────────────────────────────────────────────────
    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def _touch(self) -> None:
        """Update the updated_at timestamp. Call inside mutating methods."""
        self._updated_at = datetime.now(timezone.utc)

    # ── Soft Delete ──────────────────────────────────────────────────────
    @property
    def is_deleted(self) -> bool:
        return self._is_deleted

    @property
    def deleted_at(self) -> Optional[datetime]:
        return self._deleted_at

    def soft_delete(self) -> None:
        """Mark this entity as deleted without removing from the DB."""
        self._is_deleted = True
        self._deleted_at = datetime.now(timezone.utc)
        self._touch()

    def restore(self) -> None:
        """Undo a soft delete."""
        self._is_deleted = False
        self._deleted_at = None
        self._touch()

    # ── Domain Events ─────────────────────────────────────────────────────
    def add_domain_event(self, event: "DomainEvent") -> None:
        self._domain_events.append(event)

    def pull_domain_events(self) -> List["DomainEvent"]:
        """Return and clear pending events. Called by UnitOfWork after commit."""
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    # ── Equality ──────────────────────────────────────────────────────────
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseEntity):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self._id}>"


class AggregateRoot(BaseEntity):
    """
    Aggregate Root - special entity type representing domain aggregates.
    
    In DDD, aggregates are clusters of objects that act as a single unit.
    The aggregate root is the entry point for all transactions within the aggregate.
    """
    pass
