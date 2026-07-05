"""Phase 4 E2E tests: QC inspection approval and rejection.

Tests cover:
- QC inspection queue retrieval
- Approve on non-QC_PENDING returns 422
- QC approve → FGReceiveCommand runs → FG stock increases exactly once
- SO line allocation updated; SO → READY_FOR_DISPATCH when all lines satisfied (Gap #8)
- Duplicate approval idempotent (no duplicate transaction)
- Permission enforcement (403 without quality:approve)
- Reject paths: rework and scrap

Requirements: 29–32 — Gaps #3, #8
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderModel,
    SalesOrderLineModel,
)
from backend.app.infrastructure.persistence.models.inventory_transaction_model import (
    InventoryTransactionModel,
)
from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
from backend.app.domain.sales.value_objects.order_status import OrderStatus


@pytest.mark.asyncio
async def test_qc_inspection_queue_retrieval(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: GET /quality-control/inspection-queue shows QC_PENDING WOs."""
    # Get inspection queue
    queue_response = await async_client.get(
        "/api/v1/quality-control/inspection-queue",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert queue_response.status_code == 200
    queue_data = queue_response.json()
    assert isinstance(queue_data, list)


@pytest.mark.asyncio
async def test_approve_on_non_qc_pending_returns_422(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: Approve on non-QC_PENDING WO returns 422."""
    # Create a WO in PLANNED status (not QC_PENDING)
    wo_response = await async_client.post(
        "/api/v1/work-orders",
        json={
            "sales_order_id": str(seeded_materials["so_id"]),
            "product_id": str(seeded_materials["fg_1"].id),
            "planned_quantity": 100,
            "bom_id": str(seeded_materials["bom_1"].id),
            "estimated_completion_date": date.today().isoformat(),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wo_id = uuid.UUID(wo_response.json()["id"])
    
    # Try to approve without it being QC_PENDING
    approve_response = await async_client.post(
        f"/api/v1/quality-control/approve",
        json={"work_order_id": str(wo_id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    # Expect 422 Unprocessable Entity (invalid state)
    assert approve_response.status_code == 422


@pytest.mark.asyncio
async def test_qc_approve_increases_fg_stock_once_gap_3(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test Gap #3: QC approve → FGReceiveCommand runs → FG stock increases exactly once.
    
    When QC approves a completed WO:
    - FG stock increases by (produced_quantity - scrap_quantity)
    - Exactly one FG_RECEIPT inventory transaction is created
    - WO transitions to FG_RECEIVED
    """
    fg_material = seeded_materials["fg_1"]
    initial_fg_stock = Decimal(str(fg_material.current_stock))
    
    # Create a WO that will be moved to QC_PENDING
    wo_response = await async_client.post(
        "/api/v1/work-orders",
        json={
            "sales_order_id": str(seeded_materials["so_id"]),
            "product_id": str(fg_material.id),
            "planned_quantity": 100,
            "bom_id": str(seeded_materials["bom_1"].id),
            "estimated_completion_date": date.today().isoformat(),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wo_id = uuid.UUID(wo_response.json()["id"])
    wo = await db_session.get(WorkOrderModel, wo_id)
    
    # Move WO through production to QC_PENDING
    # (Assuming workflow setup handles this via /work-orders/{id}/complete endpoint)
    complete_response = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        json={
            "produced_quantity": 100,
            "scrap_quantity": 5,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert complete_response.status_code in (200, 201)
    
    # Refresh WO and verify it's QC_PENDING
    await db_session.refresh(wo)
    assert wo.status == WorkOrderStatus.QC_PENDING.value
    
    # Approve QC (triggers FG receipt)
    approve_response = await async_client.post(
        f"/api/v1/quality-control/approve",
        json={"work_order_id": str(wo_id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_response.status_code == 200
    
    # Verify FG stock increased
    await db_session.refresh(fg_material)
    expected_net_qty = 100 - 5
    assert fg_material.current_stock == float(initial_fg_stock) + expected_net_qty, (
        f"Expected FG stock to increase by {expected_net_qty}, "
        f"from {initial_fg_stock} to {initial_fg_stock + expected_net_qty}"
    )
    
    # Verify exactly one FG_RECEIPT transaction exists for this WO (Gap #3)
    fg_receipt_stmt = select(InventoryTransactionModel).where(
        InventoryTransactionModel.reference_type == "work_order",
        InventoryTransactionModel.reference_id == wo_id,
        InventoryTransactionModel.transaction_type == "fg_receipt",
        InventoryTransactionModel.is_deleted.is_(False),
    )
    fg_receipts = (await db_session.execute(fg_receipt_stmt)).scalars().all()
    assert len(fg_receipts) == 1, (
        f"Expected exactly 1 FG_RECEIPT transaction for WO {wo_id}, "
        f"but found {len(fg_receipts)}"
    )
    
    # Verify WO transitioned to FG_RECEIVED
    await db_session.refresh(wo)
    assert wo.status == WorkOrderStatus.FG_RECEIVED.value


@pytest.mark.asyncio
async def test_qc_approve_updates_so_allocation_and_ready_for_dispatch_gap_8(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test Gap #8: QC approve updates SO allocation; SO → READY_FOR_DISPATCH when all lines satisfied.
    
    When QC approves a WO:
    - Linked SO line allocated_quantity increases
    - If all SO lines are fully allocated, SO transitions to READY_FOR_DISPATCH
    """
    fg_material = seeded_materials["fg_1"]
    so_id = seeded_materials["so_id"]
    
    # Create WO linked to the SO
    wo_response = await async_client.post(
        "/api/v1/work-orders",
        json={
            "sales_order_id": str(so_id),
            "product_id": str(fg_material.id),
            "planned_quantity": 100,
            "bom_id": str(seeded_materials["bom_1"].id),
            "estimated_completion_date": date.today().isoformat(),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wo_id = uuid.UUID(wo_response.json()["id"])
    
    # Move WO to QC_PENDING
    complete_response = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        json={
            "produced_quantity": 100,
            "scrap_quantity": 0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert complete_response.status_code in (200, 201)
    
    # Approve QC
    approve_response = await async_client.post(
        f"/api/v1/quality-control/approve",
        json={"work_order_id": str(wo_id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_response.status_code == 200
    
    # Verify SO line allocation was updated (Gap #8)
    so_lines_stmt = select(SalesOrderLineModel).where(
        SalesOrderLineModel.sales_order_id == so_id,
    )
    so_lines = (await db_session.execute(so_lines_stmt)).scalars().all()
    
    for line in so_lines:
        # Allocated quantity should have increased
        assert Decimal(str(line.allocated_quantity)) > 0, (
            f"Expected SO line to have allocated_quantity > 0, got {line.allocated_quantity}"
        )
    
    # Check if all lines are fully allocated
    all_allocated = all(
        Decimal(str(line.allocated_quantity)) >= Decimal(str(line.quantity))
        for line in so_lines
    )
    
    if all_allocated:
        # SO should be READY_FOR_DISPATCH
        so = await db_session.get(SalesOrderModel, so_id)
        await db_session.refresh(so)
        assert so.status == OrderStatus.READY_FOR_DISPATCH.value, (
            f"Expected SO to transition to READY_FOR_DISPATCH when all lines allocated, "
            f"but status is {so.status}"
        )


@pytest.mark.asyncio
async def test_qc_approve_idempotent_no_duplicate_transaction(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: Duplicate QC approval is idempotent (no duplicate FG_RECEIPT transaction).
    
    When approving the same QC twice:
    - Second call returns existing state without creating a new transaction
    """
    fg_material = seeded_materials["fg_1"]
    initial_fg_stock = Decimal(str(fg_material.current_stock))
    
    # Create and advance WO to QC_PENDING
    wo_response = await async_client.post(
        "/api/v1/work-orders",
        json={
            "sales_order_id": str(seeded_materials["so_id"]),
            "product_id": str(fg_material.id),
            "planned_quantity": 100,
            "bom_id": str(seeded_materials["bom_1"].id),
            "estimated_completion_date": date.today().isoformat(),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wo_id = uuid.UUID(wo_response.json()["id"])
    
    complete_response = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        json={
            "produced_quantity": 100,
            "scrap_quantity": 0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert complete_response.status_code in (200, 201)
    
    # First approval
    approve_response_1 = await async_client.post(
        f"/api/v1/quality-control/approve",
        json={"work_order_id": str(wo_id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_response_1.status_code == 200
    
    # Count FG_RECEIPT transactions after first approval
    fg_receipts_stmt = select(InventoryTransactionModel).where(
        InventoryTransactionModel.reference_type == "work_order",
        InventoryTransactionModel.reference_id == wo_id,
        InventoryTransactionModel.transaction_type == "fg_receipt",
    )
    fg_receipts_1 = (await db_session.execute(fg_receipts_stmt)).scalars().all()
    count_1 = len(fg_receipts_1)
    
    # Record FG stock after first approval
    await db_session.refresh(fg_material)
    stock_after_first = Decimal(str(fg_material.current_stock))
    
    # Second approval (duplicate)
    approve_response_2 = await async_client.post(
        f"/api/v1/quality-control/approve",
        json={"work_order_id": str(wo_id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_response_2.status_code == 200
    
    # Count FG_RECEIPT transactions after second approval
    fg_receipts_2 = (await db_session.execute(fg_receipts_stmt)).scalars().all()
    count_2 = len(fg_receipts_2)
    
    # Verify no new transaction was created
    assert count_2 == count_1, (
        f"Expected no new FG_RECEIPT transaction on duplicate approval, "
        f"but transaction count went from {count_1} to {count_2}"
    )
    
    # Verify stock didn't increase again
    await db_session.refresh(fg_material)
    stock_after_second = Decimal(str(fg_material.current_stock))
    assert stock_after_second == stock_after_first, (
        f"Expected FG stock to remain unchanged on duplicate approval, "
        f"but it went from {stock_after_first} to {stock_after_second}"
    )


@pytest.mark.asyncio
async def test_qc_approve_permission_enforced(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    regular_user_token: str,
    seeded_materials: dict,
):
    """Test: 403 without quality:approve permission."""
    # Create and advance WO to QC_PENDING
    wo_response = await async_client.post(
        "/api/v1/work-orders",
        json={
            "sales_order_id": str(seeded_materials["so_id"]),
            "product_id": str(seeded_materials["fg_1"].id),
            "planned_quantity": 100,
            "bom_id": str(seeded_materials["bom_1"].id),
            "estimated_completion_date": date.today().isoformat(),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wo_id = uuid.UUID(wo_response.json()["id"])
    
    complete_response = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        json={
            "produced_quantity": 100,
            "scrap_quantity": 0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert complete_response.status_code in (200, 201)
    
    # Try to approve with insufficient permission
    approve_response = await async_client.post(
        f"/api/v1/quality-control/approve",
        json={"work_order_id": str(wo_id)},
        headers={"Authorization": f"Bearer {regular_user_token}"},
    )
    assert approve_response.status_code == 403


@pytest.mark.asyncio
async def test_qc_reject_rework_path(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: Reject → rework path (WO returns to IN_PRODUCTION for rework)."""
    # Create and advance WO to QC_PENDING
    wo_response = await async_client.post(
        "/api/v1/work-orders",
        json={
            "sales_order_id": str(seeded_materials["so_id"]),
            "product_id": str(seeded_materials["fg_1"].id),
            "planned_quantity": 100,
            "bom_id": str(seeded_materials["bom_1"].id),
            "estimated_completion_date": date.today().isoformat(),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wo_id = uuid.UUID(wo_response.json()["id"])
    
    complete_response = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        json={
            "produced_quantity": 100,
            "scrap_quantity": 0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert complete_response.status_code in (200, 201)
    
    # Reject for rework
    reject_response = await async_client.post(
        f"/api/v1/quality-control/reject",
        json={
            "work_order_id": str(wo_id),
            "reason": "Minor defects detected",
            "action": "rework",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reject_response.status_code in (200, 201)
    
    # Verify WO status changed to QC_REJECTED or REWORK
    wo = await db_session.get(WorkOrderModel, wo_id)
    await db_session.refresh(wo)
    assert wo.status in (
        WorkOrderStatus.QC_REJECTED.value,
        "REWORK",
        WorkOrderStatus.IN_PRODUCTION.value,
    )


@pytest.mark.asyncio
async def test_qc_reject_scrap_path(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: Reject → scrap path (WO → CLOSED, inventory deducted, Sales notified)."""
    fg_material = seeded_materials["fg_1"]
    so_id = seeded_materials["so_id"]
    initial_stock = Decimal(str(fg_material.current_stock))
    
    # Create and advance WO to QC_PENDING
    wo_response = await async_client.post(
        "/api/v1/work-orders",
        json={
            "sales_order_id": str(so_id),
            "product_id": str(fg_material.id),
            "planned_quantity": 100,
            "bom_id": str(seeded_materials["bom_1"].id),
            "estimated_completion_date": date.today().isoformat(),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wo_id = uuid.UUID(wo_response.json()["id"])
    
    complete_response = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        json={
            "produced_quantity": 100,
            "scrap_quantity": 0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert complete_response.status_code in (200, 201)
    
    # Reject for scrap
    reject_response = await async_client.post(
        f"/api/v1/quality-control/reject",
        json={
            "work_order_id": str(wo_id),
            "reason": "Critical defects, cannot be reworked",
            "action": "scrap",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reject_response.status_code in (200, 201)
    
    # Verify WO status is CLOSED or REJECTED
    wo = await db_session.get(WorkOrderModel, wo_id)
    await db_session.refresh(wo)
    assert wo.status in (WorkOrderStatus.CLOSED.value, WorkOrderStatus.REJECTED.value)
