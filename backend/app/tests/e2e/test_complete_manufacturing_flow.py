"""
E2E Tests for Complete Manufacturing Flow (Phases 0-8)
Tests all operational hardening phases with multiple validation criteria.
"""
import pytest
from httpx import AsyncClient
import uuid
from datetime import date, datetime


@pytest.mark.asyncio
async def test_complete_manufacturing_flow_happy_path(async_client: AsyncClient, token_headers: dict):
    """
    E2E Test: Complete Manufacturing Flow - Happy Path
    Validates: WO lifecycle, inventory mutations, QC, delivery, documents
    """
    # 1. Setup: Create tenant, user, materials, product, BOM
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Create material
    material_resp = await async_client.post(
        "/api/v1/materials",
        json={
            "code": "RM-001",
            "name": "Raw Material A",
            "description": "Test raw material",
            "unit_of_measure": "KG",
            "unit_cost": 10.0,
            "reorder_level": 100.0
        },
        headers=token_headers
    )
    assert material_resp.status_code == 201
    material_id = material_resp.json()["id"]
    unit_id = material_resp.json()["unit_id"]
    
    # Create product
    product_resp = await async_client.post(
        "/api/v1/products",
        json={
            "code": "FG-001",
            "name": "Finished Product A",
            "description": "Test finished product",
            "unit_of_measure": "PCS",
            "unit_cost": 50.0
        },
        headers=token_headers
    )
    assert product_resp.status_code == 201
    product_id = product_resp.json()["id"]
    
    # Create operation
    operation_resp = await async_client.post(
        "/api/v1/operations",
        json={
            "code": "OP-001",
            "name": "Assembly",
            "description": "Assembly operation",
            "process_type": "assembly",
            "estimated_time_hours": 2.0,
            "estimated_labor_cost": 50.0
        },
        headers=token_headers
    )
    assert operation_resp.status_code == 201
    operation_id = operation_resp.json()["id"]
    
    # Create BOM
    bom_resp = await async_client.post(
        "/api/v1/boms",
        json={
            "version": "v1.0",
            "valid_from": datetime.utcnow().isoformat(),
            "product_id": product_id,
            "lines": [
                {
                    "material_id": material_id,
                    "quantity": 2.0,
                    "unit_id": unit_id,
                    "scrap_percentage": 5.0
                }
            ],
            "operations": [operation_id]
        },
        headers=token_headers
    )
    assert bom_resp.status_code == 201
    bom_id = bom_resp.json()["id"]
    
    # 2. Initial stock for material
    stock_resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "material_id": material_id,
            "unit_id": unit_id,
            "transaction_type": "adjustment",
            "quantity": 1000.0,
            "remarks": "Initial stock for E2E test"
        },
        headers=token_headers
    )
    assert stock_resp.status_code == 200
    
    # 3. Create Work Order (PLANNED)
    wo_resp = await async_client.post(
        "/api/v1/work-orders",
        json={
            "product_id": product_id,
            "bom_id": bom_id,
            "planned_quantity": 100.0,
            "start_date": "2026-05-12",
            "due_date": "2026-05-20",
            "priority": "NORMAL",
            "notes": "E2E Test WO"
        },
        headers=token_headers
    )
    assert wo_resp.status_code == 201
    wo_id = wo_resp.json()["id"]
    wo_number = wo_resp.json()["wo_number"]
    assert wo_resp.json()["status"] == "PLANNED"
    
    # 4. Release WO (PLANNED -> RELEASED)
    release_resp = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/release",
        headers=token_headers
    )
    assert release_resp.status_code == 200
    assert release_resp.json()["status"] == "RELEASED"
    
    # 5. Reserve Stock (RELEASED -> MATERIAL_RESERVED)
    reserve_resp = await async_client.post(
        "/api/v1/storekeeper/reserve-stock",
        json={
            "work_order_id": wo_id,
            "material_id": material_id,
            "quantity": 200.0,
            "unit_id": unit_id
        },
        headers=token_headers
    )
    assert reserve_resp.status_code == 200
    
    # Verify reservation
    wo_resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    wo = wo_resp.json()
    assert wo["status"] == "MATERIAL_RESERVED"
    assert float(wo["materials"][0]["reserved_quantity"]) == 200.0
    
    # 6. Issue Stock (MATERIAL_RESERVED -> MATERIAL_ISSUED)
    issue_resp = await async_client.post(
        "/api/v1/storekeeper/issue-stock",
        json={
            "work_order_id": wo_id,
            "material_id": material_id,
            "quantity": 200.0,
            "unit_id": unit_id
        },
        headers=token_headers
    )
    assert issue_resp.status_code == 200
    
    # Verify issue
    wo_resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    wo = wo_resp.json()
    assert wo["status"] == "MATERIAL_ISSUED"
    assert float(wo["materials"][0]["issued_quantity"]) == 200.0
    assert float(wo["materials"][0]["reserved_quantity"]) == 0.0
    
    # 7. Start Production (MATERIAL_ISSUED -> IN_PRODUCTION)
    start_resp = await async_client.post(
        "/api/v1/worker/start-operation",
        json={
            "work_order_id": wo_id,
            "operation_id": operation_id,
            "assigned_to": user_id
        },
        headers=token_headers
    )
    assert start_resp.status_code == 200
    
    wo_resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    assert wo_resp.json()["status"] == "IN_PRODUCTION"
    
    # 8. Record Production
    record_resp = await async_client.post(
        "/api/v1/worker/record-production",
        json={
            "work_order_id": wo_id,
            "produced_quantity": 100.0,
            "scrap_quantity": 5.0,
            "notes": "E2E production record"
        },
        headers=token_headers
    )
    assert record_resp.status_code == 200
    
    wo_resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    assert float(wo_resp.json()["produced_quantity"]) == 100.0
    assert float(wo_resp.json()["scrap_quantity"]) == 5.0
    
    # 9. Complete Operation (IN_PRODUCTION -> QC_PENDING)
    complete_resp = await async_client.post(
        "/api/v1/worker/complete-operation",
        json={
            "work_order_id": wo_id,
            "operation_id": operation_id,
            "remarks": "Operation completed"
        },
        headers=token_headers
    )
    assert complete_resp.status_code == 200
    
    wo_resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    assert wo_resp.json()["status"] == "QC_PENDING"
    
    # 10. Create QC Inspection
    qc_resp = await async_client.post(
        "/api/v1/quality/inspections",
        json={
            "reference_type": "work_order",
            "reference_id": wo_id,
            "inspection_date": "2026-05-12",
            "result": "PENDING",
            "inspector_id": user_id,
            "details": [
                {
                    "parameter": "Dimension",
                    "tolerance_min": 9.8,
                    "tolerance_max": 10.2,
                    "measured_value": 10.0,
                    "is_passed": True
                }
            ]
        },
        headers=token_headers
    )
    assert qc_resp.status_code == 201
    inspection_id = qc_resp.json()["id"]
    
    # 11. Approve QC (QC_PENDING -> QC_APPROVED -> FG_RECEIVED)
    approve_resp = await async_client.post(
        f"/api/v1/quality/inspections/{inspection_id}/approve",
        headers=token_headers
    )
    assert approve_resp.status_code == 200
    
    wo_resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    assert wo_resp.json()["status"] == "FG_RECEIVED"
    
    # 12. Complete WO (FG_RECEIVED -> COMPLETED)
    complete_wo_resp = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        headers=token_headers
    )
    assert complete_wo_resp.status_code == 200
    assert complete_wo_resp.json()["status"] == "COMPLETED"
    
    # 13. Generate Work Order Document
    doc_resp = await async_client.post(
        f"/api/v1/documents/work_order/{wo_id}/generate",
        json={"force_regenerate": False},
        headers=token_headers
    )
    assert doc_resp.status_code == 200
    
    # 14. Generate Material Issue Slip
    mis_resp = await async_client.post(
        f"/api/v1/documents/material_issue_slip/{wo_id}/generate",
        json={"force_regenerate": False},
        headers=token_headers
    )
    assert mis_resp.status_code == 200
    
    # 15. Generate FG Receipt Note
    fgr_resp = await async_client.post(
        f"/api/v1/documents/fg_receipt_note/{wo_id}/generate",
        json={"force_regenerate": False},
        headers=token_headers
    )
    assert fgr_resp.status_code == 200
    
    # 16. Verify final state
    wo_resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    final_wo = wo_resp.json()
    assert final_wo["status"] == "COMPLETED"
    assert float(final_wo["produced_quantity"]) == 100.0
    assert float(final_wo["scrap_quantity"]) == 5.0


