"""Low Stock Checker — fires notifications when stock crosses below reorder level."""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.notification.services.notification_service import NotificationService
from backend.app.domain.inventory.entities.material import Material

logger = logging.getLogger(__name__)


class LowStockChecker:
    """Checks if a stock mutation caused the material to cross below reorder_level.

    Fires a LOW_STOCK_ALERT notification only on a downward threshold crossing:
      previous_stock > reorder_level AND current_stock <= reorder_level

    If the material was already at or below the threshold before the mutation,
    no duplicate notification is created.

    Notification creation is wrapped in try/except so that a failure in the
    notification subsystem never rolls back the stock mutation.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._notification_svc = NotificationService(session)

    async def check_and_notify(
        self,
        *,
        tenant_id: uuid.UUID,
        material: Material,
        previous_stock: Decimal,
        actor_user_id: uuid.UUID,
    ) -> Optional[uuid.UUID]:
        """Evaluate whether to fire a LOW_STOCK_ALERT notification.

        Args:
            tenant_id: The tenant that owns this material.
            material: The Material entity *after* the stock mutation has been applied.
            previous_stock: The material's current_stock value *before* the mutation.
            actor_user_id: The user who performed the stock operation.

        Returns:
            The notification UUID if a LOW_STOCK_ALERT was created, otherwise None.
        """
        reorder_level = material.reorder_level

        # No threshold configured — skip entirely
        if reorder_level is None:
            return None

        current_stock = material.current_stock
        was_above = previous_stock > reorder_level
        is_now_at_or_below = current_stock <= reorder_level

        if not (was_above and is_now_at_or_below):
            # Either stock was already at/below threshold (avoid duplicate),
            # or stock is still above threshold — no notification needed.
            return None

        # Threshold crossed downward — fire notification
        try:
            notification_id = await self._notification_svc.create_notification(
                tenant_id=tenant_id,
                user_id=actor_user_id,
                notification_type="LOW_STOCK_ALERT",
                title="Low Stock Alert",
                message=(
                    f"{material.name} ({material.code}) stock is now {current_stock}, "
                    f"below reorder level of {reorder_level}."
                ),
                reference_type="material",
                reference_id=material.id,
            )
            return notification_id
        except Exception:
            logger.exception(
                "Failed to create LOW_STOCK_ALERT notification for material %s (tenant %s). "
                "Stock mutation will proceed without notification.",
                material.id,
                tenant_id,
            )
            return None
