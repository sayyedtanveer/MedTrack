import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.application.finance.finance_service import FinanceService


@pytest.mark.asyncio
async def test_record_payment_triggers_workflow_for_full_invoice_settlement():
    session = AsyncMock()
    service = FinanceService(session)

    service.ensure_finance_setup = AsyncMock()
    service._next_payment_number = AsyncMock(return_value="PAY-001")

    invoice_id = uuid.uuid4()
    client_id = uuid.uuid4()
    sales_order_id = uuid.uuid4()
    invoice = SimpleNamespace(
        id=invoice_id,
        client_id=client_id,
        sales_order_id=sales_order_id,
        grand_total=100.0,
        paid_amount=0.0,
        invoice_number="INV-001",
        status="PENDING",
    )
    service._get_invoice = AsyncMock(return_value=invoice)
    service._post_customer_payment_entries = AsyncMock()

    workflow_service = AsyncMock()
    workflow_service.on_payment_received = AsyncMock(return_value={"fully_paid": True})

    with patch(
        "backend.app.application.manufacturing.services.workflow_orchestration_service.WorkflowOrchestrationService",
        return_value=workflow_service,
    ) as workflow_cls:
        payment = await service.record_payment(
            tenant_id=uuid.uuid4(),
            invoice_id=invoice_id,
            amount=100.0,
            payment_date=date.today(),
            payment_method="BANK_TRANSFER",
            created_by=uuid.uuid4(),
        )

    assert payment is not None
    workflow_cls.assert_called_once_with(session)
    workflow_service.on_payment_received.assert_awaited_once()
    assert workflow_service.on_payment_received.await_args.kwargs["sales_order_id"] == sales_order_id
    assert workflow_service.on_payment_received.await_args.kwargs["payment_amount"] == 100.0
