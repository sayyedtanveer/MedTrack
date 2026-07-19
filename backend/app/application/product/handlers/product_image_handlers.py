from __future__ import annotations

"""
Product image command handlers.
"""

from dataclasses import dataclass
from typing import Optional
import uuid

from backend.app.application.product.commands.product_image_commands import (
    UploadProductImageCommand,
    DeleteProductImageCommand,
    SetPrimaryImageCommand,
    ReorderImageCommand,
)
from backend.app.domain.product.entities.product_image import ProductImage
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


# ── DTOs ──────────────────────────────────────────────────────────────────────

@dataclass
class ProductImageResult:
    id: str
    tenant_id: str
    template_id: str
    variant_id: Optional[str]
    file_name: str
    file_path: str
    file_size: int
    file_mime_type: str
    image_order: int
    is_primary: bool
    is_deleted: bool


# ── Handlers ──────────────────────────────────────────────────────────────────

class UploadProductImageHandler:
    """Handler for uploading a product image."""

    def __init__(self, image_repo, uow: SQLAlchemyUnitOfWork) -> None:
        self._repo = image_repo
        self._uow = uow

    async def handle(self, cmd: UploadProductImageCommand) -> ProductImageResult:
        # Validate file
        if not cmd.file_name or not cmd.file_path:
            raise ValueError("file_name and file_path are required.")
        if cmd.file_size <= 0:
            raise ValueError("file_size must be positive.")

        # Create domain entity
        image = ProductImage(
            tenant_id=cmd.tenant_id,
            template_id=cmd.template_id,
            variant_id=cmd.variant_id,
            file_name=cmd.file_name,
            file_path=cmd.file_path,
            file_size=cmd.file_size,
            file_mime_type=cmd.file_mime_type,
            image_order=cmd.image_order,
            is_primary=cmd.is_primary,
        )

        # If marking as primary, unmark any existing primary image for the template
        if cmd.is_primary:
            existing_primary = await self._repo.get_primary_image(cmd.template_id, cmd.tenant_id)
            if existing_primary:
                existing_primary.unset_as_primary()
                await self._repo.save(existing_primary)

        await self._repo.save(image)
        await self._uow.commit()
        return _to_image_result(image)


class DeleteProductImageHandler:
    """Handler for deleting a product image."""

    def __init__(self, image_repo, uow: SQLAlchemyUnitOfWork) -> None:
        self._repo = image_repo
        self._uow = uow

    async def handle(self, cmd: DeleteProductImageCommand) -> bool:
        success = await self._repo.delete_by_id(cmd.id, cmd.tenant_id)
        if success:
            await self._uow.commit()
        return success


class SetPrimaryImageHandler:
    """Handler for setting an image as primary."""

    def __init__(self, image_repo, uow: SQLAlchemyUnitOfWork) -> None:
        self._repo = image_repo
        self._uow = uow

    async def handle(self, cmd: SetPrimaryImageCommand) -> ProductImageResult:
        image = await self._repo.get_by_id(cmd.id, cmd.tenant_id)
        if not image:
            raise ValueError(f"Product image '{cmd.id}' not found.")

        # Unmark any existing primary image for this template
        existing_primary = await self._repo.get_primary_image(cmd.template_id, cmd.tenant_id)
        if existing_primary and existing_primary.id != image.id:
            existing_primary.unset_as_primary()
            await self._repo.save(existing_primary)

        # Set this image as primary
        image.set_as_primary()
        await self._repo.save(image)
        await self._uow.commit()
        return _to_image_result(image)


class ReorderImageHandler:
    """Handler for reordering images."""

    def __init__(self, image_repo, uow: SQLAlchemyUnitOfWork) -> None:
        self._repo = image_repo
        self._uow = uow

    async def handle(self, cmd: ReorderImageCommand) -> ProductImageResult:
        image = await self._repo.get_by_id(cmd.id, cmd.tenant_id)
        if not image:
            raise ValueError(f"Product image '{cmd.id}' not found.")

        image.reorder(cmd.new_order)
        await self._repo.save(image)
        await self._uow.commit()
        return _to_image_result(image)


# ── Helper converters ─────────────────────────────────────────────────────────

def _to_image_result(img: ProductImage) -> ProductImageResult:
    return ProductImageResult(
        id=str(img.id),
        tenant_id=str(img.tenant_id),
        template_id=str(img.template_id),
        variant_id=str(img.variant_id) if img.variant_id else None,
        file_name=img.file_name,
        file_path=img.file_path,
        file_size=img.file_size,
        file_mime_type=img.file_mime_type,
        image_order=img.image_order,
        is_primary=img.is_primary,
        is_deleted=img.is_deleted,
    )
