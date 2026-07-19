"""Notifications API routes."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_current_user_id,
    get_current_tenant_id,
    get_current_role,
)
from backend.app.application.finance.notification_service import NotificationService as FinanceNotificationService
from backend.app.application.notification.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


async def _get_db_session(request: Request):
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session


@router.get("", include_in_schema=False)
async def get_notifications_root(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Compatibility alias for GET /notifications and GET /notifications/."""
    return await get_notifications(
        unread_only=unread_only,
        page=page,
        page_size=page_size,
        tenant_id=tenant_id,
        user_id=user_id,
        session=session,
    )


@router.get("/")
async def get_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Get notifications for the current user."""
    svc = FinanceNotificationService(session)
    result = await svc.get_for_user(tenant_id, user_id, unread_only, page, page_size)
    return {
        **result,
        "items": [
            {
                "id": str(n.id),
                "type": n.notification_type,
                "title": n.title,
                "message": n.message,
                "reference_type": n.reference_type,
                "reference_id": str(n.reference_id) if n.reference_id else None,
                "is_read": n.is_read,
                "sent_at": n.created_at.isoformat(),
            }
            for n in result["items"]
        ],
    }


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Mark a single notification as read."""
    svc = FinanceNotificationService(session)
    count = await svc.mark_read(tenant_id, user_id, notification_id)
    return {"marked_read": count}


@router.post("/mark-all-read")
async def mark_all_read(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Mark all notifications as read for current user."""
    svc = FinanceNotificationService(session)
    count = await svc.mark_read(tenant_id, user_id)
    return {"marked_read": count}


# ── Phase 9: Operational Notifications ─────────────────────────────────

@router.get("/operational")
async def get_operational_notifications(
    unread_only: bool = Query(False),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Get operational notifications for the current user."""
    svc = NotificationService(session)
    notifications = await svc.get_user_notifications(
        tenant_id=tenant_id,
        user_id=user_id,
        unread_only=unread_only,
    )
    return {"items": notifications}


@router.post("/operational/{notification_id}/read")
async def mark_operational_notification_read(
    notification_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Mark an operational notification as read."""
    svc = NotificationService(session)
    await svc.mark_as_read(
        tenant_id=tenant_id,
        notification_id=notification_id,
        user_id=user_id,
    )
    return {"status": "success"}


@router.post("/operational/mark-all-read")
async def mark_all_operational_read(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Mark all operational notifications as read."""
    svc = NotificationService(session)
    await svc.mark_all_as_read(
        tenant_id=tenant_id,
        user_id=user_id,
    )
    return {"status": "success"}

