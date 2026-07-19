from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class ProductImage(BaseEntity):
    """
    Represents an image/media file associated with a product template or variant.

    Domain Rules:
    - An image can be linked to a template (applies to all variants)
    - Or linked to a variant (specific to that variant)
    - file_path is the persisted location (S3 URL or local path)
    - file_size is in bytes
    - image_order determines display order (lower = earlier)
    - is_primary indicates the main/thumbnail image
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
        variant_id: Optional[uuid.UUID] = None,
        file_name: str,
        file_path: str,
        file_size: int,  # bytes
        file_mime_type: str,
        image_order: int = 0,
        is_primary: bool = False,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )

        if not file_name or not file_name.strip():
            raise ValueError("ProductImage file_name is required.")
        if not file_path or not file_path.strip():
            raise ValueError("ProductImage file_path is required.")
        if file_size <= 0:
            raise ValueError("ProductImage file_size must be positive.")
        if not file_mime_type or not file_mime_type.strip():
            raise ValueError("ProductImage file_mime_type is required.")

        self._template_id = template_id
        self._variant_id = variant_id
        self._file_name = file_name.strip()
        self._file_path = file_path.strip()
        self._file_size = file_size
        self._file_mime_type = file_mime_type.lower()
        self._image_order = image_order
        self._is_primary = is_primary

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def template_id(self) -> uuid.UUID:
        return self._template_id

    @property
    def variant_id(self) -> Optional[uuid.UUID]:
        return self._variant_id

    @property
    def file_name(self) -> str:
        return self._file_name

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def file_size(self) -> int:
        return self._file_size

    @property
    def file_mime_type(self) -> str:
        return self._file_mime_type

    @property
    def image_order(self) -> int:
        return self._image_order

    @property
    def is_primary(self) -> bool:
        return self._is_primary

    # ── Behaviour ─────────────────────────────────────────────────────────────

    def set_as_primary(self) -> None:
        """Mark this image as the primary/thumbnail image."""
        self._is_primary = True
        self._touch()

    def unset_as_primary(self) -> None:
        """Unmark this image as primary."""
        self._is_primary = False
        self._touch()

    def reorder(self, new_order: int) -> None:
        """Change the display order of this image."""
        if new_order < 0:
            raise ValueError("image_order cannot be negative.")
        self._image_order = new_order
        self._touch()

    def is_image_type(self) -> bool:
        """Check if this file is an image (mime type starts with 'image/')."""
        return self._file_mime_type.startswith("image/")

    def is_supported_image(self) -> bool:
        """Check if this is a supported image format."""
        supported = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}
        return self._file_mime_type in supported
