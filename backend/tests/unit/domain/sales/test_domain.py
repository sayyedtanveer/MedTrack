"""Unit tests for Sales domain layer."""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.sales.value_objects import (
    OrderNumber,
    OrderStatus,
    PaymentStatus,
    LineStatus,
    Money,
)
from app.domain.sales.entities import Client, SalesOrder, SalesOrderLine, PriceList, PriceListLine
from app.domain.sales.entities.sales_order import InvalidStatusTransitionError


class TestOrderNumber:
    """Tests for OrderNumber value object."""

    def test_generate_creates_valid_order_number(self):
        """Test that generate() creates valid order number with date and sequence."""
        order_num = OrderNumber.generate(sequence=1)
        
        # Should be format SO-YYYYMMDD-###
        assert str(order_num).startswith("SO-")
        parts = str(order_num).split("-")
        assert len(parts) == 3
        assert parts[0] == "SO"
        assert len(parts[1]) == 8  # YYYYMMDD
        assert parts[2].isdigit()

    def test_order_number_immutable(self):
        """Test that OrderNumber is immutable."""
        order_num = OrderNumber.generate(sequence=1)
        
        with pytest.raises(AttributeError):
            order_num.value = "new_value"

    def test_order_number_equality(self):
        """Test that same values are equal."""
        order_num1 = OrderNumber("SO-20260326-001")
        order_num2 = OrderNumber("SO-20260326-001")
        
        assert order_num1 == order_num2

    def test_order_number_string_representation(self):
        """Test string representation."""
        order_num = OrderNumber("SO-20260326-001")
        assert str(order_num) == "SO-20260326-001"


class TestMoney:
    """Tests for Money value object."""

    def test_money_creation(self):
        """Test creating Money instance."""
        money = Money(amount=Decimal("100.50"))
        assert money.amount == Decimal("100.50")

    def test_money_addition(self):
        """Test adding two Money instances."""
        money1 = Money(Decimal("100.00"))
        money2 = Money(Decimal("50.00"))
        result = money1 + money2
        
        assert result.amount == Decimal("150.00")

    def test_money_subtraction(self):
        """Test subtracting Money instances."""
        money1 = Money(Decimal("100.00"))
        money2 = Money(Decimal("30.00"))
        result = money1 - money2
        
        assert result.amount == Decimal("70.00")

    def test_money_multiplication(self):
        """Test multiplying Money."""
        money = Money(Decimal("50.00"))
        result = money * Decimal("2")
        
        assert result.amount == Decimal("100.00")

    def test_money_comparison(self):
        """Test Money comparisons."""
        money1 = Money(Decimal("100.00"))
        money2 = Money(Decimal("50.00"))
        
        assert money1 > money2
        assert money2 < money1
        assert money1 >= money2
        assert money1 != money2

    def test_money_equality(self):
        """Test Money equality."""
        money1 = Money(Decimal("100.00"))
        money2 = Money(Decimal("100.00"))
        
        assert money1 == money2

    def test_money_negative_validation(self):
        """Test that negative amounts raise error."""
        with pytest.raises(ValueError):
            Money(Decimal("-50.00"))

    def test_money_zero_allowed(self):
        """Test that zero amount is allowed."""
        money = Money(Decimal("0.00"))
        assert money.amount == Decimal("0.00")


class TestOrderStatus:
    """Tests for OrderStatus enum."""

    def test_all_statuses_defined(self):
        """Test that all required statuses exist."""
        assert OrderStatus.DRAFT
        assert OrderStatus.CONFIRMED
        assert OrderStatus.PRODUCTION
        assert OrderStatus.READY
        assert OrderStatus.SHIPPED
        assert OrderStatus.DELIVERED
        assert OrderStatus.CANCELLED

    def test_status_value(self):
        """Test status string values."""
        assert OrderStatus.DRAFT.value == "DRAFT"
        assert OrderStatus.CONFIRMED.value == "CONFIRMED"
        assert OrderStatus.CANCELLED.value == "CANCELLED"


