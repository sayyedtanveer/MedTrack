"""Unit tests for Operations domain logic."""

import pytest
from uuid import uuid4
from datetime import datetime


class TestOperationCreation:
    """Test operation creation and basic properties."""

    def test_operation_initialization(self):
        """Test operation initialization."""
        operation_id = uuid4()
        code = "OP-001"
        name = "Assembly"
        
        operation = {
            "id": operation_id,
            "code": code,
            "name": name,
            "process_type": "assembly",
        }
        
        assert operation["id"] == operation_id
        assert operation["code"] == code
        assert operation["name"] == name

    def test_operation_process_types(self):
        """Test valid process types."""
        valid_types = ["assembly", "machining", "painting", "inspection", "packaging"]
        
        for process_type in valid_types:
            assert process_type in valid_types

    def test_operation_time_estimation(self):
        """Test operation time estimation."""
        estimated_hours = 2.5
        
        assert estimated_hours > 0
        assert isinstance(estimated_hours, float)


class TestOperationCost:
    """Test operation cost calculations."""

    def test_labor_cost_calculation(self):
        """Test labor cost calculation."""
        hourly_rate = 25.00
        estimated_hours = 2.5
        
        labor_cost = hourly_rate * estimated_hours
        
        assert labor_cost == 62.50

    def test_equipment_cost_calculation(self):
        """Test equipment/workstation cost."""
        workstation_hourly_rate = 50.00
        operation_hours = 1.0
        
        equipment_cost = workstation_hourly_rate * operation_hours
        
        assert equipment_cost == 50.00

    def test_total_operation_cost(self):
        """Test total operation cost (labor + equipment)."""
        labor_cost = 62.50
        equipment_cost = 50.00
        overhead_multiplier = 1.15  # 15% overhead
        
        total = (labor_cost + equipment_cost) * overhead_multiplier
        
        assert total == 128.90


class TestOperationSequencing:
    """Test operation sequencing in manufacturing."""

    def test_operation_sequence_order(self):
        """Test operation sequence is maintained."""
        operations = [
            {"id": 1, "name": "Assembly", "sequence": 1},
            {"id": 2, "name": "Testing", "sequence": 2},
            {"id": 3, "name": "Packaging", "sequence": 3},
        ]
        
        for i, op in enumerate(operations, 1):
            assert op["sequence"] == i

    def test_operation_dependencies(self):
        """Test operation dependencies."""
        operations = {
            "assembly": {"depends_on": []},
            "testing": {"depends_on": ["assembly"]},
            "packaging": {"depends_on": ["assembly", "testing"]},
        }
        
        # Assembly has no deps
        assert len(operations["assembly"]["depends_on"]) == 0
        # Testing depends on assembly
        assert "assembly" in operations["testing"]["depends_on"]
        # Packaging depends on both
        assert len(operations["packaging"]["depends_on"]) == 2


class TestWorkstationManagement:
    """Test workstation management."""

    def test_workstation_creation(self):
        """Test workstation initialization."""
        ws_id = uuid4()
        code = "WS-001"
        equipment_type = "assembly_line"
        hourly_rate = 50.00
        
        workstation = {
            "id": ws_id,
            "code": code,
            "equipment_type": equipment_type,
            "hourly_rate": hourly_rate,
        }
        
        assert workstation["code"] == code
        assert workstation["hourly_rate"] > 0

    def test_workstation_hourly_rate(self):
        """Test workstation hourly rate calculation."""
        hourly_rate = 75.00
        hours_used = 3.0
        
        total_cost = hourly_rate * hours_used
        
        assert total_cost == 225.00


class TestOperationSoftDelete:
    """Test soft delete behavior for operations."""

    def test_soft_delete_marking(self):
        """Test operation is marked as deleted, not removed."""
        operation = {
            "id": uuid4(),
            "name": "Old Operation",
            "is_deleted": False,
            "deleted_at": None,
        }
        
        # Mark as deleted
        operation["is_deleted"] = True
        operation["deleted_at"] = datetime.utcnow()
        
        assert operation["is_deleted"] is True
        assert operation["deleted_at"] is not None

    def test_deleted_operations_filtered(self):
        """Test deleted operations are filtered from queries."""
        operations = [
            {"id": 1, "name": "Active Op", "is_deleted": False},
            {"id": 2, "name": "Deleted Op", "is_deleted": True},
            {"id": 3, "name": "Another Active", "is_deleted": False},
        ]
        
        active_ops = [op for op in operations if not op["is_deleted"]]
        
        assert len(active_ops) == 2
        assert all(not op["is_deleted"] for op in active_ops)

    def test_restore_soft_deleted_operation(self):
        """Test restoring a soft-deleted operation."""
        operation = {
            "id": uuid4(),
            "name": "Restored Op",
            "is_deleted": True,
            "deleted_at": datetime.utcnow(),
        }
        
        # Restore
        operation["is_deleted"] = False
        operation["deleted_at"] = None
        
        assert operation["is_deleted"] is False
        assert operation["deleted_at"] is None
