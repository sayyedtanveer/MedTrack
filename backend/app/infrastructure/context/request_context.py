from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


# ── ContextVars — one per request lifecycle ──────────────────────────────────
_correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
_tenant_id_var: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
_user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_ip_address_var: ContextVar[Optional[str]] = ContextVar("ip_address", default=None)


@dataclass(frozen=True)
class RequestContext:
    correlation_id: Optional[str]
    tenant_id: Optional[str]
    user_id: Optional[str]
    ip_address: Optional[str]


def set_request_context(
    correlation_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Set context variables at the start of a request."""
    if correlation_id is not None:
        _correlation_id_var.set(correlation_id)
    if tenant_id is not None:
        _tenant_id_var.set(tenant_id)
    if user_id is not None:
        _user_id_var.set(user_id)
    if ip_address is not None:
        _ip_address_var.set(ip_address)


def get_request_context() -> RequestContext:
    """Return a snapshot of the current request context."""
    return RequestContext(
        correlation_id=_correlation_id_var.get(),
        tenant_id=_tenant_id_var.get(),
        user_id=_user_id_var.get(),
        ip_address=_ip_address_var.get(),
    )


def get_correlation_id() -> str:
    """Return current correlation_id or generate a new one."""
    cid = _correlation_id_var.get()
    if not cid:
        cid = str(uuid.uuid4())
        _correlation_id_var.set(cid)
    return cid


def get_tenant_id() -> Optional[str]:
    return _tenant_id_var.get()


def get_user_id() -> Optional[str]:
    return _user_id_var.get()


def clear_request_context() -> None:
    """Reset all context vars (called at end of request)."""
    _correlation_id_var.set(None)
    _tenant_id_var.set(None)
    _user_id_var.set(None)
    _ip_address_var.set(None)
