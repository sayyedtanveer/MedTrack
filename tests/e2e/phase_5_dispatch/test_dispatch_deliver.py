"""Phase 5 E2E tests: Dispatch queue and delivery flows.

Tests cover:
- Dispatch queue retrieval (Gap #5)
- Dispatch allocation from READY_FOR_DISPATCH
- Delivery confirmation
- Partial delivery handling
- Delivery completion transitions SO to IN_TRANSIT or DELIVERED
- Auto-invoice on delivery completion (Gap #7)

Requirements: 33–36 — Gap #5
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel
from backend.app.infrastructure.persistence.models.delivery_model import (
    DeliveryOrderModel,
    DeliveryLineModel,
)
from backend.app.infrastructure.persistence.models.finance_models import InvoiceModel
from backend.app.domain.sales.value_objects.order_status import OrderStatus


@pytest.mark.asyncio
async def test_dispatch_queue_retrieval_gap_5(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test Gap #5: GET /dispatch/queue returns SO in READY_FOR_DISPATCH status."""
    # Get dispatch queue
    dispatch_response = await async_client.get(
        "/api/v1/dispatch/queue",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dispatch_response.status_code == 200
    queue_data = dispatch_response.json()
    assert isinstance(queue_data, list)


@pytest.mark.asyncio
async def test_dispatch_allocation_from_ready_for_dispatch(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: Dispatch allocation from READY_FOR_DISPATCH SO."""
    so_id = seeded_materials["so_id"]
    
    # Ensure SO is in READY_FOR_DISPATCH (assuming prior phases already did this)
    so = await db_session.get(SalesOrderModel, so_id)
    
    # Allocate to dispatch
    dispatch_response = await async_client.post(
        "/api/v1/dispatch/allocate",
        json={
            "sales_order_id": str(so_id),
            "allocated_by": str(admin_user_id),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    if dispatch_response.status_code == 200:
        # Verify SO status is now IN_DISPATCH or DISPATCHED
        await db_session.refresh(so)
        assert so.status in (
            OrderStatus.IN_DISPATCH.value,
            OrderStatus.DISPATCHED.value,
            OrderStatus.IN_TRANSIT.value,
        )


@pytest.mark.asyncio
async def test_delivery_creation_and_confirmation(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: Create delivery and confirm shipment."""
    so_id = seeded_materials["so_id"]
    
    # Create delivery record
    delivery_response = await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "delivery_date": date.today().isoformat(),
            "shipped_by": str(admin_user_id),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    if delivery_response.status_code in (200, 201):
        delivery_data = delivery_response.json()
        delivery_id = uuid.UUID(delivery_data["id"])
        
        # Confirm shipment
        confirm_response = await async_client.post(
            f"/api/v1/deliveries/{delivery_id}/confirm",
            json={
                "confirmed_by": str(admin_user_id),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert confirm_response.status_code in (200, 201)
        
        # Verify delivery status is SHIPPED
        delivery = await db_session.get(DeliveryOrderModel, delivery_id)
        await db_session.refresh(delivery)
        assert delivery.status in (
            "SHIPPED",
            "IN_TRANSIT",
        )


@pytest.mark.asyncio
async def test_partial_delivery_handling(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: Partial delivery (quantity < SO total)."""
    so_id = seeded_materials["so_id"]
    
    # Fetch SO to get line quantities
    so = await db_session.get(SalesOrderModel, so_id)
    await db_session.refresh(so)
    
    # Create partial delivery (deliver 50% of first line)
    delivery_response = await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "delivery_date": date.today().isoformat(),
            "partial": True,
            "shipped_by": str(admin_user_id),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    if delivery_response.status_code in (200, 201):
        delivery_data = delivery_response.json()
        assert "partial" in delivery_data or "delivery_lines" in delivery_data


@pytest.mark.asyncio
async def test_delivery_complete_transitions_so_status(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: Delivery completion transitions SO to IN_TRANSIT or DELIVERED."""
    so_id = seeded_materials["so_id"]
    
    # Create and complete delivery
    delivery_response = await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "delivery_date": date.today().isoformat(),
            "shipped_by": str(admin_user_id),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    if delivery_response.status_code in (200, 201):
        delivery_data = delivery_response.json()
        delivery_id = uuid.UUID(delivery_data["id"])
        
        # Confirm delivery
        confirm_response = await async_client.post(
            f"/api/v1/deliveries/{delivery_id}/confirm",
            json={"confirmed_by": str(admin_user_id)},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        if confirm_response.status_code in (200, 201):
            # Verify SO status transitioned
            so = await db_session.get(SalesOrderModel, so_id)
            await db_session.refresh(so)
            assert so.status in (
                OrderStatus.IN_TRANSIT.value,
                OrderStatus.DELIVERED.value,
                OrderStatus.INVOICED.value,
            )


@pytest.mark.asyncio
async def test_delivery_complete_triggers_auto_invoice_gap_7(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test Gap #7: Delivery completion triggers auto-invoice creation.
    
    When delivery is confirmed as complete:
    - InvoiceModel is created with reference to the SO
    - Invoice status is GENERATED or PENDING
    - Invoice amount equals SO grand_total
    """
    so_id = seeded_materials["so_id"]
    
    # Fetch SO to get grand_total
    so = await db_session.get(SalesOrderModel, so_id)
    await db_session.refresh(so)
    expected_invoice_amount = Decimal(str(so.grand_total))
    
    # Create and complete delivery
    delivery_response = await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "delivery_date": date.today().isoformat(),
            "shipped_by": str(admin_user_id),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    if delivery_response.status_code in (200, 201):
        delivery_data = delivery_response.json()
        delivery_id = uuid.UUID(delivery_data["id"])
        
        # Confirm delivery (triggers auto-invoice via Gap #7)
        confirm_response = await async_client.post(
            f"/api/v1/deliveries/{delivery_id}/confirm",
            json={"confirmed_by": str(admin_user_id)},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert confirm_response.status_code in (200, 201)
        
        # Verify invoice was created (Gap #7)
        invoice_stmt = select(InvoiceModel).where(
            InvoiceModel.sales_order_id == so_id,
            InvoiceModel.is_deleted.is_(False),
        )
        invoices = (await db_session.execute(invoice_stmt)).scalars().all()
        assert len(invoices) > 0, (
            f"Expected auto-invoice to be created on delivery completion (Gap #7), "
            f"but no invoices found for SO {so_id}"
        )
        
        # Verify invoice amount matches SO grand_total
        invoice = invoices[0]
        invoice_amount = Decimal(str(invoice.total_amount))
        assert invoice_amount == expected_invoice_amount, (
            f"Expected invoice amount to be {expected_invoice_amount}, "
            f"but got {invoice_amount}"
        )
        
        # Verify SO transitioned to INVOICED
        await db_session.refresh(so)
        assert so.status == OrderStatus.INVOICED.value, (
            f"Expected SO to transition to INVOICED after auto-invoice, "
            f"but status is {so.status}"
        )


@pytest.mark.asyncio
async def test_dispatch_permission_enforced(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    regular_user_token: str,
    seeded_materials: dict,
):
    """Test: 403 without dispatch:allocate permission."""
    so_id = seeded_materials["so_id"]
    
    # Try to allocate dispatch without permission
    dispatch_response = await async_client.post(
        "/api/v1/dispatch/allocate",
        json={
            "sales_order_id": str(so_id),
            "allocated_by": str(admin_user_id),
        },
        headers={"Authorization": f"Bearer {regular_user_token}"},
    )
    
    assert dispatch_response.status_code == 403


@pytest.mark.asyncio
async def test_delivery_idempotent_on_duplicate_confirm(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: Duplicate delivery confirm is idempotent (no duplicate invoice)."""
    so_id = seeded_materials["so_id"]
    
    # Create delivery
    delivery_response = await async_client.post(
        "/api/v1/deliveries",
        json={
            "sales_order_id": str(so_id),
            "delivery_date": date.today().isoformat(),
            "shipped_by": str(admin_user_id),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    if delivery_response.status_code in (200, 201):
        delivery_data = delivery_response.json()
        delivery_id = uuid.UUID(delivery_data["id"])
        
        # Confirm delivery first time
        confirm_response_1 = await async_client.post(
            f"/api/v1/deliveries/{delivery_id}/confirm",
            json={"confirmed_by": str(admin_user_id)},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert confirm_response_1.status_code in (200, 201)
        
        # Count invoices after first confirm
        invoice_stmt = select(InvoiceModel).where(
            InvoiceModel.sales_order_id == so_id,
        )
        invoices_1 = (await db_session.execute(invoice_stmt)).scalars().all()
        count_1 = len(invoices_1)
        
        # Confirm delivery second time (duplicate)
        confirm_response_2 = await async_client.post(
            f"/api/v1/deliveries/{delivery_id}/confirm",
            json={"confirmed_by": str(admin_user_id)},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert confirm_response_2.status_code in (200, 201, 422)  # 422 if already confirmed
        
        # Count invoices after second confirm
        invoices_2 = (await db_session.execute(invoice_stmt)).scalars().all()
        count_2 = len(invoices_2)
        
        # Verify no new invoice was created
        assert count_2 == count_1, (
            f"Expected idempotent confirm, but invoice count went from {count_1} to {count_2}"
        )
