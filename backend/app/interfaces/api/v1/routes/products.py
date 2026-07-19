from __future__ import annotations

import re
import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select

from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel

from backend.app.application.product.handlers.bulk_handlers import (
    BulkCreateVariantsHandler,
    BulkUpdateVariantsHandler,
    BulkActivateVariantsHandler,
    BulkDeactivateVariantsHandler,
)
from backend.app.application.product.commands.bulk_commands import (
    BulkCreateVariantsCommand,
    BulkUpdateVariantsCommand,
    BulkActivateVariantsCommand,
    BulkDeactivateVariantsCommand,
)
from backend.app.application.product.services.import_export_service import (
    VariantImportParser,
    VariantExportService,
)

from backend.app.application.product.commands.product_commands import (
    CreateItemTemplateCommand,
    UpdateItemTemplateCommand,
    ChangeProductStatusCommand,
    CreateItemVariantCommand,
    UpdateItemVariantCommand,
)
from backend.app.application.product.commands.product_image_commands import (
    UploadProductImageCommand,
    DeleteProductImageCommand,
    SetPrimaryImageCommand,
    ReorderImageCommand,
)
from backend.app.application.product.handlers.product_handlers import (
    CreateItemTemplateHandler,
    UpdateItemTemplateHandler,
    ChangeProductStatusHandler,
    CreateItemVariantHandler,
    UpdateItemVariantHandler,
)
from backend.app.application.product.handlers.product_image_handlers import (
    UploadProductImageHandler,
    DeleteProductImageHandler,
    SetPrimaryImageHandler,
    ReorderImageHandler,
    _to_image_result,
)
from backend.app.application.product.handlers.product_handlers import ItemVariantResult
from backend.app.application.product.handlers.product_query_handler import ProductQueryHandler
from backend.app.application.product.queries.product_queries import (
    GetItemTemplateQuery,
    ListItemTemplatesQuery,
    GetItemVariantQuery,
    ListItemVariantsQuery,
    ListAllVariantsQuery,
)
from backend.app.infrastructure.persistence.repositories.item_template_repository import ItemTemplateRepository
from backend.app.infrastructure.persistence.repositories.item_variant_repository import ItemVariantRepository
from backend.app.infrastructure.persistence.repositories.product_image_repository import ProductImageRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.domain.product.value_objects.product_status import ProductStatus
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.product_schemas import (
    BulkImportRequest,
    BulkImportResponse,
    BulkOperationResponse,
    CreateItemTemplateRequest,
    UpdateItemTemplateRequest,
    ChangeProductStatusRequest,
    ExportVariantsRequest,
    ExportVariantsResponse,
    ItemTemplateResponse,
    ItemTemplateListResponse,
    CreateItemVariantRequest,
    UpdateItemVariantRequest,
    ItemVariantResponse,
    ItemVariantListResponse,
    ItemVariantSearchItem,
    ItemVariantSearchListResponse,
    ProductImageResponse,
    ProductImageListResponse,
    SetPrimaryImageRequest,
    ReorderImageRequest,
    UploadImageResponse,
    VariantIdsRequest,
    VariantTemplateCsvResponse,
    ImportError as VariantImportError,
)
from backend.app.application.inventory.services.item_code_service import ItemCodeService

router = APIRouter(prefix="/products", tags=["Product Master"])


# ─────────────────────────────────────────────────────────────────────────────
# Helper: build repositories from session
# ─────────────────────────────────────────────────────────────────────────────

def _template_from_result(r) -> ItemTemplateResponse:
    return ItemTemplateResponse(
        id=uuid.UUID(r.id),
        tenant_id=uuid.UUID(r.tenant_id),
        code=r.code,
        item_code=r.item_code,
        item_type=r.item_type,
        name=r.name,
        description=r.description,
        category_id=uuid.UUID(r.category_id) if r.category_id else None,
        base_unit_id=uuid.UUID(r.base_unit_id) if r.base_unit_id else None,
        attributes=r.attributes,
        status=r.status,
        code_locked=r.code_locked,
        is_active=r.is_active,
    )


