"""
Unit tests — Outside Making Cost rollup.

Tests follow the approved formula:
  total_cost (per unit) = material_cost + operation_cost + making_cost

Nesting example from requirements:
  Child BOM: materials ₹120 + making ₹30 = ₹150 per child unit
  Parent uses 2 child pieces: ₹300
  Parent has extra raw ₹12
  Parent total: ₹312

All tests run without a live database (pure domain / service layer mocking).
"""

import uuid
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from backend.app.domain.bom.entities.bom import BillOfMaterial, SUPPORTED_MAKING_BASES
from backend.app.domain.bom.entities.bom_line import BOMLine
from backend.app.domain.bom.services.cost_rollup_service import CostRollupService


# ── Fixtures ─────────────────────────────────────────────────────────────────

TENANT = uuid.uuid4()
NOW = datetime.now(timezone.utc)


def _make_bom(
    *,
    variant_id=None,
    template_id=None,
    making_charge=None,
    making_charge_basis=None,
    lines=None,
    operations=None,
):
    if variant_id is None and template_id is None:
        variant_id = uuid.uuid4()
    return BillOfMaterial(
        id=uuid.uuid4(),
        tenant_id=TENANT,
        variant_id=variant_id,
        template_id=template_id,
        version="v1.0",
        valid_from=NOW,
        created_by=uuid.uuid4(),
        lines=lines or [],
        operations=operations or [],
        making_charge=making_charge,
        making_charge_basis=making_charge_basis,
    )


def _make_line(material_id=None, quantity=Decimal("1"), scrap_pct=Decimal("0"),
               template_id=None, variant_id=None):
    return BOMLine(
        id=uuid.uuid4(),
        tenant_id=TENANT,
        bom_id=uuid.uuid4(),
        material_id=material_id,
        template_id=template_id,
        variant_id=variant_id,
        quantity=quantity,
        scrap_percentage=scrap_pct,
        unit_id=None,
    )


def _make_rollup_service(
    material_costs: dict,          # material_id -> Decimal | None
    child_bom=None,                # returned by get_active_bom when asked
    tenant_currency=("INR", "₹"),
):
    """Build a CostRollupService with mocked providers."""
    cost_provider = MagicMock()

    async def _get_material_cost(tenant_id, material_id):
        return material_costs.get(material_id)

    async def _get_operation_cost(tenant_id, operation_id):
        return Decimal("0")

    cost_provider.get_material_cost = _get_material_cost
    cost_provider.get_operation_cost = _get_operation_cost

    bom_provider = MagicMock()

    async def _get_active_bom(tenant_id, template_id=None, variant_id=None):
        return child_bom

    bom_provider.get_active_bom = _get_active_bom
    bom_provider.get_bom_for_material = AsyncMock(return_value=None)

    tenant_provider = MagicMock()
    tenant_provider.get_tenant_currency = AsyncMock(return_value=tenant_currency)

    return CostRollupService(bom_provider, cost_provider, tenant_provider)


# ── Domain entity validation ──────────────────────────────────────────────────

class TestBOMDomainMakingCharge:

    def test_null_making_charge_allowed(self):
        bom = _make_bom(making_charge=None, making_charge_basis=None)
        assert bom.making_charge is None
        assert bom.making_charge_basis is None

    def test_zero_making_charge_valid(self):
        bom = _make_bom(making_charge=Decimal("0"), making_charge_basis="PER_PIECE")
        assert bom.making_charge == Decimal("0")

    def test_positive_making_charge_valid(self):
        bom = _make_bom(making_charge=Decimal("30"), making_charge_basis="PER_PIECE")
        assert bom.making_charge == Decimal("30")

    def test_negative_making_charge_rejected(self):
        with pytest.raises(ValueError, match="negative"):
            _make_bom(making_charge=Decimal("-1"), making_charge_basis="PER_PIECE")

    def test_unsupported_basis_rejected(self):
        with pytest.raises(ValueError, match="not supported"):
            _make_bom(making_charge=Decimal("10"), making_charge_basis="PER_KG")

    def test_charge_without_basis_rejected(self):
        with pytest.raises(ValueError, match="both"):
            _make_bom(making_charge=Decimal("10"), making_charge_basis=None)

    def test_basis_without_charge_rejected(self):
        with pytest.raises(ValueError, match="both"):
            _make_bom(making_charge=None, making_charge_basis="PER_PIECE")

    def test_per_piece_is_only_supported_basis(self):
        assert "PER_PIECE" in SUPPORTED_MAKING_BASES


# ── Cost rollup ───────────────────────────────────────────────────────────────

