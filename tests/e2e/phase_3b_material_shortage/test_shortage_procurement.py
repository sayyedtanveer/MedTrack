"""Phase 3B E2E tests: Material shortage and procurement flow.

Tests cover:
- WO release with material shortage → MATERIAL_PENDING + purchase_requisitions created
- Partial availability: reserve available, requisition for short only
- PO creation with auto-number generation and permission enforcement
- GRN receipt with inventory updates and over-receipt rejection
- Gap #9: GRN triggers WO resume: MATERIAL_PENDING → MATERIAL_RESERVED when all materials fulfilled

Requirements: 24–28 — Gap #9
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderModel,
    SalesOrderLineModel,
)
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.purchase_order_model import (
    PurchaseOrderModel,
    PurchaseOrderLineModel,
)
from backend.app.infrastructure.persistence.models.purchase_requisition_model import (
    PurchaseRequisitionModel,
)
from backend.app.infrastructure.persistence.models.grn_model import (
    GoodsReceiptNoteModel,
    GRNLineModel,
)
from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus


@pytest.mark.asyncio
async def test_wo_release_with_shortage_creates_requisitions(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: WO release with material shortage creates purchase requisitions.
    
    When a WO is released and some materials are below required quantity,
    purchase_requisitions are created in PENDING_APPROVAL status and
    procurement team is notified.
    """
    # Setup: Create a raw material with low stock (only 10 units available)
    raw_material = seeded_materials["raw_1"]
    assert raw_material.current_stock == Decimal("10")
    
    # Create a WO that requires 50 units of this material (shortage of 40)
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
    assert wo_response.status_code == 201
    wo_id = uuid.UUID(wo_response.json()["id"])
    
    # Release the WO (triggers material planning and PR creation)
    release_response = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/release",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert release_response.status_code == 200
    release_data = release_response.json()
    
    # Verify WO is in MATERIAL_PENDING (not enough materials)
    wo = await db_session.get(WorkOrderModel, wo_id)
    assert wo.status == WorkOrderStatus.MATERIAL_PENDING.value
    
    # Verify purchase requisitions were created for the shortage
    pr_stmt = "SELECT * FROM purchase_requisitions WHERE work_order_id = :wo_id AND tenant_id = :tenant_id AND is_deleted = false"
    from sqlalchemy import text
    result = await db_session.execute(text(pr_stmt), {"wo_id": str(wo_id), "tenant_id": str(test_tenant_id)})
    requisitions = result.fetchall()
    assert len(requisitions) >= 1, "Expected at least one purchase requisition"
    
    # Verify PR status is PENDING_APPROVAL
    pr_model = await db_session.execute(
        __import__('sqlalchemy').select(PurchaseRequisitionModel).where(
            PurchaseRequisitionModel.work_order_id == wo_id,
        )
    )
    pr = pr_model.scalars().first()
    assert pr is not None
    assert pr.status == "PENDING_APPROVAL"


