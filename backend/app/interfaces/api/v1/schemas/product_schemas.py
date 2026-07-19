from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


# ── Item Template ─────────────────────────────────────────────────────────────

class AttributeDefinition(BaseModel):
    key: str = Field(..., description="Attribute key, e.g. 'SIZE'")
    label: str = Field(..., description="Human-readable label, e.g. 'Size'")
    values: List[str] = Field(default_factory=list, description="Allowed values, e.g. ['S', 'M', 'L']")


class CreateItemTemplateRequest(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    item_code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category_id: uuid.UUID
    base_unit_id: Optional[uuid.UUID] = None
    attributes: List[AttributeDefinition] = Field(default_factory=list)


class UpdateItemTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    base_unit_id: Optional[uuid.UUID] = None
    attributes: Optional[List[AttributeDefinition]] = None
    is_active: Optional[bool] = None


class ChangeProductStatusRequest(BaseModel):
    new_status: str = Field(..., description="Target status: DRAFT, ACTIVE, INACTIVE, or ARCHIVED")

    class Config:
        examples = [{
            "new_status": "ACTIVE"
        }]


class ItemTemplateResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    item_code: str
    item_type: str
    name: str
    description: Optional[str]
    category_id: Optional[uuid.UUID]
    base_unit_id: Optional[uuid.UUID]
    attributes: List[Dict[str, Any]]
    status: str = Field(..., description="Product lifecycle status: DRAFT, ACTIVE, INACTIVE, ARCHIVED")
    code_locked: bool
    is_active: bool

    model_config = {"from_attributes": True}


class ItemTemplateListResponse(BaseModel):
    items: List[ItemTemplateResponse]
    total: int
    page: int
    page_size: int


# ── Item Variant ──────────────────────────────────────────────────────────────

class CreateItemVariantRequest(BaseModel):
    attribute_values: Dict[str, Any] = Field(
        ..., description="e.g. {\"SIZE\": \"SMALL\", \"COLOR\": \"RED\"}"
    )
    base_unit_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional finished-goods inventory material linked to this variant.",
    )
    standard_cost: Decimal = Decimal("0")
    selling_price: Optional[Decimal] = None


class UpdateItemVariantRequest(BaseModel):
    material_id: Optional[uuid.UUID] = None
    standard_cost: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ItemVariantResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    template_id: uuid.UUID
    code: str
    name: str
    variant_key: str
    attribute_values: Dict[str, Any]
    base_unit_id: Optional[uuid.UUID]
    material_id: Optional[uuid.UUID]
    standard_cost: Decimal
    selling_price: Optional[Decimal]
    is_active: bool

    model_config = {"from_attributes": True}


class ItemVariantListResponse(BaseModel):
    items: List[ItemVariantResponse]
    total: int
    page: int
    page_size: int


class ItemVariantSearchItem(ItemVariantResponse):
    """Variant row for global search — includes unit label and resolvable FG material id."""

    base_unit_code: Optional[str] = None
    stock_material_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Material id to use for receive/stock when linked (same id as variant or finished material with matching code).",
    )


class ItemVariantSearchListResponse(BaseModel):
    items: List[ItemVariantSearchItem]
    total: int
    page: int
    page_size: int


# ── Product Images ────────────────────────────────────────────────────────────

class ProductImageResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    template_id: uuid.UUID
    variant_id: Optional[uuid.UUID]
    file_name: str
    file_path: str
    file_size: int
    file_mime_type: str
    image_order: int
    is_primary: bool

    model_config = {"from_attributes": True}


class ProductImageListResponse(BaseModel):
    items: List[ProductImageResponse]
    primary_image: Optional[ProductImageResponse] = None


class SetPrimaryImageRequest(BaseModel):
    image_id: uuid.UUID = Field(..., description="ID of the image to set as primary")


class ReorderImageRequest(BaseModel):
    new_order: int = Field(..., ge=0, description="New display order (0 = first)")


class UploadImageResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    file_path: str
    file_size: int
    is_primary: bool
    message: str = "Image uploaded successfully"


# ── Bulk Operations ───────────────────────────────────────────────────────────

class ImportError(BaseModel):
    row_number: int
    field: str
    message: str


class BulkImportRequest(BaseModel):
    csv_data: str = Field(..., description="CSV content with variant data")


class BulkImportResponse(BaseModel):
    success_count: int
    error_count: int
    errors: List[ImportError] = []
    variant_ids: List[uuid.UUID] = []
    message: str


class BulkUpdateVariantRequest(BaseModel):
    variant_id: uuid.UUID
    standard_cost: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class BulkOperationResponse(BaseModel):
    success_count: int
    message: str


class VariantIdsRequest(BaseModel):
    variant_ids: List[uuid.UUID] = Field(default_factory=list)


class VariantTemplateCsvResponse(BaseModel):
    csv_content: str
    file_name: str = "variant_import_template.csv"


class ExportVariantsRequest(BaseModel):
    variant_ids: List[uuid.UUID] = Field(default_factory=list, description="Leave empty to export all")


class ExportVariantsResponse(BaseModel):
    csv_content: str
    file_name: str
    record_count: int
