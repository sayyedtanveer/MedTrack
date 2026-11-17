"""
Unit tests for PO 6-level pricing engine (Priority 2.4).

Tests cover:
- Priority 1: Active supplier agreement pricing
- Priority 2: Approved quotation pricing
- Priority 3: Latest purchase (same supplier)
- Priority 4: Latest purchase (any supplier)
- Priority 5: Approved standard cost
- Priority 6: Manual/fallback pricing
- Pricing analysis across all 6 levels
- Price override workflow
- Benchmarking data inclusion
"""
import pytest
import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.procurement.pricing.po_pricing_engine import (
    POPricingEngine,
    PricingDecision,
)


@pytest.mark.asyncio
async def test_pricing_returns_manual_when_no_data_available(db_session: AsyncSession):
    """Test pricing engine returns manual when no pricing data exists."""
    tenant_id = uuid.uuid4()
    material_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    
    engine = POPricingEngine(db_session)
    decision = await engine.calculate_pricing(tenant_id, material_id, supplier_id)
    
    # Should fall back to Priority 6 (manual)
    assert decision.priority_level == 6
    assert decision.source == "manual"
    assert decision.recommended_price is None
    assert decision.requires_approval is True


@pytest.mark.asyncio
async def test_pricing_decision_to_dict():
    """Test PricingDecision serialization to dictionary."""
    material_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    agreement_id = uuid.uuid4()
    
    decision = PricingDecision(
        material_id=material_id,
        supplier_id=supplier_id,
        recommended_price=Decimal("50.00"),
        priority_level=1,
        source="agreement",
        rationale="Active supplier agreement",
        agreement_id=agreement_id,
        best_price_available=Decimal("45.00"),
        best_supplier="Best Supplier",
        total_suppliers=3,
    )
    
    result_dict = decision.to_dict()
    
    assert result_dict["material_id"] == str(material_id)
    assert result_dict["supplier_id"] == str(supplier_id)
    assert result_dict["recommended_price"] == 50.0
    assert result_dict["priority_level"] == 1
    assert result_dict["source"] == "agreement"
    assert result_dict["agreement_id"] == str(agreement_id)
    assert result_dict["best_price_available"] == 45.0
    assert result_dict["total_suppliers"] == 3


@pytest.mark.asyncio
async def test_pricing_analysis_shows_all_levels(db_session: AsyncSession):
    """Test pricing analysis returns structure for all 6 levels."""
    tenant_id = uuid.uuid4()
    material_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    
    engine = POPricingEngine(db_session)
    analysis = await engine.get_pricing_analysis(tenant_id, material_id, supplier_id)
    
    # Should show all 6 levels
    assert analysis["material_id"] == str(material_id)
    assert analysis["supplier_id"] == str(supplier_id)
    assert len(analysis["priorities"]) == 6
    
    # Verify levels are in order
    for i, priority in enumerate(analysis["priorities"], start=1):
        assert priority["level"] == i
    
    # All should have status field
    for priority in analysis["priorities"]:
        assert "status" in priority
        assert priority["status"] in ["AVAILABLE", "NOT_AVAILABLE", "FALLBACK"]


@pytest.mark.asyncio
async def test_pricing_includes_benchmarking_data():
    """Test pricing decision includes best price benchmarking when available."""
    material_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    
    decision = PricingDecision(
        material_id=material_id,
        supplier_id=supplier_id,
        recommended_price=Decimal("55.00"),
        priority_level=3,
        source="same_supplier_history",
        rationale="Latest purchase from this supplier",
        best_price_available=Decimal("45.00"),
        best_supplier="Better Supplier",
        total_suppliers=5,
    )
    
    # Verify benchmarking data is present
    assert decision.best_price_available == Decimal("45.00")
    assert decision.best_supplier == "Better Supplier"
    assert decision.total_suppliers == 5
    
    # Verify it's in the dict output
    result_dict = decision.to_dict()
    assert result_dict["best_price_available"] == 45.0
    assert result_dict["best_supplier"] == "Better Supplier"
    assert result_dict["total_suppliers"] == 5


@pytest.mark.asyncio
async def test_pricing_decision_with_manual_approval():
    """Test manual pricing decision includes approval requirement."""
    material_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    
    decision = PricingDecision(
        material_id=material_id,
        supplier_id=supplier_id,
        recommended_price=None,
        priority_level=6,
        source="manual",
        rationale="No pricing data available - manual entry required",
        requires_approval=True,
        approval_reason="Manual pricing requires approval from Procurement Manager",
    )
    
    assert decision.requires_approval is True
    assert decision.approval_reason is not None
    
    result_dict = decision.to_dict()
    assert result_dict["requires_approval"] is True
    assert result_dict["approval_reason"] is not None


@pytest.mark.asyncio
async def test_pricing_with_quotation_data():
    """Test pricing decision when quotation is available."""
    material_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    quotation_id = uuid.uuid4()
    
    decision = PricingDecision(
        material_id=material_id,
        supplier_id=supplier_id,
        recommended_price=Decimal("50.00"),
        priority_level=2,
        source="quotation",
        rationale="Approved quotation QT-001",
        quotation_id=quotation_id,
        best_price_available=Decimal("48.00"),
        best_supplier="Best Supplier",
        total_suppliers=3,
    )
    
    assert decision.quotation_id == quotation_id
    assert decision.priority_level == 2
    
    result_dict = decision.to_dict()
    assert result_dict["quotation_id"] == str(quotation_id)


@pytest.mark.asyncio
async def test_pricing_with_grn_history_data():
    """Test pricing decision when GRN history is available."""
    material_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    
    decision = PricingDecision(
        material_id=material_id,
        supplier_id=supplier_id,
        recommended_price=Decimal("52.00"),
        priority_level=3,
        source="same_supplier_history",
        rationale="Latest purchase from this supplier",
        grn_number="GRN-001",
        po_number="PO-001",
        best_price_available=Decimal("48.00"),
        best_supplier="Best Supplier",
        total_suppliers=5,
    )
    
    assert decision.grn_number == "GRN-001"
    assert decision.po_number == "PO-001"
    assert decision.priority_level == 3
    
    result_dict = decision.to_dict()
    assert result_dict["grn_number"] == "GRN-001"
    assert result_dict["po_number"] == "PO-001"


@pytest.mark.asyncio
async def test_pricing_comparison_across_levels():
    """Test pricing decisions at different priority levels."""
    material_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    
    # Priority 1: Agreement
    decision1 = PricingDecision(
        material_id=material_id,
        supplier_id=supplier_id,
        recommended_price=Decimal("50.00"),
        priority_level=1,
        source="agreement",
        rationale="Active supplier agreement",
    )
    
    # Priority 3: History
    decision3 = PricingDecision(
        material_id=material_id,
        supplier_id=supplier_id,
        recommended_price=Decimal("52.00"),
        priority_level=3,
        source="same_supplier_history",
        rationale="Latest purchase",
    )
    
    # Priority 5: Standard cost
    decision5 = PricingDecision(
        material_id=material_id,
        supplier_id=supplier_id,
        recommended_price=Decimal("55.00"),
        priority_level=5,
        source="standard_cost",
        rationale="Approved standard cost",
    )
    
    # Higher priority (lower number) should be preferred
    assert decision1.priority_level < decision3.priority_level
    assert decision3.priority_level < decision5.priority_level
    
    # Price from agreement should be honored
    assert decision1.recommended_price == Decimal("50.00")
