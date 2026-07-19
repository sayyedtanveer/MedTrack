import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel

class GetBOMTreeQuery(BaseModel):
    tenant_id: uuid.UUID
    bom_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    max_depth: int = 20

class GetBOMCostQuery(BaseModel):
    tenant_id: uuid.UUID
    bom_id: uuid.UUID
    max_depth: int = 20

class ValidateBOMQuery(BaseModel):
    tenant_id: uuid.UUID
    bom_id: uuid.UUID
