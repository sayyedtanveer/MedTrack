"""Money Value Object - Safe decimal handling for financial data."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union


class Money:
    """
    Immutable money value object for safe financial calculations.
    Uses Decimal to avoid floating-point precision errors.
    """

    def __init__(self, amount: Union[str, int, float, Decimal], currency: str = "USD"):
        """
        Initialize Money.
        
        Args:
            amount: Numeric amount (converted to Decimal for precision)
            currency: Currency code (default USD)
            
        Raises:
            ValueError: If amount is negative or currency invalid
        """
        self.amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.currency = currency.upper()

        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if not (2 <= len(self.currency) <= 3):
            raise ValueError("Currency code must be 2-3 characters")

    def __add__(self, other: "Money") -> "Money":
        """Add two Money objects."""
        if not isinstance(other, Money):
            raise TypeError(f"Cannot add Money and {type(other)}")
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        """Subtract two Money objects."""
        if not isinstance(other, Money):
            raise TypeError(f"Cannot subtract {type(other)} from Money")
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {self.currency} and {other.currency}")
        result = self.amount - other.amount
        if result < 0:
            raise ValueError("Result cannot be negative")
        return Money(result, self.currency)

    def __mul__(self, scalar: Union[int, float, Decimal]) -> "Money":
        """Multiply Money by scalar."""
        if not isinstance(scalar, (int, float, Decimal)):
            raise TypeError(f"Cannot multiply Money by {type(scalar)}")
        result = self.amount * Decimal(str(scalar))
        return Money(result, self.currency)

    def __rmul__(self, scalar: Union[int, float, Decimal]) -> "Money":
        """Right multiply (scalar * money)."""
        return self.__mul__(scalar)

    def __truediv__(self, scalar: Union[int, float, Decimal]) -> "Money":
        """Divide Money by scalar."""
        if scalar == 0:
            raise ValueError("Cannot divide by zero")
        result = self.amount / Decimal(str(scalar))
        return Money(result, self.currency)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Money):
            return self.amount == other.amount and self.currency == other.currency
        return False

    def __lt__(self, other: "Money") -> bool:
        if not isinstance(other, Money) or self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        return self == other or self < other

    def __gt__(self, other: "Money") -> bool:
        if not isinstance(other, Money) or self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        return self == other or self > other

    def __str__(self) -> str:
        return f"{self.currency} {self.amount}"

    def __repr__(self) -> str:
        return f"Money({self.amount}, '{self.currency}')"

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))
