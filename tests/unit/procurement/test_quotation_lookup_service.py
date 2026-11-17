"""
Unit tests for supplier quotation lookup service (Priority 2.1).

Tests cover:
- Approved quotation lookup by supplier and material
- Latest quotation lookup (including expired)
- All approved quotations for material (comparison shopping)
- Expiration handling
- Tenant isolation
- Status filtering (APPROVED, AWARDED vs DRAFT)
"""
import pytest
import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.procurement.pricing.quotation_lookup_service import (
    SupplierQuotationLookupService,
    QuotationLookupResult,
)
from backend.app.infrastructure.persistence.models.quality_model import SupplierQuotationModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel


@pytest.mark.asyncio
async def test_lookup_finds_approved_quotation(db_session: AsyncSession):
    """Test lookup finds an APPROVED quotation."""
    # Setup
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    
    # Create supplier and material
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant_id,
        name="Supplier A",
        supplier_code="SUPP-A",
        is_active=True,
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name="Steel Sheet",
        code="MAT-001",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create approved quotation
    quotation = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quotation_number="QT-001",
        supplier_id=supplier_id,
        material_id=material_id,
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),
        valid_until=date.today() + timedelta(days=30),
        status="APPROVED",
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(quotation)
    await db_session.commit()
    
    # Test
    service = SupplierQuotationLookupService(db_session)
    result = await service.lookup_by_supplier_and_material(tenant_id, supplier_id, material_id)
    
    # Verify
    assert result.found is True
    assert result.quotation_id == quotation.id
    assert result.quotation_number == "QT-001"
    assert result.unit_price == Decimal("50.00")
    assert result.quantity == Decimal("100")
    assert result.status == "APPROVED"
    assert result.source == "approved_quotation"


@pytest.mark.asyncio
async def test_lookup_finds_awarded_quotation(db_session: AsyncSession):
    """Test lookup finds an AWARDED quotation."""
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    
    # Create supplier and material
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant_id,
        name="Supplier B",
        supplier_code="SUPP-B",
        is_active=True,
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name="Aluminum",
        code="MAT-002",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create awarded quotation
    quotation = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quotation_number="QT-002",
        supplier_id=supplier_id,
        material_id=material_id,
        quantity=Decimal("100"),
        unit_price=Decimal("45.00"),
        valid_until=date.today() + timedelta(days=30),
        status="AWARDED",
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(quotation)
    await db_session.commit()
    
    service = SupplierQuotationLookupService(db_session)
    result = await service.lookup_by_supplier_and_material(tenant_id, supplier_id, material_id)
    
    assert result.found is True
    assert result.status == "AWARDED"
    assert result.source == "approved_quotation"


@pytest.mark.asyncio
async def test_lookup_returns_most_recent_quotation(db_session: AsyncSession):
    """Test lookup returns most recent (latest created) quotation."""
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    
    # Create supplier and material
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant_id,
        name="Supplier C",
        supplier_code="SUPP-C",
        is_active=True,
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name="Copper",
        code="MAT-003",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create two approved quotations
    old_quotation = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quotation_number="QT-OLD",
        supplier_id=supplier_id,
        material_id=material_id,
        quantity=Decimal("100"),
        unit_price=Decimal("60.00"),
        valid_until=date.today() + timedelta(days=30),
        status="APPROVED",
        is_deleted=False,
        created_by=uuid.uuid4(),
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    new_quotation = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quotation_number="QT-NEW",
        supplier_id=supplier_id,
        material_id=material_id,
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),
        valid_until=date.today() + timedelta(days=30),
        status="APPROVED",
        is_deleted=False,
        created_by=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([old_quotation, new_quotation])
    await db_session.commit()
    
    service = SupplierQuotationLookupService(db_session)
    result = await service.lookup_by_supplier_and_material(tenant_id, supplier_id, material_id)
    
    assert result.found is True
    assert result.quotation_number == "QT-NEW"
    assert result.unit_price == Decimal("50.00")


