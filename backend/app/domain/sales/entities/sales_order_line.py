"""Sales Order Line Entity."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from backend.app.domain.sales.value_objects import LineStatus, Money


class SalesOrderLine:
    """
    Sales Order Line - Value object within SalesOrder aggregate.
    
    Responsible for:
    - Line totals calculation
    - Allocation tracking (allocated, shipped, backorder)
    - Tax computation
    """

    def __init__(
        self,
        id: UUID,
        order_id: UUID,
        product_id: UUID,
        product_type: str,  # "variant" or "finished_product"
        uom_id: UUID,
        quantity: Decimal,
        unit_price: Decimal,
        tax_rate: Decimal = Decimal("0"),
        status: LineStatus | str = LineStatus.PENDING,
        allocated_quantity: Decimal = Decimal("0"),
        shipped_quantity: Decimal = Decimal("0"),
        backorder_quantity: Decimal = Decimal("0"),
        tax_amount: Decimal | None = None,
        line_total: Decimal | None = None,
        work_order_id: UUID | None = None,
        notes: str | None = None,
        shortfall_quantity: Decimal = Decimal("0"),
        production_required: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        """Initialize Sales Order Line."""
        self.id = id
        self.order_id = order_id
        self.product_id = product_id
        self.product_type = product_type
        self.uom_id = uom_id
        self.quantity = Decimal(str(quantity))
        self.unit_price = Decimal(str(unit_price))
        self.tax_rate = Decimal(str(tax_rate))
        
        # Allocations
        self.allocated_quantity = Decimal(str(allocated_quantity))
        self.shipped_quantity = Decimal(str(shipped_quantity))
        self.backorder_quantity = Decimal(str(backorder_quantity))
        
        # Shortage tracking (Req 16 — Gap #2)
        self.shortfall_quantity = Decimal(str(shortfall_quantity))
        self.production_required = bool(production_required)
        
        # Denormalized for efficiency
        self.tax_amount = Decimal(str(tax_amount)) if tax_amount is not None else Decimal("0")
        self.line_total = Decimal(str(line_total)) if line_total is not None else Decimal("0")
        
        self.status = status if isinstance(status, LineStatus) else LineStatus(str(status).lower())
        self.work_order_id = work_order_id
        self.notes = notes
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        
        self._validate()
        if tax_amount is None or line_total is None:
            self._calculate_totals()

    def _validate(self) -> None:
        """Validate line invariants."""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        if self.tax_rate < 0 or self.tax_rate > 100:
            raise ValueError("Tax rate must be between 0 and 100")
        if self.product_type not in ("variant", "finished_product"):
            raise ValueError("Invalid product type")

    def _calculate_totals(self) -> None:
        """Calculate tax and line totals."""
        # Subtotal = quantity × unit_price
        subtotal = self.quantity * self.unit_price
        
        # Tax = subtotal × (tax_rate / 100)
        self.tax_amount = (subtotal * self.tax_rate / Decimal("100")).quantize(
            Decimal("0.01")
        )
        
        # Total = subtotal + tax
        self.line_total = (subtotal + self.tax_amount).quantize(Decimal("0.01"))

    def allocate(self, qty: Decimal) -> None:
        """
        Allocate stock for this line.
        
        Args:
            qty: Quantity to allocate
            
        Raises:
            ValueError: If exceeds line quantity
        """
        qty = Decimal(str(qty))
        if self.allocated_quantity + qty > self.quantity:
            raise ValueError(
                f"Cannot allocate {qty}: would exceed line quantity "
                f"({self.allocated_quantity + qty} > {self.quantity})"
            )
        self.allocated_quantity += qty
        self.status = LineStatus.ALLOCATED
        self.updated_at = datetime.now(timezone.utc)

    def backorder(self, qty: Decimal) -> None:
        """
        Mark quantity as backorder (work order in progress).
        
        Args:
            qty: Quantity on backorder
        """
        qty = Decimal(str(qty))
        if qty < 0:
            raise ValueError("Backorder quantity cannot be negative")
        if qty > self.quantity - self.allocated_quantity:
            raise ValueError(
                "Backorder quantity exceeds unallocated quantity"
            )
        self.backorder_quantity = qty
        self.status = LineStatus.BACKORDER
        self.updated_at = datetime.now(timezone.utc)

    def mark_shortage(self, shortfall: Decimal) -> None:
        """
        Record FG shortage for this line (Req 16 — Gap #2).

        Called when FG stock is insufficient at SO confirmation.  The line is
        flagged so a work order can be created to manufacture the missing qty.

        Args:
            shortfall: Quantity that could not be reserved from existing FG stock
        """
        shortfall = Decimal(str(shortfall))
        if shortfall < 0:
            raise ValueError("Shortfall quantity cannot be negative")
        self.shortfall_quantity = shortfall
        if shortfall > 0:
            self.production_required = True
        self.updated_at = datetime.now(timezone.utc)

    def ship(self, qty: Decimal) -> None:
        """
        Record shipment for this line.
        
        Args:
            qty: Quantity shipped
            
        Raises:
            ValueError: If exceeds allocated quantity
        """
        qty = Decimal(str(qty))
        if self.shipped_quantity + qty > self.allocated_quantity:
            raise ValueError(
                f"Cannot ship {qty}: exceeds allocated quantity "
                f"({self.shipped_quantity + qty} > {self.allocated_quantity})"
            )
        self.shipped_quantity += qty
        if self.shipped_quantity >= self.allocated_quantity:
            self.status = LineStatus.SHIPPED
        self.updated_at = datetime.now(timezone.utc)

    def get_unshipped_quantity(self) -> Decimal:
        """Get quantity allocated but not yet shipped."""
        return self.allocated_quantity - self.shipped_quantity

    def get_unallocated_quantity(self) -> Decimal:
        """Get quantity not yet allocated or backordered."""
        return self.quantity - self.allocated_quantity - self.backorder_quantity

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "product_id": str(self.product_id),
            "product_type": self.product_type,
            "product_name": getattr(self, "product_name", None),
            "product_code": getattr(self, "product_code", None),
            "uom_id": str(self.uom_id),
            "uom_code": getattr(self, "uom_code", None),
            "uom_name": getattr(self, "uom_name", None),
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "tax_rate": str(self.tax_rate),
            "tax_amount": str(self.tax_amount),
            "line_total": str(self.line_total),
            "allocated_quantity": str(self.allocated_quantity),
            "shipped_quantity": str(self.shipped_quantity),
            "backorder_quantity": str(self.backorder_quantity),
            "shortfall_quantity": str(self.shortfall_quantity),
            "production_required": self.production_required,
            "status": self.status.value,
            "work_order_id": str(self.work_order_id) if self.work_order_id else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

