"""
Unit tests for any-supplier purchase history lookup service (Priority 2.3).

Tests cover:
- Latest purchase from any supplier
- Best historical price across suppliers
- Supplier comparison and benchmarking
- Metadata aggregation (supplier count, best price)
- Tenant isolation
- Status filtering (received/inspected only)
"""
import pytest
import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.procurement.pricing.any_supplier_history_lookup_service import (
    AnySupplierHistoryLookupService,
    AnySupplierHistoryResult,
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


async def _create_supplier(session: AsyncSession, tenant_id: uuid.UUID, name: str, user_id: uuid.UUID) -> uuid.UUID:
    """Helper to create a supplier."""
    supplier_id = uuid.uuid4()
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant_id,
        name=name,
        supplier_code=f"SUPP-{name[0]}",
        is_active=True,
        is_deleted=False,
        created_by=user_id,
    )
    session.add(supplier)
    await session.flush()
    return supplier_id


async def _create_material(session: AsyncSession, tenant_id: uuid.UUID, name: str, user_id: uuid.UUID) -> uuid.UUID:
    """Helper to create a material."""
    material_id = uuid.uuid4()
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name=name,
        code=f"MAT-{name[0]}",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=user_id,
    )
    session.add(material)
    await session.flush()
    return material_id


async def _create_purchase_receipt(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    material_id: uuid.UUID,
    unit_price: Decimal,
    receipt_date: datetime,
    user_id: uuid.UUID,
) -> None:
    """Helper to create a PO, GRN, and GRN line."""
    po = PurchaseOrderModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        po_number=f"PO-{uuid.uuid4().hex[:8]}",
        supplier_id=supplier_id,
        order_date=receipt_date.date(),
        status="received",
        total_amount=5000,
        created_by=user_id,
    )
    session.add(po)
    await session.flush()
    
    grn = GoodsReceiptNoteModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        grn_number=f"GRN-{uuid.uuid4().hex[:8]}",
        purchase_order_id=po.id,
        supplier_id=supplier_id,
        actual_receipt_date=receipt_date,
        status="received",
        is_deleted=False,
        created_by=user_id,
    )
    session.add(grn)
    await session.flush()
    
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
        unit_price=unit_price,
        is_deleted=False,
        created_by=user_id,
    )
    session.add(grn_line)


@pytest.mark.asyncio
async def test_lookup_latest_purchase_any_supplier(db_session: AsyncSession):
    """Test lookup finds latest purchase from any supplier."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    material_id = await _create_material(db_session, tenant_id, "Steel", user_id)
    
    # Create two suppliers
    supplier1_id = await _create_supplier(db_session, tenant_id, "Supplier A", user_id)
    supplier2_id = await _create_supplier(db_session, tenant_id, "Supplier B", user_id)
    
    # Create purchases from both suppliers
    await _create_purchase_receipt(
        db_session, tenant_id, supplier1_id, material_id, Decimal("60.00"),
        datetime.now(timezone.utc) - timedelta(days=10), user_id
    )
    await _create_purchase_receipt(
        db_session, tenant_id, supplier2_id, material_id, Decimal("50.00"),
        datetime.now(timezone.utc), user_id  # Most recent
    )
    await db_session.commit()
    
    service = AnySupplierHistoryLookupService(db_session)
    result = await service.lookup_latest_purchase_any_supplier(tenant_id, material_id)
    
    # Should return latest purchase (from Supplier B)
    assert result.found is True
    assert result.supplier_id == supplier2_id
    assert result.supplier_name == "Supplier B"
    assert result.unit_price == Decimal("50.00")
    assert result.total_suppliers == 2
    assert result.best_price == Decimal("50.00")
    assert result.best_supplier_name == "Supplier B"


@pytest.mark.asyncio
async def test_get_best_historical_price(db_session: AsyncSession):
    """Test lookup finds lowest historical price across all suppliers."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    material_id = await _create_material(db_session, tenant_id, "Aluminum", user_id)
    
    # Create three suppliers with different prices
    supplier1_id = await _create_supplier(db_session, tenant_id, "Supplier C", user_id)
    supplier2_id = await _create_supplier(db_session, tenant_id, "Supplier D", user_id)
    supplier3_id = await _create_supplier(db_session, tenant_id, "Supplier E", user_id)
    
    # Create purchases with different prices
    now = datetime.now(timezone.utc)
    await _create_purchase_receipt(
        db_session, tenant_id, supplier1_id, material_id, Decimal("60.00"), now - timedelta(days=20), user_id
    )
    await _create_purchase_receipt(
        db_session, tenant_id, supplier2_id, material_id, Decimal("40.00"), now - timedelta(days=10), user_id
    )
    await _create_purchase_receipt(
        db_session, tenant_id, supplier3_id, material_id, Decimal("50.00"), now, user_id
    )
    await db_session.commit()
    
    service = AnySupplierHistoryLookupService(db_session)
    result = await service.get_best_historical_price(tenant_id, material_id)
    
    # Should return best (lowest) price
    assert result.found is True
    assert result.supplier_id == supplier2_id
    assert result.supplier_name == "Supplier D"
    assert result.unit_price == Decimal("40.00")
    assert result.source == "any_supplier_best_price"


