from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Attribute:
    """Compatibility value object for product attribute definitions."""

    name: str
    data_type: str
    is_required: bool = False
    allowed_values: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Attribute name is required.")
        if not self.data_type.strip():
            raise ValueError("Attribute data type is required.")
