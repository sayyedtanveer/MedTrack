from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseValueObject(ABC):
    """
    Abstract base for all value objects.

    Value objects are immutable — equality is based on value, not identity.
    Subclasses MUST override _validate() and define their fields as
    frozen-dataclass-compatible attributes.
    """

    def __post_init__(self) -> None:
        self._validate()

    @abstractmethod
    def _validate(self) -> None:
        """Raise ValueError or DomainException if value is invalid."""
        ...

    def __eq__(self, other: Any) -> bool:
        if type(self) is not type(other):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"
