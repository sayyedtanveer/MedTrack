"""Operation Master domain entity for manufacturing routing."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class OperationType(str, Enum):
    """Manufacturing operation classification."""
    CUTTING = "cutting"
    MACHINING = "machining"
    ASSEMBLY = "assembly"
    CALIBRATION = "calibration"
    TESTING = "testing"
    INSPECTION = "inspection"
    PACKAGING = "packaging"
    FINISHING = "finishing"
    OTHER = "other"


@dataclass
class Operation:
    """Operation Master domain entity.
    
    Represents a reusable manufacturing operation that can be attached to BOMs
    and inherited by work orders.
    """
    id: uuid.UUID
    tenant_id: uuid.UUID
    operation_code: str  # Business code like "10", "20", "30"
    name: str  # Human-readable: "Cutting", "Assembly"
    operation_type: OperationType

    # Routing & sequencing
    default_sequence: int  # Sequence number for ordering (10, 20, 30...)
    description: Optional[str] = None
    estimated_time_minutes: Optional[Decimal] = None  # Estimated duration
    
    # Quality & operational flags
    qc_required: bool = False  # Quality control required?
    is_active: bool = True
    
    # UI/UX metadata
    color: Optional[str] = None  # Hex color or named color for UI
    icon_code: Optional[str] = None  # Icon identifier (e.g., "cut", "hammer", "box")
    
    # Audit trail
    created_by: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Operation):
            return NotImplemented
        return self.id == other.id

    def validate(self) -> list[str]:
        """Validate operation business rules."""
        errors = []
        
        if not self.operation_code or not self.operation_code.strip():
            errors.append("Operation code is required")
        elif len(self.operation_code) > 10:
            errors.append("Operation code must be ≤10 characters")
            
        if not self.name or not self.name.strip():
            errors.append("Operation name is required")
        elif len(self.name) > 100:
            errors.append("Operation name must be ≤100 characters")
        
        if self.estimated_time_minutes and self.estimated_time_minutes <= 0:
            errors.append("Estimated time must be positive")
            
        if self.default_sequence <= 0:
            errors.append("Sequence must be positive (10, 20, 30, ...)")
        
        return errors

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "operation_code": self.operation_code,
            "name": self.name,
            "operation_type": self.operation_type.value,
            "description": self.description,
            "default_sequence": self.default_sequence,
            "estimated_time_minutes": float(self.estimated_time_minutes) if self.estimated_time_minutes else None,
            "qc_required": self.qc_required,
            "is_active": self.is_active,
            "color": self.color,
            "icon_code": self.icon_code,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
