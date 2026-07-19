"""
Property tests for Auto-Invoice Idempotency and State Consistency (Property 3).

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 3: For any sales order that transitions to DELIVERED status:
1. If auto-invoice creation succeeds → SO status SHALL be INVOICED
2. If auto-invoice creation fails → SO status SHALL remain DELIVERED
3. If invoice already exists (duplicate trigger) → return existing invoice
   without creating a new one, SO still INVOICED

# Feature: manufacturing-erp-audit, Property 3: Auto-Invoice Idempotency and State Consistency
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    sampled_from,
    uuids,
    text,
    composite,
    booleans,
    floats,
    integers,
)
from sqlalchemy import select

from backend.app.domain.sales.value_objects.order_status import OrderStatus
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderModel,
    ClientModel,
)
from backend.app.infrastructure.persistence.models.finance_models import InvoiceModel
from backend.app.application.manufacturing.services.workflow_orchestration_service import (
    WorkflowOrchestrationService,
)


# ─── Strategies ──────────────────────────────────────────────────────────────

# Use a composite to produce unique order numbers per hypothesis example
@composite
def delivered_sales_order_data(draw):
    """Generate random data for a sales order in DELIVERED status."""
    tenant_id = draw(uuids())
    sales_order_id = draw(uuids())
    client_id = draw(uuids())
    # Use UUID parts to ensure unique order numbers
    suffix = draw(integers(min_value=1, max_value=9999999))
    order_number = f"SO-{suffix:07d}-{str(sales_order_id)[:4]}"
    grand_total = draw(floats(min_value=1.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False))

    return {
        "tenant_id": tenant_id,
        "sales_order_id": sales_order_id,
        "client_id": client_id,
        "order_number": order_number,
        "grand_total": grand_total,
    }


@composite
def invoice_failure_reason(draw):
    """Generate random reasons why invoice creation might fail."""
    reasons = [
        "Client not found for sales order",
        "Database connection timeout",
        "Validation error: missing required field",
        "Concurrent modification conflict",
        "Finance module temporarily unavailable",
    ]
    return draw(sampled_from(reasons))


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _setup_delivered_so(session, data: dict) -> SalesOrderModel:
    """Create client and sales order in DELIVERED status in the test database."""
    tenant_id = data["tenant_id"]
    client_id = data["client_id"]
    sales_order_id = data["sales_order_id"]
    order_number = data["order_number"]
    grand_total = data["grand_total"]

    client = ClientModel(
        id=client_id,
        tenant_id=tenant_id,
        code=f"CLI-{str(client_id)[:8]}",
        name=f"Test Client {str(client_id)[:8]}",
        email="test@example.com",
        payment_terms_days=30,
        is_active=True,
        is_deleted=False,
    )
    session.add(client)

    so = SalesOrderModel(
        id=sales_order_id,
        tenant_id=tenant_id,
        client_id=client_id,
        order_number=order_number,
        order_date=datetime.now(timezone.utc).date().isoformat(),
        delivery_date=datetime.now(timezone.utc).date().isoformat(),
        status=OrderStatus.DELIVERED.value,
        payment_status="PENDING",
        subtotal=grand_total,
        discount_amount=0.0,
        tax_amount=0.0,
        grand_total=grand_total,
        is_active=True,
        is_deleted=False,
    )
    session.add(so)
    await session.flush()
    return so


def _make_mock_invoice(invoice_id: uuid.UUID, sales_order_id: uuid.UUID) -> MagicMock:
    """Create a mock invoice object returned by FinanceService."""
    invoice = MagicMock()
    invoice.id = invoice_id
    invoice.sales_order_id = sales_order_id
    invoice.status = "DRAFT"
    invoice.invoice_number = f"INV-{str(invoice_id)[:8]}"
    return invoice


# ─────────────────────────────────────────────────────────────────────────────
# Property 3: Auto-Invoice Idempotency and State Consistency
#
# Sub-property A: If auto-invoice creation succeeds → SO status SHALL be INVOICED
# Sub-property B: If auto-invoice creation fails → SO status SHALL remain DELIVERED
# Sub-property C: If invoice already exists → return existing without creating new,
#                 SO still INVOICED
# ─────────────────────────────────────────────────────────────────────────────


class TestAutoInvoiceIdempotency:
    """**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

    Property 3: Auto-Invoice Idempotency and State Consistency.
    """

    @given(data=delivered_sales_order_data())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_successful_invoice_transitions_so_to_invoiced(
        self,
        data: dict,
        db_session,
    ):
        """Property 3A: For any sales order that transitions to DELIVERED,
        if auto-invoice creation succeeds, the SO status SHALL be INVOICED.

        **Validates: Requirements 2.1, 2.2**
        """
        tenant_id = data["tenant_id"]
        sales_order_id = data["sales_order_id"]

        try:
            # Set up test data
            so = await _setup_delivered_so(db_session, data)

            # Create the orchestration service
            service = WorkflowOrchestrationService(db_session)

            # Mock the FinanceService to simulate successful invoice creation
            mock_invoice = _make_mock_invoice(uuid.uuid4(), sales_order_id)
            with patch(
                "backend.app.application.finance.finance_service.FinanceService.create_invoice_from_sales_order",
                new_callable=AsyncMock,
                return_value=mock_invoice,
            ):
                # Mock notification service to avoid side effects
                service.notification_service = AsyncMock()
                service.notification_service.create_notification = AsyncMock()

                result = await service.on_order_delivered(
                    tenant_id=tenant_id,
                    sales_order_id=sales_order_id,
                )

            # Verify: SO status is now INVOICED
            await db_session.refresh(so)
            assert so.status == OrderStatus.INVOICED.value, (
                f"Expected SO status to be INVOICED after successful invoice creation, "
                f"but got {so.status}"
            )

            # Verify: result indicates success
            assert result["invoice_created"] is True
            assert result["status"] == OrderStatus.INVOICED.value
        finally:
            await db_session.rollback()

    @given(data=delivered_sales_order_data(), failure_reason=invoice_failure_reason())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_failed_invoice_leaves_so_in_delivered(
        self,
        data: dict,
        failure_reason: str,
        db_session,
    ):
        """Property 3B: For any sales order that transitions to DELIVERED,
        if auto-invoice creation fails, the SO status SHALL remain DELIVERED.

        **Validates: Requirements 2.3**
        """
        tenant_id = data["tenant_id"]
        sales_order_id = data["sales_order_id"]

        try:
            # Set up test data
            so = await _setup_delivered_so(db_session, data)

            # Create the orchestration service
            service = WorkflowOrchestrationService(db_session)

            # Mock the FinanceService to simulate FAILURE
            with patch(
                "backend.app.application.finance.finance_service.FinanceService.create_invoice_from_sales_order",
                new_callable=AsyncMock,
                side_effect=Exception(failure_reason),
            ):
                # Mock notification service
                service.notification_service = AsyncMock()
                service.notification_service.create_notification = AsyncMock()

                result = await service.on_order_delivered(
                    tenant_id=tenant_id,
                    sales_order_id=sales_order_id,
                )

            # Verify: SO status remains DELIVERED
            await db_session.refresh(so)
            assert so.status == OrderStatus.DELIVERED.value, (
                f"Expected SO status to remain DELIVERED after invoice creation failure, "
                f"but got {so.status}. Failure reason: {failure_reason}"
            )

            # Verify: result indicates failure
            assert result["invoice_created"] is False
            assert result.get("error") is not None
            assert result["status"] == OrderStatus.DELIVERED.value

            # Verify: notification was created for the failure (Req 2.3)
            # Two notifications: dispatch_completed + invoice_creation_failed
            assert service.notification_service.create_notification.call_count == 2
            call_types = [
                call.kwargs.get("notification_type") if call.kwargs else call[1].get("notification_type")
                for call in service.notification_service.create_notification.call_args_list
            ]
            assert "invoice_creation_failed" in call_types
            assert "dispatch_completed" in call_types
        finally:
            await db_session.rollback()

    @given(data=delivered_sales_order_data())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_duplicate_trigger_returns_existing_invoice_no_new_creation(
        self,
        data: dict,
        db_session,
    ):
        """Property 3C: If an invoice already exists for the sales order,
        re-triggering auto-invoice SHALL return the existing invoice without
        creating a duplicate, and the SO SHALL still be INVOICED.

        **Validates: Requirements 2.4**
        """
        tenant_id = data["tenant_id"]
        sales_order_id = data["sales_order_id"]

        try:
            # Set up test data
            so = await _setup_delivered_so(db_session, data)

            # First call: successful invoice creation
            mock_invoice = _make_mock_invoice(uuid.uuid4(), sales_order_id)
            with patch(
                "backend.app.application.finance.finance_service.FinanceService.create_invoice_from_sales_order",
                new_callable=AsyncMock,
                return_value=mock_invoice,
            ):
                service = WorkflowOrchestrationService(db_session)
                service.notification_service = AsyncMock()
                service.notification_service.create_notification = AsyncMock()

                first_result = await service.on_order_delivered(
                    tenant_id=tenant_id,
                    sales_order_id=sales_order_id,
                )

            # Verify first call succeeded
            await db_session.refresh(so)
            assert so.status == OrderStatus.INVOICED.value
            assert first_result["invoice_created"] is True

            # Second call: duplicate trigger — should be caught by on_auto_transition idempotency
            with patch(
                "backend.app.application.finance.finance_service.FinanceService.create_invoice_from_sales_order",
                new_callable=AsyncMock,
                return_value=mock_invoice,
            ):
                service2 = WorkflowOrchestrationService(db_session)
                service2.notification_service = AsyncMock()
                service2.notification_service.create_notification = AsyncMock()

                second_result = await service2.on_order_delivered(
                    tenant_id=tenant_id,
                    sales_order_id=sales_order_id,
                )

            # Verify: second call is recognized as duplicate (idempotent)
            assert second_result.get("duplicate") is True, (
                f"Expected duplicate detection on second trigger, "
                f"but got result: {second_result}"
            )

            # Verify: SO is still INVOICED
            await db_session.refresh(so)
            assert so.status == OrderStatus.INVOICED.value, (
                f"Expected SO to remain INVOICED after duplicate trigger, "
                f"but got {so.status}"
            )
        finally:
            await db_session.rollback()

    @given(data=delivered_sales_order_data())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_multiple_duplicate_triggers_never_create_extra_invoices(
        self,
        data: dict,
        db_session,
    ):
        """Property 3C extended: Multiple duplicate triggers (3+) all return
        duplicate without creating new invoices. The system is stable under
        repeated invocations.

        **Validates: Requirements 2.4**
        """
        tenant_id = data["tenant_id"]
        sales_order_id = data["sales_order_id"]

        try:
            # Set up test data
            so = await _setup_delivered_so(db_session, data)

            # First call: successful
            mock_invoice = _make_mock_invoice(uuid.uuid4(), sales_order_id)
            with patch(
                "backend.app.application.finance.finance_service.FinanceService.create_invoice_from_sales_order",
                new_callable=AsyncMock,
                return_value=mock_invoice,
            ):
                service = WorkflowOrchestrationService(db_session)
                service.notification_service = AsyncMock()
                service.notification_service.create_notification = AsyncMock()

                await service.on_order_delivered(
                    tenant_id=tenant_id,
                    sales_order_id=sales_order_id,
                )

            # Trigger 2 more times — all should be duplicates
            duplicate_count = 0
            for _ in range(2):
                with patch(
                    "backend.app.application.finance.finance_service.FinanceService.create_invoice_from_sales_order",
                    new_callable=AsyncMock,
                    return_value=mock_invoice,
                ):
                    svc = WorkflowOrchestrationService(db_session)
                    svc.notification_service = AsyncMock()
                    svc.notification_service.create_notification = AsyncMock()

                    result = await svc.on_order_delivered(
                        tenant_id=tenant_id,
                        sales_order_id=sales_order_id,
                    )
                    if result.get("duplicate"):
                        duplicate_count += 1

            # All subsequent triggers should be duplicates
            assert duplicate_count == 2, (
                f"Expected 2 duplicate detections for repeated triggers, got {duplicate_count}"
            )

            # SO remains INVOICED
            await db_session.refresh(so)
            assert so.status == OrderStatus.INVOICED.value
        finally:
            await db_session.rollback()

    @given(data=delivered_sales_order_data())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_invoice_success_creates_invoice_with_correct_so_linkage(
        self,
        data: dict,
        db_session,
    ):
        """Property 3A supplementary: When invoice creation succeeds, the
        result contains the invoice_id linked to the sales order.

        **Validates: Requirements 2.1, 2.2**
        """
        tenant_id = data["tenant_id"]
        sales_order_id = data["sales_order_id"]

        try:
            # Set up test data
            await _setup_delivered_so(db_session, data)

            service = WorkflowOrchestrationService(db_session)

            # Mock successful invoice creation with a known invoice_id
            expected_invoice_id = uuid.uuid4()
            mock_invoice = _make_mock_invoice(expected_invoice_id, sales_order_id)

            with patch(
                "backend.app.application.finance.finance_service.FinanceService.create_invoice_from_sales_order",
                new_callable=AsyncMock,
                return_value=mock_invoice,
            ):
                service.notification_service = AsyncMock()
                service.notification_service.create_notification = AsyncMock()

                result = await service.on_order_delivered(
                    tenant_id=tenant_id,
                    sales_order_id=sales_order_id,
                )

            # Verify result contains invoice_id
            assert result["invoice_id"] == str(expected_invoice_id), (
                f"Expected invoice_id={expected_invoice_id} in result, "
                f"got {result.get('invoice_id')}"
            )
            assert result["sales_order_id"] == str(sales_order_id)
        finally:
            await db_session.rollback()
