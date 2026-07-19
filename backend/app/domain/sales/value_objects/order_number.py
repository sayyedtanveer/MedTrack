"""Order Number Value Object - Immutable, unique per tenant."""

from datetime import datetime
from typing import Self


class OrderNumber:
    """
    Order number format: SO-{YYYYMMDD}-{sequence}
    Example: SO-20260326-001
    
    Immutable value object ensuring uniqueness per tenant.
    """

    def __init__(self, value: str):
        """
        Initialize from formatted string or generate new.
        
        Args:
            value: Full order number string (SO-20260326-001)
            
        Raises:
            ValueError: If format is invalid
        """
        if not isinstance(value, str):
            raise ValueError("Order number must be string")
        
        parts = value.split("-")
        if len(parts) != 3 or parts[0] != "SO":
            raise ValueError("Invalid order number format. Expected: SO-YYYYMMDD-###")
        
        try:
            datetime.strptime(parts[1], "%Y%m%d")
        except ValueError as e:
            raise ValueError(f"Invalid date in order number: {parts[1]}") from e
        
        if not parts[2].isdigit() or len(parts[2]) != 3:
            raise ValueError("Sequence must be 3-digit number")
        
        self._value = value

    @classmethod
    def generate(cls, sequence: int) -> Self:
        """
        Generate new order number for today.
        
        Args:
            sequence: Sequential number (1-999)
            
        Returns:
            New OrderNumber instance
        """
        if not (1 <= sequence <= 999):
            raise ValueError("Sequence must be between 1 and 999")
        
        today = datetime.now().strftime("%Y%m%d")
        return cls(f"SO-{today}-{sequence:03d}")

    @property
    def value(self) -> str:
        """Return string representation."""
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"OrderNumber({self._value})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, OrderNumber):
            return self._value == other._value
        return self._value == other

    def __hash__(self) -> int:
        return hash(self._value)