class TestLineStatus:
    """Tests for LineStatus enum."""

    def test_line_statuses_defined(self):
        """Test that all line statuses exist."""
        assert LineStatus.PENDING
        assert LineStatus.ALLOCATED
        assert LineStatus.BACKORDER
        assert LineStatus.SHIPPED
        assert LineStatus.DELIVERED


class TestClient:
    """Tests for Client aggregate root."""

    def test_create_client(self):
        """Test creating a client."""
        client_id = uuid4()
        tenant_id = uuid4()
        
        client = Client(
            id=client_id,
            tenant_id=tenant_id,
            code="CLIENT001",
            name="Test Client",
            credit_limit=Decimal("10000.00"),
        )
        
        assert client.id == client_id
        assert client.code == "CLIENT001"
        assert client.name == "Test Client"
        assert client.credit_limit == Decimal("10000.00")
        assert client.credit_used == Decimal("0.00")
        assert client.is_active is True

    def test_check_available_credit_passes(self):
        """Test credit check when sufficient credit available."""
        client = Client(
            id=uuid4(),
            tenant_id=uuid4(),
            code="CLIENT001",
            name="Test Client",
            credit_limit=Decimal("10000.00"),
        )
        
        # Should pass with amount less than limit
        assert client.check_available_credit(Decimal("5000.00")) is True

    def test_check_available_credit_fails(self):
        """Test credit check when insufficient credit."""
        client = Client(
            id=uuid4(),
            tenant_id=uuid4(),
            code="CLIENT001",
            name="Test Client",
            credit_limit=Decimal("10000.00"),
        )
        client.credit_used = Decimal("8000.00")
        
        # Should fail when exceeding available credit
        assert client.check_available_credit(Decimal("3000.00")) is False

    def test_increase_credit_used(self):
        """Test allocating credit."""
        client = Client(
            id=uuid4(),
            tenant_id=uuid4(),
            code="CLIENT001",
            name="Test Client",
            credit_limit=Decimal("10000.00"),
        )
        
        client.increase_credit_used(Decimal("5000.00"))
        assert client.credit_used == Decimal("5000.00")

    def test_decrease_credit_used(self):
        """Test releasing credit."""
        client = Client(
            id=uuid4(),
            tenant_id=uuid4(),
            code="CLIENT001",
            name="Test Client",
            credit_limit=Decimal("10000.00"),
        )
        client.credit_used = Decimal("5000.00")
        
        client.decrease_credit_used(Decimal("2000.00"))
        assert client.credit_used == Decimal("3000.00")

    def test_deactivate_client(self):
        """Test deactivating a client."""
        client = Client(
            id=uuid4(),
            tenant_id=uuid4(),
            code="CLIENT001",
            name="Test Client",
        )
        
        assert client.is_active is True
        client.is_active = False
        assert client.is_active is False


