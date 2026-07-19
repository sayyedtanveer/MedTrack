"""
RBAC Permission Audit Logging Middleware.
Logs all permission denials (403 responses) for compliance & forensics.
"""

import logging
from datetime import datetime
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("rbac_audit")


class RBACPermissionAuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all permission denials (403 responses).
    
    Provides:
    - JSON-structured logs for easy parsing
    - User/tenant/role context
    - Timestamp for compliance
    - Request details (path, method)
    - Helps with forensics if breach suspected
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Log 403 responses with full context
        if response.status_code == 403:
            # Extract user context from request scope (set by auth dependency)
            user_id = request.scope.get("user_id", "unknown")
            tenant_id = request.scope.get("tenant_id", "unknown")
            user_role = request.scope.get("user_role", "unknown")
            
            # Extract path/method
            path = request.url.path
            method = request.method
            
            # Log with structured format for easy parsing
            log_entry = {
                "event": "PERMISSION_DENIED",
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": str(user_id),
                "tenant_id": str(tenant_id),
                "role": str(user_role),
                "path": path,
                "method": method,
                "status_code": 403,
            }
            
            # Log as JSON for easy parsing
            logger.warning(
                f"PERMISSION_DENIED | "
                f"path={path} | "
                f"method={method} | "
                f"user_id={user_id} | "
                f"tenant_id={tenant_id} | "
                f"role={user_role} | "
                f"timestamp={datetime.utcnow().isoformat()}"
            )
        
        return response
