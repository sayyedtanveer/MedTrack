"""
Value objects for procurement pricing.

Immutable, reusable value types used by domain entities.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class PricingTier:
    """
    Immutable value object for tiered pricing.

    Represents a quantity range with an associated discount percentage.
    Used in supplier price agreements for volume-based discounts.
    """

    min_quantity: Decimal
    max_quantity: Optional[Decimal]  # None = no upper limit
    discount_percent: Decimal

    def __post_init__(self) -> None:
        """Validate tier constraints."""
        if self.min_quantity < Decimal("0"):
            raise ValueError("min_quantity must be non-negative")
        if self.discount_percent < Decimal("0") or self.discount_percent > Decimal("100"):
            raise ValueError("discount_percent must be between 0 and 100")
        if self.max_quantity is not None and self.max_quantity < self.min_quantity:
            raise ValueError("max_quantity must be >= min_quantity")

    def get_price_after_discount(self, base_price: Decimal) -> Decimal:
        """
        Calculate price after applying discount.

        Args:
            base_price: Price before discount

        Returns:
            Price with discount applied, rounded to 6 decimals
        """
        discount_multiplier = (Decimal("100") - self.discount_percent) / Decimal("100")
        return (base_price * discount_multiplier).quantize(Decimal("0.000001"))
