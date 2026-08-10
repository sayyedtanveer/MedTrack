from __future__ import annotations

import uuid
from backend.app.domain.tenant.entities.tenant import Tenant
from backend.app.domain.tenant.entities.user import User

class PlatformAuthorizationService:
    """
    Encapsulates logic for determining if a user or tenant has platform administration rights.
    """

    @staticmethod
    def is_platform_admin_tenant(tenant: Tenant) -> bool:
        """
        Check if the given tenant is designated as the system/platform tenant.
        """
        return tenant.is_system_tenant

    @staticmethod
    def is_platform_admin(user: User, tenant: Tenant) -> bool:
        """
        Check if the user is a platform administrator.
        Currently, a platform admin is any user with TENANT_ADMIN role
        inside the designated system tenant.
        """
        if not PlatformAuthorizationService.is_platform_admin_tenant(tenant):
            return False
            
        return user.role in ("tenant_admin", "admin")
