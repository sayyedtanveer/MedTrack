"""Commands and Queries for Operation Master operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from backend.app.domain.manufacturing.entities.operation import OperationType


@dataclass
class CreateOperationCommand:
    """Command to create a new operation."""
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    operation_code: str
    name: str
    operation_type: str
    description: Optional[str] = None
    default_sequence: int = 10
    estimated_time_minutes: Optional[Decimal] = None
    qc_required: bool = False
    color: Optional[str] = None
    icon_code: Optional[str] = None


@dataclass
class UpdateOperationCommand:
    """Command to update an existing operation."""
    operation_id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    name: Optional[str] = None
    description: Optional[str] = None
    default_sequence: Optional[int] = None
    estimated_time_minutes: Optional[Decimal] = None
    qc_required: Optional[bool] = None
    color: Optional[str] = None
    icon_code: Optional[str] = None
    is_active: Optional[bool] = None


@dataclass
class DeleteOperationCommand:
    """Command to delete (soft delete) an operation."""
    operation_id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID


@dataclass
class DeactivateOperationCommand:
    """Command to deactivate an operation."""
    operation_id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass
class ReactivateOperationCommand:
    """Command to reactivate a deactivated operation."""
    operation_id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass
class ListOperationsQuery:
    """Query to list operations."""
    tenant_id: uuid.UUID
    query: Optional[str] = None
    operation_type: Optional[str] = None
    include_inactive: bool = False


@dataclass
class GetOperationQuery:
    """Query to get single operation by ID."""
    operation_id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass
class GetOperationByCodeQuery:
    """Query to get operation by business code."""
    tenant_id: uuid.UUID
    operation_code: str


@dataclass
class ListOperationsForBOMQuery:
    """Query to list operations available for BOM attachment."""
    tenant_id: uuid.UUID
