"""Schemas for Operation Master API requests and responses."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

from backend.app.domain.manufacturing.entities.operation import Operation


class CreateOperationRequest(BaseModel):
    """Request to create a new operation."""
    operation_code: str = Field(..., min_length=1, max_length=10, description="Business code (10, 20, 30)")
    name: str = Field(..., min_length=1, max_length=100, description="Operation name")
    operation_type: str = Field(default="other", description="Type of operation")
    description: Optional[str] = Field(None, max_length=500, description="Description")
    default_sequence: Optional[int] = Field(default=10, ge=10, description="Sequence number")
    estimated_time_minutes: Optional[Decimal] = Field(None, description="Estimated duration")
    qc_required: Optional[bool] = Field(default=False, description="Quality control required")
    color: Optional[str] = Field(None, max_length=20, description="Hex color or named color")
    icon_code: Optional[str] = Field(None, max_length=50, description="Icon identifier")


class UpdateOperationRequest(BaseModel):
    """Request to update an operation."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    default_sequence: Optional[int] = Field(None, ge=10)
    estimated_time_minutes: Optional[Decimal] = Field(None)
    qc_required: Optional[bool] = Field(None)
    color: Optional[str] = Field(None, max_length=20)
    icon_code: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = Field(None)


class OperationResponse(BaseModel):
    """Operation response model (never expose raw UUID to users)."""
    id: str  # UUID as string
    operation_code: str  # Business code
    name: str
    operation_type: str
    description: Optional[str]
    default_sequence: int
    estimated_time_minutes: Optional[float]
    qc_required: bool
    is_active: bool
    color: Optional[str]
    icon_code: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    @classmethod
    def from_entity(cls, entity: Operation) -> OperationResponse:
        """Create response from domain entity."""
        return cls(
            id=str(entity.id),
            operation_code=entity.operation_code,
            name=entity.name,
            operation_type=entity.operation_type.value,
            description=entity.description,
            default_sequence=entity.default_sequence,
            estimated_time_minutes=float(entity.estimated_time_minutes) if entity.estimated_time_minutes else None,
            qc_required=entity.qc_required,
            is_active=entity.is_active,
            color=entity.color,
            icon_code=entity.icon_code,
            created_at=entity.created_at.isoformat() if entity.created_at else None,
            updated_at=entity.updated_at.isoformat() if entity.updated_at else None,
        )


class OperationListResponse(BaseModel):
    """List of operations response."""
    items: list[OperationResponse]
    total: int
