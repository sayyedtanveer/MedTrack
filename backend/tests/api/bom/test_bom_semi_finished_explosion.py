"""
Tests for multi-level BOM explosion with semi-finished materials.

This test suite validates that semi-finished materials in BOMs 
automatically explode to show their underlying raw material components
via the variant-material relationship.
"""

import pytest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

from backend.app.domain.bom.entities.bom import BillOfMaterial
from backend.app.domain.bom.entities.bom_line import BOMLine
from backend.app.domain.bom.services.bom_browser_service import BOMBrowserService


@pytest.fixture
def tenant_id():
    """Tenant ID fixture."""
    return uuid.uuid4()


@pytest.fixture
def raw_material_ids():
    """Raw material IDs fixture."""
    return [uuid.uuid4() for _ in range(10)]


@pytest.fixture
def semi_finished_material_id():
    """Semi-finished material ID fixture."""
    return uuid.uuid4()


@pytest.fixture
def finished_good_bom_id():
    """Finished good BOM ID fixture."""
    return uuid.uuid4()


@pytest.fixture
def semi_finished_bom_id():
    """Semi-finished BOM ID fixture."""
    return uuid.uuid4()


@pytest.fixture
def mock_bom_provider():
    """Mock BOM provider for testing."""
    provider = AsyncMock()
    return provider


@pytest.fixture
def mock_details_provider():
    """Mock component detail provider for testing."""
    provider = AsyncMock()
    return provider


@pytest.fixture
def semi_finished_bom(semi_finished_bom_id, tenant_id, raw_material_ids):
    """
    Create a mock BOM for semi-finished material with 10 raw materials.
    This represents: SF-MECH-ASSY → RM-001...RM-010
    """
    bom = BillOfMaterial(
        id=semi_finished_bom_id,
        tenant_id=tenant_id,
        template_id=None,
        variant_id=uuid.uuid4(),  # Semi-finished variant
        version="1.0.0",
        is_active=True,
        valid_from=None,
        valid_to=None,
        created_by=None,
        approved_by=None,
        is_deleted=False,
        deleted_at=None,
        created_at=None,
        updated_at=None,
        operations_count=0,
        lines=[],
        operations=[]
    )
    
    # Add 10 raw material lines
    for i, material_id in enumerate(raw_material_ids, start=1):
        line = BOMLine(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            bom_id=semi_finished_bom_id,
            material_id=material_id,
            template_id=None,
            variant_id=None,
            quantity=Decimal(str(i)),  # Quantities: 1, 2, 3...10
            scrap_percentage=Decimal("0.0"),
            unit_id=uuid.uuid4()
        )
        bom.add_line(line)
    
    return bom


@pytest.fixture
def finished_good_bom(finished_good_bom_id, tenant_id, semi_finished_material_id):
    """
    Create a mock BOM for finished good that contains semi-finished material.
    This represents: FG-ROTAMETER → SF-MECH-ASSY
    """
    bom = BillOfMaterial(
        id=finished_good_bom_id,
        tenant_id=tenant_id,
        template_id=uuid.uuid4(),
        variant_id=None,
        version="1.0.0",
        is_active=True,
        valid_from=None,
        valid_to=None,
        created_by=None,
        approved_by=None,
        is_deleted=False,
        deleted_at=None,
        created_at=None,
        updated_at=None,
        operations_count=0,
        lines=[],
        operations=[]
    )
    
    # Add semi-finished material line
    line = BOMLine(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        bom_id=finished_good_bom_id,
        material_id=semi_finished_material_id,
        template_id=None,
        variant_id=None,
        quantity=Decimal("2.0"),
        scrap_percentage=Decimal("5.0"),  # 5% scrap
        unit_id=uuid.uuid4()
    )
    bom.add_line(line)
    
    return bom


