"""Validation REST API endpoints."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, Query, status

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id
from backend.app.interfaces.api.v1.dependencies.auth import get_container
from backend.app.application.validation.services.operational_validation_service import OperationalValidationService


router = APIRouter(prefix="/validation", tags=["Validation"])


@router.get("/work-order/{work_order_id}")
async def validate_work_order_flow(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Validate work order operational flow completeness."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = OperationalValidationService(session)
        validation = await service.validate_work_order_flow(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
        )
        return validation


@router.get("/inventory/material/{material_id}")
async def validate_inventory_flow(
    material_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Validate inventory flow for a material."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = OperationalValidationService(session)
        validation = await service.validate_inventory_flow(
            tenant_id=tenant_id,
            material_id=material_id,
        )
        return validation


@router.get("/delivery/{delivery_order_id}")
async def validate_delivery_flow(
    delivery_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Validate delivery operational flow."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = OperationalValidationService(session)
        validation = await service.validate_delivery_flow(
            tenant_id=tenant_id,
            delivery_order_id=delivery_order_id,
        )
        return validation


@router.get("/report")
async def generate_validation_report(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Generate comprehensive validation report for tenant."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = OperationalValidationService(session)
        report = await service.generate_validation_report(
            tenant_id=tenant_id,
        )
        return report
