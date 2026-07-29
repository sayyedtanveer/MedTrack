import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.domain.tenant.entities.tenant_audit_log import TenantAuditLog
from backend.app.domain.tenant.repositories.tenant_audit_log_repository_interface import ITenantAuditLogRepository
from backend.app.infrastructure.persistence.models.tenant_audit_log_model import TenantAuditLogModel


class TenantAuditLogRepository(ITenantAuditLogRepository):
    """SQLAlchemy implementation of ITenantAuditLogRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, audit_log: TenantAuditLog) -> None:
        model = TenantAuditLogModel(
            id=audit_log.id,
            tenant_id=audit_log.tenant_id,
            action=audit_log.action,
            reason=audit_log.reason,
            acted_by=audit_log.acted_by,
            created_at=audit_log.created_at,
            updated_at=audit_log.updated_at,
        )
        self._session.add(model)

    async def get_by_tenant(self, tenant_id: uuid.UUID) -> List[TenantAuditLog]:
        stmt = select(TenantAuditLogModel).where(TenantAuditLogModel.tenant_id == tenant_id).order_by(TenantAuditLogModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [
            TenantAuditLog(
                id=m.id,
                tenant_id=m.tenant_id,
                action=m.action,
                reason=m.reason,
                acted_by=m.acted_by,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in models
        ]