class TestSalesOrderLine:
    """Tests for SalesOrderLine entity."""

    def test_create_order_line(self):
        """Test creating an order line."""
        line_id = uuid4()
        order_id = uuid4()
        product_id = uuid4()
        uom_id = uuid4()
        
        line = SalesOrderLine(
            id=line_id,
            order_id=order_id,
            product_id=product_id,
            product_type="variant",
            uom_id=uom_id,
            quantity=Decimal("10.00"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("18.00"),
        )
        
        assert line.id == line_id
        assert line.product_id == product_id
        assert line.quantity == Decimal("10.00")
        assert line.unit_price == Decimal("100.00")
        assert line.tax_rate == Decimal("18.00")
        assert line.status == LineStatus.PENDING

    def test_line_totals_calculation(self):
        """Test that line totals are calculated correctly."""
        line = SalesOrderLine(
            id=uuid4(),
            order_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("10.00"),  # qty
            unit_price=Decimal("100.00"),  # price
            tax_rate=Decimal("10.00"),  # 10% tax
        )
        
        # subtotal = 10 * 100 = 1000
        # tax = 1000 * (10/100) = 100
        # total = 1000 + 100 = 1100
        assert line.line_total == Decimal("1100.00")
        assert line.tax_amount == Decimal("100.00")

    def test_allocate_quantity(self):
        """Test allocating stock for line."""
        line = SalesOrderLine(
            id=uuid4(),
            order_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("10.00"),
            unit_price=Decimal("100.00"),
        )
        
        line.allocate(Decimal("7.00"))
        
        assert line.allocated_quantity == Decimal("7.00")
        assert line.status == LineStatus.ALLOCATED

    def test_allocate_exceeds_quantity_fails(self):
        """Test that allocating more than line qty fails."""
        line = SalesOrderLine(
            id=uuid4(),
            order_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("10.00"),
            unit_price=Decimal("100.00"),
        )
        
        with pytest.raises(ValueError):
            line.allocate(Decimal("15.00"))

    def test_backorder_quantity(self):
        """Test marking quantity as backorder."""
        line = SalesOrderLine(
            id=uuid4(),
            order_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("10.00"),
            unit_price=Decimal("100.00"),
        )
        
        line.backorder(Decimal("5.00"))
        
        assert line.backorder_quantity == Decimal("5.00")
        assert line.status == LineStatus.BACKORDER

    def test_ship_quantity(self):
        """Test recording shipment."""
        line = SalesOrderLine(
            id=uuid4(),
            order_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("10.00"),
            unit_price=Decimal("100.00"),
        )
        
        line.allocate(Decimal("10.00"))
        line.ship(Decimal("5.00"))
        
        assert line.shipped_quantity == Decimal("5.00")
        assert line.get_unshipped_quantity() == Decimal("5.00")

    def test_get_unallocated_quantity(self):
        """Test calculating unallocated quantity."""
        line = SalesOrderLine(
            id=uuid4(),
            order_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("10.00"),
            unit_price=Decimal("100.00"),
        )
        
        line.allocate(Decimal("6.00"))
        line.backorder(Decimal("2.00"))
        
        # unallocated = 10 - 6 - 2 = 2
        assert line.get_unallocated_quantity() == Decimal("2.00")


class TestSalesOrder:
    """Tests for SalesOrder aggregate root."""

    def test_create_order(self):
        """Test creating a sales order."""
        order_id = uuid4()
        client_id = uuid4()
        tenant_id = uuid4()
        order_date = date.today()
        delivery_date = date.today() + timedelta(days=30)
        
        order = SalesOrder(
            id=order_id,
            tenant_id=tenant_id,
            order_number=OrderNumber.generate(1),
            client_id=client_id,
            order_date=order_date,
            delivery_date=delivery_date,
        )
        
        assert order.id == order_id
        assert order.status == OrderStatus.DRAFT
        assert order.payment_status == PaymentStatus.PENDING
        assert len(order.lines) == 0

    def test_delivery_before_order_fails(self):
        """Test that delivery date before order date fails."""
        with pytest.raises(ValueError):
            SalesOrder(
                id=uuid4(),
                tenant_id=uuid4(),
                order_number=OrderNumber.generate(1),
                client_id=uuid4(),
                order_date=date(2026, 4, 1),
                delivery_date=date(2026, 3, 20),
            )

    def test_add_line_to_order(self):
        """Test adding line to order."""
        order = SalesOrder(
            id=uuid4(),
            tenant_id=uuid4(),
            order_number=OrderNumber.generate(1),
            client_id=uuid4(),
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=30),
        )
        
        line = SalesOrderLine(
            id=uuid4(),
            order_id=order.id,
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("5.00"),
            unit_price=Decimal("100.00"),
        )
        
        order.add_line(line)
        
        assert len(order.lines) == 1
        assert order.lines[0] == line

    def test_remove_line_from_order(self):
        """Test removing line from order."""
        order = SalesOrder(
            id=uuid4(),
            tenant_id=uuid4(),
            order_number=OrderNumber.generate(1),
            client_id=uuid4(),
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=30),
        )
        
        line = SalesOrderLine(
            id=uuid4(),
            order_id=order.id,
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("5.00"),
            unit_price=Decimal("100.00"),
        )
        
        order.add_line(line)
        order.remove_line(line.id)
        
        assert len(order.lines) == 0

    def test_total_calculation(self):
        """Test order totals calculation."""
        order = SalesOrder(
            id=uuid4(),
            tenant_id=uuid4(),
            order_number=OrderNumber.generate(1),
            client_id=uuid4(),
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=30),
        )
        
        # Add two lines
        line1 = SalesOrderLine(
            id=uuid4(),
            order_id=order.id,
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("10.00"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("10.00"),
        )
        
        line2 = SalesOrderLine(
            id=uuid4(),
            order_id=order.id,
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("5.00"),
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("10.00"),
        )
        
        order.add_line(line1)
        order.add_line(line2)
        
        # line1: 10 * 100 = 1000, tax = 100
        # line2: 5 * 50 = 250, tax = 25
        # total: 1000 + 250 + 100 + 25 = 1375
        assert order.subtotal == Decimal("1250.00")
        assert order.tax_amount == Decimal("125.00")
        assert order.grand_total == Decimal("1375.00")

    def test_apply_discount(self):
        """Test applying discount to order."""
        order = SalesOrder(
            id=uuid4(),
            tenant_id=uuid4(),
            order_number=OrderNumber.generate(1),
            client_id=uuid4(),
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=30),
        )
        
        line = SalesOrderLine(
            id=uuid4(),
            order_id=order.id,
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("10.00"),
            unit_price=Decimal("100.00"),
        )
        
        order.add_line(line)
        order.apply_discount(Decimal("100.00"))
        
        assert order.discount_amount == Decimal("100.00")
        assert order.grand_total == Decimal("900.00")  # 1000 - 100

    def test_discount_exceeds_subtotal_fails(self):
        """Test that discount exceeding subtotal fails."""
        order = SalesOrder(
            id=uuid4(),
            tenant_id=uuid4(),
            order_number=OrderNumber.generate(1),
            client_id=uuid4(),
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=30),
        )
        
        with pytest.raises(ValueError):
            order.apply_discount(Decimal("2000.00"))

    def test_status_transitions(self):
        """Test valid status transitions."""
        order = SalesOrder(
            id=uuid4(),
            tenant_id=uuid4(),
            order_number=OrderNumber.generate(1),
            client_id=uuid4(),
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=30),
        )
        
        # DRAFT -> CONFIRMED
        assert order.can_transition_to(OrderStatus.CONFIRMED) is True
        assert order.can_transition_to(OrderStatus.SHIPPED) is False
        order.add_line(
            SalesOrderLine(
                id=uuid4(),
                order_id=order.id,
                product_id=uuid4(),
                product_type="variant",
                uom_id=uuid4(),
                quantity=Decimal("1.00"),
                unit_price=Decimal("100.00"),
            )
        )

        order.confirm()
        assert order.status == OrderStatus.CONFIRMED
        
        # CONFIRMED -> PRODUCTION
        assert order.can_transition_to(OrderStatus.PRODUCTION) is True
        order.transition_to_production()
        assert order.status == OrderStatus.PRODUCTION

    def test_invalid_status_transition_fails(self):
        """Test that invalid transitions fail."""
        order = SalesOrder(
            id=uuid4(),
            tenant_id=uuid4(),
            order_number=OrderNumber.generate(1),
            client_id=uuid4(),
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=30),
        )
        
        # Try to ship from DRAFT (invalid)
        with pytest.raises(InvalidStatusTransitionError):
            order.ship()

    def test_cannot_add_line_to_non_draft_order(self):
        """Test that lines can only be added to DRAFT orders."""
        order = SalesOrder(
            id=uuid4(),
            tenant_id=uuid4(),
            order_number=OrderNumber.generate(1),
            client_id=uuid4(),
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=30),
        )
        
        # Add initial line
        line1 = SalesOrderLine(
            id=uuid4(),
            order_id=order.id,
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("5.00"),
            unit_price=Decimal("100.00"),
        )
        order.add_line(line1)
        order.confirm()
        
        # Try to add line after confirmation (should fail)
        line2 = SalesOrderLine(
            id=uuid4(),
            order_id=order.id,
            product_id=uuid4(),
            product_type="variant",
            uom_id=uuid4(),
            quantity=Decimal("5.00"),
            unit_price=Decimal("100.00"),
        )
        
        with pytest.raises(ValueError):
            order.add_line(line2)