@pytest.mark.asyncio
class TestSemiFinishedBOMExplosion:
    """Test suite for semi-finished material BOM explosion."""

    async def test_semi_finished_material_explodes_to_raw_materials(
        self,
        tenant_id,
        finished_good_bom,
        semi_finished_bom,
        semi_finished_material_id,
        raw_material_ids,
        mock_bom_provider,
        mock_details_provider
    ):
        """
        Test that a semi-finished material in a BOM automatically explodes
        to show its underlying raw material components.
        
        Expected hierarchy:
        FG-ROTAMETER (qty: N/A)
          └─ SF-MECH-ASSY (qty: 2.1 with 5% scrap)
              ├─ RM-001 (qty: 2.1)
              ├─ RM-002 (qty: 4.2)
              ├─ RM-003 (qty: 6.3)
              ...
              └─ RM-010 (qty: 21.0)
        """
        # Setup mock providers
        # When BOM provider is asked for semi-finished material's BOM, return it
        mock_bom_provider.get_bom_for_material.return_value = semi_finished_bom
        mock_bom_provider.get_active_bom.return_value = None  # No template/variant BOMs
        
        # Setup component details
        async def get_details(tenant_id, is_material, component_id):
            if component_id == semi_finished_material_id:
                return {
                    "name": "SF-MECH-ASSY",
                    "code": "SF-001",
                    "unit_name": "pcs",
                    "material_type": "semi_finished"
                }
            elif component_id in raw_material_ids:
                idx = raw_material_ids.index(component_id) + 1
                return {
                    "name": f"RM-{idx:03d}",
                    "code": f"RM-{idx:03d}",
                    "unit_name": "kg",
                    "material_type": "raw_material"
                }
            return {"name": "Unknown", "code": "???", "unit_name": "pcs"}
        
        mock_details_provider.get_component_details.side_effect = get_details
        
        # Create service and build tree
        service = BOMBrowserService(mock_bom_provider, mock_details_provider)
        tree = await service.build_tree(tenant_id, finished_good_bom, max_depth=20)
        
        # Assertions
        assert tree is not None
        assert tree["version"] == "1.0.0"
        assert len(tree["children"]) == 1
        
        # Check semi-finished material node
        sf_node = tree["children"][0]
        assert sf_node["name"] == "SF-MECH-ASSY"
        assert sf_node["code"] == "SF-001"
        assert sf_node["type"] == "material"
        assert sf_node["material_type"] == "semi_finished"
        assert sf_node["quantity"] == 2.1  # 2.0 * (1 + 5%/100)
        
        # Check that semi-finished material exploded to 10 raw materials
        assert len(sf_node["children"]) == 10
        
        # Verify raw material quantities (base qty * SF multiplier)
        for i, raw_child in enumerate(sf_node["children"], start=1):
            expected_qty = i * 2.1  # Raw qty * SF qty
            assert raw_child["name"] == f"RM-{i:03d}"
            assert raw_child["type"] == "material"
            assert raw_child["material_type"] == "raw_material"
            assert raw_child["quantity"] == expected_qty
            assert len(raw_child["children"]) == 0  # Raw materials don't explode further
        
        # Verify get_bom_for_material was called for semi-finished material
        mock_bom_provider.get_bom_for_material.assert_called_once_with(
            tenant_id=tenant_id,
            material_id=semi_finished_material_id
        )

    async def test_raw_material_does_not_explode(
        self,
        tenant_id,
        raw_material_ids,
        mock_bom_provider,
        mock_details_provider
    ):
        """
        Test that raw materials do NOT attempt to explode,
        even if they somehow have a BOM (should not happen in practice).
        """
        # Create BOM with raw material
        raw_material_id = raw_material_ids[0]
        bom_id = uuid.uuid4()
        
        bom = BillOfMaterial(
            id=bom_id,
            tenant_id=tenant_id,
            template_id=None,
            variant_id=None,
            version="1.0.0",
            is_active=True,
            valid_from=None,
            valid_to=None,
            created_by=None,
            approved_by=None,
            is_deleted=False,
            deleted_at=None,
            created_at=None,
            updated_at=None,
            operations_count=0,
            lines=[],
            operations=[]
        )
        
        line = BOMLine(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            bom_id=bom_id,
            material_id=raw_material_id,
            template_id=None,
            variant_id=None,
            quantity=Decimal("5.0"),
            scrap_percentage=Decimal("0.0"),
            unit_id=uuid.uuid4()
        )
        bom.add_line(line)
        
        # Setup mocks
        mock_bom_provider.get_bom_for_material.return_value = None
        mock_bom_provider.get_active_bom.return_value = None
        
        async def get_details(tenant_id, is_material, component_id):
            return {
                "name": "RM-001",
                "code": "RM-001",
                "unit_name": "kg",
                "material_type": "raw_material"  # NOT semi_finished
            }
        
        mock_details_provider.get_component_details.side_effect = get_details
        
        # Build tree
        service = BOMBrowserService(mock_bom_provider, mock_details_provider)
        tree = await service.build_tree(tenant_id, bom, max_depth=20)
        
        # Assertions
        assert len(tree["children"]) == 1
        raw_node = tree["children"][0]
        assert raw_node["material_type"] == "raw_material"
        assert len(raw_node["children"]) == 0  # Should not explode
        
        # get_bom_for_material should NOT be called for raw materials
        mock_bom_provider.get_bom_for_material.assert_not_called()

    async def test_finished_good_does_not_explode_as_material(
        self,
        tenant_id,
        mock_bom_provider,
        mock_details_provider
    ):
        """
        Test that finished_good materials do NOT explode.
        Only semi_finished materials should trigger BOM explosion.
        """
        fg_material_id = uuid.uuid4()
        bom_id = uuid.uuid4()
        
        bom = BillOfMaterial(
            id=bom_id,
            tenant_id=tenant_id,
            template_id=None,
            variant_id=None,
            version="1.0.0",
            is_active=True,
            valid_from=None,
            valid_to=None,
            created_by=None,
            approved_by=None,
            is_deleted=False,
            deleted_at=None,
            created_at=None,
            updated_at=None,
            operations_count=0,
            lines=[],
            operations=[]
        )
        
        line = BOMLine(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            bom_id=bom_id,
            material_id=fg_material_id,
            template_id=None,
            variant_id=None,
            quantity=Decimal("1.0"),
            scrap_percentage=Decimal("0.0"),
            unit_id=uuid.uuid4()
        )
        bom.add_line(line)
        
        # Setup mocks
        mock_bom_provider.get_bom_for_material.return_value = None
        mock_bom_provider.get_active_bom.return_value = None
        
        async def get_details(tenant_id, is_material, component_id):
            return {
                "name": "FG-PRODUCT",
                "code": "FG-001",
                "unit_name": "pcs",
                "material_type": "finished_good"  # NOT semi_finished
            }
        
        mock_details_provider.get_component_details.side_effect = get_details
        
        # Build tree
        service = BOMBrowserService(mock_bom_provider, mock_details_provider)
        tree = await service.build_tree(tenant_id, bom, max_depth=20)
        
        # Assertions
        assert len(tree["children"]) == 1
        fg_node = tree["children"][0]
        assert fg_node["material_type"] == "finished_good"
        assert len(fg_node["children"]) == 0  # Should not explode
        
        # get_bom_for_material should NOT be called
        mock_bom_provider.get_bom_for_material.assert_not_called()

    async def test_max_depth_limits_explosion(
        self,
        tenant_id,
        finished_good_bom,
        semi_finished_bom,
        semi_finished_material_id,
        mock_bom_provider,
        mock_details_provider
    ):
        """
        Test that max_depth parameter correctly limits BOM explosion depth.
        """
        # Setup mocks
        mock_bom_provider.get_bom_for_material.return_value = semi_finished_bom
        mock_bom_provider.get_active_bom.return_value = None
        
        async def get_details(tenant_id, is_material, component_id):
            if component_id == semi_finished_material_id:
                return {
                    "name": "SF-MECH-ASSY",
                    "code": "SF-001",
                    "unit_name": "pcs",
                    "material_type": "semi_finished"
                }
            return {
                "name": "RM-TEST",
                "code": "RM-001",
                "unit_name": "kg",
                "material_type": "raw_material"
            }
        
        mock_details_provider.get_component_details.side_effect = get_details
        
        # Build tree with max_depth=1 (should only show SF, not raw materials)
        service = BOMBrowserService(mock_bom_provider, mock_details_provider)
        tree = await service.build_tree(tenant_id, finished_good_bom, max_depth=1)
        
        # Assertions
        assert len(tree["children"]) == 1
        sf_node = tree["children"][0]
        assert sf_node["name"] == "SF-MECH-ASSY"
        # At depth 1, we should NOT recurse into semi-finished materials
        assert len(sf_node["children"]) == 0

    async def test_template_and_variant_explosion_still_works(
        self,
        tenant_id,
        mock_bom_provider,
        mock_details_provider
    ):
        """
        Test that existing template/variant BOM explosion logic still works
        and is not affected by the new semi-finished material logic.
        """
        parent_bom_id = uuid.uuid4()
        child_bom_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        child_material_id = uuid.uuid4()
        
        # Child BOM (variant-based)
        child_bom = BillOfMaterial(
            id=child_bom_id,
            tenant_id=tenant_id,
            template_id=None,
            variant_id=variant_id,
            version="1.0.0",
            is_active=True,
            valid_from=None,
            valid_to=None,
            created_by=None,
            approved_by=None,
            is_deleted=False,
            deleted_at=None,
            created_at=None,
            updated_at=None,
            operations_count=0,
            lines=[],
            operations=[]
        )
        
        child_line = BOMLine(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            bom_id=child_bom_id,
            material_id=child_material_id,
            template_id=None,
            variant_id=None,
            quantity=Decimal("3.0"),
            scrap_percentage=Decimal("0.0"),
            unit_id=uuid.uuid4()
        )
        child_bom.add_line(child_line)
        
        # Parent BOM with variant reference
        parent_bom = BillOfMaterial(
            id=parent_bom_id,
            tenant_id=tenant_id,
            template_id=uuid.uuid4(),
            variant_id=None,
            version="1.0.0",
            is_active=True,
            valid_from=None,
            valid_to=None,
            created_by=None,
            approved_by=None,
            is_deleted=False,
            deleted_at=None,
            created_at=None,
            updated_at=None,
            operations_count=0,
            lines=[],
            operations=[]
        )
        
        parent_line = BOMLine(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            bom_id=parent_bom_id,
            material_id=None,
            template_id=None,
            variant_id=variant_id,  # Variant reference
            quantity=Decimal("2.0"),
            scrap_percentage=Decimal("0.0"),
            unit_id=uuid.uuid4()
        )
        parent_bom.add_line(parent_line)
        
        # Setup mocks
        mock_bom_provider.get_active_bom.return_value = child_bom
        mock_bom_provider.get_bom_for_material.return_value = None
        
        async def get_details(tenant_id, is_material, component_id):
            if component_id == variant_id:
                return {
                    "name": "Child Variant",
                    "code": "VAR-001",
                    "unit_name": "pcs"
                }
            elif component_id == child_material_id:
                return {
                    "name": "Child Material",
                    "code": "RM-100",
                    "unit_name": "kg",
                    "material_type": "raw_material"
                }
            return {"name": "Unknown", "code": "???", "unit_name": "pcs"}
        
        mock_details_provider.get_component_details.side_effect = get_details
        
        # Build tree
        service = BOMBrowserService(mock_bom_provider, mock_details_provider)
        tree = await service.build_tree(tenant_id, parent_bom, max_depth=20)
        
        # Assertions - verify variant explosion still works
        assert len(tree["children"]) == 1
        variant_node = tree["children"][0]
        assert variant_node["name"] == "Child Variant"
        assert variant_node["type"] == "variant"
        assert len(variant_node["children"]) == 1
        
        material_node = variant_node["children"][0]
        assert material_node["name"] == "Child Material"
        assert material_node["quantity"] == 6.0  # 3.0 * 2.0
        
        # Verify get_active_bom was called for variant
        mock_bom_provider.get_active_bom.assert_called_once()
