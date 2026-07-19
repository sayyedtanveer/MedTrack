from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

# ── Category Schemas ──────────────────────────────────────────────────────
class CreateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code_prefix: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=2000)
    is_active: bool = True


class UpdateCategoryRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code_prefix: Optional[str] = Field(None, min_length=2, max_length=6, pattern=r"^[A-Z0-9]{2,6}$")
    description: Optional[str] = Field(None, max_length=2000)
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code_prefix: str
    description: Optional[str]
    is_active: bool
    material_count: int = 0

    model_config = {"from_attributes": True}


# ── Location Schemas ──────────────────────────────────────────────────────
class CreateLocationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(
        "warehouse",
        pattern="^(warehouse|rack|bin|quarantine|subcontractor|production|shipping)$",
    )
    code: Optional[str] = Field(None, max_length=50)
    parent_id: Optional[uuid.UUID] = None
    is_active: bool = True


class UpdateLocationRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    parent_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class LocationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: Optional[str] = None
    location_type: str
    parent_location_id: Optional[uuid.UUID] = None
    is_active: bool

    model_config = {"from_attributes": True}


# ── Unit of Measure Schemas ───────────────────────────────────────────────
class CreateUnitRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    precision: int = Field(2, ge=0, le=6)
    is_active: bool = True


class UpdateUnitRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    precision: Optional[int] = Field(None, ge=0, le=6)
    is_active: Optional[bool] = None


class UnitResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    precision: int
    is_active: bool
    usage_count: int = 0

    model_config = {"from_attributes": True}