@pytest.mark.asyncio
async def test_lookup_rejects_draft_quotations(db_session: AsyncSession):
    """Test lookup ignores DRAFT quotations."""
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    
    # Create supplier and material
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant_id,
        name="Supplier D",
        supplier_code="SUPP-D",
        is_active=True,
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name="Bronze",
        code="MAT-004",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create draft quotation (should be ignored)
    quotation = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quotation_number="QT-DRAFT",
        supplier_id=supplier_id,
        material_id=material_id,
        quantity=Decimal("100"),
        unit_price=Decimal("40.00"),
        valid_until=date.today() + timedelta(days=30),
        status="DRAFT",
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(quotation)
    await db_session.commit()
    
    service = SupplierQuotationLookupService(db_session)
    result = await service.lookup_by_supplier_and_material(tenant_id, supplier_id, material_id)
    
    assert result.found is False


@pytest.mark.asyncio
async def test_lookup_handles_expired_quotations(db_session: AsyncSession):
    """Test lookup returns found=False for expired quotations."""
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    
    # Create supplier and material
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant_id,
        name="Supplier E",
        supplier_code="SUPP-E",
        is_active=True,
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name="Titanium",
        code="MAT-005",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create expired quotation
    quotation = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quotation_number="QT-EXP",
        supplier_id=supplier_id,
        material_id=material_id,
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),
        valid_until=date.today() - timedelta(days=1),  # Expired
        status="APPROVED",
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(quotation)
    await db_session.commit()
    
    service = SupplierQuotationLookupService(db_session)
    result = await service.lookup_by_supplier_and_material(tenant_id, supplier_id, material_id)
    
    # Expired quotation returns found=False but with metadata
    assert result.found is False
    assert result.source == "approved_quotation_expired"
    assert result.quotation_number == "QT-EXP"


@pytest.mark.asyncio
async def test_lookup_returns_not_found_for_nonexistent_quotation(db_session: AsyncSession):
    """Test lookup returns found=False when no quotation exists."""
    service = SupplierQuotationLookupService(db_session)
    result = await service.lookup_by_supplier_and_material(
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    )
    
    assert result.found is False
    assert result.quotation_id is None


@pytest.mark.asyncio
async def test_lookup_enforces_tenant_isolation(db_session: AsyncSession):
    """Test lookup enforces tenant isolation."""
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    
    # Create supplier and material for tenant 1
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant1_id,
        name="Supplier F",
        supplier_code="SUPP-F",
        is_active=True,
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant1_id,
        name="Gold",
        code="MAT-006",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create quotation for tenant 1
    quotation = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant1_id,
        quotation_number="QT-T1",
        supplier_id=supplier_id,
        material_id=material_id,
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),
        valid_until=date.today() + timedelta(days=30),
        status="APPROVED",
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(quotation)
    await db_session.commit()
    
    # Try to lookup as tenant 2
    service = SupplierQuotationLookupService(db_session)
    result = await service.lookup_by_supplier_and_material(tenant2_id, supplier_id, material_id)
    
    assert result.found is False


@pytest.mark.asyncio
async def test_lookup_latest_includes_draft_status(db_session: AsyncSession):
    """Test lookup_latest_by_supplier_and_material includes non-approved statuses."""
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    
    # Create supplier and material
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant_id,
        name="Supplier G",
        supplier_code="SUPP-G",
        is_active=True,
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name="Silver",
        code="MAT-007",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create draft quotation
    quotation = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quotation_number="QT-DRAFT-LATEST",
        supplier_id=supplier_id,
        material_id=material_id,
        quantity=Decimal("100"),
        unit_price=Decimal("55.00"),
        valid_until=date.today() + timedelta(days=30),
        status="DRAFT",
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(quotation)
    await db_session.commit()
    
    service = SupplierQuotationLookupService(db_session)
    result = await service.lookup_latest_by_supplier_and_material(tenant_id, supplier_id, material_id)
    
    # Latest should find it and indicate it's DRAFT
    assert result.found is True
    assert result.quotation_number == "QT-DRAFT-LATEST"
    assert result.status == "DRAFT"
    assert result.source == "quotation_draft"


