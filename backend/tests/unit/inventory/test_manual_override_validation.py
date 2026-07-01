"""Unit tests for ItemCodeService.validate_manual_code_with_policy().

Tests cover:
- Policy enforcement (never, admin_only, always)
- Manual code format validation (alphanumeric + hyphens + underscores, 2-50 chars)
- Uniqueness validation within tenant+entity_type
- Duplicate code error message includes conflicting entity info
- Default policy (no config): "never"

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.application.inventory.services.item_code_service import (
    ItemCodeService,
    ManualCodeResult,
    MANUAL_CODE_MIN_LENGTH,
    MANUAL_CODE_MAX_LENGTH,
)
from backend.app.infrastructure.persistence.models.number_series_models import (
    NumberSeriesConfigModel,
)


def _make_config(
    tenant_id: uuid.UUID,
    entity_type: str = "material",
    manual_override: str = "never",
    auto_generate: bool = True,
) -> NumberSeriesConfigModel:
    """Helper to build a NumberSeriesConfigModel for testing."""
    now = datetime.now(timezone.utc)
    return NumberSeriesConfigModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        entity_type=entity_type,
        auto_generate=auto_generate,
        manual_override=manual_override,
        prefix="RM",
        include_abbreviation=True,
        abbreviation_length=3,
        sequence_length=6,
        separator="-",
        lock_after_save=True,
        created_at=now,
        updated_at=now,
    )


class TestManualOverridePolicyNever:
    """Test manual_override == 'never': discard user code, auto-generate instead."""

    async def test_never_policy_discards_user_code_and_auto_generates(self):
        """Requirement 10.1: When manual_override='never', discard user code, auto-generate."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="never")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "generate_for_entity", return_value="RM-STP-000001"):
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="USER-CODE-123",
                    user_is_admin=False,
                    sub_type="raw",
                    entity_name="Steel Pipe",
                )

        assert result.code == "RM-STP-000001"
        assert result.was_auto_generated is True

    async def test_never_policy_does_not_raise_error(self):
        """Requirement 10.1: No error raised when policy is 'never'."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="never")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "generate_for_entity", return_value="RM-ABC-000001"):
                # Should NOT raise — even though user provided a code
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="MY-CUSTOM-CODE",
                    user_is_admin=True,  # Even admin is overridden
                    sub_type="raw",
                    entity_name="Copper Wire",
                )

        assert result.was_auto_generated is True


class TestManualOverridePolicyAdminOnly:
    """Test manual_override == 'admin_only': reject non-admin, accept admin."""

    async def test_admin_only_rejects_non_admin_user(self):
        """Requirement 10.2: Non-admin user with admin_only policy gets rejected."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="admin_only")

        with patch.object(service, "_try_load_config", return_value=config):
            with pytest.raises(ValueError, match="restricted to administrators"):
                await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="CUSTOM-001",
                    user_is_admin=False,
                    sub_type="raw",
                    entity_name="Steel Pipe",
                )

    async def test_admin_only_accepts_admin_user(self):
        """Requirement 10.3: Admin user with admin_only policy is accepted."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="admin_only")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "_find_entity_with_code", return_value=None):
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="CUSTOM-001",
                    user_is_admin=True,
                    sub_type="raw",
                    entity_name="Steel Pipe",
                )

        assert result.code == "CUSTOM-001"
        assert result.was_auto_generated is False


class TestManualOverridePolicyAlways:
    """Test manual_override == 'always': accept any authenticated user."""

    async def test_always_policy_accepts_any_user(self):
        """Requirement 10.4: Any authenticated user can provide manual code."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "_find_entity_with_code", return_value=None):
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="MY-CODE-42",
                    user_is_admin=False,
                    sub_type="raw",
                    entity_name="Aluminium Sheet",
                )

        assert result.code == "MY-CODE-42"
        assert result.was_auto_generated is False

    async def test_always_policy_accepts_admin_too(self):
        """Requirement 10.4: Admin user is also accepted with 'always' policy."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "_find_entity_with_code", return_value=None):
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="ADM_CODE-99",
                    user_is_admin=True,
                    sub_type="raw",
                    entity_name="Copper Wire",
                )

        assert result.code == "ADM_CODE-99"
        assert result.was_auto_generated is False


class TestManualCodeFormatValidation:
    """Test format validation: alphanumeric + hyphens + underscores, 2-50 chars."""

    async def test_rejects_code_too_short(self):
        """Requirement 10.5: Code must be at least 2 characters."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with pytest.raises(ValueError, match="at least 2 characters"):
                await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="X",
                    user_is_admin=False,
                )

    async def test_rejects_code_too_long(self):
        """Requirement 10.5: Code must be at most 50 characters."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")
        long_code = "A" * 51

        with patch.object(service, "_try_load_config", return_value=config):
            with pytest.raises(ValueError, match="at most 50 characters"):
                await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code=long_code,
                    user_is_admin=False,
                )

    async def test_rejects_code_with_spaces(self):
        """Requirement 10.5: Code cannot contain spaces."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with pytest.raises(ValueError, match="alphanumeric characters, hyphens, and underscores"):
                await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="MY CODE",
                    user_is_admin=False,
                )

    async def test_rejects_code_with_special_characters(self):
        """Requirement 10.5: Code cannot contain special characters like @, #, $."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with pytest.raises(ValueError, match="alphanumeric characters, hyphens, and underscores"):
                await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="CODE@123",
                    user_is_admin=False,
                )

    async def test_accepts_valid_alphanumeric_code(self):
        """Requirement 10.5: Alphanumeric codes are accepted."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "_find_entity_with_code", return_value=None):
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="ABC123",
                    user_is_admin=False,
                )
        assert result.code == "ABC123"

    async def test_accepts_code_with_hyphens(self):
        """Requirement 10.5: Hyphens are allowed."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "_find_entity_with_code", return_value=None):
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="RM-RAW-001",
                    user_is_admin=False,
                )
        assert result.code == "RM-RAW-001"

    async def test_accepts_code_with_underscores(self):
        """Requirement 10.5: Underscores are allowed."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "_find_entity_with_code", return_value=None):
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="ITEM_CODE_42",
                    user_is_admin=False,
                )
        assert result.code == "ITEM_CODE_42"

    async def test_accepts_minimum_length_code(self):
        """Requirement 10.5: 2-char code is accepted (minimum)."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "_find_entity_with_code", return_value=None):
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="AB",
                    user_is_admin=False,
                )
        assert result.code == "AB"

    async def test_accepts_maximum_length_code(self):
        """Requirement 10.5: 50-char code is accepted (maximum)."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")
        max_code = "A" * 50

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "_find_entity_with_code", return_value=None):
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code=max_code,
                    user_is_admin=False,
                )
        assert result.code == max_code


