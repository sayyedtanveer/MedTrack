from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from typing import List, Optional

import re
import uuid

from sqlalchemy import select

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_container
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork

from backend.app.infrastructure.persistence.repositories.material_category_repository import MaterialCategoryRepository
from backend.app.infrastructure.persistence.repositories.location_repository import LocationRepository
from backend.app.infrastructure.persistence.repositories.unit_of_measure_repository import UnitOfMeasureRepository

from backend.app.domain.inventory.entities.material_category import MaterialCategory
from backend.app.domain.inventory.entities.location import Location, LocationType
from backend.app.domain.inventory.entities.unit_of_measure import UnitOfMeasure
from backend.app.application.inventory.services.item_code_service import normalize_category_prefix

from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.interfaces.api.v1.schemas.master_data_schemas import (
    CreateCategoryRequest,
    CategoryResponse,
    UpdateCategoryRequest,
    CreateLocationRequest,
    LocationResponse,
    CreateUnitRequest,
    UnitResponse,
    UpdateLocationRequest,
    UpdateUnitRequest,
)

router = APIRouter(prefix="/inventory/master-data", tags=["Inventory Master Data"])


def _location_to_response(loc: Location) -> LocationResponse:
    lt = loc.location_type
    return LocationResponse(
        id=loc.id,
        tenant_id=loc.tenant_id,
        name=loc.name,
        code=loc.code,
        location_type=lt.value if hasattr(lt, "value") else str(lt),
        parent_location_id=loc.parent_location_id,
        is_active=loc.is_active,
    )


# ── Categories ────────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = MaterialCategoryRepository(session)
        categories = await repo.list(tenant_id, page_size=100)
    return categories

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("inventory:write"))])
async def create_category(
    req: CreateCategoryRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = MaterialCategoryRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        category = MaterialCategory(
            tenant_id=tenant_id,
            name=req.name,
            code_prefix=normalize_category_prefix(req.code_prefix, fallback_name=req.name),
            description=req.description,
            is_active=req.is_active,
        )
        
        await repo.save(category)
        await uow.commit()
    return category


def _category_to_response(cat: MaterialCategory, material_count: int = 0) -> CategoryResponse:
    """Build a CategoryResponse from a domain entity, injecting the computed material_count."""
    return CategoryResponse(
        id=cat.id,
        tenant_id=cat.tenant_id,
        name=cat.name,
        code_prefix=cat.code_prefix,
        description=cat.description,
        is_active=cat.is_active,
        material_count=material_count,
    )


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Fetch a single category by ID. Includes material_count of active materials referencing it."""
    container = get_container(request)
    async with container.session_factory() as session:
        repo = MaterialCategoryRepository(session)
        category = await repo.get_by_id(category_id, tenant_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        material_count = await repo.count_material_references(category_id)
    return _category_to_response(category, material_count=material_count)


@router.put(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def update_category(
    category_id: uuid.UUID,
    req: UpdateCategoryRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Update a category. Validates code_prefix format and uniqueness per tenant."""
    # Validate code_prefix format if provided (Pydantic pattern already covers this,
    # but we also guard explicitly so the HTTP 422 detail is clear)
    if req.code_prefix is not None:
        if not re.match(r"^[A-Z0-9]{2,6}$", req.code_prefix):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="code_prefix must match ^[A-Z0-9]{2,6}$ (2–6 uppercase letters or digits)",
            )

    container = get_container(request)
    async with container.session_factory() as session:
        repo = MaterialCategoryRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)

        category = await repo.get_by_id(category_id, tenant_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        # Uniqueness check: scan all categories for this tenant
        all_categories = await repo.list(tenant_id, page_size=200)
        new_name = req.name if req.name is not None else category.name
        new_prefix = req.code_prefix if req.code_prefix is not None else category.code_prefix
        for other in all_categories:
            if other.id == category_id:
                continue
            if other.name.lower() == new_name.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A category with name '{new_name}' already exists.",
                )
            if other.code_prefix.upper() == new_prefix.upper():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A category with code_prefix '{new_prefix}' already exists.",
                )

        # Apply patch
        if req.name is not None:
            category.name = req.name
        if req.code_prefix is not None:
            category.code_prefix = req.code_prefix
        if req.description is not None:
            category.description = req.description
        if req.is_active is not None:
            category.is_active = req.is_active

        await repo.update(category)
        await uow.commit()

        material_count = await repo.count_material_references(category_id)

    return _category_to_response(category, material_count=material_count)


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def delete_category(
    category_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Soft-delete a category. Returns 409 if any active materials reference it."""
    container = get_container(request)
    async with container.session_factory() as session:
        repo = MaterialCategoryRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)

        category = await repo.get_by_id(category_id, tenant_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        mat_count = await repo.count_material_references(category_id)
        if mat_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete — {mat_count} material(s) use this category. Deactivate it instead.",
            )

        category.is_active = False
        category._is_deleted = True
        await repo.update(category)
        await uow.commit()


# ── Locations ─────────────────────────────────────────────────────────────

@router.get("/locations", response_model=List[LocationResponse])
async def list_locations(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    type: Optional[str] = Query(None, description="Filter by location type (e.g. quarantine)"),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = LocationRepository(session)
        if type is not None:
            stmt = (
                select(LocationModel)
                .where(
                    LocationModel.tenant_id == tenant_id,
                    LocationModel.is_deleted.is_(False),
                    LocationModel.type == type,
                )
                .order_by(LocationModel.name.asc())
            )
            result = await session.execute(stmt)
            models = result.scalars().all()
            locations = [repo._to_entity(m) for m in models]
        else:
            locations = await repo.list(tenant_id, page_size=500)
    return [_location_to_response(loc) for loc in locations]

@router.post(
    "/locations",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def create_location(
    req: CreateLocationRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    try:
        lt = LocationType(req.type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid location type")
    async with container.session_factory() as session:
        repo = LocationRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)

        location = Location(
            tenant_id=tenant_id,
            name=req.name,
            location_type=lt,
            parent_location_id=req.parent_id,
            code=req.code,
            is_active=req.is_active,
        )

        await repo.save(location)
        await uow.commit()
    return _location_to_response(location)


@router.put(
    "/locations/{location_id}",
    response_model=LocationResponse,
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def update_location(
    location_id: uuid.UUID,
    req: UpdateLocationRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = LocationRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        location = await repo.get_by_id(location_id, tenant_id)
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
        if req.name is not None:
            location.name = req.name
        if req.code is not None:
            location.code = req.code
        if req.parent_id is not None:
            location.parent_location_id = req.parent_id
        if req.is_active is not None:
            location.is_active = req.is_active
        await repo.save(location)
        await uow.commit()
    return _location_to_response(location)


@router.delete(
    "/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def delete_location(
    location_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Soft-delete a location. Returns 409 if materials reference it or active child locations exist."""
    container = get_container(request)
    async with container.session_factory() as session:
        loc_repo = LocationRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)

        location = await loc_repo.get_by_id(location_id, tenant_id)
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

        mat_count = await loc_repo.count_material_references(location_id)
        if mat_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete — {mat_count} material(s) assigned here.",
            )

        child_count = await loc_repo.count_active_children(location_id)
        if child_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete — {child_count} active child location(s) exist.",
            )

        location.is_active = False
        location._is_deleted = True
        await loc_repo.save(location)
        await uow.commit()


