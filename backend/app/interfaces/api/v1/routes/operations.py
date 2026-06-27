"""Operation Master API routes."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.application.manufacturing.handlers.operation_handler import OperationHandler
from backend.app.application.manufacturing.commands.operation_commands import (
    CreateOperationCommand,
    UpdateOperationCommand,
    ListOperationsQuery,
    GetOperationQuery,
    ListOperationsForBOMQuery,
)
from backend.app.interfaces.api.v1.schemas.manufacturing_schemas import (
    OperationResponse,
    OperationListResponse,
    CreateOperationRequest,
    UpdateOperationRequest,
)

router = APIRouter(prefix="/manufacturing/operations", tags=["Manufacturing - Operations"])


async def _get_db_session(request: Request) -> AsyncSession:
    """Get database session from request context."""
    return request.state.session


@router.post(
    "/",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new manufacturing operation",
    dependencies=[Depends(require_permission("manufacturing:write"))],
)
async def create_operation(
    payload: CreateOperationRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Create a new manufacturing operation for BOM routing."""
    try:
        handler = OperationHandler(session)
        operation = await handler.create_operation(
            CreateOperationCommand(
                tenant_id=tenant_id,
                user_id=user_id,
                operation_code=payload.operation_code,
                name=payload.name,
                operation_type=payload.operation_type,
                description=payload.description,
                default_sequence=payload.default_sequence or 10,
                estimated_time_minutes=payload.estimated_time_minutes,
                qc_required=payload.qc_required or False,
                color=payload.color,
                icon_code=payload.icon_code,
            )
        )
        await session.commit()
        return OperationResponse.from_entity(operation)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/",
    response_model=OperationListResponse,
    summary="List all manufacturing operations",
    dependencies=[Depends(require_permission("manufacturing:read"))],
)
async def list_operations(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    query: Optional[str] = Query(None, description="Search by code or name"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    include_inactive: bool = Query(False, description="Include inactive operations"),
    session: AsyncSession = Depends(_get_db_session),
):
    """List manufacturing operations with optional filtering."""
    try:
        handler = OperationHandler(session)
        operations = await handler.list_operations(
            ListOperationsQuery(
                tenant_id=tenant_id,
                query=query,
                operation_type=operation_type,
                include_inactive=include_inactive,
            )
        )
        return OperationListResponse(
            items=[OperationResponse.from_entity(op) for op in operations],
            total=len(operations),
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/for-bom",
    response_model=OperationListResponse,
    summary="List active operations available for BOM attachment",
    dependencies=[Depends(require_permission("manufacturing:read"))],
)
async def list_operations_for_bom(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """List active operations available for attaching to BOMs."""
    try:
        handler = OperationHandler(session)
        operations = await handler.list_operations_for_bom(
            ListOperationsForBOMQuery(tenant_id=tenant_id)
        )
        return OperationListResponse(
            items=[OperationResponse.from_entity(op) for op in operations],
            total=len(operations),
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/{operation_id}",
    response_model=OperationResponse,
    summary="Get operation by ID",
    dependencies=[Depends(require_permission("manufacturing:read"))],
)
async def get_operation(
    operation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Get a specific manufacturing operation."""
    try:
        handler = OperationHandler(session)
        operation = await handler.get_operation(
            GetOperationQuery(operation_id=operation_id, tenant_id=tenant_id)
        )
        if not operation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operation not found")
        return OperationResponse.from_entity(operation)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put(
    "/{operation_id}",
    response_model=OperationResponse,
    summary="Update operation",
    dependencies=[Depends(require_permission("manufacturing:write"))],
)
async def update_operation(
    operation_id: uuid.UUID,
    payload: UpdateOperationRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Update a manufacturing operation."""
    try:
        from backend.app.application.manufacturing.commands.operation_commands import UpdateOperationCommand
        
        handler = OperationHandler(session)
        operation = await handler.update_operation(
            UpdateOperationCommand(
                operation_id=operation_id,
                tenant_id=tenant_id,
                user_id=user_id,
                name=payload.name,
                description=payload.description,
                default_sequence=payload.default_sequence,
                estimated_time_minutes=payload.estimated_time_minutes,
                qc_required=payload.qc_required,
                color=payload.color,
                icon_code=payload.icon_code,
                is_active=payload.is_active,
            )
        )
        await session.commit()
        return OperationResponse.from_entity(operation)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/{operation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete operation",
    dependencies=[Depends(require_permission("manufacturing:write"))],
)
async def delete_operation(
    operation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Delete (soft delete) a manufacturing operation."""
    try:
        from backend.app.application.manufacturing.commands.operation_commands import DeleteOperationCommand
        
        handler = OperationHandler(session)
        await handler.delete_operation(
            DeleteOperationCommand(operation_id=operation_id, tenant_id=tenant_id, user_id=user_id)
        )
        await session.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{operation_id}/deactivate",
    response_model=OperationResponse,
    summary="Deactivate operation",
    dependencies=[Depends(require_permission("manufacturing:write"))],
)
async def deactivate_operation(
    operation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Deactivate a manufacturing operation (soft deactivate)."""
    try:
        from backend.app.application.manufacturing.commands.operation_commands import DeactivateOperationCommand
        
        handler = OperationHandler(session)
        operation = await handler.deactivate_operation(
            DeactivateOperationCommand(operation_id=operation_id, tenant_id=tenant_id)
        )
        await session.commit()
        return OperationResponse.from_entity(operation)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{operation_id}/reactivate",
    response_model=OperationResponse,
    summary="Reactivate operation",
    dependencies=[Depends(require_permission("manufacturing:write"))],
)
async def reactivate_operation(
    operation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Reactivate a deactivated manufacturing operation."""
    try:
        from backend.app.application.manufacturing.commands.operation_commands import ReactivateOperationCommand
        
        handler = OperationHandler(session)
        operation = await handler.reactivate_operation(
            ReactivateOperationCommand(operation_id=operation_id, tenant_id=tenant_id)
        )
        await session.commit()
        return OperationResponse.from_entity(operation)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
