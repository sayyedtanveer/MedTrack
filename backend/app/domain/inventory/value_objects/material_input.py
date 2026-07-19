from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialInput:
    """Compatibility value object for legacy BOM unit tests."""

    material_id: uuid.UUID
    quantity: float
    scrap_percentage: float = 0.0

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Material quantity must be positive.")
        if not 0 <= self.scrap_percentage <= 1:
            raise ValueError("Scrap percentage must be between 0 and 1.")
