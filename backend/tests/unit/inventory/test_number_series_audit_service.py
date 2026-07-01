"""Unit tests for NumberSeriesAuditService.

Tests cover:
- Logging "generated" events with correct fields (Requirement 13.1)
- Logging "manual_override" events with correct fields (Requirement 13.2)
- Logging "config_changed" events with old/new values (Requirement 13.3)
- Tenant isolation: all entries include tenant_id (Requirement 13.5)
- Metadata serialization to JSON

Requirements: 13.1, 13.2, 13.3, 13.5
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from backend.app.application.inventory.services.number_series_audit_service import (
    NumberSeriesAuditService,
)
from backend.app.infrastructure.persistence.models.number_series_models import (
    NumberSeriesAuditLogModel,
)


class TestLogGenerated:
    """Test logging of 'generated' event type (Requirement 13.1)."""

    async def test_log_generated_creates_entry_with_correct_fields(self):
        """Requirement 13.1: Record event_type 'generated' with code, entity_type, user."""
        session = AsyncMock()
        service = NumberSeriesAuditService(session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        result = await service.log_generated(
            tenant_id=tenant_id,
            entity_type="material",
            generated_code="RM-STP-000001",
            user_id=user_id,
            entity_id=entity_id,
        )

        # Verify an entry was added to the session
        session.add.assert_called_once()
        entry = session.add.call_args[0][0]

        assert isinstance(entry, NumberSeriesAuditLogModel)
        assert entry.tenant_id == tenant_id
        assert entry.entity_type == "material"
        assert entry.event_type == "generated"
        assert entry.generated_code == "RM-STP-000001"
        assert entry.user_id == user_id
        assert entry.entity_id == entity_id
        assert entry.old_value is None
        assert entry.new_value is None
        assert isinstance(entry.timestamp, datetime)
        assert isinstance(result, uuid.UUID)

    async def test_log_generated_without_entity_id(self):
        """Generated events can omit entity_id."""
        session = AsyncMock()
        service = NumberSeriesAuditService(session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        await service.log_generated(
            tenant_id=tenant_id,
            entity_type="purchase_order",
            generated_code="PO-000042",
            user_id=user_id,
        )

        entry = session.add.call_args[0][0]
        assert entry.entity_id is None
        assert entry.entity_type == "purchase_order"

    async def test_log_generated_with_metadata(self):
        """Generated events can include metadata serialized as JSON."""
        session = AsyncMock()
        service = NumberSeriesAuditService(session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        metadata = {"sub_type": "raw", "entity_name": "Steel Pipe"}
        await service.log_generated(
            tenant_id=tenant_id,
            entity_type="material",
            generated_code="RM-STP-000001",
            user_id=user_id,
            metadata=metadata,
        )

        entry = session.add.call_args[0][0]
        assert entry.metadata_json is not None
        parsed = json.loads(entry.metadata_json)
        assert parsed["sub_type"] == "raw"
        assert parsed["entity_name"] == "Steel Pipe"

    async def test_log_generated_without_metadata(self):
        """Generated events without metadata have None metadata_json."""
        session = AsyncMock()
        service = NumberSeriesAuditService(session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        await service.log_generated(
            tenant_id=tenant_id,
            entity_type="material",
            generated_code="RM-STP-000001",
            user_id=user_id,
        )

        entry = session.add.call_args[0][0]
        assert entry.metadata_json is None


class TestLogManualOverride:
    """Test logging of 'manual_override' event type (Requirement 13.2)."""

    async def test_log_manual_override_creates_entry_with_correct_fields(self):
        """Requirement 13.2: Record event_type 'manual_override' with code, entity_type, user."""
        session = AsyncMock()
        service = NumberSeriesAuditService(session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        result = await service.log_manual_override(
            tenant_id=tenant_id,
            entity_type="material",
            generated_code="CUSTOM-001",
            user_id=user_id,
            entity_id=entity_id,
        )

        session.add.assert_called_once()
        entry = session.add.call_args[0][0]

        assert isinstance(entry, NumberSeriesAuditLogModel)
        assert entry.tenant_id == tenant_id
        assert entry.entity_type == "material"
        assert entry.event_type == "manual_override"
        assert entry.generated_code == "CUSTOM-001"
        assert entry.user_id == user_id
        assert entry.entity_id == entity_id
        assert isinstance(result, uuid.UUID)

    async def test_log_manual_override_with_metadata(self):
        """Manual override events can include metadata about user context."""
        session = AsyncMock()
        service = NumberSeriesAuditService(session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        metadata = {"sub_type": "finished", "entity_name": "Widget A", "user_is_admin": True}
        await service.log_manual_override(
            tenant_id=tenant_id,
            entity_type="material",
            generated_code="MY-WIDGET",
            user_id=user_id,
            metadata=metadata,
        )

        entry = session.add.call_args[0][0]
        parsed = json.loads(entry.metadata_json)
        assert parsed["user_is_admin"] is True
        assert parsed["entity_name"] == "Widget A"


class TestLogConfigChanged:
    """Test logging of 'config_changed' event type (Requirement 13.3)."""

    async def test_log_config_changed_creates_entry_with_old_and_new_values(self):
        """Requirement 13.3: Record 'config_changed' with old_value and new_value."""
        session = AsyncMock()
        service = NumberSeriesAuditService(session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        old_value = json.dumps({"abbreviation_length": 3, "separator": "-"})
        new_value = json.dumps({"abbreviation_length": 4, "separator": "."})

        result = await service.log_config_changed(
            tenant_id=tenant_id,
            entity_type="material",
            old_value=old_value,
            new_value=new_value,
            user_id=user_id,
        )

        session.add.assert_called_once()
        entry = session.add.call_args[0][0]

        assert isinstance(entry, NumberSeriesAuditLogModel)
        assert entry.tenant_id == tenant_id
        assert entry.entity_type == "material"
        assert entry.event_type == "config_changed"
        assert entry.old_value == old_value
        assert entry.new_value == new_value
        assert entry.user_id == user_id
        assert entry.generated_code is None
        assert entry.entity_id is None
        assert isinstance(result, uuid.UUID)

    async def test_log_config_changed_with_metadata(self):
        """Config changed events can include metadata about which fields changed."""
        session = AsyncMock()
        service = NumberSeriesAuditService(session)
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        metadata = {"fields_changed": ["abbreviation_length", "separator"]}
        await service.log_config_changed(
            tenant_id=tenant_id,
            entity_type="material",
            old_value='{"abbreviation_length": 3}',
            new_value='{"abbreviation_length": 5}',
            user_id=user_id,
            metadata=metadata,
        )

        entry = session.add.call_args[0][0]
        parsed = json.loads(entry.metadata_json)
        assert "abbreviation_length" in parsed["fields_changed"]


class TestTenantIsolation:
    """Test that all audit entries are tenant-isolated (Requirement 13.5)."""

    async def test_generated_event_includes_tenant_id(self):
        """Requirement 13.5: Generated events are scoped to tenant."""
        session = AsyncMock()
        service = NumberSeriesAuditService(session)
        tenant_id = uuid.uuid4()

        await service.log_generated(
            tenant_id=tenant_id,
            entity_type="material",
            generated_code="RM-ABC-000001",
            user_id=uuid.uuid4(),
        )

        entry = session.add.call_args[0][0]
        assert entry.tenant_id == tenant_id

    async def test_manual_override_event_includes_tenant_id(self):
        """Requirement 13.5: Manual override events are scoped to tenant."""
        session = AsyncMock()
        service = NumberSeriesAuditService(session)
        tenant_id = uuid.uuid4()

        await service.log_manual_override(
            tenant_id=tenant_id,
            entity_type="material",
            generated_code="MANUAL-001",
            user_id=uuid.uuid4(),
        )

        entry = session.add.call_args[0][0]
        assert entry.tenant_id == tenant_id

    async def test_config_changed_event_includes_tenant_id(self):
        """Requirement 13.5: Config changed events are scoped to tenant."""
        session = AsyncMock()
        service = NumberSeriesAuditService(session)
        tenant_id = uuid.uuid4()

        await service.log_config_changed(
            tenant_id=tenant_id,
            entity_type="material",
            old_value="old",
            new_value="new",
            user_id=uuid.uuid4(),
        )

        entry = session.add.call_args[0][0]
        assert entry.tenant_id == tenant_id

    async def test_different_tenants_get_separate_entries(self):
        """Requirement 13.5: Each tenant's entries have their own tenant_id."""
        session = AsyncMock()
        service = NumberSeriesAuditService(session)
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        await service.log_generated(
            tenant_id=tenant_a,
            entity_type="material",
            generated_code="RM-AAA-000001",
            user_id=uuid.uuid4(),
        )
        await service.log_generated(
            tenant_id=tenant_b,
            entity_type="material",
            generated_code="RM-BBB-000001",
            user_id=uuid.uuid4(),
        )

        calls = session.add.call_args_list
        entry_a = calls[0][0][0]
        entry_b = calls[1][0][0]

        assert entry_a.tenant_id == tenant_a
        assert entry_b.tenant_id == tenant_b
        assert entry_a.tenant_id != entry_b.tenant_id


