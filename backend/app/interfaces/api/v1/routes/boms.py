from __future__ import annotations

import uuid
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select

from backend.app.application.bom.commands.bom_commands import (
    CreateBOMCommand,
    UpdateBOMCommand,
    CopyBOMCommand,
    ActivateBOMCommand,
    DeleteBOMCommand,
    BOMLineInput,
)
from backend.app.application.bom.queries.bom_queries import GetBOMQuery, ListBOMsQuery
from backend.app.application.bom.handlers.bom_handlers import BOMHandlers
from backend.app.application.bom.handlers.routing_handlers import RoutingHandlers
from backend.app.application.bom.handlers.bom_advanced_handlers import BOMAdvancedHandlers
from backend.app.application.bom.commands.routing_commands import AttachOperationToBOMCommand, RemoveOperationFromBOMCommand
from backend.app.application.bom.queries.bom_advanced_queries import GetBOMTreeQuery, GetBOMCostQuery, ValidateBOMQuery
from backend.app.interfaces.api.v1.schemas.routing_schemas import BOMOperationAttach

from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository
from backend.app.infrastructure.persistence.repositories.workstation_repository import WorkstationRepository
from backend.app.infrastructure.persistence.repositories.operation_repository import OperationRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.bom_schemas import (
    CreateBOMRequest,
    UpdateBOMRequest,
    CopyBOMRequest,
    BOMResponse,
    BOMListResponse,
    BOMCostResponse,
    BOMLineResponse,
    BOMOperationResponse,
)
from backend.app.domain.bom.entities.bom import BillOfMaterial

router = APIRouter(tags=["Bill of Materials"])
logger = logging.getLogger(__name__)


