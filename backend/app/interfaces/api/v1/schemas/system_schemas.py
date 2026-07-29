from pydantic import BaseModel, Field
import uuid
from typing import Optional, List
from datetime import datetime

class TenantActionRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for the action (required for reject/suspend)")

class SystemTenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    status: str
    is_active: bool
    is_system_tenant: bool
    created_at: datetime
    # We can add more fields like Owner, Users count later when building the rich query

class SystemTenantListResponse(BaseModel):
    tenants: List[SystemTenantResponse]
    total: int