class TestCostRollupNOMakingCharge:
    """Existing BOMs with no making charge are unaffected."""

    @pytest.mark.asyncio
    async def test_no_making_charge_making_cost_is_zero(self):
        mat_id = uuid.uuid4()
        bom = _make_bom(lines=[_make_line(material_id=mat_id, quantity=Decimal("1"))])
        svc = _make_rollup_service({mat_id: Decimal("100")})
        result = await svc.calculate_standard_cost(TENANT, bom)
        assert result["making_cost"] == Decimal("0")
        assert result["material_cost"] == Decimal("100")
        assert result["total_cost"] == Decimal("100")
        assert result["is_complete"] is True

    @pytest.mark.asyncio
    async def test_zero_making_charge_adds_nothing(self):
        mat_id = uuid.uuid4()
        bom = _make_bom(
            making_charge=Decimal("0"),
            making_charge_basis="PER_PIECE",
            lines=[_make_line(material_id=mat_id, quantity=Decimal("1"))]
        )
        svc = _make_rollup_service({mat_id: Decimal("100")})
        result = await svc.calculate_standard_cost(TENANT, bom)
        assert result["making_cost"] == Decimal("0")
        assert result["total_cost"] == Decimal("100")


class TestCostRollupWithMakingCharge:
    """Single BOM with making charge."""

    @pytest.mark.asyncio
    async def test_per_piece_making_charge_added_once(self):
        mat1 = uuid.uuid4()
        mat2 = uuid.uuid4()
        mat3 = uuid.uuid4()
        bom = _make_bom(
            making_charge=Decimal("30"),
            making_charge_basis="PER_PIECE",
            lines=[
                _make_line(material_id=mat1, quantity=Decimal("1")),
                _make_line(material_id=mat2, quantity=Decimal("1")),
                _make_line(material_id=mat3, quantity=Decimal("1")),
            ]
        )
        svc = _make_rollup_service({
            mat1: Decimal("100"),
            mat2: Decimal("10"),
            mat3: Decimal("10"),
        })
        result = await svc.calculate_standard_cost(TENANT, bom)
        assert result["material_cost"] == Decimal("120")
        assert result["making_cost"] == Decimal("30")
        assert result["operation_cost"] == Decimal("0")
        assert result["total_cost"] == Decimal("150")
        assert result["is_complete"] is True

    @pytest.mark.asyncio
    async def test_making_cost_in_total_reconciles(self):
        """material + making + ops must equal total exactly."""
        mat = uuid.uuid4()
        bom = _make_bom(
            making_charge=Decimal("25.50"),
            making_charge_basis="PER_PIECE",
            lines=[_make_line(material_id=mat, quantity=Decimal("3"))]
        )
        svc = _make_rollup_service({mat: Decimal("40")})
        result = await svc.calculate_standard_cost(TENANT, bom)
        expected = result["material_cost"] + result["operation_cost"] + result["making_cost"]
        assert result["total_cost"] == expected


