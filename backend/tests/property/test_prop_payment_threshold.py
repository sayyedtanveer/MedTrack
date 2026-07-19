"""
Property tests for Payment Completion Threshold (Property 4).

**Validates: Requirements 3.4, 3.5, 3.6**

Property 4: For any invoice with grand_total > 0, the sales order SHALL transition
from INVOICED to COMPLETED if and only if the cumulative sum of all recorded payment
amounts >= grand_total. For any cumulative payment sum < grand_total, the sales order
SHALL remain in INVOICED status.

# Feature: manufacturing-erp-audit, Property 4: Payment Completion Threshold
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Tuple
from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    decimals,
    integers,
    lists,
    composite,
    just,
)

from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderModel,
    ClientModel,
)
from backend.app.infrastructure.persistence.models.finance_models import (
    InvoiceModel,
    PaymentModel,
)
from backend.app.application.manufacturing.services.workflow_orchestration_service import (
    WorkflowOrchestrationService,
)


# ─── Strategies ──────────────────────────────────────────────────────────────

# Grand total: positive amounts representing realistic invoice totals
grand_total_strategy = decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Individual payment amounts: positive amounts
payment_amount_strategy = decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@composite
def full_payment_scenario(draw):
    """Generate a scenario where cumulative payments >= grand_total (full payment).

    Generates a grand_total and a list of payments that sum to at least grand_total.
    """
    grand_total = draw(grand_total_strategy)

    # Generate 1-5 payments that collectively >= grand_total
    num_payments = draw(integers(min_value=1, max_value=5))

    if num_payments == 1:
        # Single payment >= grand_total
        overpay = draw(decimals(
            min_value=Decimal("0.00"),
            max_value=Decimal("100.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ))
        payments = [grand_total + overpay]
    else:
        # Multiple payments: first (num_payments-1) are partial, last tops it off
        payments = []
        remaining = grand_total
        for i in range(num_payments - 1):
            # Each intermediate payment is between 0.01 and remaining - 0.01
            # (ensure we still need more)
            if remaining <= Decimal("0.02"):
                break
            max_partial = remaining - Decimal("0.01")
            partial = draw(decimals(
                min_value=Decimal("0.01"),
                max_value=min(max_partial, Decimal("999999.99")),
                places=2,
                allow_nan=False,
                allow_infinity=False,
            ))
            payments.append(partial)
            remaining -= partial

        # Final payment covers the rest (possibly with overpay)
        overpay = draw(decimals(
            min_value=Decimal("0.00"),
            max_value=Decimal("50.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ))
        payments.append(remaining + overpay)

    return {
        "grand_total": grand_total,
        "payments": payments,
        "cumulative": sum(payments),
    }


@composite
def partial_payment_scenario(draw):
    """Generate a scenario where cumulative payments < grand_total (partial payment).

    Generates a grand_total and a list of payments that sum to less than grand_total.
    """
    grand_total = draw(decimals(
        min_value=Decimal("1.00"),
        max_value=Decimal("999999.99"),
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ))

    # Generate 1-5 payments that collectively < grand_total
    num_payments = draw(integers(min_value=1, max_value=5))

    payments = []
    # Total payments must be strictly less than grand_total
    max_total = grand_total - Decimal("0.01")

    if max_total <= Decimal("0.00"):
        # grand_total is 0.01 so no partial payment possible with > 0
        # Skip this case
        assume(False)

    for i in range(num_payments):
        remaining_budget = max_total - sum(payments)
        if remaining_budget <= Decimal("0.00"):
            break
        payment = draw(decimals(
            min_value=Decimal("0.01"),
            max_value=min(remaining_budget, Decimal("999999.99")),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ))
        payments.append(payment)

    assume(len(payments) > 0)
    assume(sum(payments) < grand_total)

    return {
        "grand_total": grand_total,
        "payments": payments,
        "cumulative": sum(payments),
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _setup_test_entities(
    db_session,
    grand_total: Decimal,
    payments: List[Decimal],
) -> Tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Create tenant, client, sales order, invoice, and payment records.

    Returns (tenant_id, sales_order_id, invoice_id).
    """
    tenant_id = uuid.uuid4()
    client_id = uuid.uuid4()
    sales_order_id = uuid.uuid4()
    invoice_id = uuid.uuid4()

    # Create tenant
    tenant = TenantModel(
        id=tenant_id,
        name="Test Tenant",
        slug=f"test-{tenant_id.hex[:8]}",
        is_active=True,
    )
    db_session.add(tenant)

    # Create client
    client = ClientModel(
        id=client_id,
        tenant_id=tenant_id,
        code=f"CLI-{client_id.hex[:8]}",
        name="Test Client",
        is_active=True,
    )
    db_session.add(client)

    # Create sales order in INVOICED status
    sales_order = SalesOrderModel(
        id=sales_order_id,
        tenant_id=tenant_id,
        order_number=f"SO-{sales_order_id.hex[:8]}",
        client_id=client_id,
        order_date=date.today().isoformat(),
        delivery_date=date.today().isoformat(),
        status="INVOICED",
        payment_status="PENDING",
        grand_total=float(grand_total),
        subtotal=float(grand_total),
        is_deleted=False,
    )
    db_session.add(sales_order)

    # Create invoice linked to the sales order
    invoice = InvoiceModel(
        id=invoice_id,
        tenant_id=tenant_id,
        invoice_number=f"INV-{invoice_id.hex[:8]}",
        sales_order_id=sales_order_id,
        client_id=client_id,
        client_name="Test Client",
        status="SENT",
        invoice_date=date.today(),
        due_date=date.today(),
        grand_total=float(grand_total),
        subtotal=float(grand_total),
        is_deleted=False,
    )
    db_session.add(invoice)

    # Create payment records
    for i, amount in enumerate(payments):
        payment = PaymentModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            payment_number=f"PAY-{uuid.uuid4().hex[:8]}",
            invoice_id=invoice_id,
            client_id=client_id,
            amount=float(amount),
            payment_date=date.today(),
            payment_method="BANK_TRANSFER",
        )
        db_session.add(payment)

    await db_session.flush()

    return tenant_id, sales_order_id, invoice_id


