from abc import ABC, abstractmethod
import uuid
from typing import List

from backend.app.domain.tenant.entities.tenant_audit_log import TenantAuditLog


class ITenantAuditLogRepository(ABC):
    """Repository interface for TenantAuditLog."""

    @abstractmethod
    async def save(self, audit_log: TenantAuditLog) -> None:
        pass

    @abstractmethod
    async def get_by_tenant(self, tenant_id: uuid.UUID) -> List[TenantAuditLog]:
        pass
