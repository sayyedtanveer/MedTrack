"""Unit tests for item code immutability enforcement.

Tests cover:
- On material creation: code_locked is set to true after code assignment (Requirement 9.1)
- On material update: if code_locked == true and request contains a different code value,
  return 422 error "Item code is immutable" (Requirement 9.2)
- If update request omits code fields entirely, retain existing code (Requirement 9.5)
- Existing materials retain their legacy codes unchanged when Number Series Engine activates (Requirement 9.4)
- Material name changes do not affect the item code (Requirement 9.3)

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.application.inventory.commands.inventory_commands import (
    MISSING,
    CreateMaterialCommand,
    UpdateMaterialCommand,
)
from backend.app.application.inventory.handlers.inventory_handlers import (
    CreateMaterialHandler,
    UpdateMaterialHandler,
)
from backend.app.domain.inventory.entities.material import Material, MaterialType


def _make_material(
    *,
    code: str = "RM-GEN-0001",
    name: str = "Steel Pipe",
    material_type: MaterialType = MaterialType.RAW,
    code_locked: bool = True,
    tenant_id: uuid.UUID | None = None,
) -> Material:
    """Helper to build a Material entity for testing."""
    return Material(
        id=uuid.uuid4(),
        tenant_id=tenant_id or uuid.uuid4(),
        code=code,
        name=name,
        material_type=material_type,
        code_locked=code_locked,
    )


class TestCodeLockedOnCreation:
    """Test Requirement 9.1: code_locked is true after code assignment on creation."""

    def test_material_entity_defaults_code_locked_true(self):
        """A newly created Material entity has code_locked=True by default."""
        material = Material(
            tenant_id=uuid.uuid4(),
            code="RM-TEST-0001",
            name="Test Material",
            material_type=MaterialType.RAW,
        )
        assert material.code_locked is True

    def test_material_entity_code_locked_is_read_only(self):
        """code_locked cannot be changed via normal property access."""
        material = _make_material(code_locked=True)
        # code_locked has no setter — verify it stays True
        assert material.code_locked is True
        # Attempting to set via attribute should fail (no setter)
        with pytest.raises(AttributeError):
            material.code_locked = False  # type: ignore[misc]


class TestCodeImmutabilityOnUpdate:
    """Test Requirement 9.2: reject update when code_locked=True and different code provided."""

    @pytest.mark.asyncio
    async def test_update_with_different_code_raises_immutable_error(self):
        """When code_locked=True and a different code is provided, raise ValueError."""
        tenant_id = uuid.uuid4()
        material = _make_material(code="RM-GEN-0001", code_locked=True, tenant_id=tenant_id)

        repo = AsyncMock()
        repo.get_by_id.return_value = material
        uow = AsyncMock()

        handler = UpdateMaterialHandler(material_repo=repo, uow=uow)

        with pytest.raises(ValueError, match="Item code is immutable"):
            await handler.handle(
                UpdateMaterialCommand(
                    id=material.id,
                    tenant_id=tenant_id,
                    code="NEW-CODE-9999",
                )
            )

    @pytest.mark.asyncio
    async def test_update_with_same_code_succeeds(self):
        """When the provided code matches the current code, no error is raised."""
        tenant_id = uuid.uuid4()
        material = _make_material(code="RM-GEN-0001", code_locked=True, tenant_id=tenant_id)

        repo = AsyncMock()
        repo.get_by_id.return_value = material
        repo.name_exists.return_value = False
        uow = AsyncMock()

        handler = UpdateMaterialHandler(material_repo=repo, uow=uow)

        # Should NOT raise — same code
        result = await handler.handle(
            UpdateMaterialCommand(
                id=material.id,
                tenant_id=tenant_id,
                code="RM-GEN-0001",
            )
        )
        assert result.code == "RM-GEN-0001"

    @pytest.mark.asyncio
    async def test_update_with_code_omitted_retains_existing(self):
        """When code is MISSING (omitted), existing code is retained unchanged."""
        tenant_id = uuid.uuid4()
        material = _make_material(code="RM-GEN-0001", code_locked=True, tenant_id=tenant_id)

        repo = AsyncMock()
        repo.get_by_id.return_value = material
        repo.name_exists.return_value = False
        uow = AsyncMock()

        handler = UpdateMaterialHandler(material_repo=repo, uow=uow)

        # code defaults to MISSING
        result = await handler.handle(
            UpdateMaterialCommand(
                id=material.id,
                tenant_id=tenant_id,
                name="New Name For Material",
            )
        )
        assert result.code == "RM-GEN-0001"

    @pytest.mark.asyncio
    async def test_update_with_none_code_retains_existing(self):
        """When code is explicitly None, existing code is retained unchanged."""
        tenant_id = uuid.uuid4()
        material = _make_material(code="RM-GEN-0001", code_locked=True, tenant_id=tenant_id)

        repo = AsyncMock()
        repo.get_by_id.return_value = material
        repo.name_exists.return_value = False
        uow = AsyncMock()

        handler = UpdateMaterialHandler(material_repo=repo, uow=uow)

        result = await handler.handle(
            UpdateMaterialCommand(
                id=material.id,
                tenant_id=tenant_id,
                code=None,
            )
        )
        assert result.code == "RM-GEN-0001"


class TestNameChangeDoesNotAffectCode:
    """Test Requirement 9.3: name changes do not regenerate or modify the item code."""

    @pytest.mark.asyncio
    async def test_name_change_preserves_item_code(self):
        """Changing the material name does not modify the item code."""
        tenant_id = uuid.uuid4()
        original_code = "RM-STP-000001"
        material = _make_material(
            code=original_code,
            name="Steel Pipe",
            code_locked=True,
            tenant_id=tenant_id,
        )

        repo = AsyncMock()
        repo.get_by_id.return_value = material
        repo.name_exists.return_value = False
        uow = AsyncMock()

        handler = UpdateMaterialHandler(material_repo=repo, uow=uow)

        result = await handler.handle(
            UpdateMaterialCommand(
                id=material.id,
                tenant_id=tenant_id,
                name="Stainless Steel Pipe",
            )
        )
        # Code must remain unchanged despite name change
        assert result.code == original_code
        assert result.name == "Stainless Steel Pipe"


class TestLegacyCodePreservation:
    """Test Requirement 9.4: existing materials retain legacy codes when engine activates."""

    @pytest.mark.asyncio
    async def test_legacy_material_code_locked_prevents_modification(self):
        """An existing material with a legacy code (code_locked=True) rejects code change."""
        tenant_id = uuid.uuid4()
        # Legacy format code
        material = _make_material(
            code="RM-GEN-0042",
            code_locked=True,
            tenant_id=tenant_id,
        )

        repo = AsyncMock()
        repo.get_by_id.return_value = material
        uow = AsyncMock()

        handler = UpdateMaterialHandler(material_repo=repo, uow=uow)

        with pytest.raises(ValueError, match="Item code is immutable"):
            await handler.handle(
                UpdateMaterialCommand(
                    id=material.id,
                    tenant_id=tenant_id,
                    code="RM-NEW-FORMAT-001",
                )
            )

    @pytest.mark.asyncio
    async def test_legacy_material_without_code_in_update_stays_unchanged(self):
        """A legacy material updated without code field retains its legacy code."""
        tenant_id = uuid.uuid4()
        material = _make_material(
            code="RM-GEN-0042",
            code_locked=True,
            tenant_id=tenant_id,
        )

        repo = AsyncMock()
        repo.get_by_id.return_value = material
        repo.name_exists.return_value = False
        uow = AsyncMock()

        handler = UpdateMaterialHandler(material_repo=repo, uow=uow)

        result = await handler.handle(
            UpdateMaterialCommand(
                id=material.id,
                tenant_id=tenant_id,
                description="Updated description",
            )
        )
        assert result.code == "RM-GEN-0042"