# ── Units of Measure ──────────────────────────────────────────────────────

@router.get("/units", response_model=List[UnitResponse])
async def list_units(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = UnitOfMeasureRepository(session)
        units = await repo.list(tenant_id, page_size=100)
    return units

@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("inventory:write"))])
async def create_unit(
    req: CreateUnitRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = UnitOfMeasureRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        unit = UnitOfMeasure(
            tenant_id=tenant_id,
            code=req.code,
            name=req.name,
            is_active=req.is_active,
        )
        
        await repo.save(unit)
        await uow.commit()
    return unit


def _unit_to_response(unit: UnitOfMeasure, usage_count: int = 0) -> UnitResponse:
    """Build a UnitResponse from a domain entity, injecting the computed usage_count."""
    return UnitResponse(
        id=unit.id,
        tenant_id=unit.tenant_id,
        code=unit.code,
        name=unit.name,
        precision=unit.precision,
        is_active=unit.is_active,
        usage_count=usage_count,
    )


@router.get("/units/{unit_id}", response_model=UnitResponse)
async def get_unit(
    unit_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Fetch a single unit of measure by ID. Includes usage_count across materials and BOMs."""
    container = get_container(request)
    async with container.session_factory() as session:
        repo = UnitOfMeasureRepository(session)
        unit = await repo.get_by_id(unit_id, tenant_id)
        if not unit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
        mat_refs = await repo.count_material_references(unit_id)
        bom_refs = await repo.count_bom_references(unit_id)
    return _unit_to_response(unit, usage_count=mat_refs + bom_refs)


@router.put(
    "/units/{unit_id}",
    response_model=UnitResponse,
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def update_unit(
    unit_id: uuid.UUID,
    req: UpdateUnitRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Update a unit of measure. The `code` field is immutable — passing it results in 422."""
    # Check raw JSON body for a "code" key — code is immutable
    body = await request.json()
    if "code" in body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Field 'code' is immutable and cannot be updated.",
        )

    container = get_container(request)
    async with container.session_factory() as session:
        repo = UnitOfMeasureRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)

        unit = await repo.get_by_id(unit_id, tenant_id)
        if not unit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

        if req.name is not None:
            unit.name = req.name
        if req.precision is not None:
            unit.precision = req.precision
        if req.is_active is not None:
            unit.is_active = req.is_active

        await repo.update(unit)
        await uow.commit()

        mat_refs = await repo.count_material_references(unit_id)
        bom_refs = await repo.count_bom_references(unit_id)

    return _unit_to_response(unit, usage_count=mat_refs + bom_refs)


@router.delete(
    "/units/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def delete_unit(
    unit_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Soft-delete a unit. Returns 409 if any materials or BOM lines reference this unit."""
    container = get_container(request)
    async with container.session_factory() as session:
        repo = UnitOfMeasureRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)

        unit = await repo.get_by_id(unit_id, tenant_id)
        if not unit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

        mat_refs = await repo.count_material_references(unit_id)
        bom_refs = await repo.count_bom_references(unit_id)
        total = mat_refs + bom_refs
        if total > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete — {total} material/BOM reference(s) exist. Deactivate it instead.",
            )

        unit.is_active = False
        unit._is_deleted = True
        await repo.update(unit)
        await uow.commit()
