"""
Unit tests for InventoryTransactionService.

Tests cover:
- Transaction types include new types: RESERVATION_RELEASE, DISPATCH_REVERSAL, PRODUCTION_CONSUMPTION
- get_transactions() with pagination and filters
- get_running_balance() computing cumulative sum per material
- check_reconciliation() comparing sum vs current_stock

Requirements: 31.1, 31.2, 31.5, 31.6, 31.7, 31.9, 31.10
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services.inventory_transaction_service import (
    InventoryTransactionService,
    InventoryTransactionType,
    VALID_TRANSACTION_TYPES,
    PaginatedTransactionResponse,
    TransactionWithBalance,
    ReconciliationStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_tx_model(
    tenant_id=None,
    material_id=None,
    transaction_type="FG_RECEIPT",
    quantity=10.0,
    reference_type="work_order",
    reference_id=None,
    created_by=None,
    created_at=None,
    from_location_id=None,
    to_location_id=None,
    batch_id=None,
    remarks=None,
):
    """Create a mock InventoryTransactionModel."""
    model = MagicMock()
    model.id = uuid.uuid4()
    model.tenant_id = tenant_id or uuid.uuid4()
    model.material_id = material_id or uuid.uuid4()
    model.transaction_type = transaction_type
    model.quantity = quantity
    model.reference_type = reference_type
    model.reference_id = reference_id or uuid.uuid4()
    model.created_by = created_by or uuid.uuid4()
    model.created_at = created_at or datetime.now(timezone.utc)
    model.from_location_id = from_location_id
    model.to_location_id = to_location_id
    model.batch_id = batch_id
    model.remarks = remarks
    model.is_deleted = False
    return model


# ---------------------------------------------------------------------------
# Transaction Type Tests (Requirement 31.1, 31.2)
# ---------------------------------------------------------------------------


class TestTransactionTypes:
    """Verify the new transaction types are included."""

    def test_reservation_release_type_exists(self):
        """RESERVATION_RELEASE is a valid transaction type."""
        assert "RESERVATION_RELEASE" in VALID_TRANSACTION_TYPES
        assert InventoryTransactionType.RESERVATION_RELEASE.value == "RESERVATION_RELEASE"

    def test_dispatch_reversal_type_exists(self):
        """DISPATCH_REVERSAL is a valid transaction type."""
        assert "DISPATCH_REVERSAL" in VALID_TRANSACTION_TYPES
        assert InventoryTransactionType.DISPATCH_REVERSAL.value == "DISPATCH_REVERSAL"

    def test_production_consumption_type_exists(self):
        """PRODUCTION_CONSUMPTION is a valid transaction type."""
        assert "PRODUCTION_CONSUMPTION" in VALID_TRANSACTION_TYPES
        assert InventoryTransactionType.PRODUCTION_CONSUMPTION.value == "PRODUCTION_CONSUMPTION"

    def test_all_required_types_present(self):
        """All 13 transaction types from design spec are present."""
        expected = {
            "OPENING_STOCK", "PURCHASE_RECEIPT", "RESERVATION", "RESERVATION_RELEASE",
            "MATERIAL_ISSUE", "PRODUCTION_CONSUMPTION", "FG_RECEIPT", "DISPATCH",
            "DISPATCH_REVERSAL", "SALES_RETURN", "SCRAP", "ADJUSTMENT", "TRANSFER",
        }
        assert expected == VALID_TRANSACTION_TYPES

    def test_transaction_type_is_string_enum(self):
        """TransactionType values are strings for DB storage."""
        for tt in InventoryTransactionType:
            assert isinstance(tt.value, str)


# ---------------------------------------------------------------------------
# get_transactions() Tests (Requirements 31.6, 31.7, 31.9)
# ---------------------------------------------------------------------------


class TestGetTransactions:
    """Test paginated transaction retrieval with filters."""

    @pytest.mark.asyncio
    async def test_returns_paginated_response(self):
        """get_transactions returns PaginatedTransactionResponse with correct structure."""
        session = _make_session()
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        tx1 = _make_tx_model(tenant_id=tenant_id, material_id=material_id)
        tx2 = _make_tx_model(tenant_id=tenant_id, material_id=material_id)

        # Mock count query
        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        # Mock data query
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [tx1, tx2]

        session.execute = AsyncMock(side_effect=[count_result, data_result])

        service = InventoryTransactionService(session)
        result = await service.get_transactions(tenant_id=tenant_id, material_id=material_id)

        assert isinstance(result, PaginatedTransactionResponse)
        assert result.total == 2
        assert len(result.items) == 2
        assert result.offset == 0
        assert result.limit == 50

    @pytest.mark.asyncio
    async def test_default_pagination(self):
        """Default offset=0, limit=50."""
        session = _make_session()
        tenant_id = uuid.uuid4()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(side_effect=[count_result, data_result])

        service = InventoryTransactionService(session)
        result = await service.get_transactions(tenant_id=tenant_id)

        assert result.offset == 0
        assert result.limit == 50

    @pytest.mark.asyncio
    async def test_limit_clamped_to_max_200(self):
        """Limit is clamped to maximum 200."""
        session = _make_session()
        tenant_id = uuid.uuid4()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(side_effect=[count_result, data_result])

        service = InventoryTransactionService(session)
        result = await service.get_transactions(tenant_id=tenant_id, limit=500)

        assert result.limit == 200

    @pytest.mark.asyncio
    async def test_negative_offset_clamped_to_zero(self):
        """Negative offset is clamped to 0."""
        session = _make_session()
        tenant_id = uuid.uuid4()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(side_effect=[count_result, data_result])

        service = InventoryTransactionService(session)
        result = await service.get_transactions(tenant_id=tenant_id, offset=-5)

        assert result.offset == 0

    @pytest.mark.asyncio
    async def test_empty_result(self):
        """Returns empty list when no transactions match filters."""
        session = _make_session()
        tenant_id = uuid.uuid4()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(side_effect=[count_result, data_result])

        service = InventoryTransactionService(session)
        result = await service.get_transactions(
            tenant_id=tenant_id,
            transaction_type="DISPATCH_REVERSAL",
        )

        assert result.total == 0
        assert result.items == []


# ---------------------------------------------------------------------------
# get_running_balance() Tests (Requirement 31.5)
# ---------------------------------------------------------------------------


class TestGetRunningBalance:
    """Test cumulative running balance computation."""

    @pytest.mark.asyncio
    async def test_running_balance_cumulative_sum(self):
        """Running balance at position k = sum(T₁..Tₖ)."""
        session = _make_session()
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        tx1 = _make_tx_model(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="PURCHASE_RECEIPT",
            quantity=100.0,
            created_at=base_time,
        )
        tx2 = _make_tx_model(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="MATERIAL_ISSUE",
            quantity=-30.0,
            created_at=base_time + timedelta(hours=1),
        )
        tx3 = _make_tx_model(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="RESERVATION_RELEASE",
            quantity=10.0,
            created_at=base_time + timedelta(hours=2),
        )

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [tx1, tx2, tx3]
        session.execute = AsyncMock(return_value=data_result)

        service = InventoryTransactionService(session)
        result = await service.get_running_balance(tenant_id=tenant_id, material_id=material_id)

        assert len(result) == 3
        assert result[0].running_balance == Decimal("100.0")
        assert result[1].running_balance == Decimal("70.0")
        assert result[2].running_balance == Decimal("80.0")

    @pytest.mark.asyncio
    async def test_running_balance_empty(self):
        """Empty transaction list returns empty result."""
        session = _make_session()
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=data_result)

        service = InventoryTransactionService(session)
        result = await service.get_running_balance(tenant_id=tenant_id, material_id=material_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_running_balance_single_transaction(self):
        """Single transaction: running balance equals its quantity."""
        session = _make_session()
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        tx = _make_tx_model(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="OPENING_STOCK",
            quantity=50.0,
        )

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [tx]
        session.execute = AsyncMock(return_value=data_result)

        service = InventoryTransactionService(session)
        result = await service.get_running_balance(tenant_id=tenant_id, material_id=material_id)

        assert len(result) == 1
        assert result[0].running_balance == Decimal("50.0")
        assert isinstance(result[0], TransactionWithBalance)


# ---------------------------------------------------------------------------
# check_reconciliation() Tests (Requirements 31.9, 31.10)
# ---------------------------------------------------------------------------


class TestCheckReconciliation:
    """Test stock reconciliation check."""

    @pytest.mark.asyncio
    async def test_reconciled_when_within_tolerance(self):
        """Reconciled when |sum - current_stock| <= 0.001."""
        session = _make_session()
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        # Sum of transactions = 100.0005 (within 0.001 of 100.0)
        sum_result = MagicMock()
        sum_result.scalar_one.return_value = 100.0005

        material_result = MagicMock()
        material_result.scalar_one_or_none.return_value = 100.0

        session.execute = AsyncMock(side_effect=[sum_result, material_result])

        service = InventoryTransactionService(session)
        result = await service.check_reconciliation(tenant_id=tenant_id, material_id=material_id)

        assert isinstance(result, ReconciliationStatus)
        assert result.is_reconciled is True
        assert result.material_id == material_id

    @pytest.mark.asyncio
    async def test_not_reconciled_when_exceeds_tolerance(self):
        """Not reconciled when |sum - current_stock| > 0.001."""
        session = _make_session()
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        # Sum of transactions = 105.0, current_stock = 100.0 -> diff = 5.0
        sum_result = MagicMock()
        sum_result.scalar_one.return_value = 105.0

        material_result = MagicMock()
        material_result.scalar_one_or_none.return_value = 100.0

        session.execute = AsyncMock(side_effect=[sum_result, material_result])

        service = InventoryTransactionService(session)
        result = await service.check_reconciliation(tenant_id=tenant_id, material_id=material_id)

        assert result.is_reconciled is False
        assert result.difference == Decimal("5.0")
        assert result.transaction_sum == Decimal("105.0")
        assert result.current_stock == Decimal("100.0")

    @pytest.mark.asyncio
    async def test_exact_match_is_reconciled(self):
        """Exact match (diff = 0) is reconciled."""
        session = _make_session()
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        sum_result = MagicMock()
        sum_result.scalar_one.return_value = 75.0

        material_result = MagicMock()
        material_result.scalar_one_or_none.return_value = 75.0

        session.execute = AsyncMock(side_effect=[sum_result, material_result])

        service = InventoryTransactionService(session)
        result = await service.check_reconciliation(tenant_id=tenant_id, material_id=material_id)

        assert result.is_reconciled is True
        assert result.difference == Decimal("0")

    @pytest.mark.asyncio
    async def test_material_not_found_raises_error(self):
        """Raises ValueError when material doesn't exist."""
        session = _make_session()
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        sum_result = MagicMock()
        sum_result.scalar_one.return_value = 0

        material_result = MagicMock()
        material_result.scalar_one_or_none.return_value = None

        session.execute = AsyncMock(side_effect=[sum_result, material_result])

        service = InventoryTransactionService(session)

        with pytest.raises(ValueError, match="not found"):
            await service.check_reconciliation(tenant_id=tenant_id, material_id=material_id)

    @pytest.mark.asyncio
    async def test_zero_stock_zero_transactions_reconciled(self):
        """Zero stock and zero transactions is reconciled."""
        session = _make_session()
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        sum_result = MagicMock()
        sum_result.scalar_one.return_value = 0

        material_result = MagicMock()
        material_result.scalar_one_or_none.return_value = 0

        session.execute = AsyncMock(side_effect=[sum_result, material_result])

        service = InventoryTransactionService(session)
        result = await service.check_reconciliation(tenant_id=tenant_id, material_id=material_id)

        assert result.is_reconciled is True
        assert result.transaction_sum == Decimal("0")
        assert result.current_stock == Decimal("0")