class TestItemCodeServiceAuditIntegration:
    """Test that ItemCodeService calls audit logging appropriately."""

    async def test_generate_for_entity_logs_generated_event(self):
        """Requirement 13.1: generate_for_entity logs 'generated' when user_id is provided."""
        from unittest.mock import patch
        from backend.app.application.inventory.services.item_code_service import ItemCodeService

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        with patch.object(service, "get_or_create_config") as mock_config:
            mock_config.return_value = MagicMock(
                auto_generate=True,
                include_abbreviation=True,
                abbreviation_length=3,
                sequence_length=6,
                separator="-",
                prefix="",
            )
            with patch.object(service, "_resolve_prefix", return_value="RM"):
                with patch.object(service, "_get_or_create_sequence") as mock_seq:
                    mock_seq.return_value = MagicMock(next_number=1)
                    with patch.object(service, "code_exists", return_value=False):
                        with patch.object(
                            service._audit_service, "log_generated"
                        ) as mock_log:
                            mock_log.return_value = uuid.uuid4()
                            result = await service.generate_for_entity(
                                tenant_id=tenant_id,
                                entity_type="material",
                                sub_type="raw",
                                entity_name="Steel Pipe",
                                user_id=user_id,
                            )

            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["tenant_id"] == tenant_id
            assert call_kwargs["entity_type"] == "material"
            assert call_kwargs["user_id"] == user_id
            assert "RM" in call_kwargs["generated_code"]

    async def test_generate_for_entity_skips_audit_when_no_user_id(self):
        """No audit log when user_id is not provided (backward compat)."""
        from unittest.mock import patch
        from backend.app.application.inventory.services.item_code_service import ItemCodeService

        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        with patch.object(service, "get_or_create_config") as mock_config:
            mock_config.return_value = MagicMock(
                auto_generate=True,
                include_abbreviation=False,
                abbreviation_length=3,
                sequence_length=6,
                separator="-",
                prefix="PO",
            )
            with patch.object(service, "_get_or_create_sequence") as mock_seq:
                mock_seq.return_value = MagicMock(next_number=1)
                with patch.object(service, "code_exists", return_value=False):
                    with patch.object(
                        service._audit_service, "log_generated"
                    ) as mock_log:
                        result = await service.generate_for_entity(
                            tenant_id=tenant_id,
                            entity_type="purchase_order",
                        )

            mock_log.assert_not_called()

    async def test_validate_manual_code_logs_manual_override_event(self):
        """Requirement 13.2: validate_manual_code_with_policy logs 'manual_override'."""
        from unittest.mock import patch
        from backend.app.application.inventory.services.item_code_service import ItemCodeService

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = MagicMock(manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "_find_entity_with_code", return_value=None):
                with patch.object(
                    service._audit_service, "log_manual_override"
                ) as mock_log:
                    mock_log.return_value = uuid.uuid4()
                    result = await service.validate_manual_code_with_policy(
                        tenant_id=tenant_id,
                        entity_type="material",
                        code="CUSTOM-CODE-01",
                        user_is_admin=False,
                        user_id=user_id,
                    )

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs["tenant_id"] == tenant_id
        assert call_kwargs["entity_type"] == "material"
        assert call_kwargs["generated_code"] == "CUSTOM-CODE-01"
        assert call_kwargs["user_id"] == user_id

    async def test_validate_manual_code_skips_audit_when_no_user_id(self):
        """No manual_override audit when user_id is not provided."""
        from unittest.mock import patch
        from backend.app.application.inventory.services.item_code_service import ItemCodeService

        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = MagicMock(manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "_find_entity_with_code", return_value=None):
                with patch.object(
                    service._audit_service, "log_manual_override"
                ) as mock_log:
                    result = await service.validate_manual_code_with_policy(
                        tenant_id=tenant_id,
                        entity_type="material",
                        code="NOAUDIT-01",
                        user_is_admin=False,
                    )

        mock_log.assert_not_called()

    async def test_log_config_change_delegates_to_audit_service(self):
        """Requirement 13.3: log_config_change delegates to NumberSeriesAuditService."""
        from unittest.mock import patch
        from backend.app.application.inventory.services.item_code_service import ItemCodeService

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        with patch.object(
            service._audit_service, "log_config_changed"
        ) as mock_log:
            mock_log.return_value = uuid.uuid4()
            await service.log_config_change(
                tenant_id=tenant_id,
                entity_type="material",
                old_value='{"separator": "-"}',
                new_value='{"separator": "."}',
                user_id=user_id,
            )

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs["tenant_id"] == tenant_id
        assert call_kwargs["entity_type"] == "material"
        assert call_kwargs["old_value"] == '{"separator": "-"}'
        assert call_kwargs["new_value"] == '{"separator": "."}'
        assert call_kwargs["user_id"] == user_id

    async def test_audit_failure_does_not_break_code_generation(self):
        """Audit logging failure should not prevent code generation from succeeding."""
        from unittest.mock import patch
        from backend.app.application.inventory.services.item_code_service import ItemCodeService

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        with patch.object(service, "get_or_create_config") as mock_config:
            mock_config.return_value = MagicMock(
                auto_generate=True,
                include_abbreviation=False,
                abbreviation_length=3,
                sequence_length=6,
                separator="-",
                prefix="PO",
            )
            with patch.object(service, "_get_or_create_sequence") as mock_seq:
                mock_seq.return_value = MagicMock(next_number=1)
                with patch.object(service, "code_exists", return_value=False):
                    with patch.object(
                        service._audit_service, "log_generated",
                        side_effect=Exception("DB connection lost"),
                    ):
                        # Should NOT raise — audit failure is non-blocking
                        result = await service.generate_for_entity(
                            tenant_id=tenant_id,
                            entity_type="purchase_order",
                            user_id=user_id,
                        )

        assert result == "PO-000001"

    async def test_manual_override_audit_failure_does_not_break_validation(self):
        """Audit logging failure for manual override should not block code validation."""
        from unittest.mock import patch
        from backend.app.application.inventory.services.item_code_service import ItemCodeService

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = MagicMock(manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "_find_entity_with_code", return_value=None):
                with patch.object(
                    service._audit_service, "log_manual_override",
                    side_effect=Exception("DB write failed"),
                ):
                    # Should NOT raise — audit failure is non-blocking
                    result = await service.validate_manual_code_with_policy(
                        tenant_id=tenant_id,
                        entity_type="material",
                        code="MY-CODE-99",
                        user_is_admin=False,
                        user_id=user_id,
                    )

        assert result.code == "MY-CODE-99"
        assert result.was_auto_generated is False
