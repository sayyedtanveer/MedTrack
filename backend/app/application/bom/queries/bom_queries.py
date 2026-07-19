import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class GetBOMQuery:
    bom_id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass
class ListBOMsQuery:
    tenant_id: uuid.UUID
    template_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None
    page: int = 1
    page_size: int = 20


@dataclass
class ListBOMLinesQuery:
    bom_id: uuid.UUID
    tenant_id: uuid.UUID
