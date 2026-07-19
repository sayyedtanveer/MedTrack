"""Storekeeper Service - operational flow for storekeeper dashboard."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderModel,
    WorkOrderMaterialModel,
)
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.inventory_reservation_model import InventoryReservationModel
from backend.app.infrastructure.persistence.models.batch_model import BatchModel
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel


class StorekeeperService:
    """Service for storekeeper operational dashboard and actions.
    
    Note: Storekeeper confirmations must be retry-safe. We enforce idempotency by
    reconciling requested quantities against the current reservation state at
    confirmation time (no duplicate mutations on browser retry / double-click).

    Responsibilities:
    - Get issue queue (pending material issues)
    - Get shortage queue
    - Get partially issued WOs
    - Issue material
    - Partially issue material
    - Reject issue
    - Return material
    """

    _BLOCKED_BATCH_STATUSES: set[str] = {
        "EXPIRED",
        "QUARANTINED",
        "QC_HOLD",
        "PICKING_HOLD",
        "DAMAGE_HOLD",
        "INVESTIGATION_HOLD",
    }

    def __init__(self, session: AsyncSession):
        self._session = session
        self._inventory = InventoryService(session)

    async def _log_operational_event(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        action: str,
        work_order_id: Optional[uuid.UUID],
        material_id: uuid.UUID,
        batch_id: Optional[uuid.UUID],
        location_id: Optional[uuid.UUID],
        quantity: Optional[Decimal] = None,
        extra: Optional[dict] = None,
    ) -> None:
        self._session.add(
            AuditLogModel(
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                entity_type="storekeeper_operation",
                entity_id=work_order_id,
                extra={
                    "work_order_id": str(work_order_id) if work_order_id else None,
                    "material_id": str(material_id),
                    "batch_id": str(batch_id) if batch_id else None,
                    "location_id": str(location_id) if location_id else None,
                    "quantity": str(quantity) if quantity is not None else None,
                    **(extra or {}),
                },
            )
        )

    async def get_issue_queue(self, *, tenant_id: uuid.UUID) -> list[dict]:
        """Get pending material issue queue for storekeeper dashboard."""
        # This is already implemented in InventoryService.get_pending_issues
        return await self._inventory.get_pending_issues(tenant_id=tenant_id)

    async def get_shortage_queue(self, *, tenant_id: uuid.UUID) -> list[dict]:
        """Get shortage queue for storekeeper dashboard."""
        from backend.app.infrastructure.persistence.models.material_shortage_model import MaterialShortageModel

        stmt = (
            select(MaterialShortageModel)
            .where(
                MaterialShortageModel.tenant_id == tenant_id,
                MaterialShortageModel.status.in_(["open", "partial"]),
            )
            .order_by(MaterialShortageModel.created_at)
        )
        result = await self._session.execute(stmt)
        shortages = result.scalars().all()

        shortage_queue = []
        for shortage in shortages:
            incoming_qty = await self._open_po_quantity(tenant_id, shortage.material_id)
            if incoming_qty >= Decimal(str(shortage.shortage_quantity or 0)):
                continue
            material = (
                await self._session.execute(
                    select(MaterialModel).where(
                        MaterialModel.id == shortage.material_id,
                        MaterialModel.tenant_id == tenant_id,
                        MaterialModel.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            wo = (
                await self._session.execute(
                    select(WorkOrderModel).where(
                        WorkOrderModel.id == shortage.work_order_id,
                        WorkOrderModel.tenant_id == tenant_id,
                        WorkOrderModel.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            shortage_queue.append({
                "shortage_id": shortage.id,
                "work_order_id": shortage.work_order_id,
                "wo_number": wo.wo_number if wo is not None else None,
                "material_id": shortage.material_id,
                "material_code": material.code if material is not None else None,
                "material_name": material.name if material is not None else None,
                "required_quantity": shortage.required_quantity,
                "available_quantity": shortage.available_quantity,
                "shortage_quantity": shortage.shortage_quantity,
                "status": shortage.status,
                "created_at": shortage.created_at,
            })

        return shortage_queue

    async def _open_po_quantity(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> Decimal:
        from backend.app.infrastructure.persistence.models.purchase_order_model import (
            PurchaseOrderLineModel,
            PurchaseOrderModel,
        )

        result = await self._session.execute(
            select(
                func.coalesce(
                    func.sum(PurchaseOrderLineModel.quantity - PurchaseOrderLineModel.received_quantity),
                    0,
                )
            )
            .join(PurchaseOrderModel, PurchaseOrderModel.id == PurchaseOrderLineModel.purchase_order_id)
            .where(
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
                PurchaseOrderLineModel.material_id == material_id,
                PurchaseOrderModel.status.in_(["sent", "partially_received", "approved"]),
            )
        )
        return Decimal(str(result.scalar() or 0))

    async def get_partially_issued_wo(self, *, tenant_id: uuid.UUID) -> list[dict]:
        """Get partially issued WOs for storekeeper dashboard."""
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.status.in_(["MATERIAL_PENDING", "MATERIAL_RESERVED", "MATERIAL_ISSUED"]),
                WorkOrderModel.is_deleted.is_(False),
            )
            .order_by(WorkOrderModel.due_date)
        )
        result = await self._session.execute(stmt)
        wos = result.scalars().all()

        partially_issued = []
        for wo in wos:
            # Get material requirements
            mat_stmt = select(WorkOrderMaterialModel).where(
                WorkOrderMaterialModel.work_order_id == wo.id
            )
            mat_result = await self._session.execute(mat_stmt)
            materials = mat_result.scalars().all()

            # Check if any material is partially issued
            has_partial = any(
                Decimal(str(m.issued_quantity)) > 0
                and Decimal(str(m.issued_quantity)) < Decimal(str(m.required_quantity))
                for m in materials
            )

            if has_partial:
                partially_issued.append({
                    "work_order_id": wo.id,
                    "wo_number": wo.wo_number,
                    "product_id": wo.product_id,
                    "due_date": wo.due_date,
                    "status": wo.status,
                })

        return partially_issued

    async def get_pending_reservations(self, *, tenant_id: uuid.UUID) -> list[dict]:
        """Get reservations that still need storekeeper issue action."""
        stmt = (
            select(InventoryReservationModel, WorkOrderModel, MaterialModel, BatchModel)
            .join(
                WorkOrderModel,
                WorkOrderModel.id == InventoryReservationModel.reference_id,
            )
            .join(MaterialModel, MaterialModel.id == InventoryReservationModel.material_id)
            .outerjoin(BatchModel, BatchModel.id == InventoryReservationModel.batch_id)
            .where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.reference_type == "work_order",
                InventoryReservationModel.status.in_(("RESERVED", "PARTIALLY_ISSUED")),
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.is_deleted.is_(False),
            )
            .order_by(WorkOrderModel.due_date, InventoryReservationModel.created_at)
        )
        rows = (await self._session.execute(stmt)).all()
        queue: list[dict] = []
        for reservation, wo, material, batch in rows:
            reserved_qty = Decimal(str(reservation.quantity or 0))
            issued_qty = Decimal(str(reservation.issued_quantity or 0))
            pending_qty = reserved_qty - issued_qty
            if pending_qty <= 0:
                continue
            queue.append({
                "reservation_id": reservation.id,
                "work_order_id": wo.id,
                "wo_number": wo.wo_number,
                "material_id": material.id,
                "material_code": material.code,
                "material_name": material.name,
                "batch_id": reservation.batch_id,
                "batch_number": batch.batch_number if batch is not None else None,
                "reserved_quantity": reserved_qty,
                "issued_quantity": issued_qty,
                "pending_quantity": pending_qty,
                "status": reservation.status,
                "created_at": reservation.created_at,
            })
        return queue

    async def get_pending_returns(self, *, tenant_id: uuid.UUID) -> list[dict]:
        """Get issued, unconsumed material that can be returned from production."""
        stmt = (
            select(InventoryReservationModel, WorkOrderModel, MaterialModel, BatchModel)
            .join(WorkOrderModel, WorkOrderModel.id == InventoryReservationModel.reference_id)
            .join(MaterialModel, MaterialModel.id == InventoryReservationModel.material_id)
            .outerjoin(BatchModel, BatchModel.id == InventoryReservationModel.batch_id)
            .where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.reference_type == "work_order",
                InventoryReservationModel.status.in_(("ISSUED", "PARTIALLY_CONSUMED")),
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.is_deleted.is_(False),
            )
            .order_by(WorkOrderModel.due_date, InventoryReservationModel.updated_at)
        )
        rows = (await self._session.execute(stmt)).all()
        queue: list[dict] = []
        for reservation, wo, material, batch in rows:
            returnable_qty = (
                Decimal(str(reservation.issued_quantity or 0))
                - Decimal(str(reservation.consumed_quantity or 0))
                - Decimal(str(reservation.returned_quantity or 0))
            )
            if returnable_qty <= 0:
                continue
            queue.append({
                "reservation_id": reservation.id,
                "work_order_id": wo.id,
                "wo_number": wo.wo_number,
                "material_id": material.id,
                "material_code": material.code,
                "material_name": material.name,
                "batch_id": reservation.batch_id,
                "batch_number": batch.batch_number if batch is not None else None,
                "issued_quantity": reservation.issued_quantity,
                "consumed_quantity": reservation.consumed_quantity,
                "returned_quantity": reservation.returned_quantity,
                "returnable_quantity": returnable_qty,
                "status": reservation.status,
                "updated_at": reservation.updated_at,
            })
        return queue

    async def get_inventory_alerts(self, *, tenant_id: uuid.UUID) -> list[dict]:
        """Get stock and batch alerts for storekeeper operations."""
        alerts: list[dict] = []
        material_rows = (
            await self._session.execute(
                select(MaterialModel).where(
                    MaterialModel.tenant_id == tenant_id,
                    MaterialModel.is_deleted.is_(False),
                    MaterialModel.is_active.is_(True),
                )
            )
        ).scalars().all()
        for material in material_rows:
            reorder_level = Decimal(str(material.reorder_level or 0))
            current_stock = Decimal(str(material.current_stock or 0))
            if reorder_level > 0 and current_stock <= reorder_level:
                alerts.append({
                    "alert_type": "LOW_STOCK",
                    "severity": "warning",
                    "material_id": material.id,
                    "material_code": material.code,
                    "material_name": material.name,
                    "current_stock": current_stock,
                    "reorder_level": reorder_level,
                    "message": f"{material.code} is at or below reorder level",
                })

        batch_rows = (
            await self._session.execute(
                select(BatchModel, MaterialModel)
                .join(MaterialModel, MaterialModel.id == BatchModel.material_id)
                .where(
                    BatchModel.tenant_id == tenant_id,
                    BatchModel.is_deleted.is_(False),
                    func.upper(BatchModel.status).in_(
                        (
                            "EXPIRED",
                            "QUARANTINED",
                            "QC_HOLD",
                            "PICKING_HOLD",
                            "DAMAGE_HOLD",
                            "INVESTIGATION_HOLD",
                        )
                    ),
                    MaterialModel.tenant_id == tenant_id,
                    MaterialModel.is_deleted.is_(False),
                )
            )
        ).all()
        for batch, material in batch_rows:
            status = str(batch.status or "").upper()
            alerts.append({
                "alert_type": status,
                "severity": "critical" if status in {"QUARANTINED", "DAMAGE_HOLD"} else "warning",
                "material_id": material.id,
                "material_code": material.code,
                "material_name": material.name,
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "remaining_quantity": batch.remaining_quantity,
                "message": f"{material.code} batch {batch.batch_number} is {status.lower()}",
            })
        return alerts

    async def get_operational_batches(self, *, tenant_id: uuid.UUID) -> list[dict]:
        """Return operator-facing batch cards with visible quantity and location state."""
        rows = (
            await self._session.execute(
                select(BatchModel, MaterialModel, LocationModel)
                .join(MaterialModel, MaterialModel.id == BatchModel.material_id)
                .outerjoin(LocationModel, LocationModel.id == BatchModel.location_id)
                .where(
                    BatchModel.tenant_id == tenant_id,
                    BatchModel.is_deleted.is_(False),
                    MaterialModel.tenant_id == tenant_id,
                    MaterialModel.is_deleted.is_(False),
                )
                .order_by(
                    BatchModel.expiry_date.is_(None),
                    BatchModel.expiry_date.asc(),
                    BatchModel.updated_at.desc(),
                )
            )
        ).all()
        cards: list[dict] = []
        for batch, material, location in rows:
            status = str(batch.status or "").upper()
            remaining = Decimal(str(batch.remaining_quantity if batch.remaining_quantity is not None else batch.quantity))
            original = Decimal(str(batch.original_quantity if batch.original_quantity is not None else batch.quantity))
            cards.append(
                {
                    "batch_id": batch.id,
                    "batch_number": batch.batch_number,
                    "material_id": material.id,
                    "material_code": material.item_code or material.code,
                    "material_name": material.name,
                    "original_quantity": original,
                    "remaining_quantity": remaining,
                    "reserved_quantity": Decimal(str(batch.reserved_quantity or 0)),
                    "consumed_quantity": Decimal(str(batch.consumed_quantity or 0)),
                    "returned_quantity": Decimal(str(batch.returned_quantity or 0)),
                    "location_id": batch.location_id,
                    "location_name": location.name if location is not None else None,
                    "location_type": location.type if location is not None else None,
                    "expiry_date": batch.expiry_date,
                    "status": status,
                    "is_blocked": status in self._BLOCKED_BATCH_STATUSES,
                    "is_near_empty": original > 0 and remaining / original <= Decimal("0.20"),
                }
            )
        return cards

    async def _assert_batch_not_blocked(
        self, *, tenant_id: uuid.UUID, batch_id: uuid.UUID
    ) -> None:
        batch = (
            await self._session.execute(
                select(BatchModel).where(
                    BatchModel.id == batch_id,
                    BatchModel.tenant_id == tenant_id,
                    BatchModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()

        if batch is None:
            raise ValueError(f"Batch {batch_id} not found for tenant {tenant_id}")

        status = str(batch.status or "").upper()
        if status in self._BLOCKED_BATCH_STATUSES:
            raise ValueError(
                f"Batch {batch.batch_number} is blocked ({status}) and cannot be issued/picked"
            )

    async def _pending_issue_qty(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        batch_id: Optional[uuid.UUID],
    ) -> Decimal:
        """Quantity still pending to be issued for this WO/material (optionally constrained to a batch)."""
        stmt = select(InventoryReservationModel).where(
            InventoryReservationModel.tenant_id == tenant_id,
            InventoryReservationModel.reference_type == "work_order",
            InventoryReservationModel.reference_id == work_order_id,
            InventoryReservationModel.material_id == material_id,
            InventoryReservationModel.batch_id == batch_id,
        )
        res = await self._session.execute(stmt)
        reservation = res.scalar_one_or_none()
        if reservation is None:
            # If there is no reservation row, treat as fully issued (no-op on retry).
            return Decimal("0")

        reserved_qty = Decimal(str(reservation.quantity or 0))
        issued_qty = Decimal(str(reservation.issued_quantity or 0))
        pending = reserved_qty - issued_qty
        return max(Decimal("0"), pending)

    async def _returnable_qty(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        batch_id: Optional[uuid.UUID],
    ) -> Decimal:
        """Quantity still returnable for this WO/material (optionally constrained to a batch)."""
        stmt = select(InventoryReservationModel).where(
            InventoryReservationModel.tenant_id == tenant_id,
            InventoryReservationModel.reference_type == "work_order",
            InventoryReservationModel.reference_id == work_order_id,
            InventoryReservationModel.material_id == material_id,
            InventoryReservationModel.batch_id == batch_id,
        )
        res = await self._session.execute(stmt)
        reservation = res.scalar_one_or_none()
        if reservation is None:
            return Decimal("0")

        issued_qty = Decimal(str(reservation.issued_quantity or 0))
        consumed_qty = Decimal(str(reservation.consumed_quantity or 0))
        returned_qty = Decimal(str(reservation.returned_quantity or 0))

        returnable = issued_qty - consumed_qty - returned_qty
        return max(Decimal("0"), returnable)

    async def reserve_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        batch_id: Optional[uuid.UUID],
        reserved_by: uuid.UUID,
    ) -> None:
        """Reserve stock for work order.
        
        Triggers WO transition: MATERIAL_PENDING → MATERIAL_RESERVED.
        Inventory: AVAILABLE → RESERVED.
        """
        # Call InventoryService to reserve stock
        await self._inventory.reserve_stock(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=quantity,
            work_order_id=work_order_id,
            unit_id=unit_id,
            batch_id=batch_id,
            created_by=reserved_by,
        )
        await self._log_operational_event(
            tenant_id=tenant_id,
            user_id=reserved_by,
            action="PICK_STARTED",
            work_order_id=work_order_id,
            material_id=material_id,
            batch_id=batch_id,
            location_id=None,
            quantity=quantity,
        )
        
        # Update WO status to MATERIAL_RESERVED
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
        from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
        
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == work_order_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        wo_model = result.scalar_one_or_none()
        
        if wo_model and wo_model.status == WorkOrderStatus.MATERIAL_PENDING.value:
            wo_model.status = WorkOrderStatus.MATERIAL_RESERVED.value
            wo_model.updated_at = datetime.now(timezone.utc)

    async def issue_material(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        batch_id: Optional[uuid.UUID],
        issued_by: uuid.UUID,
    ) -> None:
        """Issue material to work order.

        Triggers WO transition: MATERIAL_RESERVED → MATERIAL_ISSUED.
        Inventory: RESERVED → ISSUED.
        """
        if batch_id is not None:
            await self._assert_batch_not_blocked(tenant_id=tenant_id, batch_id=batch_id)

        await self._inventory.issue_material_for_wo(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            material_id=material_id,
            quantity=quantity,
            unit_id=unit_id,
            created_by=issued_by,
            transition_wo_status=True,
            batch_id=batch_id,
        )
        await self._log_operational_event(
            tenant_id=tenant_id,
            user_id=issued_by,
            action="ISSUE_COMPLETED",
            work_order_id=work_order_id,
            material_id=material_id,
            batch_id=batch_id,
            location_id=None,
            quantity=quantity,
        )

    async def partially_issue_material(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        batch_id: Optional[uuid.UUID],
        issued_by: uuid.UUID,
    ) -> None:
        """Partially issue material to work order (retry-safe).

        Idempotency strategy:
        - reconcile requested quantity against current pending issue quantity
        - cap quantity to pending
        - if pending is 0, do a no-op (no duplicate mutation)
        """
        pending_qty = await self._pending_issue_qty(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            material_id=material_id,
            batch_id=batch_id,
        )
        if pending_qty <= 0:
            await self._log_operational_event(
                tenant_id=tenant_id,
                user_id=issued_by,
                action="PARTIAL_ISSUE_NOOP_ALREADY_ISSUED",
                work_order_id=work_order_id,
                material_id=material_id,
                batch_id=batch_id,
                location_id=None,
                quantity=Decimal("0"),
            )
            return

        qty_to_issue = min(quantity, pending_qty)

        if batch_id is not None:
            await self._assert_batch_not_blocked(tenant_id=tenant_id, batch_id=batch_id)

        await self._inventory.issue_material_for_wo(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            material_id=material_id,
            quantity=qty_to_issue,
            unit_id=unit_id,
            created_by=issued_by,
            transition_wo_status=True,
            batch_id=batch_id,
        )
        await self._log_operational_event(
            tenant_id=tenant_id,
            user_id=issued_by,
            action="PARTIAL_ISSUE_COMPLETED",
            work_order_id=work_order_id,
            material_id=material_id,
            batch_id=batch_id,
            location_id=None,
            quantity=qty_to_issue,
        )

    async def reject_issue(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        reason: str,
        rejected_by: uuid.UUID,
    ) -> None:
        """Reject material issue request.
        
        Cancels reservation and logs rejection reason.
        Inventory: RESERVED → AVAILABLE.
        """
        await self._inventory.cancel_work_order_reservation(
            tenant_id=tenant_id,
            material_id=material_id,
            work_order_id=work_order_id,
            unit_id=None,
            created_by=rejected_by,
            remarks=f"Rejected: {reason}",
        )
        
        # Log rejection reason in operational audit trail only.
        # (Avoid mutating WorkOrderMaterialModel attributes that may not exist in older schemas.)
        await self._log_operational_event(
            tenant_id=tenant_id,
            user_id=rejected_by,
            action="REJECT_ISSUE",
            work_order_id=work_order_id,
            material_id=material_id,
            batch_id=None,
            location_id=None,
            extra={"reason": reason},
        )

    async def return_material(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        batch_id: Optional[uuid.UUID],
        returned_by: uuid.UUID,
    ) -> None:
        """Return issued material back to inventory (retry-safe).

        Idempotency strategy:
        - reconcile requested quantity against current returnable quantity
        - cap quantity to returnable
        - if returnable is 0, do a no-op (no duplicate mutation / no drift)
        """
        returnable_qty = await self._returnable_qty(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            material_id=material_id,
            batch_id=batch_id,
        )
        if returnable_qty <= 0:
            await self._log_operational_event(
                tenant_id=tenant_id,
                user_id=returned_by,
                action="RETURN_NOOP_NOT_RETURNABLE",
                work_order_id=work_order_id,
                material_id=material_id,
                batch_id=batch_id,
                location_id=None,
                quantity=Decimal("0"),
            )
            return

        qty_to_return = min(quantity, returnable_qty)

        if batch_id is not None:
            await self._assert_batch_not_blocked(tenant_id=tenant_id, batch_id=batch_id)

        await self._inventory.return_stock(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=qty_to_return,
            work_order_id=work_order_id,
            unit_id=unit_id,
            created_by=returned_by,
            batch_id=batch_id,
        )
        await self._log_operational_event(
            tenant_id=tenant_id,
            user_id=returned_by,
            action="RETURN_COMPLETED",
            work_order_id=work_order_id,
            material_id=material_id,
            batch_id=batch_id,
            location_id=None,
            quantity=qty_to_return,
        )
