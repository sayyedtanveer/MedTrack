"""
Property tests for Audit Log Completeness and Integrity (Property 14).

**Validates: Requirements 24.1, 24.2, 24.7**

Property 14: For any successful auditable action (from the defined set: Release WO,
Issue Material, Record Production, etc.), exactly one audit_log entry SHALL exist with
the correct user_id, action_type, entity_type, entity_id, and a before_state that
differs from after_state in at least the status field. For any failed action, no
audit_log entry SHALL be created.

# Feature: manufacturing-erp-audit, Property 14: Audit Log Completeness and Integrity
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    sampled_from,
    uuids,
    text,
    composite,
    tuples,
    booleans,
)

from backend.app.services.audit_log_service import (
    AuditLogEntry,
    AuditLogService,
    auditable,
    register_auditable_entity,
    _snapshot,
    _ENTITY_REGISTRY,
)
from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel


# ─── Strategies ──────────────────────────────────────────────────────────────

# All auditable action types defined in Requirement 24.1
AUDITABLE_ACTIONS = [
    "release_wo",
    "issue_material",
    "record_production",
    "submit_qc",
    "qc_approve",
    "qc_reject",
    "fg_receive",
    "create_delivery",
    "mark_shipped",
    "mark_delivered",
    "create_invoice",
    "record_payment",
    "cancel_sales_order",
    "cancel_work_order",
    "send_to_rework",
    "scrap_batch",
]

# Entity types associated with auditable actions
ENTITY_TYPES = [
    "work_order",
    "sales_order",
    "delivery",
    "invoice",
    "payment",
]

# Status pairs: (before_status, after_status) representing valid transitions
STATUS_TRANSITIONS = [
    ("PLANNED", "RELEASED"),
    ("MATERIAL_RESERVED", "MATERIAL_ISSUED"),
    ("MATERIAL_ISSUED", "IN_PRODUCTION"),
    ("IN_PRODUCTION", "QC_PENDING"),
    ("QC_PENDING", "QC_APPROVED"),
    ("QC_PENDING", "QC_REJECTED"),
    ("QC_APPROVED", "FG_RECEIVED"),
    ("DRAFT", "SHIPPED"),
    ("SHIPPED", "DELIVERED"),
    ("DELIVERED", "INVOICED"),
    ("INVOICED", "PAYMENT_RECEIVED"),
    ("CONFIRMED", "CANCELLED"),
    ("IN_PRODUCTION", "CANCELLED"),
    ("QC_REJECTED", "REWORK"),
    ("QC_REJECTED", "REJECTED"),
]

action_types_strategy = sampled_from(AUDITABLE_ACTIONS)
entity_types_strategy = sampled_from(ENTITY_TYPES)
status_transitions_strategy = sampled_from(STATUS_TRANSITIONS)


@composite
def auditable_action_data(draw):
    """Generate a random auditable action with all required fields."""
    action_type = draw(action_types_strategy)
    entity_type = draw(entity_types_strategy)
    before_status, after_status = draw(status_transitions_strategy)
    tenant_id = draw(uuids())
    user_id = draw(uuids())
    entity_id = draw(uuids())

    return {
        "action_type": action_type,
        "entity_type": entity_type,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "entity_id": entity_id,
        "before_status": before_status,
        "after_status": after_status,
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_mock_entity(entity_id, tenant_id, status):
    """Create a mock entity with the given status for snapshot testing."""
    entity = MagicMock()
    entity.id = entity_id
    entity.tenant_id = tenant_id
    entity.status = status
    return entity


# ─────────────────────────────────────────────────────────────────────────────
# Property 14: Audit Log Completeness and Integrity
#
# Sub-property A: For any successful auditable action, exactly one audit_log
# entry exists with matching tenant_id, user_id, action_type, entity_type,
# entity_id, and differing before/after state.
#
# Sub-property B: For failed actions (where the service method raises an
# exception), no audit_log entry should be created.
# ─────────────────────────────────────────────────────────────────────────────


class TestAuditLogCompleteness:
    """**Validates: Requirements 24.1, 24.2, 24.7**

    Property 14: Audit Log Completeness and Integrity.
    """

    @given(data=auditable_action_data())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_successful_action_produces_exactly_one_audit_entry(
        self,
        data: dict,
        db_session,
    ):
        """Property 14A: For any successful auditable action, exactly one audit_log
        entry SHALL exist with the correct tenant_id, user_id, action_type, entity_type,
        entity_id, and a before_state that differs from after_state.

        **Validates: Requirements 24.1, 24.2**
        """
        tenant_id = data["tenant_id"]
        user_id = data["user_id"]
        entity_id = data["entity_id"]
        action_type = data["action_type"]
        entity_type = data["entity_type"]
        before_status = data["before_status"]
        after_status = data["after_status"]

        service = AuditLogService(db_session)

        # Simulate a successful action by directly calling log_action
        # (which is what the @auditable decorator does on success)
        before_state = {"status": before_status, "entity_id": str(entity_id)}
        after_state = {"status": after_status, "entity_id": str(entity_id)}

        entry = await service.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
        )
        await db_session.flush()

        # Verify exactly one audit entry exists for this entity + action
        trail = await service.get_entity_audit_trail(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )

        # Filter to only this specific action (there should be exactly one)
        matching_entries = [
            e for e in trail
            if e.action_type == action_type
            and e.user_id == user_id
            and e.entity_id == entity_id
        ]

        # Property: exactly one entry
        assert len(matching_entries) == 1, (
            f"Expected exactly 1 audit entry for action={action_type}, "
            f"entity={entity_type}/{entity_id}, got {len(matching_entries)}"
        )

        audit_entry = matching_entries[0]

        # Property: correct fields
        assert audit_entry.tenant_id == tenant_id
        assert audit_entry.user_id == user_id
        assert audit_entry.action_type == action_type
        assert audit_entry.entity_type == entity_type
        assert audit_entry.entity_id == entity_id

        # Property: before_state and after_state differ (at least in status)
        assert audit_entry.before_state != audit_entry.after_state, (
            f"before_state and after_state should differ; got "
            f"before={audit_entry.before_state}, after={audit_entry.after_state}"
        )
        assert audit_entry.before_state["status"] != audit_entry.after_state["status"], (
            f"Status should differ between before and after: "
            f"before_status={audit_entry.before_state['status']}, "
            f"after_status={audit_entry.after_state['status']}"
        )

        # Property: timestamp is set
        assert audit_entry.timestamp is not None

        # Cleanup: rollback so each hypothesis iteration starts fresh
        await db_session.rollback()

    @given(data=auditable_action_data())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_failed_action_produces_no_audit_entry(
        self,
        data: dict,
        db_session,
    ):
        """Property 14B: For failed actions (where the service method raises
        an exception), no audit_log entry SHALL be created.

        **Validates: Requirements 24.7**
        """
        tenant_id = data["tenant_id"]
        user_id = data["user_id"]
        entity_id = data["entity_id"]
        action_type = data["action_type"]
        entity_type = data["entity_type"]
        before_status = data["before_status"]

        # Register a temporary entity type for testing
        _ENTITY_REGISTRY[entity_type] = (AuditLogModel, "entity_id")

        try:
            # Create a real audit log model entry to serve as "the entity"
            # that the decorator would look up
            entity_model = AuditLogModel(
                id=entity_id,
                tenant_id=tenant_id,
                user_id=user_id,
                action=before_status,  # Use status as action for snapshot
                entity_type=entity_type,
                occurred_at=datetime.now(timezone.utc),
            )
            db_session.add(entity_model)
            await db_session.flush()

            # Create a service class with the @auditable decorator where
            # the underlying method RAISES an exception (simulating failure)
            audit_svc = AuditLogService(db_session)

            class FailingService:
                def __init__(self, session, audit_service):
                    self.session = session
                    self.audit_service = audit_service

                @auditable(action_type=action_type, entity_type=entity_type)
                async def failing_action(self, *, entity_id, user_id, tenant_id, **kwargs):
                    raise RuntimeError("Simulated action failure")

            svc = FailingService(db_session, audit_svc)

            # Execute the failing action — it should raise
            with pytest.raises(RuntimeError, match="Simulated action failure"):
                await svc.failing_action(
                    entity_id=entity_id,
                    user_id=user_id,
                    tenant_id=tenant_id,
                )

            await db_session.flush()

            # Property: NO audit entry should exist for this action
            trail = await audit_svc.get_entity_audit_trail(
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_id=entity_id,
            )

            action_entries = [e for e in trail if e.action_type == action_type]

            assert len(action_entries) == 0, (
                f"Expected 0 audit entries for failed action={action_type}, "
                f"entity={entity_type}/{entity_id}, but got {len(action_entries)}"
            )
        finally:
            # Clean up registry
            _ENTITY_REGISTRY.pop(entity_type, None)
            await db_session.rollback()

    @given(data=auditable_action_data())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_successful_action_via_decorator_records_state_diff(
        self,
        data: dict,
        db_session,
    ):
        """Property 14A (decorator path): When the @auditable decorator wraps a
        successful method, the recorded before_state and after_state SHALL differ
        in at least the mutated field.

        **Validates: Requirements 24.1, 24.2**
        """
        tenant_id = data["tenant_id"]
        user_id = data["user_id"]
        entity_id = data["entity_id"]
        action_type = data["action_type"]
        entity_type = "audit_logs"  # Use AuditLogModel as a stand-in entity
        before_status = data["before_status"]
        after_status = data["after_status"]

        # Register AuditLogModel for this test
        _ENTITY_REGISTRY["audit_logs"] = (AuditLogModel, "entity_id")

        try:
            # Create entity with initial state
            entity_model = AuditLogModel(
                id=entity_id,
                tenant_id=tenant_id,
                user_id=user_id,
                action=before_status,
                entity_type="test",
                occurred_at=datetime.now(timezone.utc),
            )
            db_session.add(entity_model)
            await db_session.flush()

            audit_svc = AuditLogService(db_session)

            class SuccessService:
                def __init__(self, session, audit_service):
                    self.session = session
                    self.audit_service = audit_service

                @auditable(action_type=action_type, entity_type="audit_logs")
                async def successful_action(self, *, entity_id, user_id, tenant_id, **kwargs):
                    # Mutate the entity to simulate state change
                    ent = await self.session.get(AuditLogModel, entity_id)
                    ent.action = after_status
                    return {"success": True}

            svc = SuccessService(db_session, audit_svc)

            result = await svc.successful_action(
                entity_id=entity_id,
                user_id=user_id,
                tenant_id=tenant_id,
            )
            assert result == {"success": True}

            await db_session.flush()

            # Verify the audit entry was created with differing states
            from sqlalchemy import select

            stmt = select(AuditLogModel).where(
                AuditLogModel.action == action_type,
                AuditLogModel.entity_id == entity_id,
                AuditLogModel.tenant_id == tenant_id,
            )
            audit_rows = (await db_session.execute(stmt)).scalars().all()

            assert len(audit_rows) == 1, (
                f"Expected exactly 1 audit entry via decorator, got {len(audit_rows)}"
            )

            row = audit_rows[0]

            # Verify before and after state differ
            assert row.before_value is not None
            assert row.after_value is not None
            assert row.before_value != row.after_value, (
                f"before_value and after_value should differ: "
                f"before={row.before_value}, after={row.after_value}"
            )

            # Verify the action field changed (our simulated state change)
            assert row.before_value.get("action") == before_status
            assert row.after_value.get("action") == after_status

        finally:
            _ENTITY_REGISTRY.pop("audit_logs", None)
            await db_session.rollback()
