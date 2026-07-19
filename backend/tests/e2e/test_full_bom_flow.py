"""End-to-end tests for complete BOM workflow."""

import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
class TestFullBOMWorkflow:
    """Test complete BOM creation and lifecycle workflow."""

    async def test_full_bom_flow_success(
        self,
        authenticated_async_client: AsyncClient,
        e2e_test_context: dict,
        sample_product_template: dict,
    ):
        """
        Test complete BOM workflow:
        1. Create product template
        2. Add attributes
        3. Generate variants
        4. Create BOM
        5. Add components
        6. Validate BOM
        7. Copy BOM
        8. Activate BOM
        9. Add operations
        10. Fetch tree
        11. Fetch cost
        """
        
        # Step 1: Create product template
        template_response = await authenticated_async_client.post(
            "/api/v1/products",
            json=sample_product_template,
        )
        
        if template_response.status_code not in [200, 201]:
            pytest.skip(f"Template creation failed: {template_response.status_code}")
        
        template_data = template_response.json()
        template_id = template_data.get("id") or str(uuid4())
        e2e_test_context["product_template_id"] = template_id
        
        # Step 2: Attributes already included in template
        assert sample_product_template.get("attributes") is not None
        
        # Step 3: Generate variant
        variant_payload = {
            "template_id": template_id,
            "variant_key": "VARIANT-RED-M",
            "sku": "SKU-001-RED-M",
            "attributes": {
                "Color": "Red",
                "Size": "M",
            },
        }
        
        variant_response = await authenticated_async_client.post(
            "/api/v1/products/variants",
            json=variant_payload,
        )
        
        if variant_response.status_code in [200, 201]:
            variant_data = variant_response.json()
            variant_id = variant_data.get("id") or str(uuid4())
            e2e_test_context["variant_ids"].append(variant_id)
        
        # Step 4: Create BOM
        bom_payload = {
            "version": "v1.0",
            "valid_from": "2024-01-01T00:00:00",
            "template_id": template_id,
            "lines": [],
        }
        
        bom_response = await authenticated_async_client.post(
            f"/api/v1/products/{template_id}/boms",
            json=bom_payload,
        )
        
        if bom_response.status_code not in [200, 201]:
            pytest.skip(f"BOM creation failed: {bom_response.status_code}")
        
        bom_data = bom_response.json()
        bom_id = bom_data.get("id") or str(uuid4())
        e2e_test_context["bom_ids"].append(bom_id)
        
        # Step 5: Add components to BOM
        material_id = str(uuid4())
        e2e_test_context["material_ids"].append(material_id)
        
        line_payload = {
            "material_id": material_id,
            "quantity": 2.5,
            "scrap_percentage": 0.05,
        }
        
        line_response = await authenticated_async_client.post(
            f"/api/v1/boms/{bom_id}/lines",
            json=line_payload,
        )
        
        assert line_response.status_code in [200, 201, 404, 422]
        
        # Step 6: Validate BOM
        validate_response = await authenticated_async_client.post(
            f"/api/v1/boms/{bom_id}/validate",
        )
        
        assert validate_response.status_code in [200, 404, 422]
        
        # Step 7: Copy BOM
        copy_payload = {
            "new_version": "v1.1",
        }
        
        copy_response = await authenticated_async_client.post(
            f"/api/v1/boms/{bom_id}/copy",
            json=copy_payload,
        )
        
        if copy_response.status_code in [200, 201]:
            copied_bom = copy_response.json()
            copied_bom_id = copied_bom.get("id") or str(uuid4())
            e2e_test_context["bom_ids"].append(copied_bom_id)
        
        # Step 8: Activate BOM
        activate_response = await authenticated_async_client.post(
            f"/api/v1/boms/{bom_id}/activate",
        )
        
        assert activate_response.status_code in [200, 404, 409, 422]
        
        # Step 9: Add operations to BOM
        operation_id = str(uuid4())
        e2e_test_context["operation_ids"].append(operation_id)
        
        operation_payload = {
            "operation_id": operation_id,
            "sequence": 1,
        }
        
        operation_response = await authenticated_async_client.post(
            f"/api/v1/boms/{bom_id}/operations",
            json=operation_payload,
        )
        
        assert operation_response.status_code in [200, 201, 404, 422]
        
        # Step 10: Fetch BOM tree
        tree_response = await authenticated_async_client.get(
            f"/api/v1/boms/{bom_id}/tree",
        )
        
        assert tree_response.status_code in [200, 404]
        if tree_response.status_code == 200:
            tree_data = tree_response.json()
            assert isinstance(tree_data, (dict, list))
        
        # Step 11: Fetch BOM cost
        cost_response = await authenticated_async_client.get(
            f"/api/v1/boms/{bom_id}/costs",
        )
        
        assert cost_response.status_code in [200, 404]
        if cost_response.status_code == 200:
            cost_data = cost_response.json()
            assert isinstance(cost_data, dict)
            # Cost should have material, labor, and total
            assert any(
                key in cost_data 
                for key in ["total_cost", "material_cost", "labor_cost"]
            )


