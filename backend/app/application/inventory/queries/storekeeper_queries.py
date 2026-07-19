"""Queries for Storekeeper operational flow."""
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel


class GetIssueQueueQuery(BaseModel):
    tenant_id: uuid.UUID


class GetShortageQueueQuery(BaseModel):
    tenant_id: uuid.UUID


class GetPartiallyIssuedWOQuery(BaseModel):
    tenant_id: uuid.UUID