class TestManualCodeUniquenessValidation:
    """Test uniqueness validation within tenant+entity_type."""

    async def test_duplicate_code_returns_conflicting_entity_info(self):
        """Requirement 10.6: Duplicate code error includes which entity holds the code."""
        tenant_id = uuid.uuid4()
        conflicting_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(
                service, "_find_entity_with_code",
                return_value=(conflicting_id, "Existing Steel Pipe"),
            ):
                with pytest.raises(ValueError) as exc_info:
                    await service.validate_manual_code_with_policy(
                        tenant_id=tenant_id,
                        entity_type="material",
                        code="STEEL-001",
                        user_is_admin=False,
                    )

        error_msg = str(exc_info.value)
        assert "STEEL-001" in error_msg
        assert "Existing Steel Pipe" in error_msg
        assert str(conflicting_id) in error_msg

    async def test_unique_code_is_accepted(self):
        """Requirement 10.5: Unique code within tenant+entity_type passes."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        config = _make_config(tenant_id, manual_override="always")

        with patch.object(service, "_try_load_config", return_value=config):
            with patch.object(service, "_find_entity_with_code", return_value=None):
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="UNIQUE-CODE",
                    user_is_admin=False,
                )

        assert result.code == "UNIQUE-CODE"
        assert result.was_auto_generated is False


class TestDefaultPolicy:
    """Test default policy when no config exists."""

    async def test_no_config_defaults_to_never(self):
        """Requirement 10.7: No config defaults to 'never' (auto-generate)."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        with patch.object(service, "_try_load_config", return_value=None):
            with patch.object(service, "generate_for_entity", return_value="RM-GEN-000001"):
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="USER-CODE",
                    user_is_admin=True,
                    sub_type="raw",
                    entity_name="Generic Material",
                )

        assert result.code == "RM-GEN-000001"
        assert result.was_auto_generated is True

    async def test_no_config_auto_generates_for_admin_too(self):
        """Requirement 10.7: Even admin cannot override when default is 'never'."""
        tenant_id = uuid.uuid4()
        session = AsyncMock()
        service = ItemCodeService(session)

        with patch.object(service, "_try_load_config", return_value=None):
            with patch.object(service, "generate_for_entity", return_value="FG-ABC-000001"):
                result = await service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="material",
                    code="ADMIN-ATTEMPT",
                    user_is_admin=True,
                    sub_type="finished",
                    entity_name="Finished Product",
                )

        assert result.was_auto_generated is True
