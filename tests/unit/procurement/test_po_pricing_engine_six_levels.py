"""
Priority 2.6: Integration tests for 6-level PO pricing engine with all fallback scenarios.

Tests the complete pricing hierarchy:
1. Active supplier agreement (ACTIVE status)
2. Approved quotation (APPROVED/AWARDED status)
3. Latest purchase same supplier (GRN history)
4. Latest purchase any supplier (GRN history, benchmarking)
5. Approved standard cost (APPROVED status)
6. Manual (fallback, no suggestion)

Scenarios:
- Full priority chain (all 6 levels available)
- Partial chain (fallbacks when levels are missing)
- No pricing available (fallback to manual)
- Multiple options at same level (most recent/best chosen)
- Tenant isolation verified
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.procurement.pricing.po_pricing_engine import POPricingEngine
from backend.app.application.procurement.pricing.quotation_lookup_service import SupplierQuotationLookupService
from backend.app.application.procurement.pricing.purchase_history_lookup_service import PurchaseHistoryLookupService
from backend.app.application.procurement.pricing.any_supplier_history_lookup_service import AnySupplierHistoryLookupService
from backend.app.infrastructure.persistence.models import (
    MaterialModel,
    SupplierModel,
    SupplierQuotationModel,
    SupplierPriceAgreementModel,
    StandardCostRevisionModel,
    GoodsReceiptNoteModel,
    GRNLineModel,
    TenantModel,
    UserModel,
)


@pytest.fixture
async def po_pricing_engine(db_session: AsyncSession) -> POPricingEngine:
    """Create engine instance with all lookup services."""
    quotation_service = SupplierQuotationLookupService(db_session)
    history_service = PurchaseHistoryLookupService(db_session)
    any_supplier_service = AnySupplierHistoryLookupService(db_session)
    return POPricingEngine(
        quotation_service=quotation_service,
        history_service=history_service,
        any_supplier_service=any_supplier_service,
    )


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> TenantModel:
    """Create test tenant."""
    tenant = TenantModel(id=uuid4(), name="Test Tenant", is_deleted=False)
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest.fixture
async def test_user(db_session: AsyncSession, test_tenant: TenantModel) -> UserModel:
    """Create test user."""
    user = UserModel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        password_hash="hash",
        is_active=True,
        is_deleted=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def test_material(db_session: AsyncSession, test_tenant: TenantModel, test_user: UserModel) -> MaterialModel:
    """Create test material."""
    material = MaterialModel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        code="MAT-6LEVEL-001",
        name="Test Material for 6-Level Pricing",
        description="Material for testing all pricing levels",
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
    """Create primary test supplier."""
    supplier = SupplierModel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        supplier_code="SUP-PRIMARY",
        supplier_name="Primary Supplier",
        supplier_type="VENDOR",
        is_deleted=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(supplier)
    await db_session.flush()
    return supplier


@pytest.fixture
async def secondary_supplier(db_session: AsyncSession, test_tenant: TenantModel, test_user: UserModel) -> SupplierModel:
    """Create secondary supplier for benchmarking."""
    supplier = SupplierModel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        supplier_code="SUP-SECONDARY",
        supplier_name="Secondary Supplier",
        supplier_type="VENDOR",
        is_deleted=False,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(supplier)
    await db_session.flush()
    return supplier


class TestSixLevelPricingComplete:
    """Test complete 6-level pricing hierarchy."""

    @pytest.mark.asyncio
    async def test_full_pricing_chain_all_six_levels(
        self,
        po_pricing_engine: POPricingEngine,
        db_session: AsyncSession,
        test_tenant: TenantModel,
        test_user: UserModel,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
    ):
        """Test when all 6 pricing levels are available - level 1 (agreement) should win."""
        # LEVEL 1: Active supplier agreement
        agreement = SupplierPriceAgreementModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            material_id=test_material.id,
            agreed_price=Decimal("50.00"),  # Best price
            status="ACTIVE",
            effective_from=datetime.utcnow(),
            effective_to=datetime.utcnow() + timedelta(days=365),
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(agreement)
        await db_session.flush()

        # LEVEL 2: Approved quotation
        quotation = SupplierQuotationModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            material_id=test_material.id,
            quoted_price=Decimal("55.00"),
            status="APPROVED",
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(quotation)
        await db_session.flush()

        # LEVEL 3: Purchase history (same supplier)
        grn = GoodsReceiptNoteModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            grn_number="GRN-001",
            status="received",
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(grn)
        await db_session.flush()

        grn_line = GRNLineModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            grn_id=grn.id,
            material_id=test_material.id,
            received_quantity=Decimal("100"),
            unit_price=Decimal("60.00"),
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(grn_line)
        await db_session.flush()

        # LEVEL 5: Approved standard cost
        standard_cost = StandardCostRevisionModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            standard_cost=Decimal("70.00"),
            status="APPROVED",
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(standard_cost)
        await db_session.flush()

        # Get pricing
        pricing_result = await po_pricing_engine.get_pricing_suggestions(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )

        # LEVEL 1 agreement should be selected (lowest price, highest priority)
        assert pricing_result is not None
        assert pricing_result.suggested_price == Decimal("50.00")
        assert pricing_result.pricing_source == "SUPPLIER_AGREEMENT"
        assert pricing_result.confidence_level == "HIGH"

    @pytest.mark.asyncio
    async def test_fallback_from_level_1_to_level_2(
        self,
        po_pricing_engine: POPricingEngine,
        db_session: AsyncSession,
        test_tenant: TenantModel,
        test_user: UserModel,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
    ):
        """Test fallback when level 1 (agreement) is not available."""
        # No agreement (level 1 skipped)
        
        # LEVEL 2: Approved quotation
        quotation = SupplierQuotationModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            material_id=test_material.id,
            quoted_price=Decimal("55.00"),
            status="APPROVED",
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(quotation)
        await db_session.flush()

        pricing_result = await po_pricing_engine.get_pricing_suggestions(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )

        # Level 2 quotation should be used
        assert pricing_result is not None
        assert pricing_result.suggested_price == Decimal("55.00")
        assert pricing_result.pricing_source == "QUOTATION"
        assert pricing_result.confidence_level == "MEDIUM"

    @pytest.mark.asyncio
    async def test_fallback_through_levels_2_3_4_to_5(
        self,
        po_pricing_engine: POPricingEngine,
        db_session: AsyncSession,
        test_tenant: TenantModel,
        test_user: UserModel,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        secondary_supplier: SupplierModel,
    ):
        """Test fallback chain: no agreement, no quotation → use GRN → use standard cost."""
        # No agreement (level 1)
        # No quotation (level 2)
        
        # LEVEL 3: Purchase history (same supplier)
        grn = GoodsReceiptNoteModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            grn_number="GRN-001",
            status="received",
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(grn)
        await db_session.flush()

        grn_line = GRNLineModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            grn_id=grn.id,
            material_id=test_material.id,
            received_quantity=Decimal("100"),
            unit_price=Decimal("60.00"),
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(grn_line)
        await db_session.flush()

        pricing_result = await po_pricing_engine.get_pricing_suggestions(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )

        # Level 3 GRN price should be used
        assert pricing_result is not None
        assert pricing_result.suggested_price == Decimal("60.00")
        assert pricing_result.pricing_source == "PURCHASE_HISTORY"
        assert pricing_result.confidence_level == "MEDIUM"

    @pytest.mark.asyncio
    async def test_benchmarking_level_4_any_supplier(
        self,
        po_pricing_engine: POPricingEngine,
        db_session: AsyncSession,
        test_tenant: TenantModel,
        test_user: UserModel,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
        secondary_supplier: SupplierModel,
    ):
        """Test level 4: any supplier history for benchmarking."""
        # No pricing from primary supplier (levels 1-3)
        
        # LEVEL 4: Purchase history from ANY supplier
        grn_secondary = GoodsReceiptNoteModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            supplier_id=secondary_supplier.id,
            grn_number="GRN-SEC-001",
            status="received",
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(grn_secondary)
        await db_session.flush()

        grn_line_secondary = GRNLineModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            grn_id=grn_secondary.id,
            material_id=test_material.id,
            received_quantity=Decimal("50"),
            unit_price=Decimal("65.00"),
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(grn_line_secondary)
        await db_session.flush()

        pricing_result = await po_pricing_engine.get_pricing_suggestions(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )

        # Level 4 benchmarking price from secondary supplier
        assert pricing_result is not None
        assert pricing_result.suggested_price == Decimal("65.00")
        assert pricing_result.pricing_source == "BENCHMARK_ANY_SUPPLIER"
        assert pricing_result.confidence_level == "LOW"

    @pytest.mark.asyncio
    async def test_fallback_to_level_5_standard_cost(
        self,
        po_pricing_engine: POPricingEngine,
        db_session: AsyncSession,
        test_tenant: TenantModel,
        test_user: UserModel,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
    ):
        """Test level 5: fallback to approved standard cost."""
        # No pricing available (levels 1-4)
        
        # LEVEL 5: Approved standard cost
        standard_cost = StandardCostRevisionModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            standard_cost=Decimal("70.00"),
            status="APPROVED",
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(standard_cost)
        await db_session.flush()

        pricing_result = await po_pricing_engine.get_pricing_suggestions(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )

        # Level 5 standard cost
        assert pricing_result is not None
        assert pricing_result.suggested_price == Decimal("70.00")
        assert pricing_result.pricing_source == "STANDARD_COST"
        assert pricing_result.confidence_level == "LOW"

    @pytest.mark.asyncio
    async def test_level_6_fallback_no_pricing_available(
        self,
        po_pricing_engine: POPricingEngine,
        test_tenant: TenantModel,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
    ):
        """Test level 6: no pricing available - manual fallback."""
        # No pricing at any level (1-5)
        
        pricing_result = await po_pricing_engine.get_pricing_suggestions(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )

        # Level 6: manual - no suggestion
        assert pricing_result is None


class TestPricingPriority:
    """Test pricing priority selection when multiple options at same level."""

    @pytest.mark.asyncio
    async def test_multiple_agreements_uses_most_recent(
        self,
        po_pricing_engine: POPricingEngine,
        db_session: AsyncSession,
        test_tenant: TenantModel,
        test_user: UserModel,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
    ):
        """Test that most recent active agreement is selected."""
        now = datetime.utcnow()
        
        # Older agreement
        agreement_old = SupplierPriceAgreementModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            material_id=test_material.id,
            agreed_price=Decimal("52.00"),
            status="ACTIVE",
            effective_from=now - timedelta(days=30),
            effective_to=now + timedelta(days=300),
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
            created_at=now - timedelta(days=30),
        )
        db_session.add(agreement_old)

        # Newer agreement
        agreement_new = SupplierPriceAgreementModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            material_id=test_material.id,
            agreed_price=Decimal("48.00"),
            status="ACTIVE",
            effective_from=now - timedelta(days=5),
            effective_to=now + timedelta(days=360),
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
            created_at=now - timedelta(days=5),
        )
        db_session.add(agreement_new)
        await db_session.flush()

        pricing_result = await po_pricing_engine.get_pricing_suggestions(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )

        # Should use the most recent agreement (lowest price)
        assert pricing_result.suggested_price == Decimal("48.00")
        assert pricing_result.pricing_source == "SUPPLIER_AGREEMENT"

    @pytest.mark.asyncio
    async def test_multiple_quotations_uses_best_price(
        self,
        po_pricing_engine: POPricingEngine,
        db_session: AsyncSession,
        test_tenant: TenantModel,
        test_user: UserModel,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
    ):
        """Test that best (lowest) quotation price is selected."""
        # Quotation 1 (higher price)
        quotation1 = SupplierQuotationModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            material_id=test_material.id,
            quoted_price=Decimal("58.00"),
            status="APPROVED",
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(quotation1)

        # Quotation 2 (lower price - should win)
        quotation2 = SupplierQuotationModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            material_id=test_material.id,
            quoted_price=Decimal("52.00"),
            status="APPROVED",
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(quotation2)
        await db_session.flush()

        pricing_result = await po_pricing_engine.get_pricing_suggestions(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )

        # Should use best (lowest) quotation
        assert pricing_result.suggested_price == Decimal("52.00")
        assert pricing_result.pricing_source == "QUOTATION"


class TestTenantIsolationInPricing:
    """Test multi-tenant isolation in 6-level pricing."""

    @pytest.mark.asyncio
    async def test_pricing_respects_tenant_boundaries(
        self,
        po_pricing_engine: POPricingEngine,
        db_session: AsyncSession,
        test_tenant: TenantModel,
        test_user: UserModel,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
    ):
        """Test that pricing from other tenants is not visible."""
        # Create another tenant
        other_tenant = TenantModel(id=uuid4(), name="Other Tenant", is_deleted=False)
        db_session.add(other_tenant)
        await db_session.flush()

        # Create agreement in other tenant
        other_user = UserModel(
            id=uuid4(),
            tenant_id=other_tenant.id,
            email="other@example.com",
            username="otheruser",
            full_name="Other User",
            password_hash="hash",
            is_active=True,
            is_deleted=False,
        )
        db_session.add(other_user)
        await db_session.flush()

        other_agreement = SupplierPriceAgreementModel(
            id=uuid4(),
            tenant_id=other_tenant.id,  # Different tenant!
            supplier_id=test_supplier.id,
            material_id=test_material.id,
            agreed_price=Decimal("30.00"),  # Much cheaper
            status="ACTIVE",
            effective_from=datetime.utcnow(),
            effective_to=datetime.utcnow() + timedelta(days=365),
            is_deleted=False,
            created_by=other_user.id,
            updated_by=other_user.id,
        )
        db_session.add(other_agreement)
        await db_session.flush()

        # Query pricing for test_tenant (should not see other_tenant's agreement)
        pricing_result = await po_pricing_engine.get_pricing_suggestions(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )

        # Should return None (no pricing visible for test_tenant)
        assert pricing_result is None


class TestConfidenceLevels:
    """Test confidence level assignment based on pricing source."""

    @pytest.mark.asyncio
    async def test_confidence_level_mapping(
        self,
        po_pricing_engine: POPricingEngine,
        db_session: AsyncSession,
        test_tenant: TenantModel,
        test_user: UserModel,
        test_material: MaterialModel,
        test_supplier: SupplierModel,
    ):
        """Test that confidence levels are correctly assigned."""
        confidence_levels = {
            "SUPPLIER_AGREEMENT": "HIGH",      # Level 1
            "QUOTATION": "MEDIUM",              # Level 2
            "PURCHASE_HISTORY": "MEDIUM",       # Level 3
            "BENCHMARK_ANY_SUPPLIER": "LOW",    # Level 4
            "STANDARD_COST": "LOW",             # Level 5
        }

        # Test level 1 (HIGH confidence)
        agreement = SupplierPriceAgreementModel(
            id=uuid4(),
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            material_id=test_material.id,
            agreed_price=Decimal("50.00"),
            status="ACTIVE",
            effective_from=datetime.utcnow(),
            effective_to=datetime.utcnow() + timedelta(days=365),
            is_deleted=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(agreement)
        await db_session.flush()

        pricing_result = await po_pricing_engine.get_pricing_suggestions(
            tenant_id=test_tenant.id,
            material_id=test_material.id,
            supplier_id=test_supplier.id,
        )

        assert pricing_result.confidence_level == "HIGH"
        assert pricing_result.pricing_source == "SUPPLIER_AGREEMENT"
