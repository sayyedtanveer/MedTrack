import uuid
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class BOMOperation(BaseEntity):
    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: uuid.UUID,
        bom_id: uuid.UUID,
        operation_id: uuid.UUID,
        sequence: int,
        **kwargs
    ):
        super().__init__(id=id, tenant_id=tenant_id, **kwargs)
        if not bom_id:
            raise ValueError("BOM ID is required.")
        if not operation_id:
            raise ValueError("Operation ID is required.")
        if sequence <= 0:
            raise ValueError("Sequence must be a positive integer.")

        self.bom_id = bom_id
        self.operation_id = operation_id
        self.sequence = sequence