# ─────────────────────────────────────────────────────────────────────────────
# Property 4: Payment Completion Threshold
#
# Sub-property A: SO transitions to COMPLETED iff cumulative payments >= grand_total
# Sub-property B: SO remains INVOICED when cumulative payments < grand_total
# ─────────────────────────────────────────────────────────────────────────────


class TestPaymentCompletionThreshold:
    """**Validates: Requirements 3.4, 3.5, 3.6**

    Property 4: Payment Completion Threshold.
    """

    @given(data=full_payment_scenario())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_full_payment_transitions_so_to_completed(
        self,
        data: dict,
        db_session,
    ):
        """Property 4A: SO SHALL transition to COMPLETED when cumulative
        payments >= grand_total.

        **Validates: Requirements 3.4, 3.6**
        """
        grand_total = data["grand_total"]
        payments = data["payments"]
        cumulative = data["cumulative"]

        # Precondition: cumulative >= grand_total
        assert cumulative >= grand_total

        try:
            tenant_id, sales_order_id, invoice_id = await _setup_test_entities(
                db_session, grand_total, payments
            )

            # Execute the workflow orchestration with mocked notification service
            service = WorkflowOrchestrationService(db_session)
            service.notification_service = AsyncMock()
            result = await service.on_payment_received(
                tenant_id=tenant_id,
                sales_order_id=sales_order_id,
                payment_amount=payments[-1],  # The last payment triggers evaluation
            )

            # Verify SO transitioned to COMPLETED
            so = await db_session.get(SalesOrderModel, sales_order_id)
            assert so is not None

            assert so.status == "COMPLETED", (
                f"Expected SO to be COMPLETED when cumulative ({cumulative}) >= "
                f"grand_total ({grand_total}), but got status={so.status}"
            )

            # Verify result indicates fully paid
            assert result["fully_paid"] is True
        finally:
            await db_session.rollback()

    @given(data=partial_payment_scenario())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_partial_payment_leaves_so_in_invoiced(
        self,
        data: dict,
        db_session,
    ):
        """Property 4B: SO SHALL remain in INVOICED status when cumulative
        payments < grand_total.

        **Validates: Requirements 3.5**
        """
        grand_total = data["grand_total"]
        payments = data["payments"]
        cumulative = data["cumulative"]

        # Precondition: cumulative < grand_total
        assert cumulative < grand_total

        try:
            tenant_id, sales_order_id, invoice_id = await _setup_test_entities(
                db_session, grand_total, payments
            )

            # Execute the workflow orchestration with mocked notification service
            service = WorkflowOrchestrationService(db_session)
            service.notification_service = AsyncMock()
            result = await service.on_payment_received(
                tenant_id=tenant_id,
                sales_order_id=sales_order_id,
                payment_amount=payments[-1],  # The last payment triggers evaluation
            )

            # Verify SO remains in INVOICED
            so = await db_session.get(SalesOrderModel, sales_order_id)
            assert so is not None

            assert so.status == "INVOICED", (
                f"Expected SO to remain INVOICED when cumulative ({cumulative}) < "
                f"grand_total ({grand_total}), but got status={so.status}"
            )

            # Verify result indicates not fully paid
            assert result["fully_paid"] is False
        finally:
            await db_session.rollback()

    @given(data=full_payment_scenario())
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_exact_payment_equals_grand_total_transitions(
        self,
        data: dict,
        db_session,
    ):
        """Property 4A (boundary): SO SHALL transition to COMPLETED when cumulative
        payments exactly equal grand_total.

        **Validates: Requirements 3.4, 3.6**
        """
        grand_total = data["grand_total"]

        # Override: use exactly one payment = grand_total (boundary case)
        payments = [grand_total]

        try:
            tenant_id, sales_order_id, invoice_id = await _setup_test_entities(
                db_session, grand_total, payments
            )

            service = WorkflowOrchestrationService(db_session)
            service.notification_service = AsyncMock()
            result = await service.on_payment_received(
                tenant_id=tenant_id,
                sales_order_id=sales_order_id,
                payment_amount=grand_total,
            )

            # Verify SO transitioned to COMPLETED at exact boundary
            so = await db_session.get(SalesOrderModel, sales_order_id)
            assert so is not None

            assert so.status == "COMPLETED", (
                f"Expected SO to be COMPLETED at exact boundary "
                f"(payment={grand_total} == grand_total={grand_total}), "
                f"but got status={so.status}"
            )

            assert result["fully_paid"] is True
        finally:
            await db_session.rollback()

    @given(data=partial_payment_scenario())
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_subsequent_partials_accumulate_correctly(
        self,
        data: dict,
        db_session,
    ):
        """Property 4B (multi-payment): Multiple partial payments that don't
        reach grand_total SHALL leave SO in INVOICED status.

        **Validates: Requirements 3.5, 3.6**
        """
        grand_total = data["grand_total"]
        payments = data["payments"]
        cumulative = data["cumulative"]

        assume(len(payments) >= 2)
        assert cumulative < grand_total

        try:
            tenant_id, sales_order_id, invoice_id = await _setup_test_entities(
                db_session, grand_total, payments
            )

            # Execute the workflow orchestration (simulating the last payment trigger)
            service = WorkflowOrchestrationService(db_session)
            service.notification_service = AsyncMock()
            result = await service.on_payment_received(
                tenant_id=tenant_id,
                sales_order_id=sales_order_id,
                payment_amount=payments[-1],
            )

            # Verify SO remains in INVOICED
            so = await db_session.get(SalesOrderModel, sales_order_id)
            assert so is not None

            assert so.status == "INVOICED", (
                f"Expected SO to remain INVOICED with {len(payments)} partial payments "
                f"(cumulative={cumulative} < grand_total={grand_total}), "
                f"but got status={so.status}"
            )

            # Verify cumulative tracking is correct
            assert Decimal(str(result["cumulative_paid"])) == cumulative
            assert result["fully_paid"] is False
        finally:
            await db_session.rollback()
