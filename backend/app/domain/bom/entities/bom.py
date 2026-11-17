from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from backend.app.domain.shared.base_entity import BaseEntity
from backend.app.domain.bom.entities.bom_line import BOMLine
from backend.app.domain.bom.entities.bom_operation import BOMOperation

SUPPORTED_MAKING_BASES = frozenset({"PER_PIECE"})


class BillOfMaterial(BaseEntity):
    def __init__(
        self,
        *,
        version: str,
        valid_from: datetime,
        created_by: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
        template_id: Optional[uuid.UUID] = None,
        variant_id: Optional[uuid.UUID] = None,
        valid_to: Optional[datetime] = None,
        approved_by: Optional[uuid.UUID] = None,
        is_active: bool = False,
        lines: Optional[List[BOMLine]] = None,
        operations: Optional[List[BOMOperation]] = None,
        id: Optional[uuid.UUID] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        operations_count: int = 0,
        # Outside making charge (Option A)
        making_charge: Optional[Decimal] = None,
        making_charge_basis: Optional[str] = None,
    ):
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
            created_at=created_at,
            updated_at=updated_at,
        )

        # Enforce that exactly one product target is provided
        refs = [x for x in (template_id, variant_id) if x is not None]
        if len(refs) != 1:
            raise ValueError("BOM must reference exactly one of template_id or variant_id.")

        self.template_id = template_id
        self.variant_id = variant_id

        if not version or not version.strip():
            raise ValueError("BOM version cannot be empty.")
        self.version = version

        self.is_active = is_active
        self.valid_from = valid_from
        self.valid_to = valid_to
        self.created_by = created_by
        self.approved_by = approved_by

        self.lines: List[BOMLine] = lines or []
        self.operations: List[BOMOperation] = operations or []
        self.operations_count = operations_count

        # Making charge validation
        self._validate_making_charge(making_charge, making_charge_basis)
        self.making_charge: Optional[Decimal] = (
            Decimal(str(making_charge)) if making_charge is not None else None
        )
        self.making_charge_basis: Optional[str] = making_charge_basis

    @staticmethod
    def _validate_making_charge(
        charge: Optional[Decimal], basis: Optional[str]
    ) -> None:
        """Enforce pairing, non-negativity, and supported basis rules."""
        if charge is None and basis is None:
            return  # Not configured — allowed
        if (charge is None) != (basis is None):
            raise ValueError(
                "making_charge and making_charge_basis must both be set or both be NULL. "
                "They cannot be configured independently."
            )
        charge_decimal = Decimal(str(charge))  # type: ignore[arg-type]
        if charge_decimal < Decimal("0"):
            raise ValueError("making_charge cannot be negative.")
        basis_upper = str(basis).upper()
        if basis_upper not in SUPPORTED_MAKING_BASES:
            supported = ", ".join(sorted(SUPPORTED_MAKING_BASES))
            raise ValueError(
                f"making_charge_basis '{basis}' is not supported. "
                f"Supported values: {supported}."
            )

    @property
    def target_product_id(self) -> uuid.UUID:
        return self.template_id or self.variant_id  # type: ignore

    def add_line(self, line: BOMLine) -> None:
        if line.template_id is not None and line.template_id == self.template_id:
            raise ValueError("A BOM cannot reference its own template as a component.")
        if line.variant_id is not None and line.variant_id == self.variant_id:
            raise ValueError("A BOM cannot reference its own variant as a component.")
        self.lines.append(line)

    def add_operation(self, operation: BOMOperation) -> None:
        self.operations.append(operation)

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False
