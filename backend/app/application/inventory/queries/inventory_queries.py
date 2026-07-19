from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class ListMaterialsQuery:
    tenant_id: uuid.UUID
    query: Optional[str] = None
    category: Optional[str] = None
    material_type: Optional[str] = None
    is_active: Optional[bool] = None
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True)
class GetMaterialQuery:
    id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass(frozen=True)
class GetStockQuery:
    material_id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass(frozen=True)
class GetTransactionsQuery:
    tenant_id: uuid.UUID
    material_id: Optional[uuid.UUID] = None
    page: int = 1
    page_size: int = 50


# ── Phase 1.2 — Batch Queries ────────────────────────────────────────────

@dataclass(frozen=True)
class GetBatchesByMaterialQuery:
    tenant_id: uuid.UUID
    material_id: uuid.UUID


@dataclass(frozen=True)
class GetExpiringBatchesQuery:
    tenant_id: uuid.UUID
    days_ahead: int = 30


# ── Phase 1.3 — Serial Queries ────────────────────────────────────────────

@dataclass(frozen=True)
class GetSerialDetailsQuery:
    tenant_id: uuid.UUID
    serial_number: str


@dataclass(frozen=True)
class GetSerialsByMaterialQuery:
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    status: Optional[str] = None  # filter by SerialStatus value