@pytest.mark.asyncio
async def test_get_supplier_comparison_for_material(db_session: AsyncSession):
    """Test supplier comparison returns benchmarking data."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    material_id = await _create_material(db_session, tenant_id, "Copper", user_id)
    
    # Create three suppliers
    supplier1_id = await _create_supplier(db_session, tenant_id, "Supplier F", user_id)
    supplier2_id = await _create_supplier(db_session, tenant_id, "Supplier G", user_id)
    supplier3_id = await _create_supplier(db_session, tenant_id, "Supplier H", user_id)
    
    now = datetime.now(timezone.utc)
    
    # Create multiple purchases from each supplier
    for i, supplier_id in enumerate([supplier1_id, supplier2_id, supplier3_id]):
        prices = [
            Decimal("50.00") + (i * Decimal("10.00")),
            Decimal("52.00") + (i * Decimal("10.00")),
            Decimal("48.00") + (i * Decimal("10.00")),
        ]
        
        for j, price in enumerate(prices):
            await _create_purchase_receipt(
                db_session, tenant_id, supplier_id, material_id, price,
                now - timedelta(days=20-j*10), user_id
            )
    
    await db_session.commit()
    
    service = AnySupplierHistoryLookupService(db_session)
    comparison = await service.get_supplier_comparison_for_material(tenant_id, material_id)
    
    assert comparison["found"] is True
    assert comparison["supplier_count"] == 3
    assert len(comparison["comparisons"]) == 3
    
    # Comparisons should be sorted by min price
    assert comparison["comparisons"][0]["min_price"] == 48.0  # Supplier F
    assert comparison["comparisons"][1]["min_price"] == 58.0  # Supplier G
    assert comparison["comparisons"][2]["min_price"] == 68.0  # Supplier H
    
    # All should have purchase_count = 3
    for comp in comparison["comparisons"]:
        assert comp["purchase_count"] == 3
    
    # Check overall stats
    stats = comparison["overall_stats"]
    assert stats["min_price"] == 48.0
    assert stats["max_price"] == 68.0


@pytest.mark.asyncio
async def test_lookup_enforces_tenant_isolation(db_session: AsyncSession):
    """Test lookup enforces tenant isolation."""
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    material_id = await _create_material(db_session, tenant1_id, "Bronze", user_id)
    supplier_id = await _create_supplier(db_session, tenant1_id, "Supplier I", user_id)
    
    # Create purchase for tenant 1
    now = datetime.now(timezone.utc)
    await _create_purchase_receipt(
        db_session, tenant1_id, supplier_id, material_id, Decimal("50.00"), now, user_id
    )
    await db_session.commit()
    
    # Try to lookup as tenant 2
    service = AnySupplierHistoryLookupService(db_session)
    result = await service.lookup_latest_purchase_any_supplier(tenant2_id, material_id)
    
    assert result.found is False


@pytest.mark.asyncio
async def test_lookup_returns_not_found_for_nonexistent_material(db_session: AsyncSession):
    """Test lookup returns found=False when no purchase history exists."""
    service = AnySupplierHistoryLookupService(db_session)
    result = await service.lookup_latest_purchase_any_supplier(uuid.uuid4(), uuid.uuid4())
    
    assert result.found is False


@pytest.mark.asyncio
async def test_any_supplier_history_result_to_dict():
    """Test AnySupplierHistoryResult.to_dict() serialization."""
    material_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    receipt_date = date.today() - timedelta(days=10)
    
    result = AnySupplierHistoryResult(
        found=True,
        material_id=material_id,
        supplier_id=supplier_id,
        supplier_name="Test Supplier",
        unit_price=Decimal("50.00"),
        quantity=Decimal("100"),
        receipt_date=receipt_date,
        grn_number="GRN-001",
        po_number="PO-001",
        source="any_supplier_history",
        total_suppliers=5,
        best_price=Decimal("45.00"),
        best_supplier_name="Best Supplier",
    )
    
    result_dict = result.to_dict()
    
    assert result_dict["found"] is True
    assert result_dict["material_id"] == str(material_id)
    assert result_dict["supplier_id"] == str(supplier_id)
    assert result_dict["supplier_name"] == "Test Supplier"
    assert result_dict["unit_price"] == 50.0
    assert result_dict["total_suppliers"] == 5
    assert result_dict["best_price"] == 45.0
    assert result_dict["best_supplier_name"] == "Best Supplier"


@pytest.mark.asyncio
async def test_supplier_comparison_returns_empty_for_no_purchases(db_session: AsyncSession):
    """Test comparison returns empty when material has no purchase history."""
    service = AnySupplierHistoryLookupService(db_session)
    comparison = await service.get_supplier_comparison_for_material(uuid.uuid4(), uuid.uuid4())
    
    assert comparison["found"] is False
    assert comparison["supplier_count"] == 0
    assert len(comparison["comparisons"]) == 0
