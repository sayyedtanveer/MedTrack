"""
Unit tests for purchase history lookup service (Priority 2.2).

Tests cover:
- Latest purchase history lookup by supplier and material
- Purchase summary statistics (avg, min, max prices)
- Purchase count tracking
- Receipt date range tracking
- Price trend calculation
- Tenant isolation
- Status filtering (received/inspected only)
- Handling of missing/null data
"""
import pytest
import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.procurement.pricing.purchase_history_lookup_service import (
    PurchaseHistoryLookupService,
    PurchaseHistoryResult,
)
from backend.app.infrastructure.persistence.models.grn_model import (
    GoodsReceiptNoteModel,
    GRNLineModel,
)
from backend.app.infrastructure.persistence.models.purchase_order_model import (
    PurchaseOrderModel,
)
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel


@pytest.mark.asyncio
async def test_lookup_finds_latest_purchase_history(db_session: AsyncSession):
    """Test lookup finds latest purchase from same supplier."""
    # Setup
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create supplier and material
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant_id,
        name="Supplier A",
        supplier_code="SUPP-A",
        is_active=True,
        is_deleted=False,
        created_by=user_id,
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name="Steel",
        code="MAT-001",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create PO
    po = PurchaseOrderModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        po_number="PO-001",
        supplier_id=supplier_id,
        order_date=date.today(),
        status="received",
        total_amount=5000,
        created_by=user_id,
    )
    db_session.add(po)
    await db_session.flush()
    
    # Create GRN
    grn = GoodsReceiptNoteModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        grn_number="GRN-001",
        purchase_order_id=po.id,
        supplier_id=supplier_id,
        actual_receipt_date=datetime.now(timezone.utc),
        status="received",
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add(grn)
    await db_session.flush()
    
    # Create GRN line
    grn_line = GRNLineModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        grn_id=grn.id,
        po_line_id=uuid.uuid4(),
        material_id=material_id,
        po_quantity=Decimal("100"),
        received_quantity=Decimal("100"),
        accepted_quantity=Decimal("100"),
        rejected_quantity=Decimal("0"),
        unit_price=Decimal("50.00"),
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add(grn_line)
    await db_session.commit()
    
    # Test
    service = PurchaseHistoryLookupService(db_session)
    result = await service.lookup_by_supplier_and_material(
        tenant_id, supplier_id, material_id
    )
    
    # Verify
    assert result.found is True
    assert result.unit_price == Decimal("50.00")
    assert result.quantity == Decimal("100")
    assert result.grn_number == "GRN-001"
    assert result.po_number == "PO-001"
    assert result.source == "same_supplier_history"
    assert result.purchase_count == 1


@pytest.mark.asyncio
async def test_lookup_returns_most_recent_purchase(db_session: AsyncSession):
    """Test lookup returns most recent purchase when multiple exist."""
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create supplier and material
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant_id,
        name="Supplier B",
        supplier_code="SUPP-B",
        is_active=True,
        is_deleted=False,
        created_by=user_id,
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name="Aluminum",
        code="MAT-002",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create two POs
    po1 = PurchaseOrderModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        po_number="PO-OLD",
        supplier_id=supplier_id,
        order_date=date.today() - timedelta(days=30),
        status="received",
        total_amount=5000,
        created_by=user_id,
    )
    po2 = PurchaseOrderModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        po_number="PO-NEW",
        supplier_id=supplier_id,
        order_date=date.today(),
        status="received",
        total_amount=5000,
        created_by=user_id,
    )
    db_session.add_all([po1, po2])
    await db_session.flush()
    
    # Create two GRNs
    grn1 = GoodsReceiptNoteModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        grn_number="GRN-OLD",
        purchase_order_id=po1.id,
        supplier_id=supplier_id,
        actual_receipt_date=datetime.now(timezone.utc) - timedelta(days=30),
        status="received",
        is_deleted=False,
        created_by=user_id,
    )
    grn2 = GoodsReceiptNoteModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        grn_number="GRN-NEW",
        purchase_order_id=po2.id,
        supplier_id=supplier_id,
        actual_receipt_date=datetime.now(timezone.utc),
        status="received",
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add_all([grn1, grn2])
    await db_session.flush()
    
    # Create GRN lines
    grn_line1 = GRNLineModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        grn_id=grn1.id,
        po_line_id=uuid.uuid4(),
        material_id=material_id,
        po_quantity=Decimal("100"),
        received_quantity=Decimal("100"),
        accepted_quantity=Decimal("100"),
        rejected_quantity=Decimal("0"),
        unit_price=Decimal("60.00"),  # Old price
        is_deleted=False,
        created_by=user_id,
    )
    grn_line2 = GRNLineModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        grn_id=grn2.id,
        po_line_id=uuid.uuid4(),
        material_id=material_id,
        po_quantity=Decimal("100"),
        received_quantity=Decimal("100"),
        accepted_quantity=Decimal("100"),
        rejected_quantity=Decimal("0"),
        unit_price=Decimal("50.00"),  # New (lower) price
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add_all([grn_line1, grn_line2])
    await db_session.commit()
    
    service = PurchaseHistoryLookupService(db_session)
    result = await service.lookup_by_supplier_and_material(
        tenant_id, supplier_id, material_id
    )
    
    # Should return newest
    assert result.found is True
    assert result.unit_price == Decimal("50.00")
    assert result.grn_number == "GRN-NEW"
    assert result.purchase_count == 2


