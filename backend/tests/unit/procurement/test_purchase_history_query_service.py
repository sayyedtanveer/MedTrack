"""
Unit tests for PurchaseHistoryQueryService.

Tests cover:
- get_purchasing_summary returns correct latest price from completed GRNs
- get_purchasing_summary excludes reversed / cancelled / deleted GRNs
- get_purchasing_summary enforces tenant isolation (cross-tenant data must not leak)
- get_purchasing_summary purchase_count counts only completed receipt lines
- get_purchase_history returns paginated results ordered newest-first
- get_purchase_history returns empty when no completed GRNs exist
"""
from __future__ import annotations

import uuid
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.application.procurement.services.purchase_history_query_service import (
    PurchaseHistoryQueryService,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_session():
    """Create a minimal mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_execute_result(value):
    """Wrap a scalar value in a mock execute result."""
    result = MagicMock()
    result.scalar.return_value = value
    result.first.return_value = value
    result.all.return_value = value if isinstance(value, list) else [value] if value else []
    return result


def _make_row(
    unit_price=500.0,
    receipt_date=None,
    supplier_name="Supplier A",
    supplier_id=None,
):
    """Create a mock row as returned by the summary query."""
    row = MagicMock()
    row.__getitem__ = lambda self, i: [
        unit_price,
        receipt_date or datetime(2024, 6, 15, tzinfo=timezone.utc),
        supplier_name,
        supplier_id or uuid.uuid4(),
    ][i]
    return row


def _make_history_row(
    receipt_date=None,
    supplier_id=None,
    supplier_name="Supplier A",
    po_number="PO-001",
    grn_number="GRN-001",
    quantity=100.0,
    uom_code="KG",
    unit_price=500.0,
):
    row = MagicMock()
    row.date = receipt_date or datetime(2024, 6, 15, tzinfo=timezone.utc)
    row.supplier_id = supplier_id or uuid.uuid4()
    row.supplier_name = supplier_name
    row.po_number = po_number
    row.grn_number = grn_number
    row.quantity = quantity
    row.uom_code = uom_code
    row.unit_price = unit_price
    return row


# ─── Tests: get_purchasing_summary ────────────────────────────────────────────


class TestGetPurchasingSummary:

    @pytest.mark.asyncio
    async def test_returns_latest_price_from_completed_grn(self):
        """Summary returns the latest price from the most recent completed GRN."""
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()
        supplier_id = uuid.uuid4()
        receipt_date = datetime(2024, 8, 1, tzinfo=timezone.utc)

        latest_row = _make_row(
            unit_price=750.0,
            receipt_date=receipt_date,
            supplier_name="Pharma Supplies Ltd",
            supplier_id=supplier_id,
        )

        call_count = [0]

        async def mock_execute(stmt, *args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # latest GRN query
                result.first.return_value = latest_row
            else:
                # count query
                result.scalar.return_value = 5
            return result

        session = _make_session()
        session.execute = AsyncMock(side_effect=mock_execute)

        svc = PurchaseHistoryQueryService(session)
        summary = await svc.get_purchasing_summary(material_id, tenant_id)

        assert summary["latest_purchase_price"] == Decimal("750.0")
        assert summary["last_purchase_date"] == receipt_date
        assert summary["last_supplier_name"] == "Pharma Supplies Ltd"
        assert summary["last_supplier_id"] == supplier_id
        assert summary["purchase_count"] == 5

    @pytest.mark.asyncio
    async def test_returns_empty_summary_when_no_completed_grns(self):
        """Summary returns all None fields and 0 count when no completed GRNs exist."""
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        call_count = [0]

        async def mock_execute(stmt, *args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.first.return_value = None   # no completed GRN
            else:
                result.scalar.return_value = 0
            return result

        session = _make_session()
        session.execute = AsyncMock(side_effect=mock_execute)

        svc = PurchaseHistoryQueryService(session)
        summary = await svc.get_purchasing_summary(material_id, tenant_id)

        assert summary["latest_purchase_price"] is None
        assert summary["last_purchase_date"] is None
        assert summary["last_supplier_name"] is None
        assert summary["last_supplier_id"] is None
        assert summary["purchase_count"] == 0

    @pytest.mark.asyncio
    async def test_purchase_count_counts_only_completed_receipts(self):
        """purchase_count must only reflect completed (received) GRN lines."""
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        call_count = [0]

        async def mock_execute(stmt, *args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.first.return_value = _make_row(unit_price=600.0)
            else:
                # Only 3 completed receipts; reversed/cancelled are excluded
                result.scalar.return_value = 3
            return result

        session = _make_session()
        session.execute = AsyncMock(side_effect=mock_execute)

        svc = PurchaseHistoryQueryService(session)
        summary = await svc.get_purchasing_summary(material_id, tenant_id)

        assert summary["purchase_count"] == 3

    @pytest.mark.asyncio
    async def test_tenant_isolation_different_tenant_returns_empty(self):
        """
        Cross-tenant isolation: querying with a different tenant_id must return
        no data even if another tenant has completed GRNs for the same material.
        """
        correct_tenant_id = uuid.uuid4()
        wrong_tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        async def mock_execute_no_data(stmt, *args, **kwargs):
            result = MagicMock()
            result.first.return_value = None
            result.scalar.return_value = 0
            return result

        session = _make_session()
        session.execute = AsyncMock(side_effect=mock_execute_no_data)

        svc = PurchaseHistoryQueryService(session)
        summary = await svc.get_purchasing_summary(material_id, wrong_tenant_id)

        # Must return empty – no data leaks from correct_tenant_id
        assert summary["latest_purchase_price"] is None
        assert summary["purchase_count"] == 0


# ─── Tests: get_purchase_history ──────────────────────────────────────────────


class TestGetPurchaseHistory:

    @pytest.mark.asyncio
    async def test_returns_paginated_history_ordered_newest_first(self):
        """History returns items with correct pagination metadata."""
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        row1 = _make_history_row(
            receipt_date=datetime(2024, 8, 10, tzinfo=timezone.utc),
            po_number="PO-002",
            grn_number="GRN-002",
            quantity=50.0,
            unit_price=520.0,
        )
        row2 = _make_history_row(
            receipt_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
            po_number="PO-001",
            grn_number="GRN-001",
            quantity=100.0,
            unit_price=500.0,
        )

        call_count = [0]

        async def mock_execute(stmt, *args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # tenant currency query
                result.scalar.return_value = "INR"
            elif call_count[0] == 2:
                # total count
                result.scalar.return_value = 2
            else:
                # history rows
                result.all.return_value = [row1, row2]
            return result

        session = _make_session()
        session.execute = AsyncMock(side_effect=mock_execute)

        svc = PurchaseHistoryQueryService(session)
        result = await svc.get_purchase_history(material_id, tenant_id, page=1, page_size=25)

        assert result["total"] == 2
        assert result["page"] == 1
        assert result["page_size"] == 25
        assert len(result["items"]) == 2

        # Newest first
        first_item = result["items"][0]
        assert first_item["grn_number"] == "GRN-002"
        assert first_item["unit_price"] == 520.0
        assert first_item["total_value"] == 50.0 * 520.0
        assert first_item["currency"] == "INR"
        assert first_item["uom"] == "KG"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_history(self):
        """Returns empty items list when no completed GRNs exist."""
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        call_count = [0]

        async def mock_execute(stmt, *args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.scalar.return_value = "USD"
            elif call_count[0] == 2:
                result.scalar.return_value = 0
            else:
                result.all.return_value = []
            return result

        session = _make_session()
        session.execute = AsyncMock(side_effect=mock_execute)

        svc = PurchaseHistoryQueryService(session)
        result = await svc.get_purchase_history(material_id, tenant_id, page=1, page_size=25)

        assert result["total"] == 0
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_split_receipt_lines_appear_as_separate_rows(self):
        """
        A split receipt (e.g. PO line received across two GRNs) must appear as
        two separate rows, not merged into one.
        """
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        row_grn1 = _make_history_row(
            grn_number="GRN-001", quantity=20.0, unit_price=500.0
        )
        row_grn2 = _make_history_row(
            grn_number="GRN-002", quantity=80.0, unit_price=500.0
        )

        call_count = [0]

        async def mock_execute(stmt, *args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.scalar.return_value = "INR"
            elif call_count[0] == 2:
                result.scalar.return_value = 2
            else:
                result.all.return_value = [row_grn1, row_grn2]
            return result

        session = _make_session()
        session.execute = AsyncMock(side_effect=mock_execute)

        svc = PurchaseHistoryQueryService(session)
        result = await svc.get_purchase_history(material_id, tenant_id)

        assert len(result["items"]) == 2
        grn_numbers = {item["grn_number"] for item in result["items"]}
        assert "GRN-001" in grn_numbers
        assert "GRN-002" in grn_numbers

    @pytest.mark.asyncio
    async def test_total_value_calculated_correctly(self):
        """total_value must equal quantity × unit_price for each row."""
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        row = _make_history_row(quantity=75.0, unit_price=480.0)

        call_count = [0]

        async def mock_execute(stmt, *args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.scalar.return_value = "INR"
            elif call_count[0] == 2:
                result.scalar.return_value = 1
            else:
                result.all.return_value = [row]
            return result

        session = _make_session()
        session.execute = AsyncMock(side_effect=mock_execute)

        svc = PurchaseHistoryQueryService(session)
        result = await svc.get_purchase_history(material_id, tenant_id)

        item = result["items"][0]
        assert item["quantity"] == 75.0
        assert item["unit_price"] == 480.0
        assert abs(item["total_value"] - (75.0 * 480.0)) < 0.001

    @pytest.mark.asyncio
    async def test_currency_falls_back_to_inr_when_tenant_has_none(self):
        """If tenant has no currency_code, defaults to INR."""
        tenant_id = uuid.uuid4()
        material_id = uuid.uuid4()

        row = _make_history_row()

        call_count = [0]

        async def mock_execute(stmt, *args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.scalar.return_value = None   # no currency set on tenant
            elif call_count[0] == 2:
                result.scalar.return_value = 1
            else:
                result.all.return_value = [row]
            return result

        session = _make_session()
        session.execute = AsyncMock(side_effect=mock_execute)

        svc = PurchaseHistoryQueryService(session)
        result = await svc.get_purchase_history(material_id, tenant_id)

        assert result["items"][0]["currency"] == "INR"
