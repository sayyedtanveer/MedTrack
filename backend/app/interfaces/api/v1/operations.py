import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request

from backend.app.application.bom.commands.routing_commands import AddOperationCommand, UpdateOperationCommand, DeleteOperationCommand
from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id
from backend.app.interfaces.api.v1.schemas.routing_schemas import OperationCreate, OperationResponse, OperationUpdate

from backend.app.interfaces.api.v1.dependencies.auth import get_container
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository
from backend.app.infrastructure.persistence.repositories.workstation_repository import WorkstationRepository
from backend.app.infrastructure.persistence.repositories.operation_repository import OperationRepository
from backend.app.application.bom.handlers.routing_handlers import RoutingHandlers

router = APIRouter(prefix="/operations", tags=["Manufacturing Routing"])

@router.post("", response_model=uuid.UUID, status_code=status.HTTP_201_CREATED)
async def create_operation(
    request: Request,
    body: OperationCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))


        cmd = AddOperationCommand(
            tenant_id=tenant_id,
            **body.model_dump()
        )
        return await handlers.handle_add_operation(cmd)

@router.get("", response_model=List[OperationResponse])
async def list_operations(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))
        operations = await handlers._operation_repo.list_operations(tenant_id)
    return operations

@router.put("/{operation_id}", response_model=OperationResponse)
async def update_operation(
    operation_id: uuid.UUID,
    body: OperationUpdate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))
        cmd = UpdateOperationCommand(
            tenant_id=tenant_id,
            operation_id=operation_id,
            **body.model_dump()
        )
        try:
            op = await handlers.handle_update_operation(cmd)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return op

@router.delete("/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_operation(
    operation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))
        cmd = DeleteOperationCommand(tenant_id=tenant_id, operation_id=operation_id)
        try:
            await handlers.handle_delete_operation(cmd)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
