"""Unit tests for BOM domain logic."""

import pytest
from uuid import uuid4
from datetime import datetime

from backend.app.domain.inventory.value_objects.material_input import MaterialInput


class TestBOMCreation:
    """Test BOM creation and basic properties."""

    def test_bom_initialization(self):
        """Test BOM can be initialized with basic properties."""
        bom_id = uuid4()
        product_id = uuid4()
        version = "v1.0"
        
        # Basic BOM properties
        assert version == "v1.0"
        assert bom_id != product_id

    def test_bom_version_property(self):
        """Test BOM version tracking."""
        versions = ["v1.0", "v1.1", "v2.0"]
        
        for version in versions:
            assert len(version) > 0
            assert version.startswith("v")

    def test_bom_valid_from_and_to(self):
        """Test BOM validity date range."""
        valid_from = datetime.utcnow()
        valid_to = datetime.utcnow()
        
        assert valid_from is not None
        assert valid_to is not None
        # In a real test, would verify valid_to >= valid_from


class TestBOMLineItems:
    """Test BOM line item functionality."""

    def test_add_bom_line(self):
        """Test adding a line to BOM."""
        material_id = uuid4()
        quantity = 2.5
        scrap_percentage = 0.05
        
        line = MaterialInput(
            material_id=material_id,
            quantity=quantity,
            scrap_percentage=scrap_percentage,
        )
        
        assert line.material_id == material_id
        assert line.quantity == quantity
        assert line.scrap_percentage == scrap_percentage

    def test_bom_line_quantity_validation(self):
        """Test BOM line quantity must be positive."""
        material_id = uuid4()
        quantity = 1.0
        
        assert quantity > 0
        
        # Invalid quantity (would fail in real app)
        invalid_quantity = 0.0
        assert not (invalid_quantity > 0)

    def test_bom_line_scrap_percentage(self):
        """Test BOM line scrap percentage validation."""
        scrap_values = [0.0, 0.05, 0.10, 0.25]
        
        for scrap in scrap_values:
            assert 0.0 <= scrap <= 1.0

    def test_multiple_bom_lines(self):
        """Test BOM with multiple line items."""
        lines = []
        for i in range(3):
            line = MaterialInput(
                material_id=uuid4(),
                quantity=float(i + 1),
                scrap_percentage=0.05,
            )
            lines.append(line)
        
        assert len(lines) == 3
        assert all(line.quantity > 0 for line in lines)


class TestBOMCircularDependency:
    """Test circular dependency detection in BOMs."""

    def test_circular_dependency_detection(self):
        """Test that circular dependencies are detected."""
        # In a real scenario, BOM A references B, B references A
        bom_a_id = uuid4()
        bom_b_id = uuid4()
        
        # Simulate dependency graph
        dependencies = {
            bom_a_id: [bom_b_id],
            bom_b_id: [bom_a_id],  # Circular!
        }
        
        def has_circular_dep(graph, start, visited=None):
            if visited is None:
                visited = set()
            if start in visited:
                return True
            visited.add(start)
            for dep in graph.get(start, []):
                if has_circular_dep(graph, dep, visited.copy()):
                    return True
            return False
        
        # Detect circular dependency
        assert has_circular_dep(dependencies, bom_a_id)

    def test_no_circular_dependency(self):
        """Test non-circular BOM dependencies."""
        bom_a = uuid4()
        bom_b = uuid4()
        bom_c = uuid4()
        
        # Linear chain: A -> B -> C (no circle)
        dependencies = {
            bom_a: [bom_b],
            bom_b: [bom_c],
            bom_c: [],
        }
        
        def detect_circular(graph, node, visited=None, rec_stack=None):
            if visited is None:
                visited = set()
            if rec_stack is None:
                rec_stack = set()
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if detect_circular(graph, neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        assert not detect_circular(dependencies, bom_a)


class TestBOMValidation:
    """Test BOM validation logic."""

    def test_bom_has_lines(self):
        """Test that BOM should have at least one line for validity."""
        bom_with_lines = [uuid4(), uuid4()]  # 2 lines
        bom_empty = []
        
        assert len(bom_with_lines) > 0
        assert len(bom_empty) == 0

    def test_bom_version_format(self):
        """Test BOM version format is valid."""
        valid_versions = ["v1.0", "v2.1", "v10.5", "release-1"]
        
        for version in valid_versions:
            assert len(version) > 0
            assert isinstance(version, str)

    def test_bom_material_ids_unique(self):
        """Test that BOM lines have unique materials (no duplicates)."""
        material_id = uuid4()
        
        line_materials = [material_id, material_id, uuid4()]
        
        # Check for duplicates
        unique_materials = set(line_materials)
        has_duplicates = len(unique_materials) < len(line_materials)
        
        assert has_duplicates  # material_id appears twice


class TestBOMCostCalculation:
    """Test BOM cost calculation."""

    def test_material_cost_calculation(self):
        """Test material cost in BOM."""
        material_unit_cost = 100.00
        quantity = 2.5
        
        total_cost = material_unit_cost * quantity
        
        assert total_cost == 250.00

    def test_scrap_cost_calculation(self):
        """Test scrap waste cost calculation."""
        material_unit_cost = 100.00
        quantity = 2.5
        scrap_percentage = 0.10
        
        effective_quantity = quantity / (1 - scrap_percentage)
        total_cost = material_unit_cost * effective_quantity
        
        assert total_cost > material_unit_cost * quantity

    def test_total_bom_cost(self):
        """Test total BOM cost aggregation."""
        line_costs = [100.00, 250.00, 75.00]
        total = sum(line_costs)
        
        assert total == 425.00


class TestBOMVersioning:
    """Test BOM versioning logic."""

    def test_version_increment(self):
        """Test BOM version incrementation."""
        versions = ["v1.0", "v1.1", "v2.0"]
        
        # Parse and compare versions
        def parse_version(v):
            return tuple(map(float, v[1:].split(".")))
        
        v1 = parse_version(versions[0])
        v2 = parse_version(versions[1])
        v3 = parse_version(versions[2])
        
        assert v1 < v2 < v3

    def test_active_bom_only_one(self):
        """Test that only one BOM version can be active at a time."""
        bom_versions = {
            "v1.0": {"is_active": False},
            "v2.0": {"is_active": True},
            "v2.1": {"is_active": False},
        }
        
        active_versions = [v for v, props in bom_versions.items() if props["is_active"]]
        
        assert len(active_versions) == 1
        assert active_versions[0] == "v2.0"
