"""
End-to-End tests for Phase 2 Procurement Pricing (Priority 2.1-2.6).

Complete workflow testing:
1. Create supplier agreement (Level 1)
2. Get pricing suggestions (all 6 levels)
3. Record price override
4. Verify override tracking and analytics
"""

import pytest
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.procurement.pricing.po_pricing_engine import POPricingEngine
from backend.app.application.procurement.pricing.quotation_lookup_service import SupplierQuotationLookupService
from backend.app.application.procurement.pricing.purchase_history_lookup_service import PurchaseHistoryLookupService
from backend.app.application.procurement.pricing.any_supplier_history_lookup_service import AnySupplierHistoryLookupService
from backend.app.application.procurement.pricing.price_override_service import PriceOverrideService
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.procurement_pricing_models import (
    SupplierPriceAgreementModel,
    StandardCostRevisionModel,
    PriceOverrideRecordModel,
)
from backend.app.infrastructure.persistence.models.quality_model import SupplierQuotationModel
from backend.app.infrastructure.persistence.models.grn_model import (
    GoodsReceiptNoteModel,
    GRNLineModel,
)


class TestSixLevelPricingE2E:
    """End-to-end tests for complete pricing workflow."""

    @pytest.fixture
    async def setup(self, e2e_db_session: AsyncSession):
        """Setup test data."""
        # Create tenant and user
        tenant = TenantModel(id=uuid4(), name="E2E Test Tenant", is_deleted=False)
        e2e_db_session.add(tenant)
        await e2e_db_session.flush()

        user = UserModel(
            id=uuid4(),
            tenant_id=tenant.id,
            email="e2e@test.com",
            username="e2euser",
            full_name="E2E User",
            password_hash="hash",
            is_active=True,
            is_deleted=False,
        )
        e2e_db_session.add(user)
        await e2e_db_session.flush()

        # Create material
        material = MaterialModel(
            id=uuid4(),
            tenant_id=tenant.id,
            code="MAT-E2E-001",
            name="E2E Test Material",
            unit_id=uuid4(),
            is_deleted=False,
            created_by=user.id,
            updated_by=user.id,
        )
        e2e_db_session.add(material)
        await e2e_db_session.flush()

        # Create supplier
        supplier = SupplierModel(
            id=uuid4(),
            tenant_id=tenant.id,
            supplier_code="SUP-E2E-001",
            supplier_name="E2E Supplier",
            supplier_type="VENDOR",
            is_deleted=False,
            created_by=user.id,
            updated_by=user.id,
        )
        e2e_db_session.add(supplier)
        await e2e_db_session.flush()

        return {"tenant": tenant, "user": user, "material": material, "supplier": supplier}

    @pytest.mark.asyncio
    async def test_complete_pricing_workflow(self, e2e_db_session: AsyncSession, setup):
        """
        Test complete workflow:
        1. Create supplier agreement (Level 1)
        2. Create quotation (Level 2)
        3. Create GRN history (Levels 3 & 4)
        4. Create standard cost (Level 5)
        5. Get 6-level pricing suggestions
        6. Record override
        7. Verify override tracking
        """
        tenant = setup["tenant"]
        user = setup["user"]
        material = setup["material"]
        supplier = setup["supplier"]

        # ──────────────────────────────────────────────────────────────────────────
        # STEP 1: Create Level 1 - Active Supplier Agreement
        # ──────────────────────────────────────────────────────────────────────────
        agreement = SupplierPriceAgreementModel(
            id=uuid4(),
            tenant_id=tenant.id,
            supplier_id=supplier.id,
            material_id=material.id,
            base_price=Decimal("50.00"),
            status="ACTIVE",
            currency_code="USD",
            effective_from=datetime.utcnow(),
            effective_to=datetime.utcnow() + timedelta(days=365),
            is_deleted=False,
            created_by=user.id,
            updated_by=user.id,
        )
        e2e_db_session.add(agreement)
        await e2e_db_session.flush()

        # ──────────────────────────────────────────────────────────────────────────
        # STEP 2: Create Level 2 - Approved Quotation
        # ──────────────────────────────────────────────────────────────────────────
        quotation = SupplierQuotationModel(
            id=uuid4(),
            tenant_id=tenant.id,
            supplier_id=supplier.id,
            material_id=material.id,
            quoted_price=Decimal("55.00"),
            status="APPROVED",
            is_deleted=False,
            created_by=user.id,
            updated_by=user.id,
        )
        e2e_db_session.add(quotation)
        await e2e_db_session.flush()

        # ──────────────────────────────────────────────────────────────────────────
        # STEP 3: Create Levels 3 & 4 - GRN History
        # ──────────────────────────────────────────────────────────────────────────
        grn = GoodsReceiptNoteModel(
            id=uuid4(),
            tenant_id=tenant.id,
            supplier_id=supplier.id,
            grn_number="GRN-E2E-001",
            status="received",
            is_deleted=False,
            created_by=user.id,
            updated_by=user.id,
        )
        e2e_db_session.add(grn)
        await e2e_db_session.flush()

        grn_line = GRNLineModel(
            id=uuid4(),
            tenant_id=tenant.id,
            grn_id=grn.id,
            material_id=material.id,
            received_quantity=Decimal("100"),
            unit_price=Decimal("60.00"),
            is_deleted=False,
            created_by=user.id,
            updated_by=user.id,
        )
        e2e_db_session.add(grn_line)
        await e2e_db_session.flush()

        # ──────────────────────────────────────────────────────────────────────────
        # STEP 4: Create Level 5 - Approved Standard Cost
        # ──────────────────────────────────────────────────────────────────────────
        standard_cost = StandardCostRevisionModel(
            id=uuid4(),
            tenant_id=tenant.id,
            material_id=material.id,
            standard_cost=Decimal("70.00"),
            status="APPROVED",
            is_deleted=False,
            created_by=user.id,
            updated_by=user.id,
        )
        e2e_db_session.add(standard_cost)
        await e2e_db_session.flush()

        # ──────────────────────────────────────────────────────────────────────────
        # STEP 5: Get 6-Level Pricing Suggestions
        # ──────────────────────────────────────────────────────────────────────────
        quotation_service = SupplierQuotationLookupService(e2e_db_session)
        history_service = PurchaseHistoryLookupService(e2e_db_session)
        any_supplier_service = AnySupplierHistoryLookupService(e2e_db_session)
        engine = POPricingEngine(
            quotation_service=quotation_service,
            history_service=history_service,
            any_supplier_service=any_supplier_service,
        )

        pricing = await engine.get_pricing_suggestions(
            tenant_id=tenant.id,
            material_id=material.id,
            supplier_id=supplier.id,
        )

        # Verify Level 1 (agreement) was selected
        assert pricing is not None, "Should have pricing suggestion"
        assert pricing.suggested_price == Decimal("50.00"), "Should select Level 1 agreement price"
        assert pricing.pricing_source == "SUPPLIER_AGREEMENT", "Should be from supplier agreement"
        assert pricing.confidence_level == "HIGH", "Should have HIGH confidence"
        assert pricing.level_number == 1, "Should be level 1"

        # ──────────────────────────────────────────────────────────────────────────
        # STEP 6: Record Price Override
        # ──────────────────────────────────────────────────────────────────────────
        override_service = PriceOverrideService(e2e_db_session)

        override_record = await override_service.record_override(
            tenant_id=tenant.id,
            material_id=material.id,
            supplier_id=supplier.id,
            original_suggested_price=Decimal("50.00"),
            override_price=Decimal("48.00"),  # 4% discount
            override_reason="Bulk discount negotiated",
            override_source="MANUAL",
            overridden_by=user.id,
        )

        assert override_record is not None, "Should have created override record"
        assert override_record.material_id == material.id
        assert override_record.supplier_id == supplier.id
        assert override_record.original_suggested_price == Decimal("50.00")
        assert override_record.override_price == Decimal("48.00")

        # ──────────────────────────────────────────────────────────────────────────
        # STEP 7: Verify Override Tracking and Analytics
        # ──────────────────────────────────────────────────────────────────────────

        # Get override history
        history = await override_service.get_override_history_for_material_supplier(
            tenant_id=tenant.id,
            material_id=material.id,
            supplier_id=supplier.id,
        )

        assert len(history) == 1, "Should have 1 override in history"
        assert history[0].override_price == Decimal("48.00")

        # Get statistics
        stats = await override_service.get_override_statistics(
            tenant_id=tenant.id,
            material_id=material.id,
            supplier_id=supplier.id,
        )

        assert stats["total_overrides"] == 1
        assert stats["average_override_price"] == Decimal("48.00")
        assert stats["min_override_price"] == Decimal("48.00")
        assert stats["max_override_price"] == Decimal("48.00")

        # Get trends
        trend = await override_service.analyze_override_trends(
            tenant_id=tenant.id,
            material_id=material.id,
            supplier_id=supplier.id,
        )

        assert trend["trend_direction"] == "INSUFFICIENT_DATA", "Single override = insufficient data for trend"
        assert trend["total_records_analyzed"] == 1

    @pytest.mark.asyncio
    async def test_fallback_when_level_1_unavailable(self, e2e_db_session: AsyncSession, setup):
        """Test that pricing falls back to Level 2 when Level 1 (agreement) is not available."""
        tenant = setup["tenant"]
        user = setup["user"]
        material = setup["material"]
        supplier = setup["supplier"]

        # Only create Level 2 (quotation), no Level 1 agreement
        quotation = SupplierQuotationModel(
            id=uuid4(),
            tenant_id=tenant.id,
            supplier_id=supplier.id,
            material_id=material.id,
            quoted_price=Decimal("55.00"),
            status="APPROVED",
            is_deleted=False,
            created_by=user.id,
            updated_by=user.id,
        )
        e2e_db_session.add(quotation)
        await e2e_db_session.flush()

        # Get pricing
        quotation_service = SupplierQuotationLookupService(e2e_db_session)
        history_service = PurchaseHistoryLookupService(e2e_db_session)
        any_supplier_service = AnySupplierHistoryLookupService(e2e_db_session)
        engine = POPricingEngine(
            quotation_service=quotation_service,
            history_service=history_service,
            any_supplier_service=any_supplier_service,
        )

        pricing = await engine.get_pricing_suggestions(
            tenant_id=tenant.id,
            material_id=material.id,
            supplier_id=supplier.id,
        )

        # Verify Level 2 (quotation) was selected
        assert pricing is not None
        assert pricing.suggested_price == Decimal("55.00")
        assert pricing.pricing_source == "QUOTATION"
        assert pricing.confidence_level == "MEDIUM"
        assert pricing.level_number == 2

    @pytest.mark.asyncio
    async def test_multi_override_trend_analysis(self, e2e_db_session: AsyncSession, setup):
        """Test trend analysis with multiple overrides."""
        tenant = setup["tenant"]
        user = setup["user"]
        material = setup["material"]
        supplier = setup["supplier"]

        override_service = PriceOverrideService(e2e_db_session)
        now = datetime.utcnow()

        # Record 3 overrides with increasing prices (downward trend in costs)
        for i in range(3):
            record_model = PriceOverrideRecordModel(
                id=uuid4(),
                tenant_id=tenant.id,
                material_id=material.id,
                supplier_id=supplier.id,
                original_suggested_price=Decimal("100.00"),
                override_price=Decimal(100 - (i * 5)),  # 100, 95, 90
                override_reason=f"Override {i}",
                override_source="MANUAL",
                overridden_by=user.id,
                created_at=now - timedelta(days=i),
                is_deleted=False,
            )
            e2e_db_session.add(record_model)

        await e2e_db_session.flush()

        # Get statistics
        stats = await override_service.get_override_statistics(
            tenant_id=tenant.id,
            material_id=material.id,
            supplier_id=supplier.id,
        )

        assert stats["total_overrides"] == 3
        assert stats["average_override_price"] == Decimal("95.00")  # (100 + 95 + 90) / 3
        assert stats["min_override_price"] == Decimal("90.00")
        assert stats["max_override_price"] == Decimal("100.00")

        # Get trends
        trend = await override_service.analyze_override_trends(
            tenant_id=tenant.id,
            material_id=material.id,
            supplier_id=supplier.id,
        )

        assert trend["trend_direction"] == "DOWNWARD"
        assert trend["total_records_analyzed"] == 3

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_pricing(self, e2e_db_session: AsyncSession, setup):
        """Verify tenant isolation - pricing from other tenants not visible."""
        tenant1 = setup["tenant"]
        user1 = setup["user"]
        material1 = setup["material"]
        supplier1 = setup["supplier"]

        # Create second tenant with its own data
        tenant2 = TenantModel(id=uuid4(), name="Tenant 2", is_deleted=False)
        e2e_db_session.add(tenant2)
        await e2e_db_session.flush()

        user2 = UserModel(
            id=uuid4(),
            tenant_id=tenant2.id,
            email="user2@test.com",
            username="user2",
            full_name="User 2",
            password_hash="hash",
            is_active=True,
            is_deleted=False,
        )
        e2e_db_session.add(user2)
        await e2e_db_session.flush()

        # Create agreement in tenant2 (should not be visible to tenant1)
        agreement_tenant2 = SupplierPriceAgreementModel(
            id=uuid4(),
            tenant_id=tenant2.id,
            supplier_id=supplier1.id,
            material_id=material1.id,
            base_price=Decimal("30.00"),  # Much cheaper
            status="ACTIVE",
            currency_code="USD",
            effective_from=datetime.utcnow(),
            effective_to=datetime.utcnow() + timedelta(days=365),
            is_deleted=False,
            created_by=user2.id,
            updated_by=user2.id,
        )
        e2e_db_session.add(agreement_tenant2)
        await e2e_db_session.flush()

        # Query pricing for tenant1 (should not see tenant2's agreement)
        quotation_service = SupplierQuotationLookupService(e2e_db_session)
        history_service = PurchaseHistoryLookupService(e2e_db_session)
        any_supplier_service = AnySupplierHistoryLookupService(e2e_db_session)
        engine = POPricingEngine(
            quotation_service=quotation_service,
            history_service=history_service,
            any_supplier_service=any_supplier_service,
        )

        pricing = await engine.get_pricing_suggestions(
            tenant_id=tenant1.id,
            material_id=material1.id,
            supplier_id=supplier1.id,
        )

        # Should return None (no pricing for tenant1)
        assert pricing is None, "Tenant1 should not see Tenant2's pricing"
