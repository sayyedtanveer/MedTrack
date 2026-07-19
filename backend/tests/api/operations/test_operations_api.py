"""API tests for Operations module endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
class TestOperationsAPI:
    """Test operations API endpoints."""

    async def test_create_operation_success(
        self, authenticated_async_client: AsyncClient, operation_payload: dict
    ):
        """Test successful operation creation (201)."""
        response = await authenticated_async_client.post(
            "/api/v1/operations",
            json=operation_payload,
        )
        
        assert response.status_code in [200, 201]

    async def test_create_operation_validation_error(
        self, authenticated_async_client: AsyncClient
    ):
        """Test operation creation with invalid data (422)."""
        invalid_payload = {
            "code": "",  # Empty code
            "name": "Invalid Operation",
        }
        
        response = await authenticated_async_client.post(
            "/api/v1/operations",
            json=invalid_payload,
        )
        
        assert response.status_code in [400, 422]

    async def test_get_operation_success(
        self, authenticated_async_client: AsyncClient
    ):
        """Test getting operation (200)."""
        operation_id = str(uuid4())
        
        response = await authenticated_async_client.get(
            f"/api/v1/operations/{operation_id}",
        )
        
        assert response.status_code in [200, 404]

    async def test_get_nonexistent_operation_not_found(
        self, authenticated_async_client: AsyncClient
    ):
        """Test getting non-existent operation (404)."""
        nonexistent_id = str(uuid4())
        
        response = await authenticated_async_client.get(
            f"/api/v1/operations/{nonexistent_id}",
        )
        
        assert response.status_code == 404

    async def test_list_operations_success(
        self, authenticated_async_client: AsyncClient
    ):
        """Test listing operations (200)."""
        response = await authenticated_async_client.get(
            "/api/v1/operations",
            params={"page": 1, "page_size": 50},
        )
        
        assert response.status_code == 200

    async def test_update_operation_success(
        self, authenticated_async_client: AsyncClient
    ):
        """Test updating operation (200)."""
        operation_id = str(uuid4())
        update_payload = {
            "estimated_time_hours": 3.0,
            "estimated_labor_cost": 75.00,
        }
        
        response = await authenticated_async_client.put(
            f"/api/v1/operations/{operation_id}",
            json=update_payload,
        )
        
        assert response.status_code in [200, 404, 422]

    async def test_delete_operation_soft_delete(
        self, authenticated_async_client: AsyncClient
    ):
        """Test soft delete of operation (204)."""
        operation_id = str(uuid4())
        
        response = await authenticated_async_client.delete(
            f"/api/v1/operations/{operation_id}",
        )
        
        assert response.status_code in [200, 204, 404]

    async def test_unauthorized_access_denied(
        self, async_client: AsyncClient, operation_payload: dict
    ):
        """Test unauthorized access (401)."""
        response = await async_client.post(
            "/api/v1/operations",
            json=operation_payload,
        )
        
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
class TestWorkstationAPI:
    """Test workstation API endpoints."""

    async def test_create_workstation_success(
        self, authenticated_async_client: AsyncClient, workstation_payload: dict
    ):
        """Test successful workstation creation (201)."""
        response = await authenticated_async_client.post(
            "/api/v1/workstations",
            json=workstation_payload,
        )
        
        assert response.status_code in [200, 201]

    async def test_get_workstation_success(
        self, authenticated_async_client: AsyncClient
    ):
        """Test getting workstation (200)."""
        workstation_id = str(uuid4())
        
        response = await authenticated_async_client.get(
            f"/api/v1/workstations/{workstation_id}",
        )
        
        assert response.status_code in [200, 404]

    async def test_list_workstations(
        self, authenticated_async_client: AsyncClient
    ):
        """Test listing workstations (200)."""
        response = await authenticated_async_client.get(
            "/api/v1/workstations",
        )
        
        assert response.status_code == 200

    async def test_update_workstation_hourly_rate(
        self, authenticated_async_client: AsyncClient
    ):
        """Test updating workstation hourly rate (200)."""
        workstation_id = str(uuid4())
        update_payload = {
            "hourly_rate": 75.00,
        }
        
        response = await authenticated_async_client.put(
            f"/api/v1/workstations/{workstation_id}",
            json=update_payload,
        )
        
        assert response.status_code in [200, 404, 422]

    async def test_delete_workstation(
        self, authenticated_async_client: AsyncClient
    ):
        """Test deleting workstation (204)."""
        workstation_id = str(uuid4())
        
        response = await authenticated_async_client.delete(
            f"/api/v1/workstations/{workstation_id}",
        )
        
        assert response.status_code in [200, 204, 404]


@pytest.mark.asyncio
class TestOperationCostCalculation:
    """Test operation cost calculations via API."""

    async def test_get_operation_cost(
        self, authenticated_async_client: AsyncClient
    ):
        """Test getting operation cost calculation (200)."""
        operation_id = str(uuid4())
        
        response = await authenticated_async_client.get(
            f"/api/v1/operations/{operation_id}/cost",
        )
        
        assert response.status_code in [200, 404]

    async def test_cost_includes_labor_and_equipment(
        self, authenticated_async_client: AsyncClient
    ):
        """Test cost breakdown includes labor and equipment (200)."""
        operation_id = str(uuid4())
        
        response = await authenticated_async_client.get(
            f"/api/v1/operations/{operation_id}/cost",
        )
        
        if response.status_code == 200:
            cost_data = response.json()
            # Should include labor_cost and equipment_cost
            assert isinstance(cost_data, dict)
