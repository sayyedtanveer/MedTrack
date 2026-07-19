"""
Property tests for LowStockChecker notification threshold crossing.

**Validates: Requirements 2.1, 2.2, 2.3, 2.5, 2.6**

These tests validate two correctness properties:
  - Property 2: Notification threshold crossing (bidirectional)
  - Property 11: Notification message completeness
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import decimals, uuids, text, one_of, just, none, composite

from backend.app.application.inventory.services.low_stock_checker import LowStockChecker
from backend.app.domain.inventory.entities.material import Material, MaterialType


# ─── Strategies ──────────────────────────────────────────────────────────────

# Positive decimals suitable for stock levels and reorder levels
positive_stock = decimals(
    min_value=Decimal("0.001"),
    max_value=Decimal("999999"),
    places=3,
    allow_nan=False,
    allow_infinity=False,
)

non_negative_stock = decimals(
    min_value=Decimal("0"),
    max_value=Decimal("999999"),
    places=3,
    allow_nan=False,
    allow_infinity=False,
)

# Material names for testing (non-empty, avoid generic blocked names)
material_names = text(
    min_size=3, max_size=50,
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -",
).filter(lambda s: s.strip() and len(s.strip()) >= 3)

# Material codes for testing
material_codes = text(
    min_size=2, max_size=20,
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",
).filter(lambda s: s.strip() and len(s.strip()) >= 2)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_material(
    *,
    name: str = "Steel Rod",
    code: str = "RM-STL-001",
    current_stock: Decimal,
    reorder_level: Decimal | None,
    material_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
) -> Material:
    """Create a Material entity with the given stock/reorder state."""
    return Material(
        id=material_id or uuid.uuid4(),
        tenant_id=tenant_id or uuid.uuid4(),
        code=code,
        name=name,
        material_type=MaterialType.RAW,
        current_stock=current_stock,
        reorder_level=reorder_level,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2: Notification threshold crossing (bidirectional)
#
# A LOW_STOCK_ALERT notification is created if and only if
#   previous_stock > reorder_level AND new_stock <= reorder_level.
# No notification is created if the material was already at or below
# threshold, has no reorder_level, or stock remains above the threshold.
# ─────────────────────────────────────────────────────────────────────────────


class TestNotificationThresholdCrossing:
    """**Validates: Requirements 2.1, 2.2, 2.3**"""

    @given(
        previous_stock=positive_stock,
        reorder_level=positive_stock,
        new_stock=non_negative_stock,
    )
    @settings(max_examples=200)
    async def test_notification_created_only_on_downward_crossing(
        self,
        previous_stock: Decimal,
        reorder_level: Decimal,
        new_stock: Decimal,
    ):
        """Property 2: Notification fires iff previous > threshold AND new <= threshold.

        For any combination of previous_stock, reorder_level, and new_stock:
        - If previous_stock > reorder_level AND new_stock <= reorder_level → notification created
        - Otherwise → no notification
        """
        tenant_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        notification_id = uuid.uuid4()

        material = _make_material(
            current_stock=new_stock,
            reorder_level=reorder_level,
            tenant_id=tenant_id,
        )

        mock_session = AsyncMock()
        mock_notification_svc = AsyncMock()
        mock_notification_svc.create_notification = AsyncMock(return_value=notification_id)

        checker = LowStockChecker(mock_session)
        checker._notification_svc = mock_notification_svc

        result = await checker.check_and_notify(
            tenant_id=tenant_id,
            material=material,
            previous_stock=previous_stock,
            actor_user_id=actor_id,
        )

        should_notify = previous_stock > reorder_level and new_stock <= reorder_level

        if should_notify:
            assert result == notification_id, (
                f"Expected notification for prev={previous_stock}, "
                f"reorder={reorder_level}, new={new_stock}"
            )
            mock_notification_svc.create_notification.assert_called_once()
        else:
            assert result is None, (
                f"Expected no notification for prev={previous_stock}, "
                f"reorder={reorder_level}, new={new_stock}"
            )
            mock_notification_svc.create_notification.assert_not_called()

    @given(
        previous_stock=non_negative_stock,
        new_stock=non_negative_stock,
    )
    @settings(max_examples=100)
    async def test_no_notification_when_reorder_level_is_none(
        self,
        previous_stock: Decimal,
        new_stock: Decimal,
    ):
        """Property 2 (sub-case): No notification when material has no reorder_level."""
        tenant_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        material = _make_material(
            current_stock=new_stock,
            reorder_level=None,
            tenant_id=tenant_id,
        )

        mock_session = AsyncMock()
        mock_notification_svc = AsyncMock()

        checker = LowStockChecker(mock_session)
        checker._notification_svc = mock_notification_svc

        result = await checker.check_and_notify(
            tenant_id=tenant_id,
            material=material,
            previous_stock=previous_stock,
            actor_user_id=actor_id,
        )

        assert result is None
        mock_notification_svc.create_notification.assert_not_called()

    @given(
        reorder_level=positive_stock,
        new_stock=non_negative_stock,
    )
    @settings(max_examples=100)
    async def test_no_notification_when_already_below_threshold(
        self,
        reorder_level: Decimal,
        new_stock: Decimal,
    ):
        """Property 2 (sub-case): No duplicate notification if stock was already
        at or below reorder_level before the mutation."""
        # previous_stock must be at or below reorder_level
        previous_stock = reorder_level - Decimal("0.001")
        assume(previous_stock >= Decimal("0"))

        tenant_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        material = _make_material(
            current_stock=new_stock,
            reorder_level=reorder_level,
            tenant_id=tenant_id,
        )

        mock_session = AsyncMock()
        mock_notification_svc = AsyncMock()

        checker = LowStockChecker(mock_session)
        checker._notification_svc = mock_notification_svc

        result = await checker.check_and_notify(
            tenant_id=tenant_id,
            material=material,
            previous_stock=previous_stock,
            actor_user_id=actor_id,
        )

        assert result is None
        mock_notification_svc.create_notification.assert_not_called()

    @given(
        reorder_level=positive_stock,
        previous_stock=positive_stock,
    )
    @settings(max_examples=100)
    async def test_no_notification_when_stock_remains_above_threshold(
        self,
        reorder_level: Decimal,
        previous_stock: Decimal,
    ):
        """Property 2 (sub-case): No notification if stock remains above threshold."""
        # Both previous and new stock are above reorder_level
        assume(previous_stock > reorder_level)
        new_stock = reorder_level + Decimal("0.001")

        tenant_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        material = _make_material(
            current_stock=new_stock,
            reorder_level=reorder_level,
            tenant_id=tenant_id,
        )

        mock_session = AsyncMock()
        mock_notification_svc = AsyncMock()

        checker = LowStockChecker(mock_session)
        checker._notification_svc = mock_notification_svc

        result = await checker.check_and_notify(
            tenant_id=tenant_id,
            material=material,
            previous_stock=previous_stock,
            actor_user_id=actor_id,
        )

        assert result is None
        mock_notification_svc.create_notification.assert_not_called()

    @given(
        reorder_level=positive_stock,
        previous_stock=positive_stock,
    )
    @settings(max_examples=100)
    async def test_notification_created_on_crossing_to_exactly_threshold(
        self,
        reorder_level: Decimal,
        previous_stock: Decimal,
    ):
        """Property 2 (sub-case): Notification fires when stock drops TO exactly
        the reorder_level (at-or-below condition)."""
        assume(previous_stock > reorder_level)
        new_stock = reorder_level  # exactly at threshold

        tenant_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        notification_id = uuid.uuid4()

        material = _make_material(
            current_stock=new_stock,
            reorder_level=reorder_level,
            tenant_id=tenant_id,
        )

        mock_session = AsyncMock()
        mock_notification_svc = AsyncMock()
        mock_notification_svc.create_notification = AsyncMock(return_value=notification_id)

        checker = LowStockChecker(mock_session)
        checker._notification_svc = mock_notification_svc

        result = await checker.check_and_notify(
            tenant_id=tenant_id,
            material=material,
            previous_stock=previous_stock,
            actor_user_id=actor_id,
        )

        assert result == notification_id
        mock_notification_svc.create_notification.assert_called_once()

    async def test_notification_failure_does_not_raise(self):
        """Requirement 2.5: Notification failure does not propagate — returns None."""
        tenant_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        reorder_level = Decimal("50")

        material = _make_material(
            current_stock=Decimal("40"),
            reorder_level=reorder_level,
            tenant_id=tenant_id,
        )

        mock_session = AsyncMock()
        mock_notification_svc = AsyncMock()
        mock_notification_svc.create_notification = AsyncMock(
            side_effect=RuntimeError("DB connection lost")
        )

        checker = LowStockChecker(mock_session)
        checker._notification_svc = mock_notification_svc

        # previous_stock > reorder_level AND current_stock <= reorder_level → should try
        result = await checker.check_and_notify(
            tenant_id=tenant_id,
            material=material,
            previous_stock=Decimal("100"),
            actor_user_id=actor_id,
        )

        # Should not raise, returns None on failure
        assert result is None
        mock_notification_svc.create_notification.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Property 11: Notification message completeness
#
# For any LOW_STOCK_ALERT notification created by the LowStockChecker, the
# notification message SHALL contain the material name, material code,
# current stock level, and reorder level.
# ─────────────────────────────────────────────────────────────────────────────


class TestNotificationMessageCompleteness:
    """**Validates: Requirements 2.5, 2.6**"""

    @given(
        reorder_level=positive_stock,
        mat_name=material_names,
        mat_code=material_codes,
    )
    @settings(max_examples=150)
    async def test_notification_message_contains_all_required_fields(
        self,
        reorder_level: Decimal,
        mat_name: str,
        mat_code: str,
    ):
        """Property 11: For any LOW_STOCK_ALERT notification, the message contains
        material name, material code, current stock level, and reorder level."""
        # Generate a crossing scenario directly: previous > reorder >= new
        previous_stock = reorder_level + Decimal("1")
        new_stock = reorder_level - Decimal("0.001")
        if new_stock < Decimal("0"):
            new_stock = Decimal("0")

        tenant_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        notification_id = uuid.uuid4()

        material = _make_material(
            name=mat_name,
            code=mat_code,
            current_stock=new_stock,
            reorder_level=reorder_level,
            tenant_id=tenant_id,
        )

        mock_session = AsyncMock()
        mock_notification_svc = AsyncMock()
        mock_notification_svc.create_notification = AsyncMock(return_value=notification_id)

        checker = LowStockChecker(mock_session)
        checker._notification_svc = mock_notification_svc

        await checker.check_and_notify(
            tenant_id=tenant_id,
            material=material,
            previous_stock=previous_stock,
            actor_user_id=actor_id,
        )

        # Verify create_notification was called
        mock_notification_svc.create_notification.assert_called_once()

        # Extract the message argument
        call_kwargs = mock_notification_svc.create_notification.call_args.kwargs
        message = call_kwargs["message"]

        # Verify message contains material name
        assert material.name in message, (
            f"Message missing material name '{material.name}': {message}"
        )

        # Verify message contains material code
        assert material.code in message, (
            f"Message missing material code '{material.code}': {message}"
        )

        # Verify message contains current stock level
        assert str(new_stock) in message, (
            f"Message missing current stock '{new_stock}': {message}"
        )

        # Verify message contains reorder level
        assert str(reorder_level) in message, (
            f"Message missing reorder level '{reorder_level}': {message}"
        )

        # Verify notification type is LOW_STOCK_ALERT
        assert call_kwargs["notification_type"] == "LOW_STOCK_ALERT"

    async def test_notification_message_format_specific_example(self):
        """Property 11 (specific example): Verify message format for a known material."""
        tenant_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        notification_id = uuid.uuid4()

        material = _make_material(
            name="Brass Fitting",
            code="RM-BRS-001",
            current_stock=Decimal("15"),
            reorder_level=Decimal("20"),
            tenant_id=tenant_id,
        )

        mock_session = AsyncMock()
        mock_notification_svc = AsyncMock()
        mock_notification_svc.create_notification = AsyncMock(return_value=notification_id)

        checker = LowStockChecker(mock_session)
        checker._notification_svc = mock_notification_svc

        await checker.check_and_notify(
            tenant_id=tenant_id,
            material=material,
            previous_stock=Decimal("25"),
            actor_user_id=actor_id,
        )

        call_kwargs = mock_notification_svc.create_notification.call_args.kwargs
        message = call_kwargs["message"]

        # Check all required components are present
        assert "Brass Fitting" in message
        assert "RM-BRS-001" in message
        assert "15" in message
        assert "20" in message

        # Verify other notification fields
        assert call_kwargs["notification_type"] == "LOW_STOCK_ALERT"
        assert call_kwargs["tenant_id"] == tenant_id
        assert call_kwargs["user_id"] == actor_id
        assert call_kwargs["reference_type"] == "material"
        assert call_kwargs["reference_id"] == material.id

    async def test_notification_includes_correct_reference_fields(self):
        """Verify notification includes material reference for linkage."""
        tenant_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        material_id = uuid.uuid4()
        notification_id = uuid.uuid4()

        material = _make_material(
            name="Copper Wire",
            code="RM-COP-002",
            current_stock=Decimal("5"),
            reorder_level=Decimal("10"),
            tenant_id=tenant_id,
            material_id=material_id,
        )

        mock_session = AsyncMock()
        mock_notification_svc = AsyncMock()
        mock_notification_svc.create_notification = AsyncMock(return_value=notification_id)

        checker = LowStockChecker(mock_session)
        checker._notification_svc = mock_notification_svc

        result = await checker.check_and_notify(
            tenant_id=tenant_id,
            material=material,
            previous_stock=Decimal("15"),
            actor_user_id=actor_id,
        )

        assert result == notification_id
        call_kwargs = mock_notification_svc.create_notification.call_args.kwargs
        assert call_kwargs["reference_type"] == "material"
        assert call_kwargs["reference_id"] == material_id
        assert call_kwargs["tenant_id"] == tenant_id
        assert call_kwargs["user_id"] == actor_id
