"""Queries for Delivery operational flow."""
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel


class GetDispatchQueueQuery(BaseModel):
    tenant_id: uuid.UUID


class GetInTransitQueueQuery(BaseModel):
    tenant_id: uuid.UUID


class GetDeliveredQueueQuery(BaseModel):
    tenant_id: uuid.UUID