@pytest.mark.asyncio
async def test_qc_reject_rework_flow(async_client: AsyncClient, token_headers: dict):
    """
    E2E Test: QC Reject and Rework Flow
    Validates: QC_PENDING -> QC_REJECTED -> REWORK -> QC_PENDING
    """
    # Setup minimal data
    material_resp = await async_client.post(
        "/api/v1/materials",
        json={
            "code": "RM-002",
            "name": "Raw Material B",
            "unit_of_measure": "KG",
            "unit_cost": 10.0
        },
        headers=token_headers
    )
    material_id = material_resp.json()["id"]
    unit_id = material_resp.json()["unit_id"]
    
    product_resp = await async_client.post(
        "/api/v1/products",
        json={
            "code": "FG-002",
            "name": "Finished Product B",
            "unit_of_measure": "PCS",
            "unit_cost": 50.0
        },
        headers=token_headers
    )
    product_id = product_resp.json()["id"]
    
    operation_resp = await async_client.post(
        "/api/v1/operations",
        json={
            "code": "OP-002",
            "name": "Machining",
            "process_type": "machining",
            "estimated_time_hours": 1.0,
            "estimated_labor_cost": 30.0
        },
        headers=token_headers
    )
    operation_id = operation_resp.json()["id"]
    
    bom_resp = await async_client.post(
        "/api/v1/boms",
        json={
            "version": "v1.0",
            "valid_from": datetime.utcnow().isoformat(),
            "product_id": product_id,
            "lines": [{"material_id": material_id, "quantity": 1.0, "unit_id": unit_id}],
            "operations": [operation_id]
        },
        headers=token_headers
    )
    bom_id = bom_resp.json()["id"]
    
    # Initial stock
    await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "material_id": material_id,
            "unit_id": unit_id,
            "transaction_type": "adjustment",
            "quantity": 100.0,
            "remarks": "Initial stock"
        },
        headers=token_headers
    )
    
    # Create and progress WO to QC_PENDING
    wo_resp = await async_client.post(
        "/api/v1/work-orders",
        json={
            "product_id": product_id,
            "bom_id": bom_id,
            "planned_quantity": 50.0,
            "start_date": "2026-05-12",
            "due_date": "2026-05-15",
            "priority": "NORMAL"
        },
        headers=token_headers
    )
    wo_id = wo_resp.json()["id"]
    
    await async_client.post(f"/api/v1/work-orders/{wo_id}/release", headers=token_headers)
    await async_client.post(
        "/api/v1/storekeeper/reserve-stock",
        json={"work_order_id": wo_id, "material_id": material_id, "quantity": 50.0, "unit_id": unit_id},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/storekeeper/issue-stock",
        json={"work_order_id": wo_id, "material_id": material_id, "quantity": 50.0, "unit_id": unit_id},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/worker/start-operation",
        json={"work_order_id": wo_id, "operation_id": operation_id, "assigned_to": str(uuid.uuid4())},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/worker/record-production",
        json={"work_order_id": wo_id, "produced_quantity": 50.0, "scrap_quantity": 0.0},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/worker/complete-operation",
        json={"work_order_id": wo_id, "operation_id": operation_id},
        headers=token_headers
    )
    
    # Create QC inspection
    qc_resp = await async_client.post(
        "/api/v1/quality/inspections",
        json={
            "reference_type": "work_order",
            "reference_id": wo_id,
            "inspection_date": "2026-05-12",
            "result": "PENDING",
            "inspector_id": str(uuid.uuid4()),
            "details": [{"parameter": "Test", "tolerance_min": 0, "tolerance_max": 10, "measured_value": 5, "is_passed": True}]
        },
        headers=token_headers
    )
    inspection_id = qc_resp.json()["id"]
    
    # Reject QC
    reject_resp = await async_client.post(
        f"/api/v1/quality/inspections/{inspection_id}/reject",
        json={"reason": "Quality issue found"},
        headers=token_headers
    )
    assert reject_resp.status_code == 200
    
    wo_resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    assert wo_resp.json()["status"] == "QC_REJECTED"
    
    # Send to rework
    rework_resp = await async_client.post(
        f"/api/v1/quality/inspections/{inspection_id}/rework",
        headers=token_headers
    )
    assert rework_resp.status_code == 200
    
    wo_resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    assert wo_resp.json()["status"] == "REWORK"


