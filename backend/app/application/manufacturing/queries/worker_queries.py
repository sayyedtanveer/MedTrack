"""Queries for Worker operational flow."""
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel


class GetWorkerQueueQuery(BaseModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