@pytest.mark.asyncio
async def test_lookup_enforces_tenant_isolation(db_session: AsyncSession):
    """Test lookup enforces tenant isolation."""
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create supplier and material for tenant 1
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant1_id,
        name="Supplier C",
        supplier_code="SUPP-C",
        is_active=True,
        is_deleted=False,
        created_by=user_id,
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant1_id,
        name="Copper",
        code="MAT-003",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create PO and GRN for tenant 1
    po = PurchaseOrderModel(
        id=uuid.uuid4(),
        tenant_id=tenant1_id,
        po_number="PO-T1",
        supplier_id=supplier_id,
        order_date=date.today(),
        status="received",
        total_amount=5000,
        created_by=user_id,
    )
    db_session.add(po)
    await db_session.flush()
    
    grn = GoodsReceiptNoteModel(
        id=uuid.uuid4(),
        tenant_id=tenant1_id,
        grn_number="GRN-T1",
        purchase_order_id=po.id,
        supplier_id=supplier_id,
        actual_receipt_date=datetime.now(timezone.utc),
        status="received",
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add(grn)
    await db_session.flush()
    
    grn_line = GRNLineModel(
        id=uuid.uuid4(),
        tenant_id=tenant1_id,
        grn_id=grn.id,
        po_line_id=uuid.uuid4(),
        material_id=material_id,
        po_quantity=Decimal("100"),
        received_quantity=Decimal("100"),
        accepted_quantity=Decimal("100"),
        rejected_quantity=Decimal("0"),
        unit_price=Decimal("50.00"),
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add(grn_line)
    await db_session.commit()
    
    # Try to lookup as tenant 2
    service = PurchaseHistoryLookupService(db_session)
    result = await service.lookup_by_supplier_and_material(
        tenant2_id, supplier_id, material_id
    )
    
    assert result.found is False


@pytest.mark.asyncio
async def test_lookup_ignores_non_received_grns(db_session: AsyncSession):
    """Test lookup ignores GRNs that are not in received/inspected status."""
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create supplier and material
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant_id,
        name="Supplier D",
        supplier_code="SUPP-D",
        is_active=True,
        is_deleted=False,
        created_by=user_id,
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name="Bronze",
        code="MAT-004",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create PO and GRN with pending_receipt status (not received)
    po = PurchaseOrderModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        po_number="PO-PENDING",
        supplier_id=supplier_id,
        order_date=date.today(),
        status="pending_receipt",
        total_amount=5000,
        created_by=user_id,
    )
    db_session.add(po)
    await db_session.flush()
    
    grn = GoodsReceiptNoteModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        grn_number="GRN-PENDING",
        purchase_order_id=po.id,
        supplier_id=supplier_id,
        actual_receipt_date=datetime.now(timezone.utc),
        status="pending_receipt",  # Not received/inspected
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add(grn)
    await db_session.flush()
    
    grn_line = GRNLineModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        grn_id=grn.id,
        po_line_id=uuid.uuid4(),
        material_id=material_id,
        po_quantity=Decimal("100"),
        received_quantity=Decimal("100"),
        accepted_quantity=Decimal("0"),
        rejected_quantity=Decimal("0"),
        unit_price=Decimal("50.00"),
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add(grn_line)
    await db_session.commit()
    
    service = PurchaseHistoryLookupService(db_session)
    result = await service.lookup_by_supplier_and_material(
        tenant_id, supplier_id, material_id
    )
    
    # Should not find pending GRN
    assert result.found is False


@pytest.mark.asyncio
async def test_get_purchase_summary_statistics(db_session: AsyncSession):
    """Test purchase summary calculates statistics correctly."""
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create supplier and material
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant_id,
        name="Supplier E",
        supplier_code="SUPP-E",
        is_active=True,
        is_deleted=False,
        created_by=user_id,
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name="Titanium",
        code="MAT-005",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=user_id,
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create three POs with different prices
    prices = [Decimal("50.00"), Decimal("55.00"), Decimal("45.00")]
    po_ids = []
    
    for i, price in enumerate(prices):
        po = PurchaseOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            po_number=f"PO-{i}",
            supplier_id=supplier_id,
            order_date=date.today() - timedelta(days=30-i*10),
            status="received",
            total_amount=5000,
            created_by=user_id,
        )
        db_session.add(po)
        po_ids.append(po.id)
    
    await db_session.flush()
    
    # Create GRNs with different receipt dates
    for i, (po_id, price) in enumerate(zip(po_ids, prices)):
        grn = GoodsReceiptNoteModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            grn_number=f"GRN-{i}",
            purchase_order_id=po_id,
            supplier_id=supplier_id,
            actual_receipt_date=datetime.now(timezone.utc) - timedelta(days=30-i*10),
            status="received",
            is_deleted=False,
            created_by=user_id,
        )
        db_session.add(grn)
        await db_session.flush()
        
        grn_line = GRNLineModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            grn_id=grn.id,
            po_line_id=uuid.uuid4(),
            material_id=material_id,
            po_quantity=Decimal("100"),
            received_quantity=Decimal("100"),
            accepted_quantity=Decimal("100"),
            rejected_quantity=Decimal("0"),
            unit_price=price,
            is_deleted=False,
            created_by=user_id,
        )
        db_session.add(grn_line)
    
    await db_session.commit()
    
    service = PurchaseHistoryLookupService(db_session)
    summary = await service.get_purchase_summary_by_supplier_and_material(
        tenant_id, supplier_id, material_id
    )
    
    # Verify statistics
    assert summary["found"] is True
    assert summary["purchase_count"] == 3
    assert summary["latest_price"] == 45.0  # Most recent
    assert summary["min_price"] == 45.0
    assert summary["max_price"] == 55.0
    assert 50.0 <= summary["avg_price"] <= 50.01  # (50+55+45)/3 = 50
    assert summary["price_trend"] == "decreasing"  # Prices went from 50 → 55 → 45


