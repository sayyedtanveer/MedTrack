"""Number Series configuration API endpoints.

Provides CRUD and preview operations for the generic Number Series Engine,
allowing administrators to configure how codes are generated for all ERP
entity types (materials, POs, invoices, etc.).

Route prefix: /settings/number-series
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select

from backend.app.application.inventory.services.item_code_service import (
    DEFAULT_ENTITY_CONFIGS,
    ItemCodeService,
)
from backend.app.infrastructure.persistence.models.number_series_models import (
    NumberSeriesAuditLogModel,
    NumberSeriesConfigModel,
    NumberSeriesPrefixModel,
)
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.number_series_schemas import (
    AuditLogListResponse,
    CodePreviewResponse,
    NumberSeriesAuditLogResponse,
    NumberSeriesConfigResponse,
    NumberSeriesPrefixResponse,
    UpdateNumberSeriesConfigRequest,
    UpdatePrefixRequest,
)

router = APIRouter(prefix="/settings/number-series", tags=["Number Series"])


@router.get("/", include_in_schema=True)
async def list_configs_root(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Compatibility alias for GET /settings/number-series/ while the main route handles /settings/number-series."""
    return await list_configs(request=request, tenant_id=tenant_id)


# Supported entity types
SUPPORTED_ENTITY_TYPES = [
    "material",
    "product",
    "purchase_order",
    "sales_order",
    "invoice",
    "grn",
    "work_order",
    "batch",
    "customer",
    "supplier",
]


