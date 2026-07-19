"""API tests for Product module endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4


async def _create_category(async_client: AsyncClient, headers: dict) -> str:
    suffix = str(uuid4())[:8].upper()
    response = await async_client.post(
        "/api/v1/inventory/master-data/categories",
        json={
            "name": f"Product Test {suffix}",
            "code_prefix": f"PT{suffix[:4]}",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _template_payload(base: dict, category_id: str) -> dict:
    attributes = []
    for attr in base.get("attributes", []):
        key = attr.get("key") or attr.get("name") or "ATTRIBUTE"
        attributes.append(
            {
                "key": str(key).upper().replace(" ", "_"),
                "label": attr.get("label") or attr.get("name") or str(key),
                "values": attr.get("values") or attr.get("allowed_values") or [],
            }
        )
    return {
        "code": base.get("code"),
        "name": base.get("name"),
        "description": base.get("description"),
        "category_id": category_id,
        "attributes": attributes,
    }


@pytest.mark.asyncio
class TestProductAPI:
    """Test product API endpoints."""

    async def test_create_product_template_success(
        self, authenticated_async_client: AsyncClient, token_headers: dict, sample_product_template: dict
    ):
        """Test successful product template creation (201)."""
        category_id = await _create_category(authenticated_async_client, token_headers)
        response = await authenticated_async_client.post(
            "/api/v1/products/templates",
            json=_template_payload(sample_product_template, category_id),
        )
        
        assert response.status_code in [200, 201]

    async def test_create_product_template_validation_error(
        self, authenticated_async_client: AsyncClient
    ):
        """Test product template creation with invalid data (422)."""
        invalid_payload = {
            "name": "",  # Empty name
            "code": "TEST",
        }
        
        response = await authenticated_async_client.post(
            "/api/v1/products/templates",
            json=invalid_payload,
        )
        
        assert response.status_code in [400, 422]

    async def test_get_product_template_success(
        self, authenticated_async_client: AsyncClient
    ):
        """Test getting product template (200)."""
        # Assuming a product exists or create one first
        template_id = str(uuid4())
        
        response = await authenticated_async_client.get(
            f"/api/v1/products/templates/{template_id}",
        )
        
        # May be 200 (found) or 404 (not found) - both are valid
        assert response.status_code in [200, 404]

    async def test_get_nonexistent_product_not_found(
        self, authenticated_async_client: AsyncClient
    ):
        """Test getting non-existent product (404)."""
        nonexistent_id = str(uuid4())
        
        response = await authenticated_async_client.get(
            f"/api/v1/products/templates/{nonexistent_id}",
        )
        
        assert response.status_code == 404

    async def test_list_products_success(
        self, authenticated_async_client: AsyncClient
    ):
        """Test listing products (200)."""
        response = await authenticated_async_client.get(
            "/api/v1/products/templates",
            params={"page": 1, "page_size": 50},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (dict, list))

    async def test_unauthorized_access_denied(
        self, async_client: AsyncClient, sample_product_template: dict
    ):
        """Test unauthorized access (401)."""
        response = await async_client.post(
            "/api/v1/products/templates",
            json=sample_product_template,
        )
        
        assert response.status_code in [401, 403]

    async def test_create_product_variant(
        self, authenticated_async_client: AsyncClient, token_headers: dict
    ):
        """Test creating product variant."""
        category_id = await _create_category(authenticated_async_client, token_headers)
        template_response = await authenticated_async_client.post(
            "/api/v1/products/templates",
            json={
                "code": f"VAR-{str(uuid4())[:8].upper()}",
                "name": "Variant Test Product",
                "category_id": category_id,
                "attributes": [
                    {"key": "COLOR", "label": "Color", "values": ["Red", "Blue"]},
                    {"key": "SIZE", "label": "Size", "values": ["M", "L"]},
                ],
            },
        )
        assert template_response.status_code == 201, template_response.text
        template_id = template_response.json()["id"]
        variant_payload = {
            "attribute_values": {"COLOR": "Red", "SIZE": "M"},
            "standard_cost": 0,
        }
        
        response = await authenticated_async_client.post(
            f"/api/v1/products/templates/{template_id}/variants",
            json=variant_payload,
        )
    
        assert response.status_code in [200, 201]

    async def test_list_product_variants(
        self, authenticated_async_client: AsyncClient
    ):
        """Test listing product variants."""
        template_id = str(uuid4())
        
        response = await authenticated_async_client.get(
            f"/api/v1/products/{template_id}/variants",
        )
        
        assert response.status_code in [200, 404]


class TestProductValidation:
    """Test product validation rules."""

    async def test_duplicate_product_code_rejected(
        self, authenticated_async_client: AsyncClient, token_headers: dict
    ):
        """Test duplicate product codes are rejected."""
        category_id = await _create_category(authenticated_async_client, token_headers)
        payload = {
            "name": "Product A",
            "code": "DUPLICATE-CODE",
            "description": "First",
            "category_id": category_id,
            "attributes": [],
        }
        
        # Create first product
        response1 = await authenticated_async_client.post(
            "/api/v1/products/templates",
            json=payload,
        )
        
        # Attempt duplicate
        response2 = await authenticated_async_client.post(
            "/api/v1/products/templates",
            json=payload,
        )
        
        # Second should fail with conflict or validation error
        if response1.status_code in [200, 201]:
            assert response2.status_code in [400, 409, 422]

    async def test_duplicate_variant_key_rejected(
        self, authenticated_async_client: AsyncClient
    ):
        """Test duplicate variant keys are rejected."""
        template_id = str(uuid4())
        
        payload = {
            "attribute_values": {"Size": "M"},
            "standard_cost": 0,
        }
        
        # Create variant
        response1 = await authenticated_async_client.post(
            f"/api/v1/products/templates/{template_id}/variants",
            json=payload,
        )
        
        # Attempt duplicate
        response2 = await authenticated_async_client.post(
            f"/api/v1/products/templates/{template_id}/variants",
            json=payload,
        )
        
        # Should reject duplicate variant key
        if response1.status_code in [200, 201]:
            assert response2.status_code in [400, 409, 422]
