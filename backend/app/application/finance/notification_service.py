"""Notification service — in-app + email notification dispatch."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.finance_models import NotificationModel
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.application.rbac.service import role_has_permission


NOTIFICATION_TYPES = {
    "LOW_STOCK": "Low Stock Alert",
    "PO_RECEIVED": "Purchase Order Received",
    "NCR_CREATED": "Non-Conformance Report Created",
    "INVOICE_OVERDUE": "Invoice Overdue",
    "WORK_ORDER": "Work Order Update",
    "PAYMENT_RECEIVED": "Payment Received",
    "SYSTEM": "System Notification",
}


class NotificationService:
    """
    Handles in-app notifications and email dispatch facade.
    Email sending is delegated to IEmailService (can be stub or real SMTP).
    """

    def __init__(self, session: AsyncSession, email_service=None, connection_manager=None):
        self.session = session
        self.email_service = email_service
        self.connection_manager = connection_manager

    async def send(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        send_email: bool = False,
    ) -> NotificationModel:
        """Create and optionally email a notification."""
        notification = NotificationModel(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            reference_type=reference_type,
            reference_id=reference_id,
            is_read=False,
        )
        self.session.add(notification)
        await self.session.flush()
        payload = {
            "id": str(notification.id),
            "type": notification_type,
            "title": title,
            "message": message,
            "reference_type": reference_type,
            "reference_id": str(reference_id) if reference_id else None,
            "is_read": False,
            "sent_at": (notification.created_at or datetime.now(timezone.utc)).isoformat(),
            "timestamp": (notification.created_at or datetime.now(timezone.utc)).isoformat(),
            "data": {
                "reference_type": reference_type,
                "reference_id": str(reference_id) if reference_id else None,
            },
        }

        if send_email and self.email_service:
            try:
                user_q = await self.session.execute(
                    select(UserModel).where(UserModel.id == user_id)
                )
                user = user_q.scalar_one_or_none()
                if user and user.email:
                    await self.email_service.send_notification(
                        to=user.email,
                        subject=title,
                        body=message,
                    )
            except Exception:
                pass  # Email failure should not fail the operation

        await self.session.commit()
        await self._push_realtime(tenant_id, user_id, payload)
        return notification

    async def _push_realtime(self, tenant_id: uuid.UUID, user_id: uuid.UUID, payload: dict) -> None:
        """Best-effort live delivery; persisted notification remains source of truth."""
        if not self.connection_manager:
            return
        try:
            await self.connection_manager.send_to_user(
                tenant_id=tenant_id,
                user_id=user_id,
                message_type="notification",
                payload=payload,
            )
        except Exception:
            pass

    async def broadcast_to_role(
        self,
        tenant_id: uuid.UUID,
        role: str,
        notification_type: str,
        title: str,
        message: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Send notification to all users with a given role in the tenant."""
        users_q = await self.session.execute(
            select(UserModel).where(
                UserModel.tenant_id == tenant_id,
                UserModel.role == role,
                UserModel.is_active == True,
            )
        )
        users = users_q.scalars().all()
        count = 0
        for user in users:
            await self.send(
                tenant_id=tenant_id,
                user_id=user.id,
                notification_type=notification_type,
                title=title,
                message=message,
                reference_type=reference_type,
                reference_id=reference_id,
            )
            count += 1
        await self.session.commit()
        return count

    async def broadcast_to_permission(
        self,
        tenant_id: uuid.UUID,
        permission: str,
        notification_type: str,
        title: str,
        message: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Send notification to active users whose role grants a permission."""
        users_q = await self.session.execute(
            select(UserModel.id, UserModel.role).where(
                UserModel.tenant_id == tenant_id,
                UserModel.is_active == True,
                UserModel.is_deleted == False,
            )
        )
        users = users_q.all()
        count = 0
        for user_id, role in users:
            if not await role_has_permission(self.session, tenant_id, role, permission):
                continue
            await self.send(
                tenant_id=tenant_id,
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                reference_type=reference_type,
                reference_id=reference_id,
            )
            count += 1
        await self.session.commit()
        return count

    async def get_for_user(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        q = select(NotificationModel).where(
            NotificationModel.tenant_id == tenant_id,
            NotificationModel.user_id == user_id,
        )
        if unread_only:
            q = q.where(NotificationModel.is_read == False)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.session.execute(count_q)).scalar()

        unread_q = select(func.count()).where(
            NotificationModel.tenant_id == tenant_id,
            NotificationModel.user_id == user_id,
            NotificationModel.is_read == False,
        )
        unread_count = (await self.session.execute(unread_q)).scalar()

        q = q.order_by(NotificationModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(q)

        return {
            "items": result.scalars().all(),
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "pages": (total + page_size - 1) // page_size,
        }

    async def mark_read(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        notification_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Mark one or all notifications as read."""
        q = (
            update(NotificationModel)
            .where(
                NotificationModel.tenant_id == tenant_id,
                NotificationModel.user_id == user_id,
                NotificationModel.is_read == False,
            )
            .values(is_read=True)
        )
        if notification_id:
            q = q.where(NotificationModel.id == notification_id)

        result = await self.session.execute(q)
        await self.session.commit()
        return result.rowcount

    async def check_and_notify_low_stock(self, tenant_id: uuid.UUID, user_ids: List[uuid.UUID]) -> int:
        """Fire LOW_STOCK notifications for materials below reorder point."""
        from sqlalchemy import text
        result = await self.session.execute(
            text("""
                SELECT m.id, m.name, m.sku, sl.quantity_on_hand, m.reorder_point
                FROM materials m
                LEFT JOIN stock_levels sl ON sl.material_id = m.id AND sl.tenant_id = m.tenant_id
                WHERE m.tenant_id = :tenant_id
                    AND m.is_deleted = false
                    AND m.reorder_point IS NOT NULL
                    AND (sl.quantity_on_hand IS NULL OR sl.quantity_on_hand <= m.reorder_point)
            """),
            {"tenant_id": tenant_id}
        )
        low_stock_items = result.fetchall()
        count = 0
        for item in low_stock_items:
            for uid in user_ids:
                await self.send(
                    tenant_id=tenant_id,
                    user_id=uid,
                    notification_type="LOW_STOCK",
                    title=f"Low Stock: {item.name}",
                    message=f"Material '{item.name}' (SKU: {item.sku}) is below reorder point. Current: {item.quantity_on_hand or 0}, Reorder at: {item.reorder_point}",
                    reference_type="material",
                    reference_id=item.id,
                )
                count += 1
        return count
