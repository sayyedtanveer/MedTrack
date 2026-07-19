"""Resource ownership validation utilities.

Ensures that resources are only accessible by their owning tenant,
preventing cross-tenant data leakage.

Requirements: 58.1–58.5
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException


def verify_tenant_ownership(
    resource_tenant_id: Any,
    request_tenant_id: Any,
    resource_name: str = "resource",
) -> None:
    """Raise HTTP 403 if the resource doesn't belong to the requesting tenant.

    Pass ``None`` for either argument to skip the check (system-level access).

    Requirements: 58.1, 58.2
    """
    if resource_tenant_id is None or request_tenant_id is None:
        return

    if str(resource_tenant_id) != str(request_tenant_id):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Access denied: {resource_name} does not belong to your organisation."
            ),
        )


def apply_tenant_filter(query: Any, model: Any, tenant_id: Any) -> Any:
    """Apply tenant_id filter to a SQLAlchemy query expression.

    Requirements: 58.1
    """
    if tenant_id:
        return query.where(model.tenant_id == tenant_id)
    return query
