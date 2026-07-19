"""Notification Service - operational flow for real-time notifications."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class NotificationService:
    """Service for notification management and delivery.

    Responsibilities:
    - Create notifications for operational events
    - Get user notifications
    - Mark notifications as read
    - Notification types: MATERIAL_SHORTAGE, WO_OVERDUE, QC_REJECTED, DELIVERY_READY
    """

    def __init__(self, session: AsyncSession, connection_manager=None):
        self._session = session
        self._connection_manager = connection_manager

    async def create_notification(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        deep_link: Optional[str] = None,
        target_role: Optional[str] = None,
    ) -> uuid.UUID:
        """Create a notification for a user."""
        from backend.app.infrastructure.persistence.models.notification_model import NotificationModel

        notification = NotificationModel(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            reference_type=reference_type,
            reference_id=reference_id,
            deep_link=deep_link,
            target_role=target_role,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(notification)
        await self._session.flush()

        # Best-effort WebSocket broadcast for real-time delivery
        if self._connection_manager:
            try:
                payload = {
                    "id": str(notification.id),
                    "type": notification_type,
                    "title": title,
                    "message": message,
                    "reference_type": reference_type,
                    "reference_id": str(reference_id) if reference_id else None,
                    "is_read": False,
                    "created_at": notification.created_at.isoformat(),
                }
                await self._connection_manager.send_to_user(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    message_type="notification",
                    payload=payload,
                )
            except Exception:
                pass  # WebSocket failure must not affect persistence

        return notification.id

    async def get_user_notifications(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        unread_only: bool = False,
    ) -> list[dict]:
        """Get notifications for a user."""
        from backend.app.infrastructure.persistence.models.notification_model import NotificationModel

        stmt = (
            select(NotificationModel)
            .where(
                NotificationModel.tenant_id == tenant_id,
                NotificationModel.user_id == user_id,
            )
        )
        if unread_only:
            stmt = stmt.where(NotificationModel.is_read.is_(False))
        stmt = stmt.order_by(NotificationModel.created_at.desc())
        
        result = await self._session.execute(stmt)
        notifications = result.scalars().all()

        notification_list = []
        for notif in notifications:
            notification_list.append({
                "notification_id": notif.id,
                "notification_type": notif.notification_type,
                "title": notif.title,
                "message": notif.message,
                "reference_type": notif.reference_type,
                "reference_id": notif.reference_id,
                "is_read": notif.is_read,
                "created_at": notif.created_at,
            })

        return notification_list

    async def mark_as_read(
        self,
        *,
        tenant_id: uuid.UUID,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Mark a notification as read."""
        from backend.app.infrastructure.persistence.models.notification_model import NotificationModel

        stmt = select(NotificationModel).where(
            NotificationModel.id == notification_id,
            NotificationModel.tenant_id == tenant_id,
            NotificationModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        notification = result.scalar_one_or_none()

        if notification:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)

    async def mark_all_as_read(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Mark all notifications for a user as read."""
        from backend.app.infrastructure.persistence.models.notification_model import NotificationModel
        from sqlalchemy import update

        stmt = (
            update(NotificationModel)
            .where(
                NotificationModel.tenant_id == tenant_id,
                NotificationModel.user_id == user_id,
                NotificationModel.is_read.is_(False),
            )
            .values(
                is_read=True,
                read_at=datetime.now(timezone.utc),
            )
        )
        await self._session.execute(stmt)

    async def notify_material_shortage(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_name: str,
        shortage_quantity: float,
    ) -> uuid.UUID:
        """Create a material shortage notification."""
        return await self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type="MATERIAL_SHORTAGE",
            title="Material Shortage Alert",
            message=f"Material shortage for {material_name}: {shortage_quantity} units required but not available.",
            reference_type="work_order",
            reference_id=work_order_id,
        )

    async def notify_wo_overdue(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
        due_date: datetime,
    ) -> uuid.UUID:
        """Create a work order overdue notification."""
        return await self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type="WO_OVERDUE",
            title="Work Order Overdue",
            message=f"Work Order {wo_number} is overdue. Due date: {due_date.strftime('%Y-%m-%d')}",
            reference_type="work_order",
            reference_id=work_order_id,
        )

    async def notify_qc_rejected(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        work_order_id: uuid.UUID,
        wo_number: str,
        reason: str,
    ) -> uuid.UUID:
        """Create a QC rejection notification."""
        return await self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type="QC_REJECTED",
            title="QC Rejection Alert",
            message=f"Work Order {wo_number} failed QC inspection. Reason: {reason}",
            reference_type="work_order",
            reference_id=work_order_id,
        )

    async def notify_delivery_ready(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        delivery_order_id: uuid.UUID,
        do_number: str,
        customer_id: uuid.UUID,
    ) -> uuid.UUID:
        """Create a delivery ready notification."""
        return await self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type="DELIVERY_READY",
            title="Delivery Ready to Ship",
            message=f"Delivery Order {do_number} is ready to ship.",
            reference_type="delivery_order",
            reference_id=delivery_order_id,
        )