@pytest.mark.asyncio
async def test_lookup_latest_excludes_expired_by_default(db_session: AsyncSession):
    """Test lookup_latest_by_supplier_and_material excludes expired by default."""
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    
    # Create supplier and material
    supplier = SupplierModel(
        id=supplier_id,
        tenant_id=tenant_id,
        name="Supplier H",
        supplier_code="SUPP-H",
        is_active=True,
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name="Platinum",
        code="MAT-008",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(supplier)
    db_session.add(material)
    await db_session.flush()
    
    # Create expired quotation
    quotation = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quotation_number="QT-EXP-LATEST",
        supplier_id=supplier_id,
        material_id=material_id,
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),
        valid_until=date.today() - timedelta(days=1),
        status="APPROVED",
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add(quotation)
    await db_session.commit()
    
    service = SupplierQuotationLookupService(db_session)
    result = await service.lookup_latest_by_supplier_and_material(
        tenant_id, supplier_id, material_id, include_expired=False
    )
    
    assert result.found is False


@pytest.mark.asyncio
async def test_lookup_all_approved_returns_comparison_list(db_session: AsyncSession):
    """Test lookup_all_approved_by_material returns all approved quotations."""
    tenant_id = uuid.uuid4()
    supplier1_id = uuid.uuid4()
    supplier2_id = uuid.uuid4()
    material_id = uuid.uuid4()
    
    # Create suppliers and material
    supplier1 = SupplierModel(
        id=supplier1_id,
        tenant_id=tenant_id,
        name="Supplier I",
        supplier_code="SUPP-I",
        is_active=True,
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    supplier2 = SupplierModel(
        id=supplier2_id,
        tenant_id=tenant_id,
        name="Supplier J",
        supplier_code="SUPP-J",
        is_active=True,
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    material = MaterialModel(
        id=material_id,
        tenant_id=tenant_id,
        name="Lead",
        code="MAT-009",
        base_unit_id=uuid.uuid4(),
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add_all([supplier1, supplier2, material])
    await db_session.flush()
    
    # Create quotations from two suppliers
    q1 = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quotation_number="QT-S1",
        supplier_id=supplier1_id,
        material_id=material_id,
        quantity=Decimal("100"),
        unit_price=Decimal("55.00"),
        valid_until=date.today() + timedelta(days=30),
        status="APPROVED",
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    q2 = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quotation_number="QT-S2",
        supplier_id=supplier2_id,
        material_id=material_id,
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),  # Better price
        valid_until=date.today() + timedelta(days=30),
        status="APPROVED",
        is_deleted=False,
        created_by=uuid.uuid4(),
    )
    db_session.add_all([q1, q2])
    await db_session.commit()
    
    service = SupplierQuotationLookupService(db_session)
    results = await service.lookup_all_approved_by_material(tenant_id, material_id)
    
    # Should return both, sorted by price
    assert len(results) == 2
    assert results[0].unit_price == Decimal("50.00")  # Cheaper first
    assert results[1].unit_price == Decimal("55.00")


@pytest.mark.asyncio
async def test_quotation_lookup_result_to_dict():
    """Test QuotationLookupResult.to_dict() serialization."""
    quotation_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    valid_until = date.today() + timedelta(days=30)
    
    result = QuotationLookupResult(
        found=True,
        quotation_id=quotation_id,
        supplier_id=supplier_id,
        quotation_number="QT-001",
        unit_price=Decimal("50.00"),
        quantity=Decimal("100"),
        valid_until=valid_until,
        status="APPROVED",
        source="approved_quotation",
    )
    
    result_dict = result.to_dict()
    
    assert result_dict["found"] is True
    assert result_dict["quotation_id"] == str(quotation_id)
    assert result_dict["supplier_id"] == str(supplier_id)
    assert result_dict["quotation_number"] == "QT-001"
    assert result_dict["unit_price"] == 50.0
    assert result_dict["quantity"] == 100.0
    assert result_dict["status"] == "APPROVED"
    assert result_dict["source"] == "approved_quotation"
