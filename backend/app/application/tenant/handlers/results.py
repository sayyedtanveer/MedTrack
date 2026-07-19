from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RegisterTenantResult:
    tenant_id: str
    tenant_name: str
    slug: str
    user_id: str
    email: str
    role: str
    access_token: str


@dataclass
class LoginResult:
    access_token: str
    token_type: str
    user_id: str
    tenant_id: str
    email: str
    role: str
    full_name: str
