"""Operational Validation Service - E2E operational flow validation."""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.delivery_model import DeliveryOrderModel


class OperationalValidationService:
    """Service for E2E operational flow validation.

    Responsibilities:
    - Validate work order operational flow
    - Validate inventory reservation flow
    - Validate material issuance flow
    - Validate QC flow
    - Validate delivery flow
    - Generate validation reports
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def validate_work_order_flow(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
    ) -> dict:
        """Validate work order operational flow completeness."""
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == work_order_id,
            WorkOrderModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        wo = result.scalar_one_or_none()

        if not wo:
            return {"valid": False, "errors": ["Work order not found"]}

        errors = []
        warnings = []

        # Validate state transitions
        if wo.status == "PLANNED":
            warnings.append("Work order is in PLANNED state")
        elif wo.status == "RELEASED":
            # Check if material is reserved
            if wo.reserved_stock == 0:
                errors.append("Material not reserved after release")
        elif wo.status == "IN_PRODUCTION":
            # Check if material is issued
            if wo.issued_stock == 0:
                errors.append("Material not issued before production")
        elif wo.status == "QC_PENDING":
            # Check if production is complete
            if wo.produced_quantity == 0:
                errors.append("No production recorded before QC")
        elif wo.status == "FG_RECEIVED":
            # Check if QC is approved
            if wo.status != "QC_APPROVED":
                errors.append("FG received without QC approval")
        elif wo.status == "CLOSED":
            # Check if all steps are complete
            if wo.issued_stock == 0:
                errors.append("Material not issued before close")
            if wo.produced_quantity == 0:
                errors.append("No production recorded before close")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "work_order_id": str(work_order_id),
            "current_status": wo.status,
        }

    async def validate_inventory_flow(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> dict:
        """Validate inventory flow for a material."""
        stmt = select(InventoryTransactionModel).where(
            InventoryTransactionModel.tenant_id == tenant_id,
            InventoryTransactionModel.material_id == material_id,
            InventoryTransactionModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        transactions = result.scalars().all()

        errors = []
        warnings = []

        # Check for negative stock
        running_balance = 0
        for tx in transactions:
            if tx.transaction_type in ("receipt", "purchase_receipt", "production_receipt", "transfer_in"):
                running_balance += tx.quantity
            elif tx.transaction_type in ("issue", "transfer_out", "consumption"):
                running_balance -= tx.quantity

            if running_balance < 0:
                errors.append(f"Negative stock at transaction {tx.id}: {running_balance}")

        # Check for missing transactions
        if len(transactions) == 0:
            warnings.append("No inventory transactions found")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "material_id": str(material_id),
            "transaction_count": len(transactions),
            "current_balance": running_balance,
        }

    async def validate_delivery_flow(
        self,
        *,
        tenant_id: uuid.UUID,
        delivery_order_id: uuid.UUID,
    ) -> dict:
        """Validate delivery operational flow."""
        stmt = select(DeliveryOrderModel).where(
            DeliveryOrderModel.id == delivery_order_id,
            DeliveryOrderModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        do = result.scalar_one_or_none()

        if not do:
            return {"valid": False, "errors": ["Delivery order not found"]}

        errors = []
        warnings = []

        # Validate delivery flow
        if do.status == "DELIVERED":
            if not do.delivery_date:
                errors.append("Delivery marked as DELIVERED but no delivery date")
            if not do.shipped_at:
                errors.append("Delivery marked as DELIVERED but not shipped")
        elif do.status == "IN_TRANSIT":
            if not do.shipped_at:
                errors.append("Delivery marked as IN_TRANSIT but not shipped")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "delivery_order_id": str(delivery_order_id),
            "current_status": do.status,
        }

    async def generate_validation_report(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Generate comprehensive validation report for tenant."""
        # Get all work orders
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        wos = result.scalars().all()

        total_wos = len(wos)
        valid_wos = 0
        invalid_wos = 0

        wo_errors = []
        for wo in wos:
            validation = await self.validate_work_order_flow(
                tenant_id=tenant_id,
                work_order_id=wo.id,
            )
            if validation["valid"]:
                valid_wos += 1
            else:
                invalid_wos += 1
                wo_errors.extend(validation["errors"])

        return {
            "tenant_id": str(tenant_id),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_work_orders": total_wos,
                "valid_work_orders": valid_wos,
                "invalid_work_orders": invalid_wos,
                "validation_rate": (valid_wos / total_wos * 100) if total_wos > 0 else 100,
            },
            "errors": wo_errors,
        }
