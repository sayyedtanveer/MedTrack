import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from backend.app.application.bom.commands.routing_commands import AddWorkstationCommand, UpdateWorkstationCommand, DeleteWorkstationCommand
from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id
from backend.app.interfaces.api.v1.schemas.routing_schemas import WorkstationCreate, WorkstationResponse, WorkstationUpdate

from backend.app.interfaces.api.v1.dependencies.auth import get_container
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository
from backend.app.infrastructure.persistence.repositories.workstation_repository import WorkstationRepository
from backend.app.infrastructure.persistence.repositories.operation_repository import OperationRepository
from backend.app.application.bom.handlers.routing_handlers import RoutingHandlers

router = APIRouter(prefix="/workstations", tags=["Manufacturing Routing"])

@router.post("", response_model=uuid.UUID, status_code=status.HTTP_201_CREATED)
async def create_workstation(
    request: Request,
    body: WorkstationCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))

        cmd = AddWorkstationCommand(
            tenant_id=tenant_id,
            **body.model_dump()
        )
        try:
            return await handlers.handle_add_workstation(cmd)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=f"500-DEBUG: {str(e)}\n{traceback.format_exc()}")

@router.get("", response_model=List[WorkstationResponse])
async def list_workstations(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))
        workstations = await handlers._workstation_repo.list_workstations(tenant_id)
    return workstations

@router.get("/{workstation_id}", response_model=WorkstationResponse)
async def get_workstation(
    workstation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))
        workstation = await handlers._workstation_repo.get_by_id(workstation_id, tenant_id)
        if not workstation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workstation not found")
    return workstation

@router.put("/{workstation_id}", response_model=WorkstationResponse)
async def update_workstation(
    workstation_id: uuid.UUID,
    body: WorkstationUpdate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))
        cmd = UpdateWorkstationCommand(
            tenant_id=tenant_id,
            workstation_id=workstation_id,
            **body.model_dump()
        )
        try:
            ws = await handlers.handle_update_workstation(cmd)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ws

@router.delete("/{workstation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workstation(
    workstation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))
        cmd = DeleteWorkstationCommand(tenant_id=tenant_id, workstation_id=workstation_id)
        try:
            await handlers.handle_delete_workstation(cmd)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