class TestCostRollupNested:
    """Multi-level BOM: parent uses child BOM output as component."""

    @pytest.mark.asyncio
    async def test_nested_semi_finished_child_total_included_once(self):
        """
        Child BOM: 3 materials × ₹40 = ₹120 + making ₹30 = ₹150 per child unit
        Parent: 2 child units → ₹300 + extra raw ₹12 = ₹312
        """
        child_mat1 = uuid.uuid4()
        child_mat2 = uuid.uuid4()
        child_mat3 = uuid.uuid4()
        parent_mat = uuid.uuid4()
        child_variant_id = uuid.uuid4()

        child_bom = _make_bom(
            variant_id=child_variant_id,
            making_charge=Decimal("30"),
            making_charge_basis="PER_PIECE",
            lines=[
                _make_line(material_id=child_mat1, quantity=Decimal("1")),
                _make_line(material_id=child_mat2, quantity=Decimal("1")),
                _make_line(material_id=child_mat3, quantity=Decimal("1")),
            ]
        )

        parent_bom = _make_bom(
            lines=[
                _make_line(variant_id=child_variant_id, quantity=Decimal("2")),
                _make_line(material_id=parent_mat, quantity=Decimal("1")),
            ]
        )

        material_costs = {
            child_mat1: Decimal("40"),
            child_mat2: Decimal("40"),
            child_mat3: Decimal("40"),
            parent_mat: Decimal("12"),
        }
        svc = _make_rollup_service(material_costs, child_bom=child_bom)
        result = await svc.calculate_standard_cost(TENANT, parent_bom)

        # Child: ₹120 mat + ₹30 making = ₹150 per unit × 2 = ₹300
        # Parent adds raw ₹12 → total ₹312
        assert result["total_cost"] == Decimal("312")
        assert result["is_complete"] is True

    @pytest.mark.asyncio
    async def test_child_making_cost_not_double_counted(self):
        """Making charge appears once per child BOM, not once per child use."""
        child_mat = uuid.uuid4()
        child_variant_id = uuid.uuid4()

        child_bom = _make_bom(
            variant_id=child_variant_id,
            making_charge=Decimal("10"),
            making_charge_basis="PER_PIECE",
            lines=[_make_line(material_id=child_mat, quantity=Decimal("1"))]
        )

        # Parent uses 5 of the child — child making cost per parent output = 5 × 10 = 50
        parent_bom = _make_bom(
            lines=[_make_line(variant_id=child_variant_id, quantity=Decimal("5"))]
        )

        svc = _make_rollup_service({child_mat: Decimal("20")}, child_bom=child_bom)
        result = await svc.calculate_standard_cost(TENANT, parent_bom)
        # child total = 20 + 10 = 30 per unit × 5 = 150
        assert result["total_cost"] == Decimal("150")
        assert result["making_cost"] == Decimal("0")  # parent has no own making charge

    @pytest.mark.asyncio
    async def test_scrap_applied_before_making_charge(self):
        """Scrap increases material usage; making charge stays at 1× per output unit."""
        mat = uuid.uuid4()
        bom = _make_bom(
            making_charge=Decimal("10"),
            making_charge_basis="PER_PIECE",
            lines=[_make_line(material_id=mat, quantity=Decimal("10"), scrap_pct=Decimal("10"))]
        )
        svc = _make_rollup_service({mat: Decimal("5")})
        result = await svc.calculate_standard_cost(TENANT, bom)
        # 10 qty × 1.10 scrap = 11 effective qty × ₹5 = ₹55 material
        assert result["material_cost"] == Decimal("55")
        # Making stays 1×
        assert result["making_cost"] == Decimal("10")
        assert result["total_cost"] == Decimal("65")


class TestCostRollupMissingCosts:
    """Missing approved material costs are handled correctly."""

    @pytest.mark.asyncio
    async def test_missing_material_cost_marks_incomplete(self):
        mat_configured = uuid.uuid4()
        mat_missing = uuid.uuid4()
        bom = _make_bom(
            making_charge=Decimal("30"),
            making_charge_basis="PER_PIECE",
            lines=[
                _make_line(material_id=mat_configured, quantity=Decimal("1")),
                _make_line(material_id=mat_missing, quantity=Decimal("1")),
            ]
        )
        svc = _make_rollup_service({mat_configured: Decimal("100"), mat_missing: None})
        result = await svc.calculate_standard_cost(TENANT, bom)
        assert result["is_complete"] is False
        assert len(result["missing_costs"]) == 1
        assert result["total_cost"] == Decimal("0")  # suppressed when incomplete

    @pytest.mark.asyncio
    async def test_making_charge_does_not_make_missing_cost_complete(self):
        """A missing material cost marks the BOM incomplete regardless of making charge."""
        mat_missing = uuid.uuid4()
        bom = _make_bom(
            making_charge=Decimal("100"),
            making_charge_basis="PER_PIECE",
            lines=[_make_line(material_id=mat_missing, quantity=Decimal("1"))]
        )
        svc = _make_rollup_service({mat_missing: None})
        result = await svc.calculate_standard_cost(TENANT, bom)
        assert result["is_complete"] is False
        assert result["total_cost"] == Decimal("0")


class TestCostRollupTenantIsolation:

    @pytest.mark.asyncio
    async def test_tenant_id_passed_to_cost_provider(self):
        mat_id = uuid.uuid4()
        visited_tenants = []

        cost_provider = MagicMock()
        async def _get_material_cost(tenant_id, material_id):
            visited_tenants.append(tenant_id)
            return Decimal("50")
        async def _get_operation_cost(tenant_id, operation_id):
            return Decimal("0")
        cost_provider.get_material_cost = _get_material_cost
        cost_provider.get_operation_cost = _get_operation_cost

        bom_provider = MagicMock()
        bom_provider.get_active_bom = AsyncMock(return_value=None)
        bom_provider.get_bom_for_material = AsyncMock(return_value=None)

        tenant_provider = MagicMock()
        tenant_provider.get_tenant_currency = AsyncMock(return_value=("INR", "₹"))

        svc = CostRollupService(bom_provider, cost_provider, tenant_provider)
        bom = _make_bom(lines=[_make_line(material_id=mat_id)])
        await svc.calculate_standard_cost(TENANT, bom)
        assert all(t == TENANT for t in visited_tenants)
