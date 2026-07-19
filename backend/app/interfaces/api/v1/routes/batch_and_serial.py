from __future__ import annotations

"""
Batch & Serial Number API routes — Phase 1.2 & 1.3
Mounted at /inventory/batches and /inventory/serial-numbers
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.app.application.inventory.commands.inventory_commands import (
    AddSerialStockCommand,
    AddStockWithBatchCommand,
    IssueSerialCommand,
    RemoveStockFromBatchCommand,
    ReturnSerialCommand,
)
from backend.app.application.inventory.handlers.batch_handlers import (
    AddStockWithBatchHandler,
    BatchQueryHandler,
    BatchResult,
    RemoveStockFromBatchHandler,
)
from backend.app.application.inventory.handlers.serial_handlers import (
    AddSerialStockHandler,
    IssueSerialHandler,
    ReturnSerialHandler,
    SerialQueryHandler,
)
from backend.app.application.inventory.queries.inventory_queries import (
    GetBatchesByMaterialQuery,
    GetExpiringBatchesQuery,
    GetSerialDetailsQuery,
    GetSerialsByMaterialQuery,
)
from backend.app.infrastructure.persistence.repositories.batch_repository import BatchRepository
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.infrastructure.persistence.repositories.serial_number_repository import SerialNumberRepository
from backend.app.infrastructure.persistence.repositories.transaction_repository import TransactionRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.inventory_schemas import (
    AddSerialStockRequest,
    AddStockWithBatchRequest,
    BatchListResponse,
    BatchResponse,
    IssueSerialRequest,
    RemoveStockFromBatchRequest,
    ReturnSerialRequest,
    SerialNumberListResponse,
    SerialNumberResponse,
)

router = APIRouter(prefix="/inventory", tags=["Inventory — Batch & Serial"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _batch_to_response(result: BatchResult) -> BatchResponse:
    return BatchResponse(
        id=result.id,
        tenant_id=result.tenant_id,
        material_id=result.material_id,
        batch_number=result.batch_number,
        quantity=result.quantity,
        remaining_quantity=result.remaining_quantity,
        expiry_date=result.expiry_date,
        location_id=result.location_id,
        status=result.status,
        is_expired=result.is_expired,
        days_until_expiry=result.days_until_expiry,
        created_at=result.created_at,
    )


# ── Batch Endpoints ────────────────────────────────────────────────────────────

@router.post(
    "/batches/add-stock",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add stock to a batch-tracked material (creates or updates the batch)",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def add_stock_with_batch(
    body: AddStockWithBatchRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        batch_repo = BatchRepository(session)
        tx_repo = TransactionRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = AddStockWithBatchHandler(
            material_repo=material_repo,
            batch_repo=batch_repo,
            tx_repo=tx_repo,
            uow=uow,
        )
        try:
            result = await handler.handle(
                AddStockWithBatchCommand(
                    tenant_id=tenant_id,
                    material_id=body.material_id,
                    batch_number=body.batch_number,
                    quantity=body.quantity,
                    expiry_date=body.expiry_date,
                    unit_id=body.unit_id,
                    to_location_id=body.to_location_id,
                    created_by=user_id,
                    remarks=body.remarks,
                    reference_id=body.reference_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _batch_to_response(result)


@router.post(
    "/batches/remove-stock",
    response_model=BatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove stock from a specific batch",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def remove_stock_from_batch(
    body: RemoveStockFromBatchRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        batch_repo = BatchRepository(session)
        tx_repo = TransactionRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = RemoveStockFromBatchHandler(
            material_repo=material_repo,
            batch_repo=batch_repo,
            tx_repo=tx_repo,
            uow=uow,
        )
        try:
            result = await handler.handle(
                RemoveStockFromBatchCommand(
                    tenant_id=tenant_id,
                    material_id=body.material_id,
                    batch_number=body.batch_number,
                    quantity=body.quantity,
                    unit_id=body.unit_id,
                    from_location_id=body.from_location_id,
                    created_by=user_id,
                    remarks=body.remarks,
                    reference_id=body.reference_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _batch_to_response(result)


@router.get(
    "/batches",
    response_model=BatchListResponse,
    summary="List batches for a material",
)
async def list_batches(
    request: Request,
    material_id: uuid.UUID = Query(..., description="Filter batches by material"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        batch_repo = BatchRepository(session)
        handler = BatchQueryHandler(batch_repo=batch_repo)
        results = await handler.get_batches_by_material(
            GetBatchesByMaterialQuery(tenant_id=tenant_id, material_id=material_id)
        )
    items = [_batch_to_response(r) for r in results]
    return BatchListResponse(items=items, total=len(items))


@router.get(
    "/batches/expiring",
    response_model=BatchListResponse,
    summary="List batches expiring within the next N days (default 30)",
)
async def list_expiring_batches(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Look-ahead window in days"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        batch_repo = BatchRepository(session)
        handler = BatchQueryHandler(batch_repo=batch_repo)
        results = await handler.get_expiring_batches(
            GetExpiringBatchesQuery(tenant_id=tenant_id, days_ahead=days)
        )
    items = [_batch_to_response(r) for r in results]
    return BatchListResponse(items=items, total=len(items))


# ── Serial Number Endpoints ────────────────────────────────────────────────────

@router.post(
    "/serial-numbers/add-stock",
    response_model=List[SerialNumberResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register serial numbers for a serialised material",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def add_serial_stock(
    body: AddSerialStockRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        serial_repo = SerialNumberRepository(session)
        tx_repo = TransactionRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = AddSerialStockHandler(
            material_repo=material_repo,
            serial_repo=serial_repo,
            tx_repo=tx_repo,
            uow=uow,
        )
        try:
            results = await handler.handle(
                AddSerialStockCommand(
                    tenant_id=tenant_id,
                    material_id=body.material_id,
                    serial_numbers=body.serial_numbers,
                    location_id=body.location_id,
                    created_by=user_id,
                    remarks=body.remarks,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return [
        SerialNumberResponse(
            id=r.id,
            tenant_id=r.tenant_id,
            material_id=r.material_id,
            serial_number=r.serial_number,
            status=r.status,
            current_location_id=r.current_location_id,
            reference_id=r.reference_id,
            created_at=r.created_at,
        )
        for r in results
    ]


@router.post(
    "/serial-numbers/issue",
    response_model=SerialNumberResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue a serial number (IN_STOCK/RETURNED → ISSUED)",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def issue_serial(
    body: IssueSerialRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        serial_repo = SerialNumberRepository(session)
        tx_repo = TransactionRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = IssueSerialHandler(
            material_repo=material_repo,
            serial_repo=serial_repo,
            tx_repo=tx_repo,
            uow=uow,
        )
        try:
            result = await handler.handle(
                IssueSerialCommand(
                    tenant_id=tenant_id,
                    serial_number=body.serial_number,
                    created_by=user_id,
                    reference_id=body.reference_id,
                    location_id=body.location_id,
                    remarks=body.remarks,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return SerialNumberResponse(
        id=result.id,
        tenant_id=result.tenant_id,
        material_id=result.material_id,
        serial_number=result.serial_number,
        status=result.status,
        current_location_id=result.current_location_id,
        reference_id=result.reference_id,
        created_at=result.created_at,
    )


@router.post(
    "/serial-numbers/return",
    response_model=SerialNumberResponse,
    status_code=status.HTTP_200_OK,
    summary="Return a serial number (ISSUED → RETURNED)",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def return_serial(
    body: ReturnSerialRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        serial_repo = SerialNumberRepository(session)
        tx_repo = TransactionRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = ReturnSerialHandler(
            material_repo=material_repo,
            serial_repo=serial_repo,
            tx_repo=tx_repo,
            uow=uow,
        )
        try:
            result = await handler.handle(
                ReturnSerialCommand(
                    tenant_id=tenant_id,
                    serial_number=body.serial_number,
                    created_by=user_id,
                    location_id=body.location_id,
                    remarks=body.remarks,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return SerialNumberResponse(
        id=result.id,
        tenant_id=result.tenant_id,
        material_id=result.material_id,
        serial_number=result.serial_number,
        status=result.status,
        current_location_id=result.current_location_id,
        reference_id=result.reference_id,
        created_at=result.created_at,
    )


@router.get(
    "/serial-numbers",
    response_model=SerialNumberListResponse,
    summary="List serial numbers for a material, with optional status filter",
)
async def list_serial_numbers(
    request: Request,
    material_id: uuid.UUID = Query(..., description="Filter serials by material"),
    serial_status: Optional[str] = Query(None, alias="status", description="Filter by status: in_stock, issued, returned"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        serial_repo = SerialNumberRepository(session)
        handler = SerialQueryHandler(serial_repo=serial_repo)
        results = await handler.get_serials_by_material(
            GetSerialsByMaterialQuery(
                tenant_id=tenant_id,
                material_id=material_id,
                status=serial_status,
            )
        )
    items = [
        SerialNumberResponse(
            id=r.id,
            tenant_id=r.tenant_id,
            material_id=r.material_id,
            serial_number=r.serial_number,
            status=r.status,
            current_location_id=r.current_location_id,
            reference_id=r.reference_id,
            created_at=r.created_at,
        )
        for r in results
    ]
    return SerialNumberListResponse(items=items, total=len(items))


@router.get(
    "/serial-numbers/{serial_number}",
    response_model=SerialNumberResponse,
    summary="Get details for a specific serial number",
)
async def get_serial_number(
    serial_number: str,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        serial_repo = SerialNumberRepository(session)
        handler = SerialQueryHandler(serial_repo=serial_repo)
        result = await handler.get_serial_details(
            GetSerialDetailsQuery(tenant_id=tenant_id, serial_number=serial_number)
        )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serial number not found")
    return SerialNumberResponse(
        id=result.id,
        tenant_id=result.tenant_id,
        material_id=result.material_id,
        serial_number=result.serial_number,
        status=result.status,
        current_location_id=result.current_location_id,
        reference_id=result.reference_id,
        created_at=result.created_at,
    )