class TestPriceList:
    """Tests for PriceList aggregate root."""

    def test_create_price_list(self):
        """Test creating a price list."""
        price_list = PriceList(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Default Pricing",
            is_default=True,
        )
        
        assert price_list.name == "Default Pricing"
        assert price_list.is_default is True
        assert price_list.is_active is True
        assert len(price_list.lines) == 0

    def test_add_pricing_line(self):
        """Test adding pricing line."""
        price_list = PriceList(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Default Pricing",
        )
        
        line = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=uuid4(),
            product_type="variant",
            unit_price=Decimal("100.00"),
        )
        
        price_list.add_line(line)
        
        assert len(price_list.lines) == 1
        assert price_list.lines[0] == line

    def test_duplicate_product_fails(self):
        """Test that adding duplicate product fails."""
        price_list = PriceList(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Default Pricing",
        )
        
        product_id = uuid4()
        product_type = "variant"
        
        line1 = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=product_id,
            product_type=product_type,
            unit_price=Decimal("100.00"),
        )
        
        price_list.add_line(line1)
        
        # Try to add same product again
        line2 = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=product_id,
            product_type=product_type,
            unit_price=Decimal("150.00"),
        )
        
        with pytest.raises(ValueError):
            price_list.add_line(line2)

    def test_get_price(self):
        """Test getting price for product."""
        price_list = PriceList(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Default Pricing",
        )
        
        product_id = uuid4()
        product_type = "variant"
        
        line = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=product_id,
            product_type=product_type,
            unit_price=Decimal("100.00"),
        )
        
        price_list.add_line(line)
        price = price_list.get_price(product_id, product_type)
        
        assert price == Decimal("100.00")

    def test_get_price_not_found(self):
        """Test getting price for non-existent product."""
        price_list = PriceList(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Default Pricing",
        )
        
        price = price_list.get_price(uuid4(), "variant")
        assert price is None

    def test_is_valid_on_date(self):
        """Test checking validity on date."""
        today = date.today()
        price_list = PriceList(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Default Pricing",
        )
        price_list.valid_from = today
        price_list.valid_to = today + timedelta(days=365)
        
        assert price_list.is_valid_on(today) is True
        assert price_list.is_valid_on(today + timedelta(days=365)) is True
        assert price_list.is_valid_on(today - timedelta(days=365)) is False
        assert price_list.is_valid_on(today + timedelta(days=366)) is False

    def test_update_price(self):
        """Test updating a pricing line."""
        price_list = PriceList(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Default Pricing",
        )
        
        product_id = uuid4()
        product_type = "variant"
        
        line = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=product_id,
            product_type=product_type,
            unit_price=Decimal("100.00"),
        )
        
        price_list.add_line(line)
        price_list.update_line_price(product_id, product_type, Decimal("150.00"))
        
        assert price_list.get_price(product_id, product_type) == Decimal("150.00")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