def _bom_to_response(bom: BillOfMaterial) -> BOMResponse:
    return BOMResponse(
        id=bom.id,
        tenant_id=bom.tenant_id,
        template_id=bom.template_id,
        variant_id=bom.variant_id,
        version=bom.version,
        is_active=bom.is_active,
        valid_from=bom.valid_from,
        valid_to=bom.valid_to,
        created_at=bom.created_at,
        updated_at=bom.updated_at,
        created_by=bom.created_by,
        approved_by=bom.approved_by,
        operations_count=len(bom.operations),
        making_charge=bom.making_charge,
        making_charge_basis=bom.making_charge_basis,
        lines=[
            BOMLineResponse(
                id=line.id,
                bom_id=line.bom_id,
                quantity=line.quantity,
                scrap_percentage=line.scrap_percentage,
                unit_id=line.unit_id,
                material_id=line.material_id,
                template_id=line.template_id,
                variant_id=line.variant_id,
            )
            for line in bom.lines
        ],
        operations=[
            BOMOperationResponse(
                id=operation.id,
                bom_id=operation.bom_id,
                operation_id=operation.operation_id,
                sequence=operation.sequence,
            )
            for operation in bom.operations
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# BOMs under a product (template or variant)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/products/{product_id}/boms",
    response_model=BOMListResponse,
    summary="List BOMs for a product (template or variant)",
)
async def list_product_boms(
    product_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    is_template: bool = Query(True, description="True if product_id is a template, False if variant"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = BOMRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = BOMHandlers(bom_repo=repo, uow=uow)
        boms, total = await handlers.handle_list(
            ListBOMsQuery(
                tenant_id=tenant_id,
                template_id=product_id if is_template else None,
                variant_id=None if is_template else product_id,
                page=page,
                page_size=page_size,
            )
        )
        if not is_template and total == 0:
            variant = (
                await session.execute(
                    select(ItemVariantModel).where(
                        ItemVariantModel.id == product_id,
                        ItemVariantModel.tenant_id == tenant_id,
                        ItemVariantModel.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if variant and variant.template_id:
                boms, total = await handlers.handle_list(
                    ListBOMsQuery(
                        tenant_id=tenant_id,
                        template_id=variant.template_id,
                        variant_id=None,
                        page=page,
                        page_size=page_size,
                    )
                )
    return BOMListResponse(items=[_bom_to_response(b) for b in boms], total=total, page=page, page_size=page_size)


@router.post(
    "/products/{product_id}/boms",
    response_model=BOMResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new BOM version for a product",
    dependencies=[Depends(require_permission("manufacturing:write"))],
)
async def create_bom(
    product_id: uuid.UUID,
    body: CreateBOMRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    # Safety check: if the request body explicitly names a target product,
    # verify it matches the product_id in the URL path.
    # This prevents creating a BOM for Variant B by using
    #   POST /products/variant_A_id/boms  with body { variant_id: variant_B_id }
    #
    # If neither template_id nor variant_id is provided in the body, we infer
    # from the URL (original design intent — the BOM domain entity will still
    # enforce that exactly one of template_id/variant_id is set).
    if body.template_id is not None and body.template_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"BOM target mismatch: the product_id in the URL ({product_id}) "
                f"does not match the template_id in the request body ({body.template_id}). "
                "To create a BOM for a different product, use that product's URL."
            ),
        )
    if body.variant_id is not None and body.variant_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"BOM target mismatch: the product_id in the URL ({product_id}) "
                f"does not match the variant_id in the request body ({body.variant_id}). "
                "To create a BOM for a different product, use that product's URL."
            ),
        )
    container = get_container(request)
    async with container.session_factory() as session:
        repo = BOMRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = BOMHandlers(bom_repo=repo, uow=uow)
        try:
            bom = await handlers.handle_create(
                CreateBOMCommand(
                    tenant_id=tenant_id,
                    created_by=user_id,
                    version=body.version,
                    valid_from=body.valid_from,
                    valid_to=body.valid_to,
                    approved_by=body.approved_by,
                    template_id=body.template_id,
                    variant_id=body.variant_id,
                    making_charge=body.making_charge,
                    making_charge_basis=body.making_charge_basis,
                    lines=[
                        BOMLineInput(
                            material_id=ln.material_id,
                            template_id=ln.template_id,
                            variant_id=ln.variant_id,
                            quantity=ln.quantity,
                            scrap_percentage=ln.scrap_percentage,
                            unit_id=ln.unit_id,
                        )
                        for ln in body.lines
                    ],
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error creating BOM for product {product_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Creation failed: {str(e)}")
    return _bom_to_response(bom)


# ─────────────────────────────────────────────────────────────────────────────
# BOM by ID
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/boms/{bom_id}", response_model=BOMResponse, summary="Get BOM by ID")
async def get_bom(
    bom_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = BOMRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = BOMHandlers(bom_repo=repo, uow=uow)
        try:
            bom = await handlers.handle_get(GetBOMQuery(bom_id=bom_id, tenant_id=tenant_id))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _bom_to_response(bom)


@router.put("/boms/{bom_id}", response_model=BOMResponse, summary="Update a BOM (inactive only)", dependencies=[Depends(require_permission("manufacturing:write"))])
async def update_bom(
    bom_id: uuid.UUID,
    body: UpdateBOMRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = BOMRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = BOMHandlers(bom_repo=repo, uow=uow)
        try:
            bom = await handlers.handle_update(
                UpdateBOMCommand(
                    bom_id=bom_id,
                    tenant_id=tenant_id,
                    valid_from=body.valid_from,
                    valid_to=body.valid_to,
                    approved_by=body.approved_by,
                    making_charge=body.making_charge,
                    making_charge_basis=body.making_charge_basis,
                    clear_making_charge=body.clear_making_charge,
                    lines=[
                        BOMLineInput(
                            material_id=ln.material_id,
                            template_id=ln.template_id,
                            variant_id=ln.variant_id,
                            quantity=ln.quantity,
                            scrap_percentage=ln.scrap_percentage,
                            unit_id=ln.unit_id,
                        )
                        for ln in body.lines
                    ] if body.lines is not None else None,
                )
            )
        except ValueError as e:
            code = status.HTTP_404_NOT_FOUND if "not found" in str(e) else status.HTTP_409_CONFLICT
            raise HTTPException(status_code=code, detail=str(e))
        except Exception as e:
            # Log the full exception for debugging
            logger.exception(f"Error updating BOM {bom_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Update failed: {str(e)}")
    return _bom_to_response(bom)


@router.delete("/boms/{bom_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft-delete a BOM", dependencies=[Depends(require_permission("manufacturing:write"))])
async def delete_bom(
    bom_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = BOMRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = BOMHandlers(bom_repo=repo, uow=uow)
        try:
            await handlers.handle_delete(DeleteBOMCommand(bom_id=bom_id, tenant_id=tenant_id))
        except ValueError as e:
            code = status.HTTP_404_NOT_FOUND if "not found" in str(e) else status.HTTP_409_CONFLICT
            raise HTTPException(status_code=code, detail=str(e))


@router.post("/boms/{bom_id}/activate", response_model=BOMResponse, summary="Activate a BOM (auto-deactivates previous)", dependencies=[Depends(require_permission("manufacturing:write"))])
async def activate_bom(
    bom_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = BOMRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = BOMHandlers(bom_repo=repo, uow=uow)
        try:
            bom = await handlers.handle_activate(ActivateBOMCommand(bom_id=bom_id, tenant_id=tenant_id))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _bom_to_response(bom)


@router.post("/boms/{bom_id}/copy", response_model=BOMResponse, status_code=status.HTTP_201_CREATED, summary="Copy a BOM to a new version", dependencies=[Depends(require_permission("manufacturing:write"))])
async def copy_bom(
    bom_id: uuid.UUID,
    body: CopyBOMRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = BOMRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handlers = BOMHandlers(bom_repo=repo, uow=uow)
        try:
            bom = await handlers.handle_copy(
                CopyBOMCommand(
                    bom_id=bom_id,
                    tenant_id=tenant_id,
                    new_version=body.new_version,
                    created_by=user_id,
                )
            )
        except ValueError as e:
            code = status.HTTP_404_NOT_FOUND if "not found" in str(e) else status.HTTP_409_CONFLICT
            raise HTTPException(status_code=code, detail=str(e))
    return _bom_to_response(bom)


# ─────────────────────────────────────────────────────────────────────────────
# Advanced Endpoints (Routing & Cost)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/boms/{bom_id}/operations", response_model=uuid.UUID, summary="Attach an Operation to BOM", dependencies=[Depends(require_permission("manufacturing:write"))])
async def attach_operation(
    bom_id: uuid.UUID,
    body: BOMOperationAttach,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        bom_repo = BOMRepository(session)
        workstation_repo = WorkstationRepository(uow)
        operation_repo = OperationRepository(session)
        handlers = RoutingHandlers(uow, bom_repo, workstation_repo, operation_repo)
        
        try:
            op_id = await handlers.handle_attach_operation(
                AttachOperationToBOMCommand(
                    tenant_id=tenant_id,
                    bom_id=bom_id,
                    operation_id=body.operation_id,
                    sequence=body.sequence
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return op_id


@router.delete(
    "/boms/{bom_id}/operations/{bom_operation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an Operation from a draft BOM",
    dependencies=[Depends(require_permission("manufacturing:write"))],
)
async def remove_operation(
    bom_id: uuid.UUID,
    bom_operation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        bom_repo = BOMRepository(session)
        workstation_repo = WorkstationRepository(uow)
        operation_repo = OperationRepository(session)
        handlers = RoutingHandlers(uow, bom_repo, workstation_repo, operation_repo)
        try:
            await handlers.handle_remove_operation_from_bom(
                RemoveOperationFromBOMCommand(
                    tenant_id=tenant_id,
                    bom_id=bom_id,
                    bom_operation_id=bom_operation_id,
                )
            )
        except ValueError as e:
            code = status.HTTP_404_NOT_FOUND if "not found" in str(e) else status.HTTP_409_CONFLICT
            raise HTTPException(status_code=code, detail=str(e))


@router.post("/boms/{bom_id}/validate", summary="Validate BOM constraints", dependencies=[Depends(require_permission("manufacturing:write"))])
async def validate_bom(
    bom_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        bom_repo = BOMRepository(session)
        handlers = BOMAdvancedHandlers(uow, bom_repo)
        
        try:
            result = await handlers.handle_validate(
                ValidateBOMQuery(tenant_id=tenant_id, bom_id=bom_id)
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return result

@router.get("/boms/{bom_id}/tree", summary="Get multi-level BOM Tree")
async def get_bom_tree(
    bom_id: uuid.UUID,
    request: Request,
    parent_id: Optional[uuid.UUID] = Query(None, description="Lazy load children of this node ID"),
    max_depth: int = 20,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        bom_repo = BOMRepository(session)
        handlers = BOMAdvancedHandlers(uow, bom_repo)
        
        try:
            tree = await handlers.handle_get_tree(
                GetBOMTreeQuery(tenant_id=tenant_id, bom_id=bom_id, parent_id=parent_id, max_depth=max_depth)
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return tree

@router.get("/boms/{bom_id}/cost", response_model=BOMCostResponse, summary="Get Rolled-up Standard Cost")
async def get_bom_cost(
    bom_id: uuid.UUID,
    request: Request,
    max_depth: int = 20,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        bom_repo = BOMRepository(session)
        handlers = BOMAdvancedHandlers(uow, bom_repo)
        
        try:
            cost_dict = await handlers.handle_get_cost(
                GetBOMCostQuery(tenant_id=tenant_id, bom_id=bom_id, max_depth=max_depth)
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            
    # cost_dict contains material_cost, operation_cost, total_cost, currency, is_complete, missing_costs
    # Enrich missing_costs with name + code by batch-fetching material records
    raw_missing = cost_dict.get("missing_costs") or []
    enriched_missing = []
    if raw_missing:
        async with container.session_factory() as session:
            material_ids = [
                uuid.UUID(m["component_id"])
                for m in raw_missing
                if m.get("component_type") == "material"
            ]
            if material_ids:
                result = await session.execute(
                    select(MaterialModel.id, MaterialModel.name, MaterialModel.code).where(
                        MaterialModel.id.in_(material_ids),
                        MaterialModel.tenant_id == tenant_id,
                        MaterialModel.is_deleted == False,
                    )
                )
                name_map = {str(row.id): {"name": row.name, "code": row.code} for row in result}
            else:
                name_map = {}

            for m in raw_missing:
                cid = m.get("component_id", "")
                info = name_map.get(cid, {})
                enriched_missing.append({
                    **m,
                    "name": info.get("name") or m.get("name") or f"Unknown ({cid[:8]}…)",
                    "code": info.get("code") or m.get("code"),
                })

    return {
        "bom_id": str(bom_id),
        "material_cost": cost_dict.get("material_cost"),
        "operation_cost": cost_dict.get("operation_cost"),
        "making_cost": cost_dict.get("making_cost", Decimal("0")),
        "total_cost": cost_dict.get("total_cost"),
        "currency_code": cost_dict.get("currency_code"),
        "currency_symbol": cost_dict.get("currency_symbol"),
        "is_complete": cost_dict.get("is_complete"),
        "missing_costs": enriched_missing,
    }
