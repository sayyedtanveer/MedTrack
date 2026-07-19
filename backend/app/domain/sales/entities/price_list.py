"""Price List Entities for sales order pricing."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from backend.app.domain.shared.base_entity import AggregateRoot


class PriceListLine:
    """Price entry for a product in a price list."""

    def __init__(
        self,
        id: UUID,
        price_list_id: UUID,
        product_id: UUID,
        product_type: str,  # "variant" or "finished_product"
        unit_price: Decimal,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        """Initialize Price List Line."""
        self.id = id
        self.price_list_id = price_list_id
        self.product_id = product_id
        self.product_type = product_type
        self.unit_price = Decimal(str(unit_price))
        self.created_at = created_at
        self.updated_at = updated_at
        
        self._validate()

    def _validate(self) -> None:
        """Validate line invariants."""
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        if self.product_type not in ("variant", "finished_product"):
            raise ValueError("Invalid product type")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "product_id": str(self.product_id),
            "product_type": self.product_type,
            "unit_price": str(self.unit_price),
        }


class PriceList(AggregateRoot):
    """
    Price List - Master data for pricing strategy.
    
    Supports:
    - Default pricing (applies when no client-specific list exists)
    - Client-specific pricing (higher priority than default)
    - Date-based validity (valid_from, valid_to)
    """

    def __init__(
        self,
        id: UUID,
        tenant_id: UUID,
        name: str,
        is_default: bool = False,
        valid_from: date | str | None = None,
        valid_to: date | str | None = None,
        lines: list | None = None,
        is_active: bool = True,
        is_deleted: bool = False,
        deleted_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        """Initialize Price List."""
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )
        self.is_active = is_active
        
        # Price List fields
        self.name = name
        self.is_default = is_default
        self.valid_from = (
            date.fromisoformat(valid_from)
            if isinstance(valid_from, str)
            else valid_from or date.today()
        )
        self.valid_to: date | None = (
            date.fromisoformat(valid_to) if isinstance(valid_to, str) else valid_to
        )
        
        # Lines collection
        self.lines: list = lines or []  # List[PriceListLine]
        
        self._validate()

    def _validate(self) -> None:
        """Validate price list invariants."""
        if not self.name or not self.name.strip():
            raise ValueError("Price list name is required")
        if self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to cannot be before valid_from")

    def set_validity_period(self, valid_from: date, valid_to: date | None) -> None:
        """
        Set validity period for this price list.
        
        Args:
            valid_from: Start date
            valid_to: End date (None = open-ended)
            
        Raises:
            ValueError: If dates invalid
        """
        if valid_to and valid_to < valid_from:
            raise ValueError("valid_to cannot be before valid_from")
        
        self.valid_from = valid_from
        self.valid_to = valid_to
        self._touch()

    def add_line(self, line: PriceListLine) -> None:
        """
        Add a pricing line to this list.
        
        Args:
            line: PriceListLine instance
        """
        # Check for duplicate (same product + product_type)
        for existing in self.lines:
            if (existing.product_id == line.product_id and
                existing.product_type == line.product_type):
                raise ValueError(
                    f"Product {line.product_id} ({line.product_type}) "
                    "already has a price in this list"
                )
        
        self.lines.append(line)
        self._touch()

    def update_line_price(self, product_id: UUID, product_type: str, new_price: Decimal) -> None:
        """
        Update price for a product in this list.
        
        Args:
            product_id: Product ID
            product_type: Product type
            new_price: New unit price
            
        Raises:
            ValueError: If product not found or price invalid
        """
        new_price = Decimal(str(new_price))
        if new_price < 0:
            raise ValueError("Unit price cannot be negative")
        
        for line in self.lines:
            if line.product_id == product_id and line.product_type == product_type:
                line.unit_price = new_price
                self._touch()
                return
        
        raise ValueError(
            f"Product {product_id} ({product_type}) not found in this price list"
        )

    def remove_line(self, product_id: UUID, product_type: str) -> None:
        """
        Remove a pricing line from this list.
        
        Args:
            product_id: Product ID
            product_type: Product type
            
        Raises:
            ValueError: If product not found
        """
        original_count = len(self.lines)
        self.lines = [
            line for line in self.lines
            if not (line.product_id == product_id and line.product_type == product_type)
        ]
        
        if len(self.lines) == original_count:
            raise ValueError(
                f"Product {product_id} ({product_type}) not found in this price list"
            )
        
        self._touch()

    def get_price(self, product_id: UUID, product_type: str) -> Decimal | None:
        """
        Get unit price for a product.
        
        Args:
            product_id: Product ID
            product_type: Product type
            
        Returns:
            Unit price or None if not found
        """
        for line in self.lines:
            if line.product_id == product_id and line.product_type == product_type:
                return line.unit_price
        return None

    def is_valid_on(self, check_date: date) -> bool:
        """
        Check if this price list is valid on a given date.
        
        Args:
            check_date: Date to check
            
        Returns:
            True if valid, False otherwise
        """
        if not self.is_active:
            return False
        if check_date < self.valid_from:
            return False
        if self.valid_to and check_date > self.valid_to:
            return False
        return True

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "is_default": self.is_default,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "is_active": self.is_active,
            "lines": [line.to_dict() for line in self.lines],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

