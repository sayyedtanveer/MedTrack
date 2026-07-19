from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.app.infrastructure.persistence.models.quality_model import InspectionTemplateModel
from backend.app.interfaces.api.v1.dependencies.auth import get_container, get_current_tenant_id
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission

router = APIRouter(prefix="/inspection-templates", tags=["Quality"])


class InspectionTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parameters: List[dict[str, Any]] = Field(
        default_factory=list,
        description="JSON array of parameter rows, e.g. [{\"name\": \"width\", \"tolerance_min\": 0, \"tolerance_max\": 10}]",
    )
    is_active: bool = True


class InspectionTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    parameters: Optional[List[dict[str, Any]]] = None
    is_active: Optional[bool] = None


class InspectionTemplateResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    parameters: List[Any]
    is_active: bool

    model_config = {"from_attributes": True}


def _to_response(m: InspectionTemplateModel) -> InspectionTemplateResponse:
    return InspectionTemplateResponse(
        id=m.id,
        tenant_id=m.tenant_id,
        name=m.name,
        parameters=m.parameters if isinstance(m.parameters, list) else [],
        is_active=m.is_active,
    )


@router.get("", response_model=List[InspectionTemplateResponse])
async def list_inspection_templates(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(InspectionTemplateModel)
            .where(
                InspectionTemplateModel.tenant_id == tenant_id,
                InspectionTemplateModel.is_deleted.is_(False),
            )
            .order_by(InspectionTemplateModel.name.asc())
        )
        rows = (await session.execute(stmt)).scalars().all()
    return [_to_response(m) for m in rows]


@router.post(
    "",
    response_model=InspectionTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("quality:write"))],
)
async def create_inspection_template(
    body: InspectionTemplateCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        now = datetime.now(timezone.utc)
        m = InspectionTemplateModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=body.name.strip(),
            parameters=body.parameters or [],
            is_active=body.is_active,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        session.add(m)
        await session.commit()
        await session.refresh(m)
    return _to_response(m)


@router.get("/{template_id}", response_model=InspectionTemplateResponse)
async def get_inspection_template(
    template_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        m = await session.get(InspectionTemplateModel, template_id)
    if not m or m.tenant_id != tenant_id or m.is_deleted:
        raise HTTPException(status_code=404, detail="Inspection template not found")
    return _to_response(m)


@router.put(
    "/{template_id}",
    response_model=InspectionTemplateResponse,
    dependencies=[Depends(require_permission("quality:write"))],
)
async def update_inspection_template(
    template_id: uuid.UUID,
    body: InspectionTemplateUpdate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        m = await session.get(InspectionTemplateModel, template_id)
        if not m or m.tenant_id != tenant_id or m.is_deleted:
            raise HTTPException(status_code=404, detail="Inspection template not found")
        if body.name is not None:
            m.name = body.name.strip()
        if body.parameters is not None:
            m.parameters = body.parameters
        if body.is_active is not None:
            m.is_active = body.is_active
        m.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(m)
    return _to_response(m)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("quality:write"))],
)
async def delete_inspection_template(
    template_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        m = await session.get(InspectionTemplateModel, template_id)
        if not m or m.tenant_id != tenant_id or m.is_deleted:
            raise HTTPException(status_code=404, detail="Inspection template not found")
        m.is_deleted = True
        m.deleted_at = datetime.now(timezone.utc)
        m.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return None
