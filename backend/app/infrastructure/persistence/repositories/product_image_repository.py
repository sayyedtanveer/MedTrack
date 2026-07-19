from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.product.entities.product_image import ProductImage
from backend.app.infrastructure.persistence.models.product_image_model import ProductImageModel


class ProductImageRepository:
    """Repository for ProductImage entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, image: ProductImage) -> None:
        """Save or update an image."""
        model = await self._session.get(ProductImageModel, image.id)
        if model:
            model.file_name = image.file_name
            model.file_path = image.file_path
            model.file_size = image.file_size
            model.file_mime_type = image.file_mime_type
            model.image_order = image.image_order
            model.is_primary = image.is_primary
            model.is_deleted = image.is_deleted
            model.deleted_at = image.deleted_at
            model.updated_at = image.updated_at
        else:
            model = ProductImageModel(
                id=image.id,
                tenant_id=image.tenant_id,
                template_id=image.template_id,
                variant_id=image.variant_id,
                file_name=image.file_name,
                file_path=image.file_path,
                file_size=image.file_size,
                file_mime_type=image.file_mime_type,
                image_order=image.image_order,
                is_primary=image.is_primary,
                is_deleted=image.is_deleted,
                deleted_at=image.deleted_at,
                created_at=image.created_at,
                updated_at=image.updated_at,
            )
            self._session.add(model)
        await self._session.flush()

    async def get_by_id(self, id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[ProductImage]:
        """Get a single image by ID."""
        stmt = select(ProductImageModel).where(
            and_(
                ProductImageModel.id == id,
                ProductImageModel.tenant_id == tenant_id,
                ProductImageModel.is_deleted.is_(False),
            )
        )
        model = await self._session.scalar(stmt)
        return self._to_domain(model) if model else None

    async def get_template_images(
        self, template_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> List[ProductImage]:
        """Get all images for a template (excluding deleted)."""
        stmt = select(ProductImageModel).where(
            and_(
                ProductImageModel.template_id == template_id,
                ProductImageModel.tenant_id == tenant_id,
                ProductImageModel.variant_id.is_(None),  # Only template-level images
                ProductImageModel.is_deleted.is_(False),
            )
        ).order_by(ProductImageModel.image_order)
        models = await self._session.scalars(stmt)
        return [self._to_domain(m) for m in models.all()]

    async def get_variant_images(
        self, variant_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> List[ProductImage]:
        """Get all images for a variant (excluding deleted)."""
        stmt = select(ProductImageModel).where(
            and_(
                ProductImageModel.variant_id == variant_id,
                ProductImageModel.tenant_id == tenant_id,
                ProductImageModel.is_deleted.is_(False),
            )
        ).order_by(ProductImageModel.image_order)
        models = await self._session.scalars(stmt)
        return [self._to_domain(m) for m in models.all()]

    async def get_primary_image(
        self, template_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[ProductImage]:
        """Get the primary/thumbnail image for a template."""
        stmt = select(ProductImageModel).where(
            and_(
                ProductImageModel.template_id == template_id,
                ProductImageModel.tenant_id == tenant_id,
                ProductImageModel.is_primary.is_(True),
                ProductImageModel.is_deleted.is_(False),
            )
        ).limit(1)
        model = await self._session.scalar(stmt)
        return self._to_domain(model) if model else None

    async def delete_by_id(self, id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """Soft delete an image by ID."""
        stmt = select(ProductImageModel).where(
            and_(
                ProductImageModel.id == id,
                ProductImageModel.tenant_id == tenant_id,
                ProductImageModel.is_deleted.is_(False),
            )
        )
        model = await self._session.scalar(stmt)
        if not model:
            return False
        model.is_deleted = True
        model.deleted_at = model.deleted_at or model.updated_at
        await self._session.flush()
        return True

    async def delete_template_images(self, template_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
        """Soft delete all images for a template."""
        stmt = select(ProductImageModel).where(
            and_(
                ProductImageModel.template_id == template_id,
                ProductImageModel.tenant_id == tenant_id,
                ProductImageModel.is_deleted.is_(False),
            )
        )
        models = await self._session.scalars(stmt)
        count = 0
        for model in models.all():
            model.is_deleted = True
            model.deleted_at = model.deleted_at or model.updated_at
            count += 1
        await self._session.flush()
        return count

    async def delete_variant_images(self, variant_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
        """Soft delete all images for a variant."""
        stmt = select(ProductImageModel).where(
            and_(
                ProductImageModel.variant_id == variant_id,
                ProductImageModel.tenant_id == tenant_id,
                ProductImageModel.is_deleted.is_(False),
            )
        )
        models = await self._session.scalars(stmt)
        count = 0
        for model in models.all():
            model.is_deleted = True
            model.deleted_at = model.deleted_at or model.updated_at
            count += 1
        await self._session.flush()
        return count

    @staticmethod
    def _to_domain(model: ProductImageModel) -> ProductImage:
        """Convert ORM model to domain entity."""
        return ProductImage(
            id=model.id,
            tenant_id=model.tenant_id,
            template_id=model.template_id,
            variant_id=model.variant_id,
            file_name=model.file_name,
            file_path=model.file_path,
            file_size=model.file_size,
            file_mime_type=model.file_mime_type,
            image_order=model.image_order,
            is_primary=model.is_primary,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
