from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.app.application.inventory.commands.inventory_commands import (
    MISSING,
    AddStockCommand,
    AdjustStockCommand,
    CreateMaterialCommand,
    RemoveStockCommand,
    UpdateMaterialCommand,
)
from backend.app.application.inventory.handlers.inventory_handlers import (
    AddStockHandler,
    AdjustStockHandler,
    CreateMaterialHandler,
    RemoveStockHandler,
    UpdateMaterialHandler,
)
from backend.app.application.inventory.handlers.inventory_query_handler import InventoryQueryHandler
from backend.app.application.inventory.services.item_code_service import ItemCodeService
from backend.app.application.inventory.queries.inventory_queries import (
    GetMaterialQuery,
    GetStockQuery,
    GetTransactionsQuery,
    ListMaterialsQuery,
)
from backend.app.domain.inventory.entities.inventory_transaction import TransactionType
from backend.app.domain.manufacturing.exceptions import InsufficientStockError
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.infrastructure.persistence.repositories.transaction_repository import TransactionRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_role,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.inventory_schemas import (
    AdjustStockRequest,
    CreateMaterialRequest,
    MaterialListResponse,
    MaterialResponse,
    StockResponse,
    TransactionRequest,
    TransactionResponse,
    UpdateMaterialRequest,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


def _get_repos(request: Request):
    """Helper: open a session and return (material_repo, tx_repo, uow)."""
    container = get_container(request)
    return container


def _material_error_status(message: str) -> int:
    normalized = message.lower()
    if "not found" in normalized:
        return status.HTTP_404_NOT_FOUND
    if "already exists" in normalized:
        return status.HTTP_409_CONFLICT
    if "immutable" in normalized:
        return status.HTTP_422_UNPROCESSABLE_ENTITY
    return status.HTTP_400_BAD_REQUEST


# ── Materials CRUD ─────────────────────────────────────────────────────────────

@router.post(
    "/materials",
    response_model=MaterialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new material",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def create_material(
    body: CreateMaterialRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = CreateMaterialHandler(
            material_repo=material_repo,
            uow=uow,
            item_code_service=ItemCodeService(session),
        )
        try:
            result = await handler.handle(
                CreateMaterialCommand(
                    tenant_id=tenant_id,
                    created_by=user_id,
                    code=body.item_code or body.code,
                    name=body.name,
                    material_type=body.material_type,
                    description=body.description,
                    category_id=body.category_id,
                    base_unit_id=body.base_unit_id,
                    reorder_level=body.reorder_level,
                    location_id=body.location_id,
                    is_batch_tracked=body.is_batch_tracked,
                    is_serialized=body.is_serialized,
                    opening_stock=body.opening_stock,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=_material_error_status(str(e)), detail=str(e))

    return MaterialResponse.model_validate(result)


@router.get(
    "/materials",
    response_model=MaterialListResponse,
    summary="List all materials with optional search and filter",
    dependencies=[Depends(require_permission("inventory:read"))],
)
async def list_materials(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    query: Optional[str] = Query(None, description="Search by name or code"),
    category: Optional[str] = Query(None),
    material_type: Optional[str] = Query(None, description="Filter by raw or finished"),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        tx_repo = TransactionRepository(session)
        handler = InventoryQueryHandler(material_repo=material_repo, tx_repo=tx_repo)
        result = await handler.list_materials(
            ListMaterialsQuery(
                tenant_id=tenant_id,
                query=query,
                category=category,
                material_type=material_type,
                is_active=is_active,
                page=page,
                page_size=page_size,
            )
        )

    return MaterialListResponse(
        items=[MaterialResponse.model_validate(m) for m in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/materials/{material_id}",
    response_model=MaterialResponse,
    summary="Get a single material by ID",
    dependencies=[Depends(require_permission("inventory:read"))],
)
async def get_material(
    material_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        tx_repo = TransactionRepository(session)
        handler = InventoryQueryHandler(material_repo=material_repo, tx_repo=tx_repo)
        result = await handler.get_material(GetMaterialQuery(id=material_id, tenant_id=tenant_id))

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")

    return MaterialResponse.model_validate(result)


@router.put(
    "/materials/{material_id}",
    response_model=MaterialResponse,
    summary="Update material metadata (not stock)",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def update_material(
    material_id: uuid.UUID,
    body: UpdateMaterialRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = UpdateMaterialHandler(material_repo=material_repo, uow=uow)
        patch = body.model_dump(exclude_unset=True)
        try:
            # Determine code value: use MISSING if neither code nor item_code was sent in the request
            code_value = MISSING
            if "item_code" in patch and patch["item_code"] is not None:
                code_value = patch["item_code"]
            elif "code" in patch and patch["code"] is not None:
                code_value = patch["code"]

            result = await handler.handle(
                UpdateMaterialCommand(
                    id=material_id,
                    tenant_id=tenant_id,
                    name=body.name,
                    description=body.description,
                    category_id=body.category_id,
                    base_unit_id=body.base_unit_id,
                    material_type=body.material_type,
                    reorder_level=body.reorder_level,
                    location_id=body.location_id,
                    is_batch_tracked=body.is_batch_tracked,
                    is_serialized=body.is_serialized,
                    is_active=body.is_active,
                    inspection_required=patch["inspection_required"]
                    if "inspection_required" in patch
                    else MISSING,
                    inspection_template_id=patch["inspection_template_id"]
                    if "inspection_template_id" in patch
                    else MISSING,
                    code=code_value,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=_material_error_status(str(e)), detail=str(e))

    return MaterialResponse.model_validate(result)


@router.delete(
    "/materials/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a material",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def delete_material(
    material_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        material = await material_repo.get_by_id(material_id, tenant_id)
        if not material:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
        await material_repo.delete(material_id, tenant_id)
        await uow.commit()


# ── Stock Info ─────────────────────────────────────────────────────────────────

@router.get(
    "/materials/{material_id}/stock",
    response_model=StockResponse,
    summary="Get current stock levels for a material",
    dependencies=[Depends(require_permission("inventory:read"))],
)
async def get_stock(
    material_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        tx_repo = TransactionRepository(session)
        handler = InventoryQueryHandler(material_repo=material_repo, tx_repo=tx_repo)
        result = await handler.get_stock(GetStockQuery(material_id=material_id, tenant_id=tenant_id))

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")

    return StockResponse(
        material_id=result.material_id,
        material_code=result.material_code,
        material_name=result.material_name,
        current_stock=result.current_stock,
        reserved_stock=result.reserved_stock,
        available_stock=result.available_stock,
        base_unit_id=result.base_unit_id,
        is_low_stock=result.is_low_stock,
        reorder_level=result.reorder_level,
    )


# ── Transactions ───────────────────────────────────────────────────────────────

@router.post(
    "/transactions",
    response_model=MaterialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a stock transaction (IN / OUT / ADJUSTMENT)",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def create_transaction(
    body: TransactionRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        tx_repo = TransactionRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)

        try:
            if body.transaction_type == "in":
                handler = AddStockHandler(material_repo=material_repo, tx_repo=tx_repo, uow=uow, connection_manager=getattr(container, 'connection_manager', None))
                result = await handler.handle(
                    AddStockCommand(
                        tenant_id=tenant_id,
                        material_id=body.material_id,
                        quantity=body.quantity,
                        unit_id=body.unit_id,
                        to_location_id=body.to_location_id,
                        created_by=user_id,
                        remarks=body.remarks,
                        reference_id=body.reference_id,
                    )
                )

            elif body.transaction_type == "out":
                handler = RemoveStockHandler(material_repo=material_repo, tx_repo=tx_repo, uow=uow, connection_manager=getattr(container, 'connection_manager', None))
                result = await handler.handle(
                    RemoveStockCommand(
                        tenant_id=tenant_id,
                        material_id=body.material_id,
                        quantity=body.quantity,
                        unit_id=body.unit_id,
                        from_location_id=body.from_location_id,
                        created_by=user_id,
                        remarks=body.remarks,
                        reference_id=body.reference_id,
                    )
                )

            elif body.transaction_type == "transfer":
                if body.from_location_id is None or body.to_location_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Transfer requires both from_location_id and to_location_id",
                    )
                if body.from_location_id == body.to_location_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Source and destination locations must be different",
                    )
                from backend.app.application.manufacturing.services.inventory_service import InventoryService

                inventory_service = InventoryService(session)
                await inventory_service.transfer_stock(
                    tenant_id=tenant_id,
                    material_id=body.material_id,
                    quantity=body.quantity,
                    from_location_id=body.from_location_id,
                    to_location_id=body.to_location_id,
                    unit_id=body.unit_id,
                    created_by=user_id,
                    reference_id=body.reference_id,
                    remarks=body.remarks,
                )
                await uow.commit()
                query_handler = InventoryQueryHandler(material_repo=material_repo, tx_repo=tx_repo)
                result = await query_handler.get_material(
                    GetMaterialQuery(id=body.material_id, tenant_id=tenant_id)
                )
                if result is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Material not found",
                    )

            else:  # adjustment
                new_qty = body.new_quantity if body.new_quantity is not None else body.quantity
                handler = AdjustStockHandler(material_repo=material_repo, tx_repo=tx_repo, uow=uow, connection_manager=getattr(container, 'connection_manager', None))
                result = await handler.handle(
                    AdjustStockCommand(
                        tenant_id=tenant_id,
                        material_id=body.material_id,
                        new_quantity=new_qty,
                        unit_id=body.unit_id,
                        location_id=body.to_location_id or body.from_location_id,
                        created_by=user_id,
                        remarks=body.remarks,
                    )
                )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except InsufficientStockError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return MaterialResponse.model_validate(result)


@router.get(
    "/transactions",
    response_model=List[TransactionResponse],
    summary="List all transactions, optionally filtered by material",
    dependencies=[Depends(require_permission("inventory:read"))],
)
async def list_transactions(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    material_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        tx_repo = TransactionRepository(session)
        handler = InventoryQueryHandler(material_repo=material_repo, tx_repo=tx_repo)
        results = await handler.get_transactions(
            GetTransactionsQuery(
                tenant_id=tenant_id,
                material_id=material_id,
                page=page,
                page_size=page_size,
            )
        )

    return [TransactionResponse.model_validate(tx) for tx in results]
