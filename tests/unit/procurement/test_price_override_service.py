"""
Unit tests for PriceOverrideService.

Tests cover:
- Recording price overrides with validation
- Retrieving override history filtered by material and supplier
- Computing override statistics (count, averages, trends)
- Analyzing override trends over time
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.procurement.pricing.price_override_service import (
    PriceOverrideService,
    PriceOverrideRecord,
)
from backend.app.infrastructure.persistence.models import (
    PriceOverrideRecordModel,
    MaterialModel,
    SupplierModel,
    UserModel,
    TenantModel,
)


@pytest.fixture
async def price_override_service(db_session: AsyncSession) -> PriceOverrideService:
    """Create service instance with test session."""
    return PriceOverrideService(db_session)


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> TenantModel:
    """Create a test tenant."""
    tenant = TenantModel(
        id=uuid4(),
        name="Test Tenant",
        is_deleted=False,
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest.fixture
async def test_user(db_session: AsyncSession, test_tenant: TenantModel) -> UserModel:
    """Create a test user."""
    user = UserModel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        password_hash="hashed_password",
        is_active=True,
        is_deleted=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def test_material(db_session: AsyncSession, test_tenant: TenantModel, test_user: UserModel) -> MaterialModel:
    """Create a test material."""
    material = MaterialModel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        code="MAT-OVERRIDE-001",
        name="Test Material for Override",
        description="Material for testing price overrides",
        unit_id=uuid4(),
        is_deleted=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(material)
    await db_session.flush()
    return material


@pytest.fixture
async def test_supplier(db_session: AsyncSession, test_tenant: TenantModel, test_user: UserModel) -> SupplierModel:
    """Create a test supplier."""
    supplier = SupplierModel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        supplier_code="SUP-OVERRIDE-001",
        supplier_name="Test Supplier",
        supplier_type="VENDOR",
        is_deleted=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(supplier)
    await db_session.flush()
    return supplier


class TestPriceOverrideRecord:
    """Test PriceOverrideRecord data class."""

    def test_to_dict_conversion(self):
        """Test conversion of PriceOverrideRecord to dictionary."""
        record = PriceOverrideRecord(
            id=uuid4(),
            material_id=uuid4(),
            supplier_id=uuid4(),
            original_suggested_price=Decimal("100.00"),
            override_price=Decimal("95.00"),
            override_reason="Budget constraint",
            override_source="MANUAL",
            overridden_by=uuid4(),
            override_timestamp=datetime.utcnow(),
        )
        
        record_dict = record.to_dict()
        
        assert isinstance(record_dict, dict)
        assert record_dict["override_price"] == Decimal("95.00")
        assert record_dict["override_reason"] == "Budget constraint"
        assert record_dict["override_source"] == "MANUAL"

    def test_to_dict_with_none_values(self):
        """Test conversion with optional None values."""
        override_time = datetime.utcnow()
        record = PriceOverrideRecord(
            id=uuid4(),
            material_id=uuid4(),
            supplier_id=uuid4(),
            original_suggested_price=Decimal("100.00"),
            override_price=Decimal("95.00"),
            override_reason=None,
            override_source=None,
            overridden_by=uuid4(),
            override_timestamp=override_time,
        )
        
        record_dict = record.to_dict()
        
        assert record_dict["override_reason"] is None
        assert record_dict["override_source"] is None


class TestRecordOverride:
    """Test recording price overrides."""

    @pytest.mark.asyncio
    async def test_record_override_success(
        self,
        price_override_service: PriceOverrideService,
        db_session: AsyncSession,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_user: UserModel,
        test_tenant: TenantModel,
    ):
        """Test successful recording of price override."""
        material_id = test_material.id
        supplier_id = test_supplier.id
        original_price = Decimal("100.00")
        override_price = Decimal("95.00")
        
        record = await price_override_service.record_override(
            tenant_id=test_tenant.id,
            material_id=material_id,
            supplier_id=supplier_id,
            original_suggested_price=original_price,
            override_price=override_price,
            override_reason="Budget constraint",
            override_source="MANUAL",
            overridden_by=test_user.id,
        )
        
        assert record is not None
        assert record.material_id == material_id
        assert record.supplier_id == supplier_id
        assert record.original_suggested_price == original_price
        assert record.override_price == override_price
        assert record.override_reason == "Budget constraint"
        
        # Verify persisted to database
        stmt = select(PriceOverrideRecordModel).where(
            PriceOverrideRecordModel.id == record.id,
            PriceOverrideRecordModel.tenant_id == test_tenant.id,
        )
        result = await db_session.execute(stmt)
        persisted = result.scalars().first()
        assert persisted is not None
        assert persisted.override_price == override_price

    @pytest.mark.asyncio
    async def test_record_override_with_none_reason(
        self,
        price_override_service: PriceOverrideService,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_user: UserModel,
        test_tenant: TenantModel,
    ):
        """Test recording override with no reason provided."""
        record = await price_override_service.record_override(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
            original_suggested_price=Decimal("100.00"),
            override_price=Decimal("85.00"),
            override_reason=None,
            override_source="MANUAL",
            overridden_by=test_user.id,
        )
        
        assert record is not None
        assert record.override_reason is None
        assert record.override_price == Decimal("85.00")

    @pytest.mark.asyncio
    async def test_record_override_price_increase(
        self,
        price_override_service: PriceOverrideService,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_user: UserModel,
        test_tenant: TenantModel,
    ):
        """Test recording override where price is increased (not decreased)."""
        record = await price_override_service.record_override(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
            original_suggested_price=Decimal("100.00"),
            override_price=Decimal("110.00"),
            override_reason="Quality premium",
            override_source="MANUAL",
            overridden_by=test_user.id,
        )
        
        assert record.override_price == Decimal("110.00")


class TestGetOverrideHistory:
    """Test retrieving override history."""

    @pytest.mark.asyncio
    async def test_get_override_history_for_material_supplier(
        self,
        price_override_service: PriceOverrideService,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_user: UserModel,
        test_tenant: TenantModel,
    ):
        """Test retrieving override history for specific material-supplier pair."""
        # Record multiple overrides
        await price_override_service.record_override(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
            original_suggested_price=Decimal("100.00"),
            override_price=Decimal("95.00"),
            override_reason="First override",
            override_source="MANUAL",
            overridden_by=test_user.id,
        )
        
        await price_override_service.record_override(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
            original_suggested_price=Decimal("95.00"),
            override_price=Decimal("90.00"),
            override_reason="Second override",
            override_source="MANUAL",
            overridden_by=test_user.id,
        )
        
        history = await price_override_service.get_override_history_for_material_supplier(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )
        
        assert len(history) == 2
        assert history[0].override_reason == "Second override"  # Most recent first
        assert history[1].override_reason == "First override"
        assert all(h.material_id == test_material.id for h in history)
        assert all(h.supplier_id == test_supplier.id for h in history)

    @pytest.mark.asyncio
    async def test_get_override_history_empty(
        self,
        price_override_service: PriceOverrideService,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_tenant: TenantModel,
    ):
        """Test retrieving history for material-supplier pair with no overrides."""
        history = await price_override_service.get_override_history_for_material_supplier(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )
        
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_get_override_history_tenant_isolation(
        self,
        db_session: AsyncSession,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_user: UserModel,
        test_tenant: TenantModel,
    ):
        """Test that override history respects tenant isolation."""
        # Create another tenant and service
        other_tenant = TenantModel(
            id=uuid4(),
            name="Other Tenant",
            is_deleted=False,
        )
        db_session.add(other_tenant)
        await db_session.flush()
        
        other_service = PriceOverrideService(db_session)
        
        # Record override in first tenant
        service1 = PriceOverrideService(db_session)
        await service1.record_override(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
            original_suggested_price=Decimal("100.00"),
            override_price=Decimal("95.00"),
            override_reason="Override in tenant 1",
            override_source="MANUAL",
            overridden_by=test_user.id,
        )
        
        # Query from other tenant should return empty
        history = await other_service.get_override_history_for_material_supplier(
            tenant_id=other_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )
        
        assert len(history) == 0


class TestGetOverrideStatistics:
    """Test computing override statistics."""

    @pytest.mark.asyncio
    async def test_get_override_statistics_basic(
        self,
        price_override_service: PriceOverrideService,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_user: UserModel,
        test_tenant: TenantModel,
    ):
        """Test basic override statistics calculation."""
        # Record overrides with varying discounts
        await price_override_service.record_override(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
            original_suggested_price=Decimal("100.00"),
            override_price=Decimal("100.00"),  # No change
            override_reason="No discount",
            override_source="MANUAL",
            overridden_by=test_user.id,
        )
        
        await price_override_service.record_override(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
            original_suggested_price=Decimal("100.00"),
            override_price=Decimal("90.00"),  # 10% discount
            override_reason="10% discount",
            override_source="MANUAL",
            overridden_by=test_user.id,
        )
        
        await price_override_service.record_override(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
            original_suggested_price=Decimal("100.00"),
            override_price=Decimal("80.00"),  # 20% discount
            override_reason="20% discount",
            override_source="MANUAL",
            overridden_by=test_user.id,
        )
        
        stats = await price_override_service.get_override_statistics(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )
        
        assert stats["total_overrides"] == 3
        assert stats["average_override_price"] == Decimal("90.00")  # (100+90+80)/3
        assert stats["min_override_price"] == Decimal("80.00")
        assert stats["max_override_price"] == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_get_override_statistics_no_data(
        self,
        price_override_service: PriceOverrideService,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_tenant: TenantModel,
    ):
        """Test statistics with no override history."""
        stats = await price_override_service.get_override_statistics(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )
        
        assert stats["total_overrides"] == 0
        assert stats["average_override_price"] is None
        assert stats["min_override_price"] is None
        assert stats["max_override_price"] is None

    @pytest.mark.asyncio
    async def test_get_override_statistics_single_override(
        self,
        price_override_service: PriceOverrideService,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_user: UserModel,
        test_tenant: TenantModel,
    ):
        """Test statistics with single override."""
        await price_override_service.record_override(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
            original_suggested_price=Decimal("100.00"),
            override_price=Decimal("85.00"),
            override_reason="Single override",
            override_source="MANUAL",
            overridden_by=test_user.id,
        )
        
        stats = await price_override_service.get_override_statistics(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )
        
        assert stats["total_overrides"] == 1
        assert stats["average_override_price"] == Decimal("85.00")
        assert stats["min_override_price"] == Decimal("85.00")
        assert stats["max_override_price"] == Decimal("85.00")


class TestAnalyzeOverrideTrends:
    """Test analyzing override trends over time."""

    @pytest.mark.asyncio
    async def test_analyze_override_trends_downward(
        self,
        price_override_service: PriceOverrideService,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_user: UserModel,
        test_tenant: TenantModel,
    ):
        """Test trend analysis showing decreasing prices."""
        now = datetime.utcnow()
        
        # Record overrides over time with decreasing prices
        for i in range(3):
            record_model = PriceOverrideRecordModel(
                id=uuid4(),
                tenant_id=test_tenant.id,
                material_id=test_material.id,
                supplier_id=test_supplier.id,
                original_suggested_price=Decimal("100.00"),
                override_price=Decimal(100 - (i * 5)),  # 100, 95, 90
                override_reason=f"Override {i}",
                override_source="MANUAL",
                overridden_by=test_user.id,
                created_at=now - timedelta(days=i),
                is_deleted=False,
            )
            price_override_service.session.add(record_model)
        
        await price_override_service.session.flush()
        
        trend = await price_override_service.analyze_override_trends(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )
        
        assert trend["trend_direction"] == "DOWNWARD"
        assert trend["total_records_analyzed"] == 3

    @pytest.mark.asyncio
    async def test_analyze_override_trends_upward(
        self,
        price_override_service: PriceOverrideService,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_user: UserModel,
        test_tenant: TenantModel,
    ):
        """Test trend analysis showing increasing prices."""
        now = datetime.utcnow()
        
        # Record overrides over time with increasing prices
        for i in range(3):
            record_model = PriceOverrideRecordModel(
                id=uuid4(),
                tenant_id=test_tenant.id,
                material_id=test_material.id,
                supplier_id=test_supplier.id,
                original_suggested_price=Decimal("100.00"),
                override_price=Decimal(80 + (i * 5)),  # 80, 85, 90
                override_reason=f"Override {i}",
                override_source="MANUAL",
                overridden_by=test_user.id,
                created_at=now - timedelta(days=i),
                is_deleted=False,
            )
            price_override_service.session.add(record_model)
        
        await price_override_service.session.flush()
        
        trend = await price_override_service.analyze_override_trends(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )
        
        assert trend["trend_direction"] == "UPWARD"
        assert trend["total_records_analyzed"] == 3

    @pytest.mark.asyncio
    async def test_analyze_override_trends_stable(
        self,
        price_override_service: PriceOverrideService,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_user: UserModel,
        test_tenant: TenantModel,
    ):
        """Test trend analysis showing stable prices."""
        now = datetime.utcnow()
        
        # Record overrides over time with same price
        for i in range(3):
            record_model = PriceOverrideRecordModel(
                id=uuid4(),
                tenant_id=test_tenant.id,
                material_id=test_material.id,
                supplier_id=test_supplier.id,
                original_suggested_price=Decimal("100.00"),
                override_price=Decimal("90.00"),  # Same price every time
                override_reason=f"Override {i}",
                override_source="MANUAL",
                overridden_by=test_user.id,
                created_at=now - timedelta(days=i),
                is_deleted=False,
            )
            price_override_service.session.add(record_model)
        
        await price_override_service.session.flush()
        
        trend = await price_override_service.analyze_override_trends(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )
        
        assert trend["trend_direction"] == "STABLE"
        assert trend["total_records_analyzed"] == 3

    @pytest.mark.asyncio
    async def test_analyze_override_trends_insufficient_data(
        self,
        price_override_service: PriceOverrideService,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        test_tenant: TenantModel,
    ):
        """Test trend analysis with insufficient data points."""
        trend = await price_override_service.analyze_override_trends(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )
        
        assert trend["trend_direction"] == "INSUFFICIENT_DATA"
        assert trend["total_records_analyzed"] == 0