@pytest.mark.asyncio
async def test_purchase_history_result_to_dict():
    """Test PurchaseHistoryResult.to_dict() serialization."""
    material_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    receipt_date = date.today() - timedelta(days=10)
    
    result = PurchaseHistoryResult(
        found=True,
        material_id=material_id,
        supplier_id=supplier_id,
        unit_price=Decimal("50.00"),
        quantity=Decimal("100"),
        receipt_date=receipt_date,
        grn_number="GRN-001",
        po_number="PO-001",
        source="same_supplier_history",
        purchase_count=5,
    )
    
    result_dict = result.to_dict()
    
    assert result_dict["found"] is True
    assert result_dict["material_id"] == str(material_id)
    assert result_dict["supplier_id"] == str(supplier_id)
    assert result_dict["unit_price"] == 50.0
    assert result_dict["quantity"] == 100.0
    assert result_dict["receipt_date"] == receipt_date.isoformat()
    assert result_dict["grn_number"] == "GRN-001"
    assert result_dict["po_number"] == "PO-001"
    assert result_dict["source"] == "same_supplier_history"
    assert result_dict["purchase_count"] == 5


@pytest.mark.asyncio
async def test_lookup_returns_not_found_for_nonexistent_purchase(db_session: AsyncSession):
    """Test lookup returns found=False when no purchase history exists."""
    service = PurchaseHistoryLookupService(db_session)
    result = await service.lookup_by_supplier_and_material(
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    )
    
    assert result.found is False
    assert result.purchase_count == 0
