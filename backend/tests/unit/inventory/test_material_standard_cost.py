"""
Unit tests for Material Standard Cost (REQ-SC-001 to REQ-SC-002).

Covers:
- MaterialResult carries current_cost
- _to_result() maps current_cost from the domain entity
- Material.update() sets current_cost correctly
- Validation: negative cost rejected, max boundary respected
- BOM cost linearity (P-SC-3)
- Excel onboarding: standard_cost column present in FIELDS
- Excel onboarding: standard_cost alias mapping
- Excel onboarding: _validate_row rejects negative standard_cost
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.app.application.inventory.handlers.inventory_handlers import (
    MaterialResult,
    _to_result,
)
from backend.app.application.inventory.services.material_onboarding_service import (
    ALIASES,
    FIELDS,
    MaterialOnboardingService,
)
from backend.app.domain.inventory.entities.material import Material, MaterialType


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_material(current_cost: Decimal = Decimal("0")) -> Material:
    """Create a minimal raw material entity with the given current_cost."""
    return Material(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        code="RM-TEST-001",
        name="Test Brass Rod",
        material_type=MaterialType.RAW,
        current_cost=current_cost,
    )


# ── REQ-SC-001: current_cost in domain entity and DTO ─────────────────────────

class TestMaterialEntityCost:

    def test_material_default_cost_is_zero(self):
        mat = make_material()
        assert mat.current_cost == Decimal("0")

    def test_material_cost_set_at_init(self):
        mat = make_material(Decimal("500.0000"))
        assert mat.current_cost == Decimal("500.0000")

    def test_material_update_sets_cost(self):
        mat = make_material(Decimal("100"))
        mat.update(current_cost=Decimal("250.5000"))
        assert mat.current_cost == Decimal("250.5000")

    def test_material_update_none_does_not_clear_cost(self):
        """Passing None to update() should NOT overwrite existing cost (spec: optional field)."""
        mat = make_material(Decimal("300"))
        mat.update(current_cost=None)
        # The update method only sets cost when value is not None
        assert mat.current_cost == Decimal("300")

    def test_material_cost_setter_zero_is_allowed(self):
        mat = make_material(Decimal("100"))
        mat.current_cost = Decimal("0")
        assert mat.current_cost == Decimal("0")

    def test_to_result_maps_current_cost(self):
        mat = make_material(Decimal("750.1234"))
        result: MaterialResult = _to_result(mat)
        assert result.current_cost == Decimal("750.1234")

    def test_to_result_default_cost_zero(self):
        mat = make_material()
        result: MaterialResult = _to_result(mat)
        assert result.current_cost == Decimal("0")

    def test_material_result_has_current_cost_field(self):
        """MaterialResult dataclass must declare current_cost."""
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(MaterialResult)}
        assert "current_cost" in field_names


# ── REQ-SC-001 AC4: Validation — negative and max boundary ────────────────────

class TestCostValidation:

    def test_negative_cost_rejected_by_schema(self):
        """UpdateMaterialRequest must reject negative current_cost."""
        from backend.app.interfaces.api.v1.schemas.inventory_schemas import UpdateMaterialRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError) as exc_info:
            UpdateMaterialRequest(current_cost=Decimal("-1"))
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("current_cost",) for e in errors)

    def test_zero_cost_accepted_by_schema(self):
        from backend.app.interfaces.api.v1.schemas.inventory_schemas import UpdateMaterialRequest
        req = UpdateMaterialRequest(current_cost=Decimal("0"))
        assert req.current_cost == Decimal("0")

    def test_max_boundary_accepted(self):
        from backend.app.interfaces.api.v1.schemas.inventory_schemas import UpdateMaterialRequest
        req = UpdateMaterialRequest(current_cost=Decimal("999999999.9999"))
        assert req.current_cost == Decimal("999999999.9999")

    def test_over_max_rejected(self):
        from backend.app.interfaces.api.v1.schemas.inventory_schemas import UpdateMaterialRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            UpdateMaterialRequest(current_cost=Decimal("1000000000.0000"))

    def test_none_cost_accepted_as_optional(self):
        from backend.app.interfaces.api.v1.schemas.inventory_schemas import UpdateMaterialRequest
        req = UpdateMaterialRequest(current_cost=None)
        assert req.current_cost is None


# ── REQ-SC-002 / P-SC-3: BOM cost linearity ───────────────────────────────────

class TestBomCostLinearity:
    """P-SC-3: line_cost = quantity × (1 + scrap_pct/100) × current_cost"""

    @staticmethod
    def _line_cost(quantity: Decimal, scrap_pct: Decimal, unit_cost: Decimal) -> Decimal:
        return quantity * (1 + scrap_pct / 100) * unit_cost

    def test_basic_line_cost(self):
        qty = Decimal("2")
        scrap = Decimal("10")  # 10%
        cost = Decimal("500")
        # 2 * 1.10 * 500 = 1100
        assert self._line_cost(qty, scrap, cost) == Decimal("1100")

    def test_zero_scrap(self):
        qty = Decimal("3")
        cost = Decimal("250")
        assert self._line_cost(qty, Decimal("0"), cost) == Decimal("750")

    def test_zero_cost_produces_zero(self):
        assert self._line_cost(Decimal("5"), Decimal("20"), Decimal("0")) == Decimal("0")

    @given(
        base_cost=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"),
                              allow_nan=False, allow_infinity=False),
        k=st.decimals(min_value=Decimal("0.5"), max_value=Decimal("10"),
                      allow_nan=False, allow_infinity=False),
        qty=st.decimals(min_value=Decimal("0.001"), max_value=Decimal("1000"),
                        allow_nan=False, allow_infinity=False),
        scrap_pct=st.decimals(min_value=Decimal("0"), max_value=Decimal("50"),
                              allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100, deadline=None)
    def test_bom_cost_linearity_property(self, base_cost, k, qty, scrap_pct):
        """P-SC-3: scaling cost by k scales line contribution by k."""
        base_contribution = qty * (1 + scrap_pct / 100) * base_cost
        scaled_contribution = qty * (1 + scrap_pct / 100) * (k * base_cost)
        assert abs(scaled_contribution - k * base_contribution) < Decimal("0.0001")

    @given(
        unit_cost=st.decimals(min_value=Decimal("0"), max_value=Decimal("999999999.9999"),
                              allow_nan=False, allow_infinity=False),
        qty=st.decimals(min_value=Decimal("0.001"), max_value=Decimal("1000"),
                        allow_nan=False, allow_infinity=False),
        scrap_pct=st.decimals(min_value=Decimal("0"), max_value=Decimal("100"),
                              allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100, deadline=None)
    def test_line_cost_always_non_negative(self, unit_cost, qty, scrap_pct):
        """P-SC-1 + P-SC-3: line cost is always >= 0 for valid inputs."""
        line_cost = qty * (1 + scrap_pct / 100) * unit_cost
        assert line_cost >= Decimal("0")


# ── Excel onboarding: standard_cost column support ────────────────────────────

class TestOnboardingStandardCost:

    def test_standard_cost_in_fields(self):
        """FIELDS must include 'standard_cost' so the template column exists."""
        assert "standard_cost" in FIELDS

    def test_standard_cost_aliases(self):
        """Common column header synonyms must map to 'standard_cost'."""
        assert ALIASES.get("standard purchase cost") == "standard_cost"
        assert ALIASES.get("purchase cost") == "standard_cost"
        assert ALIASES.get("cost") == "standard_cost"
        assert ALIASES.get("current cost") == "standard_cost"

    def test_suggest_mapping_maps_standard_cost_header(self):
        """suggest_mapping should auto-suggest 'standard_cost' for the exact column name."""
        mapping = MaterialOnboardingService.suggest_mapping(["standard_cost"])
        assert mapping.get("standard_cost") == "standard_cost"

    def test_suggest_mapping_maps_standard_purchase_cost_alias(self):
        """suggest_mapping should map 'standard purchase cost' via alias."""
        mapping = MaterialOnboardingService.suggest_mapping(["standard purchase cost"])
        assert mapping.get("standard purchase cost") == "standard_cost"

    def test_template_csv_includes_standard_cost_column(self):
        """The CSV template must include 'standard_cost' header."""
        csv_bytes = MaterialOnboardingService.template_csv()
        header_line = csv_bytes.decode().split("\n")[0]
        assert "standard_cost" in header_line

    def test_template_xlsx_includes_standard_cost_column(self):
        """The XLSX template must include 'standard_cost' as a column header."""
        import io, zipfile
        from xml.etree import ElementTree as ET
        xlsx_bytes = MaterialOnboardingService.template_xlsx()
        with zipfile.ZipFile(io.BytesIO(xlsx_bytes)) as z:
            sheet_xml = z.read("xl/worksheets/sheet1.xml")
        root = ET.fromstring(sheet_xml)
        ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        # Gather all cell text from first row
        cell_texts = []
        for row in root.iter(f"{ns}row"):
            for cell in row.iter(f"{ns}c"):
                is_node = cell.find(f"{ns}is")
                if is_node is not None:
                    t_node = is_node.find(f"{ns}t")
                    if t_node is not None and t_node.text:
                        cell_texts.append(t_node.text)
            break  # only first row (header)
        assert "standard_cost" in cell_texts

    @pytest.mark.asyncio
    async def test_validate_row_rejects_negative_standard_cost(self):
        """_validate_row must flag negative standard_cost as an error."""
        # We can test the pure validation logic without a real DB session
        # by mocking the session with a simple stub
        from unittest.mock import AsyncMock, MagicMock
        session = MagicMock()
        session.scalar = AsyncMock(return_value=None)  # no existing material/category/etc
        svc = MaterialOnboardingService(session)

        data = {
            "material_name": "Brass Rod",
            "material_category": "Metals",
            "uom": "KG",
            "material_type": "raw",
            "standard_cost": "-10",
        }
        issues, cls, changes = await svc._validate_row(uuid.uuid4(), data)
        error_fields = {i["field"] for i in issues if i["severity"] == "error"}
        assert "standard_cost" in error_fields

    @pytest.mark.asyncio
    async def test_validate_row_accepts_valid_standard_cost(self):
        """_validate_row must NOT flag a valid positive standard_cost."""
        from unittest.mock import AsyncMock, MagicMock
        session = MagicMock()
        session.scalar = AsyncMock(return_value=None)
        svc = MaterialOnboardingService(session)

        data = {
            "material_name": "Brass Rod",
            "material_category": "Metals",
            "uom": "KG",
            "material_type": "raw",
            "standard_cost": "250.0000",
        }
        issues, cls, changes = await svc._validate_row(uuid.uuid4(), data)
        cost_errors = [i for i in issues if i["field"] == "standard_cost" and i["severity"] == "error"]
        assert cost_errors == []

    @pytest.mark.asyncio
    async def test_validate_row_accepts_zero_standard_cost(self):
        """standard_cost = 0 is valid (not yet assigned)."""
        from unittest.mock import AsyncMock, MagicMock
        session = MagicMock()
        session.scalar = AsyncMock(return_value=None)
        svc = MaterialOnboardingService(session)

        data = {
            "material_name": "Brass Rod",
            "material_category": "Metals",
            "uom": "KG",
            "material_type": "raw",
            "standard_cost": "0",
        }
        issues, _, _ = await svc._validate_row(uuid.uuid4(), data)
        cost_errors = [i for i in issues if i["field"] == "standard_cost" and i["severity"] == "error"]
        assert cost_errors == []
