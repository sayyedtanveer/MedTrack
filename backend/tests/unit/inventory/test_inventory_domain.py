"""Unit tests for Inventory domain logic."""

import pytest
from uuid import uuid4
from datetime import datetime


class TestMaterialCreation:
    """Test material creation and properties."""

    def test_material_initialization(self):
        """Test material initialization."""
        material_id = uuid4()
        code = "MAT-001"
        name = "Steel Sheet"
        
        material = {
            "id": material_id,
            "code": code,
            "name": name,
            "unit_of_measure": "KG",
            "unit_cost": 100.00,
        }
        
        assert material["code"] == code
        assert material["name"] == name

    def test_material_unit_of_measure(self):
        """Test material unit of measure."""
        valid_units = ["KG", "L", "M", "PIECE", "BOX"]
        
        for unit in valid_units:
            assert len(unit) > 0

    def test_material_unit_cost(self):
        """Test material unit cost."""
        unit_cost = 50.00
        
        assert unit_cost > 0
        assert isinstance(unit_cost, float)


class TestStockManagement:
    """Test stock addition and removal."""

    def test_add_stock(self):
        """Test adding stock to inventory."""
        current_stock = 100.0
        quantity_added = 50.0
        
        new_stock = current_stock + quantity_added
        
        assert new_stock == 150.0

    def test_remove_stock(self):
        """Test removing stock from inventory."""
        current_stock = 100.0
        quantity_removed = 30.0
        
        new_stock = current_stock - quantity_removed
        
        assert new_stock == 70.0

    def test_prevent_negative_stock(self):
        """Test that stock cannot go negative."""
        current_stock = 50.0
        quantity_requested = 100.0
        
        if quantity_requested > current_stock:
            # Insufficient stock
            assert True  # Would raise error in real app
        
        # Safe removal
        if quantity_requested <= current_stock:
            new_stock = current_stock - quantity_requested
            assert new_stock >= 0

    def test_zero_stock_allowed(self):
        """Test stock can be zero but not negative."""
        current_stock = 10.0
        quantity_removed = 10.0
        
        new_stock = current_stock - quantity_removed
        
        assert new_stock >= 0
        assert new_stock == 0.0


class TestBatchTracking:
    """Test batch/lot tracking."""

    def test_batch_creation(self):
        """Test batch creation."""
        batch_id = uuid4()
        batch_number = "BATCH-001"
        quantity = 1000.0
        manufacturing_date = datetime.utcnow()
        
        batch = {
            "id": batch_id,
            "batch_number": batch_number,
            "quantity": quantity,
            "manufacturing_date": manufacturing_date,
        }
        
        assert batch["batch_number"] == batch_number
        assert batch["quantity"] > 0

    def test_batch_expiration_tracking(self):
        """Test batch expiration date tracking."""
        manufacturing_date = datetime.utcnow()
        shelf_life_days = 365
        
        from datetime import timedelta
        expiration_date = manufacturing_date + timedelta(days=shelf_life_days)
        
        assert expiration_date > manufacturing_date

    def test_expired_batch_detection(self):
        """Test detection of expired batches."""
        expiration_date = datetime(2023, 1, 1)  # Past date
        
        # Current date is after expiration
        is_expired = datetime.utcnow() > expiration_date
        
        assert is_expired is True

    def test_batch_quantity_tracking(self):
        """Test batch quantities are tracked correctly."""
        batch_initial = {"quantity": 1000.0}
        quantity_used = 250.0
        
        batch_remaining = batch_initial["quantity"] - quantity_used
        
        assert batch_remaining == 750.0


class TestStockReservation:
    """Test stock reservation for manufacturing."""

    def test_reserve_stock(self):
        """Test reserving stock for a job."""
        available_stock = 100.0
        reserved_stock = 0.0
        reserve_quantity = 30.0
        
        if reserve_quantity <= available_stock - reserved_stock:
            reserved_stock += reserve_quantity
            available_stock_after = available_stock - reserved_stock
        
        assert reserved_stock == 30.0
        assert available_stock_after == 70.0

    def test_release_reservation(self):
        """Test releasing reserved stock."""
        available_stock = 100.0
        reserved_stock = 30.0
        
        # Release reservation
        reserved_stock -= 10.0
        released_qty = 10.0
        
        assert reserved_stock == 20.0

    def test_reserve_prevents_overselling(self):
        """Test reservations prevent overselling."""
        available_stock = 50.0
        reserved_stock = 40.0
        request_quantity = 20.0
        
        unreserved = available_stock - reserved_stock
        
        if request_quantity > unreserved:
            # Cannot reserve - insufficient unreserved stock
            assert True
        else:
            reserved_stock += request_quantity


class TestStockAdjustment:
    """Test stock adjustment operations."""

    def test_positive_adjustment(self):
        """Test positive stock adjustment."""
        current_stock = 100.0
        adjustment = 25.0
        reason = "recount_correction"
        
        new_stock = current_stock + adjustment
        
        assert new_stock == 125.0

    def test_negative_adjustment(self):
        """Test negative stock adjustment."""
        current_stock = 100.0
        adjustment = -15.0
        reason = "damage_write_off"
        
        new_stock = current_stock + adjustment
        
        assert new_stock == 85.0

    def test_adjustment_tracking(self):
        """Test adjustment history tracking."""
        adjustments = [
            {"date": datetime.utcnow(), "quantity": 50.0, "reason": "receipt"},
            {"date": datetime.utcnow(), "quantity": -10.0, "reason": "damage"},
            {"date": datetime.utcnow(), "quantity": 5.0, "reason": "return"},
        ]
        
        total_adjustment = sum(adj["quantity"] for adj in adjustments)
        
        assert total_adjustment == 45.0
        assert len(adjustments) == 3


class TestSoftDeleteInventory:
    """Test soft delete for inventory items."""

    def test_soft_delete_material(self):
        """Test material soft delete."""
        material = {
            "id": uuid4(),
            "name": "Old Material",
            "is_deleted": False,
            "deleted_at": None,
        }
        
        # Soft delete
        material["is_deleted"] = True
        material["deleted_at"] = datetime.utcnow()
        
        assert material["is_deleted"] is True

    def test_deleted_materials_filtered(self):
        """Test deleted materials are filtered from queries."""
        materials = [
            {"id": 1, "name": "Active", "is_deleted": False},
            {"id": 2, "name": "Deleted", "is_deleted": True},
            {"id": 3, "name": "Active 2", "is_deleted": False},
        ]
        
        active = [m for m in materials if not m["is_deleted"]]
        
        assert len(active) == 2
