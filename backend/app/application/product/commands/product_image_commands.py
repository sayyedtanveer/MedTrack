from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import uuid


@dataclass(frozen=True)
class UploadProductImageCommand:
    """Command to upload and attach an image to a product."""
    tenant_id: uuid.UUID
    template_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    created_by: uuid.UUID = None
    # File data
    file_name: str = None
    file_path: str = None  # S3 URL or local file path
    file_size: int = None  # bytes
    file_mime_type: str = None
    # Metadata
    image_order: int = 0
    is_primary: bool = False


@dataclass(frozen=True)
class DeleteProductImageCommand:
    """Command to delete a product image."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    deleted_by: uuid.UUID = None


@dataclass(frozen=True)
class SetPrimaryImageCommand:
    """Command to set an image as the primary/thumbnail for a product."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    template_id: uuid.UUID
    updated_by: uuid.UUID = None


@dataclass(frozen=True)
class ReorderImageCommand:
    """Command to reorder product images."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    new_order: int
    updated_by: uuid.UUID = None
