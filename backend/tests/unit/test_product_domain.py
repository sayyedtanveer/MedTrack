"""
Product Module Tests - Unit & Integration Tests
"""

import pytest
import uuid
from decimal import Decimal
from datetime import datetime

from backend.app.domain.product.entities.item_template import ItemTemplate
from backend.app.domain.product.entities.item_variant import ItemVariant
from backend.app.domain.product.entities.product_image import ProductImage
from backend.app.domain.product.value_objects.product_status import ProductStatus


class TestProductStatus:
    """Test ProductStatus state machine."""

    def test_valid_transition_draft_to_active(self):
        """Draft can transition to Active."""
        assert ProductStatus.can_transition(ProductStatus.DRAFT, ProductStatus.ACTIVE)

    def test_invalid_transition_inactive_to_draft(self):
        """Inactive cannot transition to Draft."""
        assert not ProductStatus.can_transition(ProductStatus.INACTIVE, ProductStatus.DRAFT)

    def test_archived_is_terminal(self):
        """Archived state is terminal."""
        assert not ProductStatus.can_transition(ProductStatus.ARCHIVED, ProductStatus.ACTIVE)
        assert not ProductStatus.can_transition(ProductStatus.ARCHIVED, ProductStatus.INACTIVE)

    def test_no_op_transition_allowed(self):
        """Same-state transitions always allowed."""
        for status in ProductStatus:
            assert ProductStatus.can_transition(status, status)


class TestItemTemplate:
    """Test ItemTemplate domain entity."""

    def test_create_template_with_status(self):
        """Create template with lifecycle status."""
        tenant_id = uuid.uuid4()
        template = ItemTemplate(
            tenant_id=tenant_id,
            code="TSHIRT",
            name="T-Shirt",
            status=ProductStatus.DRAFT,
        )
        assert template.status == ProductStatus.DRAFT
        assert template.is_active is False  # DRAFT is not "active"

    def test_transition_to_active(self):
        """Test status transition to ACTIVE."""
        tenant_id = uuid.uuid4()
        template = ItemTemplate(
            tenant_id=tenant_id,
            code="TSHIRT",
            name="T-Shirt",
            status=ProductStatus.DRAFT,
        )
        template.transition_to(ProductStatus.ACTIVE)
        assert template.status == ProductStatus.ACTIVE
        assert template.is_active is True

    def test_cannot_delete_active_product(self):
        """Cannot delete ACTIVE products."""
        tenant_id = uuid.uuid4()
        template = ItemTemplate(
            tenant_id=tenant_id,
            code="TSHIRT",
            name="T-Shirt",
            status=ProductStatus.ACTIVE,
        )
        assert not template.can_delete_product()

    def test_can_delete_draft_product(self):
        """Can delete DRAFT products."""
        tenant_id = uuid.uuid4()
        template = ItemTemplate(
            tenant_id=tenant_id,
            code="TSHIRT",
            name="T-Shirt",
            status=ProductStatus.DRAFT,
        )
        assert template.can_delete_product()

    def test_invalid_status_transition_raises_error(self):
        """Invalid transitions raise ValueError."""
        tenant_id = uuid.uuid4()
        template = ItemTemplate(tenant_id=tenant_id, code="TSHIRT", name="T-Shirt")
        
        # ACTIVE -> DRAFT is invalid
        with pytest.raises(ValueError):
            template.transition_to(ProductStatus.DRAFT)


class TestItemVariant:
    """Test ItemVariant domain entity."""

    def test_create_variant(self):
        """Create variant with attributes."""
        tenant_id = uuid.uuid4()
        template_id = uuid.uuid4()
        
        variant = ItemVariant(
            tenant_id=tenant_id,
            template_id=template_id,
            template_code="TSHIRT",
            template_name="T-Shirt",
            attribute_keys_ordered=["SIZE", "COLOR"],
            attribute_values={"SIZE": "LARGE", "COLOR": "RED"},
            standard_cost=Decimal("10.00"),
            selling_price=Decimal("20.00"),
        )
        
        assert variant.code == "TSHIRT-LARGE-RED"
        assert variant.variant_key == "SIZE=LARGE|COLOR=RED"

    def test_variant_activate_deactivate(self):
        """Test variant activation and deactivation."""
        tenant_id = uuid.uuid4()
        template_id = uuid.uuid4()
        
        variant = ItemVariant(
            tenant_id=tenant_id,
            template_id=template_id,
            template_code="TSHIRT",
            template_name="T-Shirt",
            attribute_keys_ordered=["SIZE"],
            attribute_values={"SIZE": "M"},
        )
        
        assert variant.is_active is True
        variant.deactivate()
        assert variant.is_active is False
        variant.activate()
        assert variant.is_active is True


class TestProductImage:
    """Test ProductImage domain entity."""

    def test_create_product_image(self):
        """Create product image."""
        tenant_id = uuid.uuid4()
        template_id = uuid.uuid4()
        
        image = ProductImage(
            tenant_id=tenant_id,
            template_id=template_id,
            file_name="photo.jpg",
            file_path="/uploads/photo.jpg",
            file_size=50000,
            file_mime_type="image/jpeg",
            is_primary=True,
        )
        
        assert image.is_primary is True
        assert image.is_supported_image() is True

    def test_set_image_as_primary(self):
        """Test marking image as primary."""
        tenant_id = uuid.uuid4()
        template_id = uuid.uuid4()
        
        image = ProductImage(
            tenant_id=tenant_id,
            template_id=template_id,
            file_name="photo.jpg",
            file_path="/uploads/photo.jpg",
            file_size=50000,
            file_mime_type="image/jpeg",
            is_primary=False,
        )
        
        assert image.is_primary is False
        image.set_as_primary()
        assert image.is_primary is True

    def test_unsupported_image_type(self):
        """Reject unsupported image types."""
        tenant_id = uuid.uuid4()
        template_id = uuid.uuid4()
        
        image = ProductImage(
            tenant_id=tenant_id,
            template_id=template_id,
            file_name="file.txt",
            file_path="/uploads/file.txt",
            file_size=1000,
            file_mime_type="text/plain",
        )
        
        assert image.is_image_type() is False
        assert image.is_supported_image() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