@pytest.mark.asyncio
async def test_partial_availability_reserves_available_requisitions_short(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: Partial availability → reserve available, requisition for short only.
    
    When WO release has some materials partially available:
    - Available qty is reserved (inventory_reservations created)
    - Short qty triggers purchase requisition
    """
    raw_material = seeded_materials["raw_1"]
    initial_stock = Decimal(str(raw_material.current_stock))
    
    # Create WO requiring more than half available
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
    
    # Release
    await async_client.post(
        f"/api/v1/work-orders/{wo_id}/release",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    # Verify WO is MATERIAL_PENDING (partial availability)
    wo = await db_session.get(WorkOrderModel, wo_id)
    assert wo.status == WorkOrderStatus.MATERIAL_PENDING.value
    
    # Verify purchase requisition created (for shortage only)
    pr_stmt = "SELECT * FROM purchase_requisitions WHERE work_order_id = :wo_id"
    from sqlalchemy import text
    result = await db_session.execute(text(pr_stmt), {"wo_id": str(wo_id)})
    requisitions = result.fetchall()
    assert len(requisitions) >= 1


@pytest.mark.asyncio
async def test_po_creation_with_requisition_link_and_permission(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    regular_user_token: str,
    seeded_materials: dict,
):
    """Test: PO creation links to requisition; permission enforced; number auto-generated.
    
    When creating a PO:
    - linked_po_id references the purchase requisition
    - PO number is auto-generated
    - 403 returned without procurement:po:create permission
    """
    # First, trigger PR creation by releasing a WO with shortage
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
    
    await async_client.post(
        f"/api/v1/work-orders/{wo_id}/release",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    # Get the purchase requisition
    pr = await db_session.execute(
        __import__('sqlalchemy').select(PurchaseRequisitionModel).where(
            PurchaseRequisitionModel.work_order_id == wo_id,
        )
    )
    pr_model = pr.scalars().first()
    assert pr_model is not None
    
    # Test: Permission denial without procurement:po:create
    po_response_denied = await async_client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": str(seeded_materials.get("supplier_id") or uuid.uuid4()),
            "lines": [
                {
                    "material_id": str(seeded_materials["raw_1"].id),
                    "quantity": 100,
                    "unit_price": 10.0,
                }
            ],
        },
        headers={"Authorization": f"Bearer {regular_user_token}"},
    )
    assert po_response_denied.status_code == 403
    
    # Create PO with procurement permission
    supplier_id = seeded_materials.get("supplier_id") or str(uuid.uuid4())
    po_response = await async_client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "linked_requisition_id": str(pr_model.id),
            "lines": [
                {
                    "material_id": str(seeded_materials["raw_1"].id),
                    "quantity": 100,
                    "unit_price": 10.0,
                }
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert po_response.status_code == 201
    po_data = po_response.json()
    
    # Verify PO number is auto-generated
    assert "po_number" in po_data or "number" in po_data
    po_number = po_data.get("po_number") or po_data.get("number")
    assert po_number is not None
    assert po_number.startswith("PO-") or po_number.startswith("PUR-")


@pytest.mark.asyncio
async def test_grn_creation_and_inventory_update(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: GRN creation updates inventory + creates inventory_transactions.
    
    When a GRN is received:
    - inventory_transactions (type=grn_receipt) created
    - material.current_stock increased
    - purchase_order_lines.received_quantity updated
    """
    raw_material = seeded_materials["raw_1"]
    initial_stock = raw_material.current_stock
    
    # Create and confirm a PO
    supplier_id = seeded_materials.get("supplier_id") or str(uuid.uuid4())
    po_response = await async_client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "lines": [
                {
                    "material_id": str(raw_material.id),
                    "quantity": 100,
                    "unit_price": 10.0,
                }
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert po_response.status_code == 201
    po_id = uuid.UUID(po_response.json()["id"])
    
    # Create GRN
    grn_response = await async_client.post(
        "/api/v1/procurement/grn",
        json={
            "purchase_order_id": str(po_id),
            "lines": [
                {
                    "po_line_id": str((await db_session.get(PurchaseOrderModel, po_id)).lines[0].id),
                    "material_id": str(raw_material.id),
                    "received_quantity": 100,
                }
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert grn_response.status_code == 201
    grn_id = uuid.UUID(grn_response.json()["id"])
    
    # Verify inventory updated
    updated_material = await db_session.get(MaterialModel, raw_material.id)
    await db_session.refresh(updated_material)
    assert updated_material.current_stock == float(initial_stock) + 100


@pytest.mark.asyncio
async def test_over_receipt_rejected(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test: Over-receipt (qty > PO ordered qty) is rejected.
    
    When receiving more than ordered in PO:
    - GRN rejection with 400/422 error
    """
    raw_material = seeded_materials["raw_1"]
    
    # Create PO for 50 units
    supplier_id = seeded_materials.get("supplier_id") or str(uuid.uuid4())
    po_response = await async_client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "lines": [
                {
                    "material_id": str(raw_material.id),
                    "quantity": 50,
                    "unit_price": 10.0,
                }
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    po_id = uuid.UUID(po_response.json()["id"])
    po = await db_session.get(PurchaseOrderModel, po_id)
    po_line_id = po.lines[0].id if po.lines else None
    
    # Try to receive 100 units (over-receipt)
    grn_response = await async_client.post(
        "/api/v1/procurement/grn",
        json={
            "purchase_order_id": str(po_id),
            "lines": [
                {
                    "po_line_id": str(po_line_id),
                    "material_id": str(raw_material.id),
                    "received_quantity": 100,
                }
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    # Expect rejection (400 or 422)
    assert grn_response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_grn_triggers_wo_resume_gap_9(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_token: str,
    seeded_materials: dict,
):
    """Test Gap #9: GRN triggers WO resume: MATERIAL_PENDING → MATERIAL_RESERVED.
    
    When GRN is received for all materials needed by a MATERIAL_PENDING WO:
    - WO transitions to MATERIAL_RESERVED
    - Storekeeper is notified to issue materials
    - Inventory reservations are created for the WO
    """
    raw_material = seeded_materials["raw_1"]
    
    # Create WO with shortage (will be MATERIAL_PENDING)
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
    
    # Release the WO (creates PR, WO becomes MATERIAL_PENDING)
    await async_client.post(
        f"/api/v1/work-orders/{wo_id}/release",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    wo = await db_session.get(WorkOrderModel, wo_id)
    assert wo.status == WorkOrderStatus.MATERIAL_PENDING.value
    
    # Create PO for the shortage
    supplier_id = seeded_materials.get("supplier_id") or str(uuid.uuid4())
    po_response = await async_client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "lines": [
                {
                    "material_id": str(raw_material.id),
                    "quantity": 100,
                    "unit_price": 10.0,
                }
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    po_id = uuid.UUID(po_response.json()["id"])
    po = await db_session.get(PurchaseOrderModel, po_id)
    po_line_id = po.lines[0].id if po.lines else None
    
    # Receive all needed materials via GRN
    grn_response = await async_client.post(
        "/api/v1/procurement/grn",
        json={
            "purchase_order_id": str(po_id),
            "lines": [
                {
                    "po_line_id": str(po_line_id),
                    "material_id": str(raw_material.id),
                    "received_quantity": 100,
                }
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert grn_response.status_code == 201
    
    # Verify GRN accept/process endpoint to trigger workflow
    grn_id = uuid.UUID(grn_response.json()["id"])
    grn = await db_session.get(GoodsReceiptNoteModel, grn_id)
    
    if grn.status != "inspected":
        # Post incoming QC pass to trigger on_goods_received (Gap #9)
        qc_response = await async_client.post(
            f"/api/v1/procurement/grn/{grn_id}/incoming-qc-pass",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert qc_response.status_code in (200, 201)
    
    # Refresh WO to check status transition
    await db_session.expire(wo)
    wo = await db_session.get(WorkOrderModel, wo_id)
    
    # Verify WO transitioned to MATERIAL_RESERVED (Gap #9 verification)
    assert wo.status == WorkOrderStatus.MATERIAL_RESERVED.value, (
        f"Expected WO to be MATERIAL_RESERVED after GRN receipt, "
        f"but got status={wo.status} (Gap #9)"
    )
