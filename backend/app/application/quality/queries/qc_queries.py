"""Queries for QC operational flow."""
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel


class GetInspectionQueueQuery(BaseModel):
    tenant_id: uuid.UUID


class GetRejectedQueueQuery(BaseModel):
    tenant_id: uuid.UUID


class GetReworkQueueQuery(BaseModel):
    tenant_id: uuid.UUID