def _variant_from_result(r) -> ItemVariantResponse:
    from decimal import Decimal
    return ItemVariantResponse(
        id=uuid.UUID(r.id),
        tenant_id=uuid.UUID(r.tenant_id),
        template_id=uuid.UUID(r.template_id),
        code=r.code,
        name=r.name,
        variant_key=r.variant_key,
        attribute_values=r.attribute_values,
        base_unit_id=uuid.UUID(r.base_unit_id) if r.base_unit_id else None,
        material_id=uuid.UUID(r.material_id) if r.material_id else None,
        standard_cost=Decimal(r.standard_cost),
        selling_price=Decimal(r.selling_price) if r.selling_price else None,
        is_active=r.is_active,
    )


async def _validate_variant_material_link(
    session,
    tenant_id: uuid.UUID,
    material_id: Optional[uuid.UUID],
) -> None:
    if material_id is None:
        return

    material = (
        await session.execute(
            select(MaterialModel).where(
                MaterialModel.id == material_id,
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.is_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked inventory material not found",
        )
    if material.material_type != "finished":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Variant inventory link must point to a finished material",
        )


async def _batch_fg_material_ids(
    session,
    tenant_id: uuid.UUID,
    variant_rows: List[ItemVariantResult],
) -> Dict[str, Optional[uuid.UUID]]:
    """Resolve FG stock material id: same UUID as variant, or finished material with matching code."""
    if not variant_rows:
        return {}
    out: Dict[str, Optional[uuid.UUID]] = {
        r.id: uuid.UUID(r.material_id) if getattr(r, "material_id", None) else None
        for r in variant_rows
    }
    ids = [uuid.UUID(r.id) for r in variant_rows]
    stmt = select(MaterialModel).where(
        MaterialModel.tenant_id == tenant_id,
        MaterialModel.id.in_(ids),
        MaterialModel.is_deleted.is_(False),
    )
    res = await session.execute(stmt)
    for m in res.scalars().all():
        key = str(m.id)
        if key in out:
            out[key] = m.id
    for r in variant_rows:
        if out[r.id] is not None:
            continue
        stmt2 = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.code == r.code,
            MaterialModel.material_type == "finished",
            MaterialModel.is_deleted.is_(False),
        ).limit(1)
        m = (await session.execute(stmt2)).scalar_one_or_none()
        if m:
            out[r.id] = m.id
    return out


async def _batch_unit_codes(
    session,
    tenant_id: uuid.UUID,
    base_unit_ids: List[uuid.UUID],
) -> Dict[uuid.UUID, str]:
    if not base_unit_ids:
        return {}
    uniq = list({u for u in base_unit_ids})
    stmt = select(UnitOfMeasureModel).where(
        UnitOfMeasureModel.tenant_id == tenant_id,
        UnitOfMeasureModel.id.in_(uniq),
        UnitOfMeasureModel.is_deleted.is_(False),
    )
    res = await session.execute(stmt)
    return {m.id: m.code for m in res.scalars().all()}


