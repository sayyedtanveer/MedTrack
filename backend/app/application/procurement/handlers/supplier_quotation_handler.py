"""
Supplier Quotation application handler with domain entity integration.

Coordinates quotation lifecycle transitions using SupplierQuotation domain entity.
"""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from backend.app.infrastructure.persistence.models.quality_model import SupplierQuotationModel
from backend.app.domain.procurement.entities import (
    SupplierQuotation,
    SupplierQuotationStatus,
    InvalidQuotationTransitionError,
    QuotationRejectedError,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


class SupplierQuotationHandler:
    """Handler for supplier quotation business logic with state machine validation."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.uow: Optional[SQLAlchemyUnitOfWork] = None

    def with_uow(self, uow: SQLAlchemyUnitOfWork) -> SupplierQuotationHandler:
        """Fluent setter for UnitOfWork (for event dispatch)."""
        self.uow = uow
        return self

    async def submit_quotation(self, quotation_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """
        Transition Quotation from DRAFT → SUBMITTED.
        
        Raises:
            ValueError: If quotation not found or invalid transition
        """
        quotation_model = await self.session.get(SupplierQuotationModel, quotation_id)
        if not quotation_model or quotation_model.tenant_id != tenant_id or quotation_model.is_deleted:
            raise ValueError(f"Quotation {quotation_id} not found")

        # Create domain entity from model
        quotation_entity = SupplierQuotation(
            id=quotation_model.id,
            tenant_id=quotation_model.tenant_id,
            supplier_id=quotation_model.supplier_id,
            material_id=quotation_model.material_id,
            purchase_order_id=quotation_model.purchase_order_id,
            quoted_price=quotation_model.quoted_price,
            quantity=quotation_model.quantity,
            delivery_days=quotation_model.delivery_days,
            created_by=quotation_model.created_by,
            status=SupplierQuotationStatus(quotation_model.status),
            notes=quotation_model.notes,
            is_deleted=quotation_model.is_deleted,
            created_at=quotation_model.created_at,
            updated_at=quotation_model.updated_at,
        )

        # Validate transition
        try:
            quotation_entity.submit()
        except InvalidQuotationTransitionError as e:
            raise ValueError(str(e))
        except QuotationRejectedError as e:
            raise ValueError(str(e))

        # Update model
        quotation_model.status = quotation_entity.status.value
        quotation_model.updated_at = quotation_entity.updated_at
        await self.session.flush()

        return {"status": "ok", "quotation_id": str(quotation_id)}

    async def approve_quotation(self, quotation_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """
        Transition Quotation from SUBMITTED → APPROVED.
        
        Raises:
            ValueError: If quotation not found or invalid transition
        """
        quotation_model = await self.session.get(SupplierQuotationModel, quotation_id)
        if not quotation_model or quotation_model.tenant_id != tenant_id or quotation_model.is_deleted:
            raise ValueError(f"Quotation {quotation_id} not found")

        # Create domain entity
        quotation_entity = SupplierQuotation(
            id=quotation_model.id,
            tenant_id=quotation_model.tenant_id,
            supplier_id=quotation_model.supplier_id,
            material_id=quotation_model.material_id,
            purchase_order_id=quotation_model.purchase_order_id,
            quoted_price=quotation_model.quoted_price,
            quantity=quotation_model.quantity,
            delivery_days=quotation_model.delivery_days,
            created_by=quotation_model.created_by,
            status=SupplierQuotationStatus(quotation_model.status),
            notes=quotation_model.notes,
            is_deleted=quotation_model.is_deleted,
            created_at=quotation_model.created_at,
            updated_at=quotation_model.updated_at,
        )

        # Validate transition
        try:
            quotation_entity.approve()
        except InvalidQuotationTransitionError as e:
            raise ValueError(str(e))
        except QuotationRejectedError as e:
            raise ValueError(str(e))

        # Update model
        quotation_model.status = quotation_entity.status.value
        quotation_model.updated_at = quotation_entity.updated_at
        await self.session.flush()

        return {"status": "ok", "quotation_id": str(quotation_id)}

    async def reject_quotation(self, quotation_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """
        Transition Quotation to REJECTED from any state.
        
        Raises:
            ValueError: If quotation not found or already rejected
        """
        quotation_model = await self.session.get(SupplierQuotationModel, quotation_id)
        if not quotation_model or quotation_model.tenant_id != tenant_id or quotation_model.is_deleted:
            raise ValueError(f"Quotation {quotation_id} not found")

        # Create domain entity
        quotation_entity = SupplierQuotation(
            id=quotation_model.id,
            tenant_id=quotation_model.tenant_id,
            supplier_id=quotation_model.supplier_id,
            material_id=quotation_model.material_id,
            purchase_order_id=quotation_model.purchase_order_id,
            quoted_price=quotation_model.quoted_price,
            quantity=quotation_model.quantity,
            delivery_days=quotation_model.delivery_days,
            created_by=quotation_model.created_by,
            status=SupplierQuotationStatus(quotation_model.status),
            notes=quotation_model.notes,
            is_deleted=quotation_model.is_deleted,
            created_at=quotation_model.created_at,
            updated_at=quotation_model.updated_at,
        )

        # Validate transition
        try:
            quotation_entity.reject()
        except InvalidQuotationTransitionError as e:
            raise ValueError(str(e))
        except QuotationRejectedError as e:
            raise ValueError(str(e))

        # Update model
        quotation_model.status = quotation_entity.status.value
        quotation_model.updated_at = quotation_entity.updated_at
        await self.session.flush()

        return {"status": "rejected", "quotation_id": str(quotation_id)}
