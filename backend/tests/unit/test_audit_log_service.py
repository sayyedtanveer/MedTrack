"""Unit tests for AuditLogService.

Tests the core audit logging service including:
- log_action() creates correct audit entries
- get_entity_audit_trail() retrieves and filters entries correctly
- @auditable decorator captures before/after state
- _snapshot() helper produces correct JSON-serializable output
- register_auditable_entity() properly registers entity types

Requirements: 24.1, 24.2, 24.7
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.audit_log_service import (
    AuditLogEntry,
    AuditLogFilters,
    AuditLogService,
    _snapshot,
    _get_entity_for_audit,
    auditable,
    register_auditable_entity,
    _ENTITY_REGISTRY,
)


# ---------------------------------------------------------------------------
# Test _snapshot helper
# ---------------------------------------------------------------------------


class TestSnapshot:
    """Tests for the _snapshot() helper function."""

    def test_snapshot_none_returns_empty_dict(self):
        assert _snapshot(None) == {}

    def test_snapshot_captures_uuid_as_string(self, db_session):
        """UUID columns should be serialized as strings."""
        from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel

        entry_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        model = AuditLogModel(
            id=entry_id,
            tenant_id=tenant_id,
            action="test_action",
            entity_type="test_entity",
            occurred_at=datetime.now(timezone.utc),
        )
        result = _snapshot(model)

        assert result["id"] == str(entry_id)
        assert result["tenant_id"] == str(tenant_id)

    def test_snapshot_captures_datetime_as_iso(self, db_session):
        """Datetime columns should be serialized as ISO strings."""
        from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel

        now = datetime.now(timezone.utc)
        model = AuditLogModel(
            id=uuid.uuid4(),
            action="test",
            occurred_at=now,
        )
        result = _snapshot(model)

        assert result["occurred_at"] == now.isoformat()

    def test_snapshot_captures_none_values(self, db_session):
        """None values should be preserved as None."""
        from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel

        model = AuditLogModel(
            id=uuid.uuid4(),
            action="test",
            entity_type=None,
            entity_id=None,
            occurred_at=datetime.now(timezone.utc),
        )
        result = _snapshot(model)

        assert result["entity_type"] is None
        assert result["entity_id"] is None

    def test_snapshot_captures_string_values(self, db_session):
        """String columns should be preserved as-is."""
        from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel

        model = AuditLogModel(
            id=uuid.uuid4(),
            action="release_wo",
            entity_type="work_order",
            occurred_at=datetime.now(timezone.utc),
        )
        result = _snapshot(model)

        assert result["action"] == "release_wo"
        assert result["entity_type"] == "work_order"


# ---------------------------------------------------------------------------
# Test AuditLogService.log_action()
# ---------------------------------------------------------------------------


class TestLogAction:
    """Tests for AuditLogService.log_action() method."""

    @pytest.mark.asyncio
    async def test_log_action_creates_entry(self, db_session: AsyncSession):
        """log_action should create an AuditLogModel record and return AuditLogEntry."""
        service = AuditLogService(db_session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        result = await service.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="release_wo",
            entity_type="work_order",
            entity_id=entity_id,
            before_state={"status": "PLANNED"},
            after_state={"status": "RELEASED"},
        )

        assert isinstance(result, AuditLogEntry)
        assert result.tenant_id == tenant_id
        assert result.user_id == user_id
        assert result.action_type == "release_wo"
        assert result.entity_type == "work_order"
        assert result.entity_id == entity_id
        assert result.before_state == {"status": "PLANNED"}
        assert result.after_state == {"status": "RELEASED"}
        assert result.reason is None
        assert result.metadata is None
        assert result.timestamp is not None

    @pytest.mark.asyncio
    async def test_log_action_with_reason_and_metadata(self, db_session: AsyncSession):
        """log_action should persist reason and metadata."""
        service = AuditLogService(db_session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        result = await service.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="qc_reject",
            entity_type="work_order",
            entity_id=entity_id,
            before_state={"status": "QC_PENDING"},
            after_state={"status": "QC_REJECTED"},
            reason="Surface defects detected",
            metadata={"inspector_notes": "Scratches on panel A"},
        )

        assert result.reason == "Surface defects detected"
        assert result.metadata == {"inspector_notes": "Scratches on panel A"}

    @pytest.mark.asyncio
    async def test_log_action_persists_to_database(self, db_session: AsyncSession):
        """log_action should add the model to the session (persisted on flush/commit)."""
        from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel
        from sqlalchemy import select

        service = AuditLogService(db_session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        await service.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="issue_material",
            entity_type="work_order",
            entity_id=entity_id,
            before_state={"issued": 0},
            after_state={"issued": 100},
        )

        await db_session.flush()

        stmt = select(AuditLogModel).where(AuditLogModel.entity_id == entity_id)
        result = (await db_session.execute(stmt)).scalar_one_or_none()

        assert result is not None
        assert result.action == "issue_material"
        assert result.entity_type == "work_order"
        assert result.before_value == {"issued": 0}
        assert result.after_value == {"issued": 100}


# ---------------------------------------------------------------------------
# Test AuditLogService.get_entity_audit_trail()
# ---------------------------------------------------------------------------


class TestGetEntityAuditTrail:
    """Tests for AuditLogService.get_entity_audit_trail() method."""

    @pytest.mark.asyncio
    async def test_returns_entries_for_entity(self, db_session: AsyncSession):
        """Should return all audit entries for a specific entity."""
        service = AuditLogService(db_session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        # Create two entries for the same entity
        await service.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="release_wo",
            entity_type="work_order",
            entity_id=entity_id,
            before_state={"status": "PLANNED"},
            after_state={"status": "RELEASED"},
        )
        await service.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="start_production",
            entity_type="work_order",
            entity_id=entity_id,
            before_state={"status": "MATERIAL_ISSUED"},
            after_state={"status": "IN_PRODUCTION"},
        )
        await db_session.flush()

        trail = await service.get_entity_audit_trail(
            tenant_id=tenant_id,
            entity_type="work_order",
            entity_id=entity_id,
        )

        assert len(trail) == 2
        # Most recent first
        assert trail[0].action_type == "start_production"
        assert trail[1].action_type == "release_wo"

    @pytest.mark.asyncio
    async def test_does_not_return_entries_from_other_tenants(self, db_session: AsyncSession):
        """Audit trail should be tenant-isolated."""
        service = AuditLogService(db_session)
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        await service.log_action(
            tenant_id=tenant_a,
            user_id=user_id,
            action_type="release_wo",
            entity_type="work_order",
            entity_id=entity_id,
            before_state={},
            after_state={},
        )
        await service.log_action(
            tenant_id=tenant_b,
            user_id=user_id,
            action_type="release_wo",
            entity_type="work_order",
            entity_id=entity_id,
            before_state={},
            after_state={},
        )
        await db_session.flush()

        trail = await service.get_entity_audit_trail(
            tenant_id=tenant_a,
            entity_type="work_order",
            entity_id=entity_id,
        )

        assert len(trail) == 1
        assert trail[0].tenant_id == tenant_a

    @pytest.mark.asyncio
    async def test_filter_by_action_type(self, db_session: AsyncSession):
        """Should filter by action_type."""
        service = AuditLogService(db_session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        await service.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="release_wo",
            entity_type="work_order",
            entity_id=entity_id,
            before_state={},
            after_state={},
        )
        await service.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="qc_approve",
            entity_type="work_order",
            entity_id=entity_id,
            before_state={},
            after_state={},
        )
        await db_session.flush()

        trail = await service.get_entity_audit_trail(
            tenant_id=tenant_id,
            entity_type="work_order",
            entity_id=entity_id,
            filters=AuditLogFilters(action_type="qc_approve"),
        )

        assert len(trail) == 1
        assert trail[0].action_type == "qc_approve"

    @pytest.mark.asyncio
    async def test_filter_by_user_id(self, db_session: AsyncSession):
        """Should filter by user_id."""
        service = AuditLogService(db_session)
        tenant_id = uuid.uuid4()
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        entity_id = uuid.uuid4()

        await service.log_action(
            tenant_id=tenant_id,
            user_id=user_a,
            action_type="release_wo",
            entity_type="work_order",
            entity_id=entity_id,
            before_state={},
            after_state={},
        )
        await service.log_action(
            tenant_id=tenant_id,
            user_id=user_b,
            action_type="qc_approve",
            entity_type="work_order",
            entity_id=entity_id,
            before_state={},
            after_state={},
        )
        await db_session.flush()

        trail = await service.get_entity_audit_trail(
            tenant_id=tenant_id,
            entity_type="work_order",
            entity_id=entity_id,
            filters=AuditLogFilters(user_id=user_a),
        )

        assert len(trail) == 1
        assert trail[0].user_id == user_a

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self, db_session: AsyncSession):
        """Should filter by date range."""
        from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel

        service = AuditLogService(db_session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)

        # Manually create entries with specific timestamps
        old_entry = AuditLogModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            action="old_action",
            entity_type="work_order",
            entity_id=entity_id,
            before_value={},
            after_value={},
            occurred_at=two_days_ago,
        )
        new_entry = AuditLogModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            action="new_action",
            entity_type="work_order",
            entity_id=entity_id,
            before_value={},
            after_value={},
            occurred_at=now,
        )
        db_session.add_all([old_entry, new_entry])
        await db_session.flush()

        trail = await service.get_entity_audit_trail(
            tenant_id=tenant_id,
            entity_type="work_order",
            entity_id=entity_id,
            filters=AuditLogFilters(date_from=yesterday),
        )

        assert len(trail) == 1
        assert trail[0].action_type == "new_action"


# ---------------------------------------------------------------------------
# Test @auditable decorator
# ---------------------------------------------------------------------------


class TestAuditableDecorator:
    """Tests for the @auditable decorator."""

    @pytest.mark.asyncio
    async def test_decorator_calls_log_action(self, db_session: AsyncSession):
        """The decorator should call audit_service.log_action with correct params."""
        from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel

        # Register a simple entity type for this test
        register_auditable_entity("audit_logs", AuditLogModel, "entity_id")

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        # Create an entity in DB so it can be fetched
        entry = AuditLogModel(
            id=entity_id,
            tenant_id=tenant_id,
            user_id=user_id,
            action="placeholder",
            entity_type="test",
            occurred_at=datetime.now(timezone.utc),
        )
        db_session.add(entry)
        await db_session.flush()

        # Create a service class with the decorator
        class MockService:
            def __init__(self, session, audit_svc):
                self.session = session
                self.audit_service = audit_svc

            @auditable(action_type="test_action", entity_type="audit_logs")
            async def do_something(self, *, entity_id, user_id, tenant_id, reason=None):
                # Modify the entity to simulate state change
                ent = await self.session.get(AuditLogModel, entity_id)
                ent.action = "modified"
                return {"ok": True}

        audit_svc = AuditLogService(db_session)
        svc = MockService(db_session, audit_svc)

        result = await svc.do_something(
            entity_id=entity_id,
            user_id=user_id,
            tenant_id=tenant_id,
        )

        assert result == {"ok": True}

        # Verify audit entry was created
        from sqlalchemy import select

        await db_session.flush()
        stmt = select(AuditLogModel).where(
            AuditLogModel.action == "test_action",
            AuditLogModel.entity_id == entity_id,
        )
        audit_entry = (await db_session.execute(stmt)).scalar_one_or_none()
        assert audit_entry is not None
        assert audit_entry.before_value["action"] == "placeholder"
        assert audit_entry.after_value["action"] == "modified"

        # Clean up registry
        _ENTITY_REGISTRY.pop("audit_logs", None)

    @pytest.mark.asyncio
    async def test_decorator_does_not_break_on_missing_audit_service(self, db_session):
        """If no audit_service attribute, the decorator should still execute the method."""

        class NoAuditService:
            def __init__(self, session):
                self.session = session

            @auditable(action_type="test_action", entity_type="nonexistent")
            async def do_work(self, **kwargs):
                return "done"

        svc = NoAuditService(db_session)
        result = await svc.do_work(user_id=uuid.uuid4(), tenant_id=uuid.uuid4())
        assert result == "done"

    @pytest.mark.asyncio
    async def test_decorator_does_not_break_on_audit_failure(self, db_session):
        """If audit logging raises, the primary method result should still be returned."""
        from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel

        register_auditable_entity("audit_logs", AuditLogModel, "entity_id")

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        entry = AuditLogModel(
            id=entity_id,
            tenant_id=tenant_id,
            action="test",
            entity_type="test",
            occurred_at=datetime.now(timezone.utc),
        )
        db_session.add(entry)
        await db_session.flush()

        # Create a mock audit service that raises
        broken_audit = AsyncMock()
        broken_audit.log_action = AsyncMock(side_effect=RuntimeError("DB error"))

        class TestService:
            def __init__(self, session, audit_svc):
                self.session = session
                self.audit_service = audit_svc

            @auditable(action_type="test_action", entity_type="audit_logs")
            async def do_work(self, *, entity_id, user_id, tenant_id, **kwargs):
                return "success"

        svc = TestService(db_session, broken_audit)
        result = await svc.do_work(
            entity_id=entity_id, user_id=user_id, tenant_id=tenant_id
        )
        assert result == "success"

        _ENTITY_REGISTRY.pop("audit_logs", None)


# ---------------------------------------------------------------------------
# Test register_auditable_entity
# ---------------------------------------------------------------------------


class TestRegisterAuditableEntity:
    """Tests for register_auditable_entity()."""

    def test_registers_entity_type(self):
        """Should add the entity type to the registry."""
        register_auditable_entity("test_entity", MagicMock, "test_id")
        assert "test_entity" in _ENTITY_REGISTRY
        assert _ENTITY_REGISTRY["test_entity"][1] == "test_id"
        _ENTITY_REGISTRY.pop("test_entity", None)

    def test_overwrites_existing_registration(self):
        """Re-registering should overwrite."""
        register_auditable_entity("test_entity", MagicMock, "id_a")
        register_auditable_entity("test_entity", MagicMock, "id_b")
        assert _ENTITY_REGISTRY["test_entity"][1] == "id_b"
        _ENTITY_REGISTRY.pop("test_entity", None)