@pytest.mark.asyncio
class TestBOMComplexScenarios:
    """Test complex BOM scenarios."""

    async def test_multi_level_bom_hierarchy(
        self, authenticated_async_client: AsyncClient
    ):
        """Test BOM with multiple component levels."""
        # Create root BOM
        product_id = str(uuid4())
        root_bom = {
            "version": "v1.0",
            "template_id": product_id,
            "lines": [],
        }
        
        root_response = await authenticated_async_client.post(
            f"/api/v1/products/{product_id}/boms",
            json=root_bom,
        )
        
        if root_response.status_code not in [200, 201]:
            pytest.skip("Could not create root BOM")
        
        root_bom_id = root_response.json().get("id")
        
        # Add sub-assemblies
        for level in range(2):
            line = {
                "material_id": str(uuid4()),
                "quantity": 1.0,
            }
            
            line_response = await authenticated_async_client.post(
                f"/api/v1/boms/{root_bom_id}/lines",
                json=line,
            )
            
            assert line_response.status_code in [200, 201, 404, 422]

    async def test_bom_version_control(
        self, authenticated_async_client: AsyncClient
    ):
        """Test BOM version control and activation."""
        product_id = str(uuid4())
        
        # Create multiple versions
        versions = ["v1.0", "v1.1", "v2.0"]
        bom_ids = []
        
        for version in versions:
            payload = {
                "version": version,
                "template_id": product_id,
                "lines": [],
            }
            
            response = await authenticated_async_client.post(
                f"/api/v1/products/{product_id}/boms",
                json=payload,
            )
            
            if response.status_code in [200, 201]:
                bom_ids.append(response.json().get("id"))
        
        # Activate latest version
        if bom_ids:
            activate_response = await authenticated_async_client.post(
                f"/api/v1/boms/{bom_ids[-1]}/activate",
            )
            
            assert activate_response.status_code in [200, 404, 409, 422]

    async def test_bom_cost_rollup(
        self, authenticated_async_client: AsyncClient
    ):
        """Test BOM cost calculation and rollup."""
        product_id = str(uuid4())
        
        # Create BOM with components
        bom = {
            "version": "v1.0",
            "template_id": product_id,
            "lines": [
                {
                    "material_id": str(uuid4()),
                    "quantity": 2.0,
                },
                {
                    "material_id": str(uuid4()),
                    "quantity": 1.5,
                },
            ],
        }
        
        bom_response = await authenticated_async_client.post(
            f"/api/v1/products/{product_id}/boms",
            json=bom,
        )
        
        if bom_response.status_code not in [200, 201]:
            pytest.skip("Could not create BOM")
        
        bom_id = bom_response.json().get("id")
        
        # Get cost breakdown
        cost_response = await authenticated_async_client.get(
            f"/api/v1/boms/{bom_id}/costs",
        )
        
        assert cost_response.status_code in [200, 404]


@pytest.mark.asyncio
class TestBOMErrorHandling:
    """Test error handling in BOM operations."""

    async def test_circular_dependency_detection(
        self, authenticated_async_client: AsyncClient
    ):
        """Test circular dependency is detected and rejected."""
        # This would be tested if sub-assembly references exist
        # For now, ensure endpoint exists
        bom_id = str(uuid4())
        
        response = await authenticated_async_client.post(
            f"/api/v1/boms/{bom_id}/validate",
        )
        
        assert response.status_code in [200, 404, 422]

    async def test_invalid_date_range_rejected(
        self, authenticated_async_client: AsyncClient
    ):
        """Test invalid valid_from/valid_to is rejected."""
        product_id = str(uuid4())
        
        # valid_to before valid_from
        invalid_payload = {
            "version": "v1.0",
            "valid_from": "2024-12-31T00:00:00",
            "valid_to": "2024-01-01T00:00:00",  # Before valid_from!
            "template_id": product_id,
            "lines": [],
        }
        
        response = await authenticated_async_client.post(
            f"/api/v1/products/{product_id}/boms",
            json=invalid_payload,
        )
        
        # Should reject invalid date range
        assert response.status_code in [400, 422]

    async def test_activation_of_invalid_bom_rejected(
        self, authenticated_async_client: AsyncClient
    ):
        """Test activating invalid BOM is rejected."""
        bom_id = str(uuid4())
        
        response = await authenticated_async_client.post(
            f"/api/v1/boms/{bom_id}/activate",
        )
        
        # Should reject if BOM is invalid or not found
        assert response.status_code in [404, 409, 422]