# ── List all configs ───────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=List[NumberSeriesConfigResponse],
    summary="List all number series configurations for tenant",
    dependencies=[Depends(require_permission("inventory:read"))],
)
async def list_configs(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Returns configs for all entity types. Seeds defaults on first access."""
    container = get_container(request)
    async with container.session_factory() as session:
        item_code_service = ItemCodeService(session)

        # Ensure all entity types have configs (seeds defaults if missing)
        for entity_type in SUPPORTED_ENTITY_TYPES:
            await item_code_service.get_or_create_config(
                tenant_id=tenant_id, entity_type=entity_type
            )
        await session.commit()

        # Load all configs for the tenant
        result = await session.execute(
            select(NumberSeriesConfigModel)
            .where(NumberSeriesConfigModel.tenant_id == tenant_id)
            .order_by(NumberSeriesConfigModel.entity_type)
        )
        configs = result.scalars().all()

    return [NumberSeriesConfigResponse.model_validate(c) for c in configs]


# ── Get config for entity type ─────────────────────────────────────────────────


@router.get(
    "/audit-log",
    response_model=AuditLogListResponse,
    summary="List number series audit log entries",
    dependencies=[Depends(require_permission("inventory:read"))],
)
async def get_audit_log(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Returns paginated audit log entries, optionally filtered by entity_type."""
    container = get_container(request)
    async with container.session_factory() as session:
        # Build base query
        base_query = select(NumberSeriesAuditLogModel).where(
            NumberSeriesAuditLogModel.tenant_id == tenant_id
        )
        count_query = select(func.count(NumberSeriesAuditLogModel.id)).where(
            NumberSeriesAuditLogModel.tenant_id == tenant_id
        )

        if entity_type:
            base_query = base_query.where(
                NumberSeriesAuditLogModel.entity_type == entity_type
            )
            count_query = count_query.where(
                NumberSeriesAuditLogModel.entity_type == entity_type
            )

        # Get total count
        total = await session.scalar(count_query) or 0

        # Get paginated results
        offset = (page - 1) * page_size
        result = await session.execute(
            base_query.order_by(NumberSeriesAuditLogModel.timestamp.desc())
            .offset(offset)
            .limit(page_size)
        )
        entries = result.scalars().all()

    return AuditLogListResponse(
        items=[NumberSeriesAuditLogResponse.model_validate(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{entity_type}",
    response_model=NumberSeriesConfigResponse,
    summary="Get number series config for entity type",
    dependencies=[Depends(require_permission("inventory:read"))],
)
async def get_config(
    entity_type: str,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Returns config for the entity type. Creates defaults if none exists."""
    _validate_entity_type(entity_type)

    container = get_container(request)
    async with container.session_factory() as session:
        item_code_service = ItemCodeService(session)
        config = await item_code_service.get_or_create_config(
            tenant_id=tenant_id, entity_type=entity_type
        )
        await session.commit()

    return NumberSeriesConfigResponse.model_validate(config)


# ── Update config ──────────────────────────────────────────────────────────────


@router.put(
    "/{entity_type}",
    response_model=NumberSeriesConfigResponse,
    summary="Update number series config for entity type",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def update_config(
    entity_type: str,
    body: UpdateNumberSeriesConfigRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update configuration. Logs audit trail for changes."""
    _validate_entity_type(entity_type)

    container = get_container(request)
    async with container.session_factory() as session:
        item_code_service = ItemCodeService(session)
        config = await item_code_service.get_or_create_config(
            tenant_id=tenant_id, entity_type=entity_type
        )

        # Track changes for audit log
        changes = {}
        update_data = body.model_dump(exclude_unset=True)

        for field, new_value in update_data.items():
            old_value = getattr(config, field)
            if old_value != new_value:
                changes[field] = {"old": str(old_value), "new": str(new_value)}
                setattr(config, field, new_value)

        if changes:
            config.updated_at = datetime.now(timezone.utc)

            # Log audit trail entry
            audit_entry = NumberSeriesAuditLogModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                entity_type=entity_type,
                event_type="config_changed",
                old_value=json.dumps({k: v["old"] for k, v in changes.items()}),
                new_value=json.dumps({k: v["new"] for k, v in changes.items()}),
                user_id=user_id,
                timestamp=datetime.now(timezone.utc),
                metadata_json=json.dumps({"fields_changed": list(changes.keys())}),
            )
            session.add(audit_entry)

        await session.commit()
        await session.refresh(config)

    return NumberSeriesConfigResponse.model_validate(config)


# ── Prefixes ───────────────────────────────────────────────────────────────────


@router.get(
    "/{entity_type}/prefixes",
    response_model=List[NumberSeriesPrefixResponse],
    summary="List sub-type prefixes for entity type",
    dependencies=[Depends(require_permission("inventory:read"))],
)
async def list_prefixes(
    entity_type: str,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Returns all configurable sub-type → prefix mappings for this entity type."""
    _validate_entity_type(entity_type)

    container = get_container(request)
    async with container.session_factory() as session:
        # Ensure defaults are seeded (by loading config which triggers seed)
        item_code_service = ItemCodeService(session)
        await item_code_service.get_or_create_config(
            tenant_id=tenant_id, entity_type=entity_type
        )
        await session.flush()

        result = await session.execute(
            select(NumberSeriesPrefixModel)
            .where(
                NumberSeriesPrefixModel.tenant_id == tenant_id,
                NumberSeriesPrefixModel.entity_type == entity_type,
            )
            .order_by(NumberSeriesPrefixModel.sub_type)
        )
        prefixes = result.scalars().all()
        await session.commit()

    return [NumberSeriesPrefixResponse.model_validate(p) for p in prefixes]


@router.put(
    "/{entity_type}/prefixes/{sub_type}",
    response_model=NumberSeriesPrefixResponse,
    summary="Update a sub-type prefix",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def update_prefix(
    entity_type: str,
    sub_type: str,
    body: UpdatePrefixRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update a single prefix mapping. Validates: uppercase alphanumeric, 1-10 chars."""
    _validate_entity_type(entity_type)

    container = get_container(request)
    async with container.session_factory() as session:
        # Find existing prefix
        prefix_row = await session.scalar(
            select(NumberSeriesPrefixModel).where(
                NumberSeriesPrefixModel.tenant_id == tenant_id,
                NumberSeriesPrefixModel.entity_type == entity_type,
                NumberSeriesPrefixModel.sub_type == sub_type,
            )
        )

        if prefix_row is None:
            # Create a new prefix mapping
            now = datetime.now(timezone.utc)
            prefix_row = NumberSeriesPrefixModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                entity_type=entity_type,
                sub_type=sub_type,
                prefix=body.prefix,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            session.add(prefix_row)

            # Log audit trail
            audit_entry = NumberSeriesAuditLogModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                entity_type=entity_type,
                event_type="prefix_changed",
                old_value=None,
                new_value=body.prefix,
                user_id=user_id,
                timestamp=now,
                metadata_json=json.dumps({"sub_type": sub_type, "action": "created"}),
            )
            session.add(audit_entry)
        else:
            old_prefix = prefix_row.prefix
            prefix_row.prefix = body.prefix
            prefix_row.updated_at = datetime.now(timezone.utc)

            # Log audit trail
            audit_entry = NumberSeriesAuditLogModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                entity_type=entity_type,
                event_type="prefix_changed",
                old_value=old_prefix,
                new_value=body.prefix,
                user_id=user_id,
                timestamp=datetime.now(timezone.utc),
                metadata_json=json.dumps({"sub_type": sub_type, "action": "updated"}),
            )
            session.add(audit_entry)

        await session.commit()
        await session.refresh(prefix_row)

    return NumberSeriesPrefixResponse.model_validate(prefix_row)


# ── Preview ────────────────────────────────────────────────────────────────────


@router.get(
    "/{entity_type}/preview",
    response_model=CodePreviewResponse,
    summary="Preview generated code format",
    dependencies=[Depends(require_permission("inventory:read"))],
)
async def preview_code(
    entity_type: str,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    sub_type: str = Query("", description="Sub-type for prefix lookup"),
    entity_name: str = Query("", description="Sample entity name for abbreviation preview"),
):
    """Returns a preview of the generated code WITHOUT incrementing the sequence."""
    _validate_entity_type(entity_type)

    container = get_container(request)
    async with container.session_factory() as session:
        item_code_service = ItemCodeService(session)
        preview, pattern = await item_code_service.format_preview(
            tenant_id=tenant_id,
            entity_type=entity_type,
            sub_type=sub_type,
            entity_name=entity_name,
        )
        await session.commit()

    return CodePreviewResponse(preview=preview, format_pattern=pattern)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _validate_entity_type(entity_type: str) -> None:
    """Validate that the entity_type is one of the supported types."""
    if entity_type not in SUPPORTED_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity type '{entity_type}'. "
            f"Supported types: {', '.join(SUPPORTED_ENTITY_TYPES)}",
        )
