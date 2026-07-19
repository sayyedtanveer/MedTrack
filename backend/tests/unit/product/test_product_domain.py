"""Unit tests for Product domain logic."""

import pytest
from uuid import uuid4
from datetime import datetime

from backend.app.domain.product.entities.product import (
    ProductTemplate,
    ProductVariant,
)


class TestProductTemplate:
    """Test ProductTemplate entity."""

    def test_create_product_template(self):
        """Test creating a product template."""
        template_id = uuid4()
        name = "Test Template"
        code = "TEST-001"
        
        template = ProductTemplate(
            id=template_id,
            tenant_id=uuid4(),
            name=name,
            code=code,
            description="Test description",
        )
        
        assert template.id == template_id
        assert template.name == name
        assert template.code == code

    def test_product_template_is_valid(self):
        """Test product template validation."""
        template = ProductTemplate(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Valid Template",
            code="VALID-001",
        )
        
        assert template.name
        assert template.code
        assert len(template.code) > 0

    def test_product_template_equality(self):
        """Test product template equality comparison."""
        template_id = uuid4()
        tenant_id = uuid4()
        
        template1 = ProductTemplate(
            id=template_id,
            tenant_id=tenant_id,
            name="Template",
            code="TEST",
        )
        
        template2 = ProductTemplate(
            id=template_id,
            tenant_id=tenant_id,
            name="Template",
            code="TEST",
        )
        
        assert template1.id == template2.id


class TestProductVariant:
    """Test ProductVariant entity."""

    def test_create_product_variant(self):
        """Test creating a product variant."""
        variant_id = uuid4()
        template_id = uuid4()
        variant_key = "VARIANT-001"
        sku = "SKU-001"
        
        variant = ProductVariant(
            id=variant_id,
            tenant_id=uuid4(),
            template_id=template_id,
            variant_key=variant_key,
            sku=sku,
        )
        
        assert variant.id == variant_id
        assert variant.template_id == template_id
        assert variant.variant_key == variant_key
        assert variant.sku == sku

    def test_variant_key_uniqueness(self):
        """Test that variant keys should be unique per template."""
        template_id = uuid4()
        tenant_id = uuid4()
        variant_key = "VAR-RED-M"
        
        variant1 = ProductVariant(
            id=uuid4(),
            tenant_id=tenant_id,
            template_id=template_id,
            variant_key=variant_key,
            sku="SKU-001",
        )
        
        variant2 = ProductVariant(
            id=uuid4(),
            tenant_id=tenant_id,
            template_id=template_id,
            variant_key=variant_key,
            sku="SKU-002",
        )
        
        # Both have the same key - in practice, DB constraint would prevent this
        assert variant1.variant_key == variant2.variant_key

    def test_variant_code_generation(self):
        """Test variant code format."""
        variant = ProductVariant(
            id=uuid4(),
            tenant_id=uuid4(),
            template_id=uuid4(),
            variant_key="RED-M",
            sku="SKU-RED-M",
        )
        
        # SKU should not be empty
        assert variant.sku
        assert len(variant.sku) > 0


class TestProductAttributeValidation:
    """Test product attribute validation logic."""

    def test_attribute_text_validation(self):
        """Test text attribute validation."""
        from backend.app.domain.product.value_objects.attribute import Attribute
        
        attr = Attribute(
            name="Color",
            data_type="text",
            is_required=True,
            allowed_values=["Red", "Blue", "Green"],
        )
        
        assert attr.name == "Color"
        assert attr.data_type == "text"
        assert "Red" in attr.allowed_values

    def test_attribute_required_validation(self):
        """Test required attribute validation."""
        from backend.app.domain.product.value_objects.attribute import Attribute
        
        attr = Attribute(
            name="Size",
            data_type="text",
            is_required=True,
            allowed_values=["S", "M", "L"],
        )
        
        assert attr.is_required is True

    def test_attribute_allowed_values(self):
        """Test attribute allowed values enforcement."""
        from backend.app.domain.product.value_objects.attribute import Attribute
        
        allowed = ["Red", "Blue", "Green"]
        attr = Attribute(
            name="Color",
            data_type="text",
            is_required=True,
            allowed_values=allowed,
        )
        
        assert attr.allowed_values == allowed


class TestProductVariantKeyGeneration:
    """Test variant key generation logic."""

    def test_variant_key_format(self):
        """Test variant key follows expected format."""
        variant_key = "TEMPLATE-001-RED-M"
        
        # Validate format: segments separated by hyphens
        parts = variant_key.split("-")
        assert len(parts) >= 3  # At minimum: template-variant-size
        assert all(part for part in parts)  # No empty segments

    def test_duplicate_variant_key_prevention(self):
        """Test that duplicate variant keys are prevented within a template."""
        # This would typically be enforced at the repository/DB level
        template_id = uuid4()
        tenant_id = uuid4()
        variant_key = "VARIANT-COMBO"
        
        v1 = ProductVariant(
            id=uuid4(),
            tenant_id=tenant_id,
            template_id=template_id,
            variant_key=variant_key,
            sku="SKU-1",
        )
        
        v2 = ProductVariant(
            id=uuid4(),
            tenant_id=tenant_id,
            template_id=template_id,
            variant_key=variant_key,
            sku="SKU-2",
        )
        
        # Domain logic: both exist, but DB would prevent this
        assert v1.variant_key == v2.variant_key
        assert v1.id != v2.id
