"""
Property tests for opening balance atomicity on material creation.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

These tests validate four correctness properties:
  - Property 1: Opening stock atomicity
  - Property 8: Backward compatibility — opening stock omission
  - Property 9: Negative opening stock rejection
  - Property 10: Opening stock ignored on update
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.inventory_transaction_model import (
    InventoryTransactionModel,
)


def _unique_suffix() -> str:
    """Generate a short unique suffix for test isolation."""
    return uuid.uuid4().hex[:8].upper()


# ─────────────────────────────────────────────────────────────────────────────
# Property 1: Opening stock atomicity
# For any valid material creation request with opening_stock=N where N > 0,
# after the endpoint returns successfully, material.current_stock == N AND
# exactly one transaction record exists with transaction_type="in",
# reference_type="opening_balance", and quantity=N.
# ─────────────────────────────────────────────────────────────────────────────


class TestOpeningStockAtomicity:
    """**Validates: Requirements 1.1, 1.2**"""

    @pytest.mark.parametrize(
        "opening_stock",
        [
            "1",
            "0.001",
            "100",
            "999.99",
            "12345.678",
        ],
        ids=["one", "fractional", "hundred", "large_decimal", "five_digits"],
    )
    async def test_material_created_with_correct_stock_and_transaction(
        self,
        authenticated_async_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant_id: uuid.UUID,
        opening_stock: str,
    ):
        """Property 1: For any opening_stock > 0, current_stock == N and exactly one
        opening_balance transaction with quantity == N exists."""
        suffix = _unique_suffix()
        response = await authenticated_async_client.post(
            "/api/v1/inventory/materials",
            json={
                "name": f"Opening Stock Test {suffix}",
                "material_type": "raw",
                "opening_stock": opening_stock,
            },
        )

        assert response.status_code == 201, response.text
        data = response.json()
        material_id = uuid.UUID(data["id"])
        expected = Decimal(opening_stock)

        # Assert current_stock in response equals opening_stock
        assert Decimal(str(data["current_stock"])) == expected

        # Assert exactly one transaction with correct attributes
        result = await db_session.execute(
            select(InventoryTransactionModel).where(
                InventoryTransactionModel.tenant_id == test_tenant_id,
                InventoryTransactionModel.material_id == material_id,
                InventoryTransactionModel.is_deleted.is_(False),
            )
        )
        transactions = result.scalars().all()
        opening_txs = [
            tx
            for tx in transactions
            if tx.transaction_type == "in" and tx.reference_type == "opening_balance"
        ]

        assert len(opening_txs) == 1, (
            f"Expected exactly 1 opening_balance transaction, found {len(opening_txs)}"
        )
        assert Decimal(str(opening_txs[0].quantity)) == expected


# ─────────────────────────────────────────────────────────────────────────────
# Property 8: Backward compatibility — opening stock omission
# For any material creation request that does NOT include opening_stock
# (or includes it as null/zero), the material is created with current_stock == 0
# and no opening balance transaction is recorded.
# ─────────────────────────────────────────────────────────────────────────────


class TestBackwardCompatibilityOpeningStockOmission:
    """**Validates: Requirements 1.3**"""

    @pytest.mark.parametrize(
        "opening_stock_value,description",
        [
            (None, "omitted"),
            ("0", "explicit_zero"),
        ],
        ids=["omitted", "explicit_zero"],
    )
    async def test_no_opening_stock_means_zero_stock_no_transaction(
        self,
        authenticated_async_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant_id: uuid.UUID,
        opening_stock_value,
        description: str,
    ):
        """Property 8: No opening_stock → current_stock == 0, no opening_balance tx."""
        suffix = _unique_suffix()
        payload: dict = {
            "name": f"No Opening {description} {suffix}",
            "material_type": "raw",
        }
        if opening_stock_value is not None:
            payload["opening_stock"] = opening_stock_value

        response = await authenticated_async_client.post(
            "/api/v1/inventory/materials",
            json=payload,
        )

        assert response.status_code == 201, response.text
        data = response.json()
        material_id = uuid.UUID(data["id"])

        # current_stock must be 0
        assert Decimal(str(data["current_stock"])) == Decimal("0")

        # No opening_balance transaction should exist
        result = await db_session.execute(
            select(InventoryTransactionModel).where(
                InventoryTransactionModel.tenant_id == test_tenant_id,
                InventoryTransactionModel.material_id == material_id,
                InventoryTransactionModel.is_deleted.is_(False),
            )
        )
        transactions = result.scalars().all()
        opening_txs = [
            tx
            for tx in transactions
            if tx.reference_type == "opening_balance"
        ]
        assert len(opening_txs) == 0, (
            f"Expected no opening_balance transactions, found {len(opening_txs)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 9: Negative opening stock rejection
# For any opening_stock value less than zero, the system SHALL reject the request
# with a 422 validation error.
# ─────────────────────────────────────────────────────────────────────────────


class TestNegativeOpeningStockRejection:
    """**Validates: Requirements 1.4**"""

    @pytest.mark.parametrize(
        "negative_value",
        ["-1", "-0.001", "-100", "-99999"],
        ids=["minus_one", "small_negative", "large_negative", "very_large_negative"],
    )
    async def test_negative_opening_stock_returns_422(
        self,
        authenticated_async_client: AsyncClient,
        negative_value: str,
    ):
        """Property 9: Negative opening_stock → 422 validation error."""
        suffix = _unique_suffix()
        response = await authenticated_async_client.post(
            "/api/v1/inventory/materials",
            json={
                "name": f"Negative Stock Test {suffix}",
                "material_type": "raw",
                "opening_stock": negative_value,
            },
        )

        assert response.status_code == 422, (
            f"Expected 422 for opening_stock={negative_value}, got {response.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 10: Opening stock ignored on update
# For any existing material and any update request containing an opening_stock
# field (regardless of value), the material's current_stock SHALL remain unchanged.
# ─────────────────────────────────────────────────────────────────────────────


class TestOpeningStockIgnoredOnUpdate:
    """**Validates: Requirements 1.5**"""

    @pytest.mark.parametrize(
        "update_opening_stock",
        ["50", "0", "999"],
        ids=["positive", "zero", "large"],
    )
    async def test_update_with_opening_stock_does_not_change_stock(
        self,
        authenticated_async_client: AsyncClient,
        update_opening_stock: str,
    ):
        """Property 10: Update with opening_stock field → stock unchanged."""
        suffix = _unique_suffix()
        initial_stock = "25"

        # Create material with known opening_stock
        create_resp = await authenticated_async_client.post(
            "/api/v1/inventory/materials",
            json={
                "name": f"Update Ignore Test {suffix}",
                "material_type": "raw",
                "opening_stock": initial_stock,
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        created = create_resp.json()
        material_id = created["id"]
        stock_before = Decimal(str(created["current_stock"]))

        # Update with opening_stock in body — should be ignored
        update_resp = await authenticated_async_client.put(
            f"/api/v1/inventory/materials/{material_id}",
            json={
                "description": f"Updated description {suffix}",
                "opening_stock": update_opening_stock,
            },
        )
        # UpdateMaterialRequest doesn't have opening_stock field, so the
        # extra field is simply ignored by Pydantic (no error, no effect)
        assert update_resp.status_code == 200, update_resp.text
        updated = update_resp.json()

        # Stock must remain unchanged
        stock_after = Decimal(str(updated["current_stock"]))
        assert stock_after == stock_before, (
            f"Stock changed from {stock_before} to {stock_after} after update with "
            f"opening_stock={update_opening_stock}"
        )
