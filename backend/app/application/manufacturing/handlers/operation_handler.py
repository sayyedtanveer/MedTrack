"""Application handler for Operation Master operations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.manufacturing.entities.operation import Operation, OperationType
from backend.app.application.manufacturing.commands.operation_commands import (
    CreateOperationCommand,
    UpdateOperationCommand,
    DeleteOperationCommand,
    DeactivateOperationCommand,
    ReactivateOperationCommand,
    ListOperationsQuery,
    GetOperationQuery,
    GetOperationByCodeQuery,
    ListOperationsForBOMQuery,
)
from backend.app.infrastructure.persistence.repositories.operation_repository import OperationRepository


class OperationHandler:
    """Handler for Operation Master CQRS operations."""

    def __init__(self, session: AsyncSession):
        self._repo = OperationRepository(session)
        self._session = session

    async def create_operation(self, cmd: CreateOperationCommand) -> Operation:
        """Create a new manufacturing operation."""
        # Validate business rules
        if await self._repo.code_exists(cmd.tenant_id, cmd.operation_code):
            raise ValueError(f"Operation code '{cmd.operation_code}' already exists for this tenant")

        # Create entity
        operation = Operation(
            id=uuid.uuid4(),
            tenant_id=cmd.tenant_id,
            operation_code=cmd.operation_code,
            name=cmd.name,
            operation_type=OperationType(cmd.operation_type),
            description=cmd.description,
            default_sequence=cmd.default_sequence,
            estimated_time_minutes=cmd.estimated_time_minutes,
            qc_required=cmd.qc_required,
            is_active=True,
            color=cmd.color,
            icon_code=cmd.icon_code,
            workstation_id=cmd.workstation_id,
            setup_time=cmd.setup_time or 0.0,
            run_time=cmd.run_time or 0.0,
            created_by=cmd.user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Validate
        errors = operation.validate()
        if errors:
            raise ValueError(f"Validation errors: {', '.join(errors)}")

        # Persist
        await self._repo.save(operation)
        await self._session.flush()

        return operation

    async def update_operation(self, cmd: UpdateOperationCommand) -> Operation:
        """Update an existing operation."""
        operation = await self._repo.get_by_id(cmd.operation_id, cmd.tenant_id)
        if not operation:
            raise ValueError(f"Operation '{cmd.operation_id}' not found")

        # Update mutable fields
        if cmd.name is not None:
            operation.name = cmd.name
        if cmd.description is not None:
            operation.description = cmd.description
        if cmd.default_sequence is not None:
            operation.default_sequence = cmd.default_sequence
        if cmd.estimated_time_minutes is not None:
            operation.estimated_time_minutes = cmd.estimated_time_minutes
        if cmd.qc_required is not None:
            operation.qc_required = cmd.qc_required
        if cmd.color is not None:
            operation.color = cmd.color
        if cmd.icon_code is not None:
            operation.icon_code = cmd.icon_code
        if cmd.is_active is not None:
            operation.is_active = cmd.is_active
        if cmd.workstation_id is not None:
            operation.workstation_id = cmd.workstation_id
        if cmd.setup_time is not None:
            operation.setup_time = cmd.setup_time
        if cmd.run_time is not None:
            operation.run_time = cmd.run_time

        operation.updated_at = datetime.utcnow()

        # Validate
        errors = operation.validate()
        if errors:
            raise ValueError(f"Validation errors: {', '.join(errors)}")

        await self._repo.save(operation)
        await self._session.flush()

        return operation

    async def delete_operation(self, cmd: DeleteOperationCommand) -> None:
        """Soft delete an operation."""
        operation = await self._repo.get_by_id(cmd.operation_id, cmd.tenant_id)
        if not operation:
            raise ValueError(f"Operation '{cmd.operation_id}' not found")

        # Check if in use
        in_use = await self._repo.check_operation_in_use(cmd.tenant_id, cmd.operation_id)
        if in_use:
            raise ValueError("Cannot delete operation that is currently used in BOMs")

        operation.is_deleted = True
        operation.deleted_at = datetime.utcnow()

        await self._repo.save(operation)
        await self._session.flush()

    async def deactivate_operation(self, cmd: DeactivateOperationCommand) -> Operation:
        """Deactivate an operation (soft deactivate)."""
        operation = await self._repo.get_by_id(cmd.operation_id, cmd.tenant_id)
        if not operation:
            raise ValueError(f"Operation '{cmd.operation_id}' not found")

        operation.is_active = False
        operation.updated_at = datetime.utcnow()

        await self._repo.save(operation)
        await self._session.flush()

        return operation

    async def reactivate_operation(self, cmd: ReactivateOperationCommand) -> Operation:
        """Reactivate a deactivated operation."""
        operation = await self._repo.get_by_id(cmd.operation_id, cmd.tenant_id)
        if not operation:
            raise ValueError(f"Operation '{cmd.operation_id}' not found")

        operation.is_active = True
        operation.updated_at = datetime.utcnow()

        await self._repo.save(operation)
        await self._session.flush()

        return operation

    async def list_operations(self, query: ListOperationsQuery) -> list[Operation]:
        """List operations with optional filtering."""
        return await self._repo.list_active(
            tenant_id=query.tenant_id,
            query=query.query,
            operation_type=query.operation_type,
            include_inactive=query.include_inactive,
        )

    async def get_operation(self, query: GetOperationQuery) -> Optional[Operation]:
        """Get operation by ID."""
        return await self._repo.get_by_id(query.operation_id, query.tenant_id)

    async def get_operation_by_code(self, query: GetOperationByCodeQuery) -> Optional[Operation]:
        """Get operation by business code."""
        return await self._repo.get_by_code(query.tenant_id, query.operation_code)

    async def list_operations_for_bom(self, query: ListOperationsForBOMQuery) -> list[Operation]:
        """List active operations available for BOM attachment."""
        return await self._repo.list_for_bom(query.tenant_id)
