from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select

from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.interfaces.api.v1.dependencies.auth import get_container, get_current_tenant_id
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
    dependencies=[Depends(require_permission("audit:read"))],
)


def _stringify_uuid(value: uuid.UUID | None) -> str | None:
    return str(value) if value else None


def _actor_name(first_name: str | None, last_name: str | None, email: str | None) -> str | None:
    name = " ".join(part for part in [first_name, last_name] if part)
    return name or email


def _audit_log_to_dict(
    log: AuditLogModel,
    actor_email: str | None,
    actor_first_name: str | None,
    actor_last_name: str | None,
) -> dict:
    extra = log.extra or {}
    return {
        "id": str(log.id),
        "tenant_id": _stringify_uuid(log.tenant_id),
        "user_id": _stringify_uuid(log.user_id),
        "actor": {
            "email": actor_email,
            "name": _actor_name(actor_first_name, actor_last_name, actor_email),
        },
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": _stringify_uuid(log.entity_id),
        "summary": extra.get("summary"),
        "business_step": extra.get("business_step"),
        "module": extra.get("module"),
        "document_no": extra.get("document_no"),
        "source": extra.get("source") or "system",
        "status_code": extra.get("status_code"),
        "before_value": log.before_value,
        "after_value": log.after_value,
        "ip_address": log.ip_address,
        "correlation_id": _stringify_uuid(log.correlation_id),
        "extra": extra,
        "occurred_at": log.occurred_at.isoformat(),
    }


@router.get("")
async def list_audit_logs(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    action: Optional[str] = Query(None, description="Filter by action, e.g. PO_SENT"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[uuid.UUID] = Query(None, description="Filter by entity ID"),
    search: Optional[str] = Query(None, description="Search action or entity type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Tenant-scoped ERP audit trail for admins.

    This mirrors the ERP audit-summary pattern: admins can see who changed which
    business document, when it happened, and the detailed before/after payload
    when the operation captured one.
    """
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(
                AuditLogModel,
                UserModel.email,
                UserModel.first_name,
                UserModel.last_name,
            )
            .outerjoin(
                UserModel,
                (AuditLogModel.user_id == UserModel.id)
                & (AuditLogModel.tenant_id == UserModel.tenant_id),
            )
            .where(AuditLogModel.tenant_id == tenant_id)
        )

        if action:
            stmt = stmt.where(AuditLogModel.action == action)
        if entity_type:
            stmt = stmt.where(AuditLogModel.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AuditLogModel.entity_id == entity_id)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    AuditLogModel.action.ilike(pattern),
                    AuditLogModel.entity_type.ilike(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(AuditLogModel.occurred_at.desc()).offset(skip).limit(limit)
        result = await session.execute(stmt)
        rows = result.all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            _audit_log_to_dict(log, email, first_name, last_name)
            for log, email, first_name, last_name in rows
        ],
    }