# ─────────────────────────────────────────────────────────────────────────────
# Item Template endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/templates",
    response_model=ItemTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Item Template",
    dependencies=[Depends(require_permission("sales:write"))],
)
async def create_template(
    body: CreateItemTemplateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = ItemTemplateRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = CreateItemTemplateHandler(
            template_repo=repo,
            uow=uow,
            item_code_service=ItemCodeService(session),
        )
        try:
            result = await handler.handle(
                CreateItemTemplateCommand(
                    tenant_id=tenant_id,
                    created_by=user_id,
                    code=body.item_code or body.code,
                    name=body.name,
                    description=body.description,
                    category_id=body.category_id,
                    base_unit_id=body.base_unit_id,
                    attributes=[a.model_dump() for a in body.attributes],
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return _template_from_result(result)


@router.get(
    "/templates",
    response_model=ItemTemplateListResponse,
    summary="List all Item Templates",
)
async def list_templates(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    query: Optional[str] = Query(None, description="Search by name or code"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        handler = ProductQueryHandler(template_repo=t_repo, variant_repo=v_repo)
        result = await handler.list_templates(
            ListItemTemplatesQuery(
                tenant_id=tenant_id,
                category_id=category_id,
                query=query,
                is_active=is_active,
                page=page,
                page_size=page_size,
            )
        )
    return ItemTemplateListResponse(
        items=[_template_from_result(t) for t in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/templates/{template_id}",
    response_model=ItemTemplateResponse,
    summary="Get a single Item Template by ID",
)
async def get_template(
    template_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        handler = ProductQueryHandler(template_repo=t_repo, variant_repo=v_repo)
        result = await handler.get_template(GetItemTemplateQuery(id=template_id, tenant_id=tenant_id))
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item template not found")
    return _template_from_result(result)


@router.put(
    "/templates/{template_id}",
    response_model=ItemTemplateResponse,
    summary="Update an Item Template",
    dependencies=[Depends(require_permission("sales:write"))],
)
async def update_template(
    template_id: uuid.UUID,
    body: UpdateItemTemplateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = ItemTemplateRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = UpdateItemTemplateHandler(template_repo=repo, uow=uow)
        try:
            result = await handler.handle(
                UpdateItemTemplateCommand(
                    id=template_id,
                    tenant_id=tenant_id,
                    name=body.name,
                    description=body.description,
                    category_id=body.category_id,
                    base_unit_id=body.base_unit_id,
                    attributes=[a.model_dump() for a in body.attributes] if body.attributes is not None else None,
                    is_active=body.is_active,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _template_from_result(result)


# ─────────────────────────────────────────────────────────────────────────────
# Item Variant endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/templates/{template_id}/variants",
    response_model=ItemVariantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a variant for a template",
    dependencies=[Depends(require_permission("sales:write"))],
)
async def create_variant(
    template_id: uuid.UUID,
    body: CreateItemVariantRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = CreateItemVariantHandler(template_repo=t_repo, variant_repo=v_repo, uow=uow)
        try:
            await _validate_variant_material_link(session, tenant_id, body.material_id)
            result = await handler.handle(
                CreateItemVariantCommand(
                    tenant_id=tenant_id,
                    template_id=template_id,
                    created_by=user_id,
                    attribute_values=body.attribute_values,
                    base_unit_id=body.base_unit_id,
                    material_id=body.material_id,
                    standard_cost=body.standard_cost,
                    selling_price=body.selling_price,
                )
            )
        except ValueError as e:
            code = status.HTTP_409_CONFLICT if "already exists" in str(e) else status.HTTP_400_BAD_REQUEST
            raise HTTPException(status_code=code, detail=str(e))
    return _variant_from_result(result)


@router.get(
    "/templates/{template_id}/variants",
    response_model=ItemVariantListResponse,
    summary="List all variants for a template",
)
async def list_variants(
    template_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    query: Optional[str] = Query(None, description="Search variants by name or code"),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        handler = ProductQueryHandler(template_repo=t_repo, variant_repo=v_repo)
        result = await handler.list_variants(
            ListItemVariantsQuery(
                template_id=template_id,
                tenant_id=tenant_id,
                query=query,
                is_active=is_active,
                page=page,
                page_size=page_size,
            )
        )
    return ItemVariantListResponse(
        items=[_variant_from_result(v) for v in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/variants",
    response_model=ItemVariantSearchListResponse,
    summary="Search all item variants (tenant-wide)",
)
async def search_all_variants(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    search: Optional[str] = Query(None, description="Search by name or code"),
    is_active: Optional[bool] = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        handler = ProductQueryHandler(template_repo=t_repo, variant_repo=v_repo)
        result = await handler.list_all_variants(
            ListAllVariantsQuery(
                tenant_id=tenant_id,
                query=search,
                is_active=is_active,
                page=page,
                page_size=page_size,
            )
        )
        fg_map = await _batch_fg_material_ids(session, tenant_id, result.items)
        bu_ids: List[uuid.UUID] = []
        for r in result.items:
            if r.base_unit_id:
                bu_ids.append(uuid.UUID(r.base_unit_id))
        unit_codes = await _batch_unit_codes(session, tenant_id, bu_ids)
        items: List[ItemVariantSearchItem] = []
        for r in result.items:
            base = _variant_from_result(r)
            bu = uuid.UUID(r.base_unit_id) if r.base_unit_id else None
            items.append(
                ItemVariantSearchItem(
                    **base.model_dump(),
                    base_unit_code=unit_codes.get(bu) if bu else None,
                    stock_material_id=fg_map.get(r.id),
                )
            )
    return ItemVariantSearchListResponse(
        items=items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/variants/{variant_id}",
    response_model=ItemVariantResponse,
    summary="Get a single variant by ID",
)
async def get_variant(
    variant_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        handler = ProductQueryHandler(template_repo=t_repo, variant_repo=v_repo)
        result = await handler.get_variant(GetItemVariantQuery(id=variant_id, tenant_id=tenant_id))
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item variant not found")
    return _variant_from_result(result)


@router.put(
    "/variants/{variant_id}",
    response_model=ItemVariantResponse,
    summary="Update variant pricing and status",
    dependencies=[Depends(require_permission("sales:write"))],
)
async def update_variant(
    variant_id: uuid.UUID,
    body: UpdateItemVariantRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        v_repo = ItemVariantRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = UpdateItemVariantHandler(variant_repo=v_repo, uow=uow)
        try:
            await _validate_variant_material_link(session, tenant_id, body.material_id)
            result = await handler.handle(
                UpdateItemVariantCommand(
                    id=variant_id,
                    tenant_id=tenant_id,
                    material_id=body.material_id,
                    standard_cost=body.standard_cost,
                    selling_price=body.selling_price,
                    is_active=body.is_active,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _variant_from_result(result)


def _csv_error_to_response(message: str) -> VariantImportError:
    match = re.match(r"Row\s+(\d+):\s*(.*)", message)
    if match:
        return VariantImportError(
            row_number=int(match.group(1)),
            field="csv",
            message=match.group(2),
        )
    return VariantImportError(row_number=0, field="csv", message=message)


@router.get(
    "/templates/{template_id}/variants/import-template",
    response_model=VariantTemplateCsvResponse,
    summary="Download a CSV template for importing variants",
    dependencies=[Depends(require_permission("sales:write"))],
)
async def get_variant_import_template(
    template_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = ItemTemplateRepository(session)
        template = await repo.get_by_id(template_id, tenant_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item template not found")

    return VariantTemplateCsvResponse(
        csv_content=VariantImportParser.generate_csv_template(template.attributes),
        file_name=f"{template.code}_variant_import_template.csv",
    )


@router.post(
    "/templates/{template_id}/variants/bulk-import",
    response_model=BulkImportResponse,
    summary="Bulk import product variants from CSV",
    dependencies=[Depends(require_permission("sales:write"))],
)
async def bulk_import_variants(
    template_id: uuid.UUID,
    body: BulkImportRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        template = await t_repo.get_by_id(template_id, tenant_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item template not found")

        variants_data, parse_errors = VariantImportParser.parse_csv(body.csv_data, template.attributes)
        parser_error_rows = [_csv_error_to_response(err) for err in parse_errors]

        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = BulkCreateVariantsHandler(template_repo=t_repo, variant_repo=v_repo, uow=uow)
        result = await handler.handle(
            BulkCreateVariantsCommand(
                tenant_id=tenant_id,
                template_id=template_id,
                created_by=user_id,
                variants_data=variants_data,
            )
        )

    handler_errors = [
        VariantImportError(
            row_number=err.row_number,
            field=err.field,
            message=err.message,
        )
        for err in result.errors
    ]
    all_errors = parser_error_rows + handler_errors
    return BulkImportResponse(
        success_count=result.success_count,
        error_count=len(all_errors),
        errors=all_errors,
        variant_ids=[uuid.UUID(v) for v in result.variant_ids],
        message=f"Imported {result.success_count} variant(s); {len(all_errors)} row(s) need attention.",
    )


@router.post(
    "/templates/{template_id}/variants/bulk-activate",
    response_model=BulkOperationResponse,
    summary="Activate multiple variants",
    dependencies=[Depends(require_permission("sales:write"))],
)
async def bulk_activate_variants(
    template_id: uuid.UUID,
    body: VariantIdsRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        if not await t_repo.get_by_id(template_id, tenant_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item template not found")
        v_repo = ItemVariantRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = BulkActivateVariantsHandler(variant_repo=v_repo, uow=uow)
        count = await handler.handle(BulkActivateVariantsCommand(tenant_id=tenant_id, variant_ids=body.variant_ids))
    return BulkOperationResponse(success_count=count, message=f"Activated {count} variant(s).")


@router.post(
    "/templates/{template_id}/variants/bulk-deactivate",
    response_model=BulkOperationResponse,
    summary="Deactivate multiple variants",
    dependencies=[Depends(require_permission("sales:write"))],
)
async def bulk_deactivate_variants(
    template_id: uuid.UUID,
    body: VariantIdsRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        if not await t_repo.get_by_id(template_id, tenant_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item template not found")
        v_repo = ItemVariantRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = BulkDeactivateVariantsHandler(variant_repo=v_repo, uow=uow)
        count = await handler.handle(BulkDeactivateVariantsCommand(tenant_id=tenant_id, variant_ids=body.variant_ids))
    return BulkOperationResponse(success_count=count, message=f"Deactivated {count} variant(s).")


@router.post(
    "/templates/{template_id}/variants/export",
    response_model=ExportVariantsResponse,
    summary="Export product variants as CSV",
)
async def export_variants(
    template_id: uuid.UUID,
    body: ExportVariantsRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        template = await t_repo.get_by_id(template_id, tenant_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item template not found")
        handler = ProductQueryHandler(template_repo=t_repo, variant_repo=v_repo)
        if body.variant_ids:
            rows = []
            for variant_id in body.variant_ids:
                item = await handler.get_variant(GetItemVariantQuery(id=variant_id, tenant_id=tenant_id))
                if item and item.template_id == str(template_id):
                    rows.append(item)
        else:
            rows = (await handler.list_variants(
                ListItemVariantsQuery(
                    template_id=template_id,
                    tenant_id=tenant_id,
                    page=1,
                    page_size=1000,
                )
            )).items

    csv_content = VariantExportService.export_variants_to_csv(
        [
            {
                "code": row.code,
                "attribute_values": row.attribute_values,
                "standard_cost": row.standard_cost,
                "selling_price": row.selling_price,
                "is_active": row.is_active,
            }
            for row in rows
        ],
        template.attributes,
    )
    return ExportVariantsResponse(
        csv_content=csv_content,
        file_name=f"{template.code}_variants.csv",
        record_count=len(rows),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Product Lifecycle Management
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/templates/{template_id}/status",
    response_model=ItemTemplateResponse,
    summary="Change product template status",
    dependencies=[Depends(require_permission("sales:write"))],
)
async def change_product_status(
    template_id: uuid.UUID,
    body: ChangeProductStatusRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Change product template status with validation.
    
    Valid status values: DRAFT, ACTIVE, INACTIVE, ARCHIVED
    
    State transitions:
    - DRAFT → ACTIVE or ARCHIVED
    - ACTIVE → INACTIVE or ARCHIVED
    - INACTIVE → ACTIVE or ARCHIVED
    - ARCHIVED → (terminal, no further transitions)
    """
    try:
        new_status = ProductStatus(body.new_status)
    except ValueError:
        valid_statuses = [str(s.value) for s in ProductStatus]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    container = get_container(request)
    async with container.session_factory() as session:
        repo = ItemTemplateRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = ChangeProductStatusHandler(template_repo=repo, uow=uow)
        try:
            result = await handler.handle(
                ChangeProductStatusCommand(
                    id=template_id,
                    tenant_id=tenant_id,
                    new_status=new_status,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _template_from_result(result)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product template (soft delete)",
    dependencies=[Depends(require_permission("sales:write"))],
)
async def delete_template(
    template_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Soft delete a product template.
    
    Only DRAFT or ARCHIVED products can be deleted.
    Active products must first be deactivated.
    """
    container = get_container(request)
    async with container.session_factory() as session:
        repo = ItemTemplateRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        template = await repo.get_by_id(template_id, tenant_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
        
        # Check if deletion is allowed
        if not template.can_delete_product():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"Cannot delete product in {template.status.value} status. Only DRAFT or ARCHIVED products can be deleted."
            )
        
        # Perform soft delete
        template.soft_delete()
        await repo.save(template)
        await uow.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Product Images Management
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/templates/{template_id}/images",
    response_model=UploadImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image for a product template",
)
async def upload_template_image(
    template_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Upload an image for a product template.
    
    Supported formats: JPEG, PNG, WebP, GIF, SVG
    Max file size: 10MB
    """
    # Validate file size (10MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to start

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 10MB limit."
        )

    # Validate MIME type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image."
        )

    supported_types = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}
    if file.content_type not in supported_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format. Supported: {', '.join(supported_types)}"
        )

    try:
        # Read file data
        file_data = await file.read()

        # Store file
        container = get_container(request)
        file_path, file_size_stored = await container.storage_service.upload(
            file_data=file_data,
            file_name=file.filename or "image",
            tenant_id=tenant_id,
        )

        # Save image metadata
        async with container.session_factory() as session:
            img_repo = ProductImageRepository(session)
            uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
            handler = UploadProductImageHandler(image_repo=img_repo, uow=uow)

            result = await handler.handle(
                UploadProductImageCommand(
                    tenant_id=tenant_id,
                    template_id=template_id,
                    created_by=user_id,
                    file_name=file.filename or "image",
                    file_path=file_path,
                    file_size=file_size_stored,
                    file_mime_type=file.content_type,
                    is_primary=False,  # New images are not primary by default
                )
            )

        return UploadImageResponse(
            id=uuid.UUID(result.id),
            file_name=result.file_name,
            file_path=result.file_path,
            file_size=result.file_size,
            is_primary=result.is_primary,
            message="Image uploaded successfully."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


@router.post(
    "/variants/{variant_id}/images",
    response_model=UploadImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image for a specific variant",
)
async def upload_variant_image(
    variant_id: uuid.UUID,
    request: Request,
    template_id: uuid.UUID = Query(..., description="Parent template ID"),
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Upload an image for a specific product variant.
    """
    # Validate file size (10MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File size exceeds 10MB limit.")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image.")

    supported_types = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}
    if file.content_type not in supported_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported image format.")

    try:
        file_data = await file.read()
        container = get_container(request)
        file_path, file_size_stored = await container.storage_service.upload(
            file_data=file_data,
            file_name=file.filename or "image",
            tenant_id=tenant_id,
        )

        async with container.session_factory() as session:
            img_repo = ProductImageRepository(session)
            uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
            handler = UploadProductImageHandler(image_repo=img_repo, uow=uow)

            result = await handler.handle(
                UploadProductImageCommand(
                    tenant_id=tenant_id,
                    template_id=template_id,
                    variant_id=variant_id,
                    created_by=user_id,
                    file_name=file.filename or "image",
                    file_path=file_path,
                    file_size=file_size_stored,
                    file_mime_type=file.content_type,
                    is_primary=False,
                )
            )

        return UploadImageResponse(
            id=uuid.UUID(result.id),
            file_name=result.file_name,
            file_path=result.file_path,
            file_size=result.file_size,
            is_primary=result.is_primary,
            message="Image uploaded successfully."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload image: {str(e)}")


@router.get(
    "/templates/{template_id}/images",
    response_model=ProductImageListResponse,
    summary="Get all images for a product template",
)
async def get_template_images(
    template_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get all images attached to a product template."""
    container = get_container(request)
    async with container.session_factory() as session:
        img_repo = ProductImageRepository(session)
        images = await img_repo.get_template_images(template_id, tenant_id)
        primary = await img_repo.get_primary_image(template_id, tenant_id)

    items = [
        ProductImageResponse(
            id=img.id,
            tenant_id=img.tenant_id,
            template_id=img.template_id,
            variant_id=img.variant_id,
            file_name=img.file_name,
            file_path=img.file_path,
            file_size=img.file_size,
            file_mime_type=img.file_mime_type,
            image_order=img.image_order,
            is_primary=img.is_primary,
        )
        for img in images
    ]

    primary_response = None
    if primary:
        primary_response = ProductImageResponse(
            id=primary.id,
            tenant_id=primary.tenant_id,
            template_id=primary.template_id,
            variant_id=primary.variant_id,
            file_name=primary.file_name,
            file_path=primary.file_path,
            file_size=primary.file_size,
            file_mime_type=primary.file_mime_type,
            image_order=primary.image_order,
            is_primary=primary.is_primary,
        )

    return ProductImageListResponse(items=items, primary_image=primary_response)


@router.get(
    "/variants/{variant_id}/images",
    response_model=ProductImageListResponse,
    summary="Get all images for a variant",
)
async def get_variant_images(
    variant_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get all images attached to a specific variant."""
    container = get_container(request)
    async with container.session_factory() as session:
        img_repo = ProductImageRepository(session)
        images = await img_repo.get_variant_images(variant_id, tenant_id)

    items = [
        ProductImageResponse(
            id=img.id,
            tenant_id=img.tenant_id,
            template_id=img.template_id,
            variant_id=img.variant_id,
            file_name=img.file_name,
            file_path=img.file_path,
            file_size=img.file_size,
            file_mime_type=img.file_mime_type,
            image_order=img.image_order,
            is_primary=img.is_primary,
        )
        for img in images
    ]

    return ProductImageListResponse(items=items)


@router.post(
    "/images/{image_id}/set-primary",
    response_model=ProductImageResponse,
    summary="Set an image as the primary/thumbnail",
)
async def set_primary_image(
    image_id: uuid.UUID,
    body: SetPrimaryImageRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Set an image as the primary thumbnail for the product."""
    container = get_container(request)
    async with container.session_factory() as session:
        img_repo = ProductImageRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        # Get the image first to find template ID
        image = await img_repo.get_by_id(image_id, tenant_id)
        if not image:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found.")

        handler = SetPrimaryImageHandler(image_repo=img_repo, uow=uow)
        try:
            result = await handler.handle(
                SetPrimaryImageCommand(
                    id=image_id,
                    tenant_id=tenant_id,
                    template_id=image.template_id,
                    updated_by=user_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return ProductImageResponse(
        id=uuid.UUID(result.id),
        tenant_id=uuid.UUID(result.tenant_id),
        template_id=uuid.UUID(result.template_id),
        variant_id=uuid.UUID(result.variant_id) if result.variant_id else None,
        file_name=result.file_name,
        file_path=result.file_path,
        file_size=result.file_size,
        file_mime_type=result.file_mime_type,
        image_order=result.image_order,
        is_primary=result.is_primary,
    )


@router.post(
    "/images/{image_id}/reorder",
    response_model=ProductImageResponse,
    summary="Change image display order",
)
async def reorder_image(
    image_id: uuid.UUID,
    body: ReorderImageRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Reorder an image (change its display position)."""
    container = get_container(request)
    async with container.session_factory() as session:
        img_repo = ProductImageRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = ReorderImageHandler(image_repo=img_repo, uow=uow)

        try:
            result = await handler.handle(
                ReorderImageCommand(
                    id=image_id,
                    tenant_id=tenant_id,
                    new_order=body.new_order,
                    updated_by=user_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return ProductImageResponse(
        id=uuid.UUID(result.id),
        tenant_id=uuid.UUID(result.tenant_id),
        template_id=uuid.UUID(result.template_id),
        variant_id=uuid.UUID(result.variant_id) if result.variant_id else None,
        file_name=result.file_name,
        file_path=result.file_path,
        file_size=result.file_size,
        file_mime_type=result.file_mime_type,
        image_order=result.image_order,
        is_primary=result.is_primary,
    )


@router.delete(
    "/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product image",
)
async def delete_image(
    image_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Delete a product image and remove it from storage."""
    container = get_container(request)
    async with container.session_factory() as session:
        img_repo = ProductImageRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)

        # Get image first
        image = await img_repo.get_by_id(image_id, tenant_id)
        if not image:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found.")

        # Delete from storage
        try:
            await container.storage_service.delete(image.file_path, tenant_id)
        except Exception as e:
            # Log error but don't fail the request
            pass

        # Delete from database
        handler = DeleteProductImageHandler(image_repo=img_repo, uow=uow)
        success = await handler.handle(
            DeleteProductImageCommand(
                id=image_id,
                tenant_id=tenant_id,
                deleted_by=user_id,
            )
        )

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found.")
