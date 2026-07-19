from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from backend.app.domain.shared.base_entity import BaseEntity
from backend.app.domain.bom.entities.bom_line import BOMLine
from backend.app.domain.bom.entities.bom_operation import BOMOperation


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
