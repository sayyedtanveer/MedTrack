from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import uuid


@dataclass(frozen=True)
class GetItemTemplateQuery:
    id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass(frozen=True)
class ListItemTemplatesQuery:
    tenant_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    query: Optional[str] = None          # text search on name/code
    is_active: Optional[bool] = None
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True)
class GetItemVariantQuery:
    id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass(frozen=True)
class ListItemVariantsQuery:
    template_id: uuid.UUID
    tenant_id: uuid.UUID
    query: Optional[str] = None
    is_active: Optional[bool] = None
    page: int = 1
    page_size: int = 50


@dataclass(frozen=True)
class ListAllVariantsQuery:
    """Tenant-wide variant search (e.g. FG picker for subcontract receive)."""

    tenant_id: uuid.UUID
    query: Optional[str] = None
    is_active: Optional[bool] = True
    page: int = 1
    page_size: int = 50