@pytest.mark.asyncio
async def test_qc_scrap_flow(async_client: AsyncClient, token_headers: dict):
    """
    E2E Test: QC Scrap Flow
    Validates: QC_PENDING -> QC_REJECTED -> REJECTED
    """
    # Setup minimal data
    material_resp = await async_client.post(
        "/api/v1/materials",
        json={"code": "RM-003", "name": "Raw Material C", "unit_of_measure": "KG", "unit_cost": 10.0},
        headers=token_headers
    )
    material_id = material_resp.json()["id"]
    unit_id = material_resp.json()["unit_id"]
    
    product_resp = await async_client.post(
        "/api/v1/products",
        json={"code": "FG-003", "name": "Finished Product C", "unit_of_measure": "PCS", "unit_cost": 50.0},
        headers=token_headers
    )
    product_id = product_resp.json()["id"]
    
    operation_resp = await async_client.post(
        "/api/v1/operations",
        json={"code": "OP-003", "name": "Welding", "process_type": "welding", "estimated_time_hours": 1.0, "estimated_labor_cost": 30.0},
        headers=token_headers
    )
    operation_id = operation_resp.json()["id"]
    
    bom_resp = await async_client.post(
        "/api/v1/boms",
        json={
            "version": "v1.0",
            "valid_from": datetime.utcnow().isoformat(),
            "product_id": product_id,
            "lines": [{"material_id": material_id, "quantity": 1.0, "unit_id": unit_id}],
            "operations": [operation_id]
        },
        headers=token_headers
    )
    bom_id = bom_resp.json()["id"]
    
    await async_client.post(
        "/api/v1/inventory/transactions",
        json={"material_id": material_id, "unit_id": unit_id, "transaction_type": "adjustment", "quantity": 100.0, "remarks": "Initial stock"},
        headers=token_headers
    )
    
    # Create and progress WO to QC_PENDING
    wo_resp = await async_client.post(
        "/api/v1/work-orders",
        json={"product_id": product_id, "bom_id": bom_id, "planned_quantity": 30.0, "start_date": "2026-05-12", "due_date": "2026-05-15", "priority": "NORMAL"},
        headers=token_headers
    )
    wo_id = wo_resp.json()["id"]
    
    await async_client.post(f"/api/v1/work-orders/{wo_id}/release", headers=token_headers)
    await async_client.post(
        "/api/v1/storekeeper/reserve-stock",
        json={"work_order_id": wo_id, "material_id": material_id, "quantity": 30.0, "unit_id": unit_id},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/storekeeper/issue-stock",
        json={"work_order_id": wo_id, "material_id": material_id, "quantity": 30.0, "unit_id": unit_id},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/worker/start-operation",
        json={"work_order_id": wo_id, "operation_id": operation_id, "assigned_to": str(uuid.uuid4())},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/worker/record-production",
        json={"work_order_id": wo_id, "produced_quantity": 30.0, "scrap_quantity": 0.0},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/worker/complete-operation",
        json={"work_order_id": wo_id, "operation_id": operation_id},
        headers=token_headers
    )
    
    # Create QC inspection
    qc_resp = await async_client.post(
        "/api/v1/quality/inspections",
        json={
            "reference_type": "work_order",
            "reference_id": wo_id,
            "inspection_date": "2026-05-12",
            "result": "PENDING",
            "inspector_id": str(uuid.uuid4()),
            "details": [{"parameter": "Test", "tolerance_min": 0, "tolerance_max": 10, "measured_value": 5, "is_passed": True}]
        },
        headers=token_headers
    )
    inspection_id = qc_resp.json()["id"]
    
    # Reject QC
    await async_client.post(
        f"/api/v1/quality/inspections/{inspection_id}/reject",
        json={"reason": "Critical quality failure"},
        headers=token_headers
    )
    
    # Scrap batch
    scrap_resp = await async_client.post(
        f"/api/v1/quality/inspections/{inspection_id}/scrap",
        json={"reason": "Cannot rework - scrap"},
        headers=token_headers
    )
    assert scrap_resp.status_code == 200
    
    wo_resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    assert wo_resp.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_delivery_flow(async_client: AsyncClient, token_headers: dict):
    """
    E2E Test: Delivery Flow
    Validates: DRAFT -> PACKING -> SHIPPED -> DELIVERED
    """
    # Setup client and sales order
    client_resp = await async_client.post(
        "/api/v1/clients",
        json={"name": "Test Client", "email": "test@client.com", "phone": "1234567890", "address": "Test Address"},
        headers=token_headers
    )
    client_id = client_resp.json()["id"]
    
    # Create product for SO
    product_resp = await async_client.post(
        "/api/v1/products",
        json={"code": "FG-004", "name": "Finished Product D", "unit_of_measure": "PCS", "unit_cost": 50.0},
        headers=token_headers
    )
    product_id = product_resp.json()["id"]
    
    # Create sales order
    so_resp = await async_client.post(
        "/api/v1/sales-orders",
        json={
            "client_id": client_id,
            "order_date": "2026-05-12",
            "due_date": "2026-05-20",
            "lines": [{"product_id": product_id, "quantity": 10.0, "unit_price": 100.0}],
            "status": "CONFIRMED"
        },
        headers=token_headers
    )
    sales_order_id = so_resp.json()["id"]
    
    # Create delivery order
    delivery_resp = await async_client.post(
        "/api/v1/deliveries",
        json={"sales_order_id": sales_order_id, "shipping_address": "Test Shipping Address", "carrier": "Test Carrier"},
        headers=token_headers
    )
    assert delivery_resp.status_code == 201
    delivery_id = delivery_resp.json()["id"]
    assert delivery_resp.json()["status"] == "DRAFT"
    
    # Pack delivery
    pack_resp = await async_client.post(
        "/api/v1/delivery/pack",
        json={"delivery_order_id": delivery_id, "packing_notes": "Packed for E2E test"},
        headers=token_headers
    )
    assert pack_resp.status_code == 200
    assert pack_resp.json()["status"] == "PACKING"
    assert pack_resp.json()["packed_at"] is not None
    
    # Ship delivery
    ship_resp = await async_client.post(
        f"/api/v1/deliveries/{delivery_id}/ship",
        json={"tracking_number": "TRACK123456"},
        headers=token_headers
    )
    assert ship_resp.status_code == 200
    assert ship_resp.json()["status"] == "SHIPPED"
    assert ship_resp.json()["shipped_at"] is not None
    
    # Confirm delivery
    confirm_resp = await async_client.post(
        "/api/v1/delivery/confirm-delivery",
        json={"delivery_order_id": delivery_id, "delivery_notes": "Delivered successfully"},
        headers=token_headers
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "DELIVERED"
    assert confirm_resp.json()["delivered_at"] is not None


@pytest.mark.asyncio
async def test_storekeeper_operations(async_client: AsyncClient, token_headers: dict):
    """
    E2E Test: Storekeeper Operations
    Validates: Reserve, Issue, Partial Issue, Reject, Return
    """
    # Setup
    material_resp = await async_client.post(
        "/api/v1/materials",
        json={"code": "RM-005", "name": "Raw Material E", "unit_of_measure": "KG", "unit_cost": 10.0},
        headers=token_headers
    )
    material_id = material_resp.json()["id"]
    unit_id = material_resp.json()["unit_id"]
    
    product_resp = await async_client.post(
        "/api/v1/products",
        json={"code": "FG-005", "name": "Finished Product E", "unit_of_measure": "PCS", "unit_cost": 50.0},
        headers=token_headers
    )
    product_id = product_resp.json()["id"]
    
    operation_resp = await async_client.post(
        "/api/v1/operations",
        json={"code": "OP-005", "name": "Cutting", "process_type": "cutting", "estimated_time_hours": 1.0, "estimated_labor_cost": 30.0},
        headers=token_headers
    )
    operation_id = operation_resp.json()["id"]
    
    bom_resp = await async_client.post(
        "/api/v1/boms",
        json={
            "version": "v1.0",
            "valid_from": datetime.utcnow().isoformat(),
            "product_id": product_id,
            "lines": [{"material_id": material_id, "quantity": 5.0, "unit_id": unit_id}],
            "operations": [operation_id]
        },
        headers=token_headers
    )
    bom_id = bom_resp.json()["id"]
    
    await async_client.post(
        "/api/v1/inventory/transactions",
        json={"material_id": material_id, "unit_id": unit_id, "transaction_type": "adjustment", "quantity": 500.0, "remarks": "Initial stock"},
        headers=token_headers
    )
    
    # Create WO
    wo_resp = await async_client.post(
        "/api/v1/work-orders",
        json={"product_id": product_id, "bom_id": bom_id, "planned_quantity": 100.0, "start_date": "2026-05-12", "due_date": "2026-05-15", "priority": "NORMAL"},
        headers=token_headers
    )
    wo_id = wo_resp.json()["id"]
    
    await async_client.post(f"/api/v1/work-orders/{wo_id}/release", headers=token_headers)
    
    # Reserve stock
    reserve_resp = await async_client.post(
        "/api/v1/storekeeper/reserve-stock",
        json={"work_order_id": wo_id, "material_id": material_id, "quantity": 500.0, "unit_id": unit_id},
        headers=token_headers
    )
    assert reserve_resp.status_code == 200
    
    # Partial issue
    partial_resp = await async_client.post(
        "/api/v1/storekeeper/issue-stock",
        json={"work_order_id": wo_id, "material_id": material_id, "quantity": 250.0, "unit_id": unit_id},
        headers=token_headers
    )
    assert partial_resp.status_code == 200
    
    wo_resp = await async_client.get(f"/api/v1/work-orders/{wo_id}", headers=token_headers)
    assert float(wo_resp.json()["materials"][0]["reserved_quantity"]) == 250.0
    assert float(wo_resp.json()["materials"][0]["issued_quantity"]) == 250.0
    
    # Return material
    return_resp = await async_client.post(
        "/api/v1/storekeeper/return-stock",
        json={"work_order_id": wo_id, "material_id": material_id, "quantity": 50.0, "unit_id": unit_id, "reason": "Excess material"},
        headers=token_headers
    )
    assert return_resp.status_code == 200


@pytest.mark.asyncio
async def test_worker_operations(async_client: AsyncClient, token_headers: dict):
    """
    E2E Test: Worker Operations
    Validates: Start, Pause, Resume, Complete, Report Wastage
    """
    # Setup
    material_resp = await async_client.post(
        "/api/v1/materials",
        json={"code": "RM-006", "name": "Raw Material F", "unit_of_measure": "KG", "unit_cost": 10.0},
        headers=token_headers
    )
    material_id = material_resp.json()["id"]
    unit_id = material_resp.json()["unit_id"]
    
    product_resp = await async_client.post(
        "/api/v1/products",
        json={"code": "FG-006", "name": "Finished Product F", "unit_of_measure": "PCS", "unit_cost": 50.0},
        headers=token_headers
    )
    product_id = product_resp.json()["id"]
    
    operation_resp = await async_client.post(
        "/api/v1/operations",
        json={"code": "OP-006", "name": "Drilling", "process_type": "drilling", "estimated_time_hours": 1.0, "estimated_labor_cost": 30.0},
        headers=token_headers
    )
    operation_id = operation_resp.json()["id"]
    
    bom_resp = await async_client.post(
        "/api/v1/boms",
        json={
            "version": "v1.0",
            "valid_from": datetime.utcnow().isoformat(),
            "product_id": product_id,
            "lines": [{"material_id": material_id, "quantity": 2.0, "unit_id": unit_id}],
            "operations": [operation_id]
        },
        headers=token_headers
    )
    bom_id = bom_resp.json()["id"]
    
    await async_client.post(
        "/api/v1/inventory/transactions",
        json={"material_id": material_id, "unit_id": unit_id, "transaction_type": "adjustment", "quantity": 200.0, "remarks": "Initial stock"},
        headers=token_headers
    )
    
    # Create WO
    wo_resp = await async_client.post(
        "/api/v1/work-orders",
        json={"product_id": product_id, "bom_id": bom_id, "planned_quantity": 50.0, "start_date": "2026-05-12", "due_date": "2026-05-15", "priority": "NORMAL"},
        headers=token_headers
    )
    wo_id = wo_resp.json()["id"]
    
    await async_client.post(f"/api/v1/work-orders/{wo_id}/release", headers=token_headers)
    await async_client.post(
        "/api/v1/storekeeper/reserve-stock",
        json={"work_order_id": wo_id, "material_id": material_id, "quantity": 100.0, "unit_id": unit_id},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/storekeeper/issue-stock",
        json={"work_order_id": wo_id, "material_id": material_id, "quantity": 100.0, "unit_id": unit_id},
        headers=token_headers
    )
    
    worker_id = str(uuid.uuid4())
    
    # Start operation
    start_resp = await async_client.post(
        "/api/v1/worker/start-operation",
        json={"work_order_id": wo_id, "operation_id": operation_id, "assigned_to": worker_id},
        headers=token_headers
    )
    assert start_resp.status_code == 200
    
    # Pause operation
    pause_resp = await async_client.post(
        "/api/v1/worker/pause-operation",
        json={"work_order_id": wo_id, "operation_id": operation_id, "reason": "Maintenance"},
        headers=token_headers
    )
    assert pause_resp.status_code == 200
    
    # Resume operation
    resume_resp = await async_client.post(
        "/api/v1/worker/resume-operation",
        json={"work_order_id": wo_id, "operation_id": operation_id},
        headers=token_headers
    )
    assert resume_resp.status_code == 200
    
    # Report wastage
    wastage_resp = await async_client.post(
        "/api/v1/worker/report-wastage",
        json={"work_order_id": wo_id, "material_id": material_id, "quantity": 5.0, "unit_id": unit_id, "reason": "Defective material"},
        headers=token_headers
    )
    assert wastage_resp.status_code == 200
    
    # Record production
    record_resp = await async_client.post(
        "/api/v1/worker/record-production",
        json={"work_order_id": wo_id, "produced_quantity": 50.0, "scrap_quantity": 5.0, "notes": "Production completed"},
        headers=token_headers
    )
    assert record_resp.status_code == 200
    
    # Complete operation
    complete_resp = await async_client.post(
        "/api/v1/worker/complete-operation",
        json={"work_order_id": wo_id, "operation_id": operation_id, "remarks": "All done"},
        headers=token_headers
    )
    assert complete_resp.status_code == 200


@pytest.mark.asyncio
async def test_dashboard_queues(async_client: AsyncClient, token_headers: dict):
    """
    E2E Test: Dashboard Queues
    Validates: QC, Storekeeper, Worker dashboard queues
    """
    # Create WOs in different states
    
    # WO in QC_PENDING
    material_resp = await async_client.post(
        "/api/v1/materials",
        json={"code": "RM-007", "name": "Raw Material G", "unit_of_measure": "KG", "unit_cost": 10.0},
        headers=token_headers
    )
    material_id = material_resp.json()["id"]
    unit_id = material_resp.json()["unit_id"]
    
    product_resp = await async_client.post(
        "/api/v1/products",
        json={"code": "FG-007", "name": "Finished Product G", "unit_of_measure": "PCS", "unit_cost": 50.0},
        headers=token_headers
    )
    product_id = product_resp.json()["id"]
    
    operation_resp = await async_client.post(
        "/api/v1/operations",
        json={"code": "OP-007", "name": "Assembly", "process_type": "assembly", "estimated_time_hours": 1.0, "estimated_labor_cost": 30.0},
        headers=token_headers
    )
    operation_id = operation_resp.json()["id"]
    
    bom_resp = await async_client.post(
        "/api/v1/boms",
        json={
            "version": "v1.0",
            "valid_from": datetime.utcnow().isoformat(),
            "product_id": product_id,
            "lines": [{"material_id": material_id, "quantity": 1.0, "unit_id": unit_id}],
            "operations": [operation_id]
        },
        headers=token_headers
    )
    bom_id = bom_resp.json()["id"]
    
    await async_client.post(
        "/api/v1/inventory/transactions",
        json={"material_id": material_id, "unit_id": unit_id, "transaction_type": "adjustment", "quantity": 100.0, "remarks": "Initial stock"},
        headers=token_headers
    )
    
    wo_resp = await async_client.post(
        "/api/v1/work-orders",
        json={"product_id": product_id, "bom_id": bom_id, "planned_quantity": 20.0, "start_date": "2026-05-12", "due_date": "2026-05-15", "priority": "NORMAL"},
        headers=token_headers
    )
    wo_id = wo_resp.json()["id"]
    
    await async_client.post(f"/api/v1/work-orders/{wo_id}/release", headers=token_headers)
    await async_client.post(
        "/api/v1/storekeeper/reserve-stock",
        json={"work_order_id": wo_id, "material_id": material_id, "quantity": 20.0, "unit_id": unit_id},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/storekeeper/issue-stock",
        json={"work_order_id": wo_id, "material_id": material_id, "quantity": 20.0, "unit_id": unit_id},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/worker/start-operation",
        json={"work_order_id": wo_id, "operation_id": operation_id, "assigned_to": str(uuid.uuid4())},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/worker/record-production",
        json={"work_order_id": wo_id, "produced_quantity": 20.0, "scrap_quantity": 0.0},
        headers=token_headers
    )
    await async_client.post(
        "/api/v1/worker/complete-operation",
        json={"work_order_id": wo_id, "operation_id": operation_id},
        headers=token_headers
    )
    
    # Test QC Dashboard
    qc_dash_resp = await async_client.get("/api/v1/dashboard/qc", headers=token_headers)
    assert qc_dash_resp.status_code == 200
    qc_dash = qc_dash_resp.json()
    assert "queues" in qc_dash
    assert "inspection" in qc_dash["queues"]
    
    # Test Storekeeper Dashboard
    sk_dash_resp = await async_client.get("/api/v1/dashboard/storekeeper", headers=token_headers)
    assert sk_dash_resp.status_code == 200
    sk_dash = sk_dash_resp.json()
    assert "queues" in sk_dash
    assert "material_issues" in sk_dash["queues"]
    
    # Test Worker Dashboard
    worker_dash_resp = await async_client.get("/api/v1/dashboard/worker", headers=token_headers)
    assert worker_dash_resp.status_code == 200
    worker_dash = worker_dash_resp.json()
    assert "queues" in worker_dash
    assert "assigned_operations" in worker_dash["queues"]
