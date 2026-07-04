"""FGReceiveCommandHandler — Gap #3.

Registered as the async event consumer on the QC_APPROVED transition.

Responsibilities
────────────────
1. Guard on wo.status == QC_APPROVED (idempotency).
2. Compute net_qty = produced_quantity - scrap_quantity.
3. Atomically: materials.current_stock += net_qty  +  insert inventory_transactions
   (type=FG_RECEIPT, ref=work_order).
4. Update linked sales_order_lines.allocated_quantity += net_qty.
5. Transition WO → FG_RECEIVED.
6. On any DB error: keep WO in QC_APPROVED, rollback the FG writes, emit
   fg_receipt_failed notification to Finance.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
from backend.app.infrastructure.persistence.models.inventory_transaction_model import (
    InventoryTransactionModel,
)
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.sales_models import SalesOrderLineModel
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.application.manufacturing.services.workflow_orchestration_service import (
    WorkflowOrchestrationService,
)
from backend.app.application.notifications.notification_service import (
    NotificationService,
    NOTIFICATION_TYPE_FG_RECEIPT_FAILED,
)

logger = logging.getLogger(__name__)


class FGReceiveCommandHandler:
    """Handles the FGReceiveCommand triggered after QC approval.

    This handler is the single authoritative path that turns a QC_APPROVED
    work order into FG_RECEIVED inventory stock.  All writes are protected
    by row-level SELECT … FOR UPDATE locks and rolled back atomically on
    failure (Gap #3).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._inventory = InventoryService(session)
        self._notifications = NotificationService(session)

    # ──────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ──────────────────────────────────────────────────────────────────────────

    async def handle(
        self,
        wo_id: uuid.UUID,
        tenant_id: uuid.UUID,
        received_by: uuid.UUID,
    ) -> Dict[str, Any]:
        """Execute the FG receipt for the given work order.

        Returns a dict describing the outcome.  On any DB failure the work
        order is left in QC_APPROVED (caller must NOT commit) and a
        fg_receipt_failed notification is sent to Finance.
        """
        # ── 1. Load WO (with row-level lock for idempotency) ─────────────────
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.id == wo_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        wo = result.scalar_one_or_none()

        if not wo:
            raise ValueError(f"Work Order {wo_id} not found")

        # ── 2. Idempotency guard ──────────────────────────────────────────────
        if wo.status == WorkOrderStatus.FG_RECEIVED.value:
            logger.info(
                "FGReceiveCommandHandler: WO already FG_RECEIVED — skipping",
                extra={"wo_id": str(wo_id)},
            )
            return {
                "work_order_id": str(wo_id),
                "skipped": True,
                "reason": "already FG_RECEIVED",
            }

        if wo.status != WorkOrderStatus.QC_APPROVED.value:
            raise ValueError(
                f"FGReceiveCommandHandler: WO {wo_id} is in status {wo.status!r}; "
                "expected QC_APPROVED"
            )

        # ── 3. Compute net quantity ───────────────────────────────────────────
        net_qty = Decimal(str(wo.produced_quantity or 0)) - Decimal(
            str(wo.scrap_quantity or 0)
        )
        if net_qty < 0:
            net_qty = Decimal("0")

        # ── 4. Resolve FG material ID ─────────────────────────────────────────
        fg_material_id = await self._resolve_fg_material(wo)

        try:
            # ── 5. Idempotency: skip if FG_RECEIPT already recorded ───────────
            existing = (
                await self._session.execute(
                    select(InventoryTransactionModel.id).where(
                        InventoryTransactionModel.tenant_id == tenant_id,
                        InventoryTransactionModel.material_id == fg_material_id,
                        InventoryTransactionModel.reference_type == "work_order",
                        InventoryTransactionModel.reference_id == wo_id,
                        InventoryTransactionModel.transaction_type == "FG_RECEIPT",
                        InventoryTransactionModel.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()

            receipt_created = False
            if net_qty > 0 and existing is None:
                # ── 6. Atomic stock increase + inventory_transaction insert ───
                await self._inventory.receive_fg(
                    tenant_id=tenant_id,
                    product_id=fg_material_id,
                    quantity=net_qty,
                    work_order_id=wo_id,
                    created_by=received_by,
                )
                receipt_created = True

                logger.info(
                    "FGReceiveCommandHandler: FG stock increased",
                    extra={
                        "tenant_id": str(tenant_id),
                        "material_id": str(fg_material_id),
                        "net_qty": float(net_qty),
                    },
                )

            # ── 7. Update linked SO line allocated_quantity ──────────────────
            so_line_updated = False
            if net_qty > 0 and wo.sales_order_id:
                so_line_updated = await self._allocate_to_so_line(
                    wo=wo,
                    fg_material_id=fg_material_id,
                    net_qty=net_qty,
                    tenant_id=tenant_id,
                )

            # ── 8. Transition WO → FG_RECEIVED ───────────────────────────────
            from datetime import datetime, timezone

            wo.status = WorkOrderStatus.FG_RECEIVED.value
            wo.updated_at = datetime.now(timezone.utc)
            await self._session.flush()

            logger.info(
                "FGReceiveCommandHandler: WO transitioned to FG_RECEIVED",
                extra={"wo_id": str(wo_id)},
            )

            # ── 9. Wire SO allocation chain → READY_FOR_DISPATCH (Gap #8) ────
            # WorkflowOrchestrationService.on_fg_received() checks whether all
            # SO lines are fully allocated and, if so, transitions the SO to
            # READY_FOR_DISPATCH and emits a dispatch_queue_updated notification
            # to the Dispatch role.  The SO line allocated_quantity was already
            # incremented in step 7 above, so on_fg_received() will detect
            # reserve_qty == 0 and skip the duplicate reservation, proceeding
            # only to the READY_FOR_DISPATCH check and notification.
            if wo.sales_order_id:
                try:
                    orchestration = WorkflowOrchestrationService(self._session)
                    await orchestration.on_fg_received(
                        tenant_id=tenant_id,
                        work_order_id=wo_id,
                        received_by=received_by,
                    )
                    logger.info(
                        "FGReceiveCommandHandler: on_fg_received orchestration complete",
                        extra={"wo_id": str(wo_id), "so_id": str(wo.sales_order_id)},
                    )
                except Exception as orch_exc:
                    # Non-fatal: log and continue.  WO is already FG_RECEIVED;
                    # a human can re-trigger the READY_FOR_DISPATCH check if needed.
                    logger.warning(
                        "FGReceiveCommandHandler: on_fg_received orchestration failed "
                        "(WO already FG_RECEIVED — SO status update skipped)",
                        extra={"wo_id": str(wo_id), "error": str(orch_exc)},
                    )

            return {
                "work_order_id": str(wo_id),
                "fg_material_id": str(fg_material_id),
                "net_qty": float(net_qty),
                "receipt_created": receipt_created,
                "so_line_updated": so_line_updated,
                "skipped": False,
            }

        except Exception as exc:
            # ── Error recovery (Gap #3) ────────────────────────────────────────
            # WO remains in QC_APPROVED.  The caller must rollback the transaction
            # (no flush/commit after this point).  We emit a notification to Finance
            # so that a human can intervene.
            logger.error(
                "FGReceiveCommandHandler: FG receipt failed — WO stays QC_APPROVED",
                extra={"wo_id": str(wo_id), "error": str(exc)},
                exc_info=True,
            )

            # Restore WO status to QC_APPROVED in case it was partially modified
            wo.status = WorkOrderStatus.QC_APPROVED.value

            # Send fg_receipt_failed notification to Finance (non-blocking best effort)
            try:
                await self._notifications.create_notification(
                    tenant_id=tenant_id,
                    notification_type=NOTIFICATION_TYPE_FG_RECEIPT_FAILED,
                    title=f"FG Receipt Failed — WO {wo.wo_number}",
                    message=(
                        f"Finished goods receipt for Work Order {wo.wo_number} failed. "
                        "The work order remains in QC_APPROVED. "
                        f"Error: {exc!s}"
                    ),
                    reference_id=str(wo_id),
                    reference_type="work_order",
                )
            except Exception as notify_exc:  # pragma: no cover
                logger.warning(
                    "FGReceiveCommandHandler: failed to emit fg_receipt_failed notification",
                    extra={"notify_error": str(notify_exc)},
                )

            raise  # re-raise so the outer transaction rolls back

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    async def _resolve_fg_material(self, wo: WorkOrderModel) -> uuid.UUID:
        """Resolve the work order's product reference to its materials row ID."""
        from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel

        # Direct material reference
        material = (
            await self._session.execute(
                select(MaterialModel).where(
                    MaterialModel.id == wo.product_id,
                    MaterialModel.tenant_id == wo.tenant_id,
                    MaterialModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if material is not None:
            return material.id

        # Indirect via product variant
        variant = (
            await self._session.execute(
                select(ItemVariantModel).where(
                    ItemVariantModel.id == wo.product_id,
                    ItemVariantModel.tenant_id == wo.tenant_id,
                    ItemVariantModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if variant is None:
            raise ValueError(f"FG product {wo.product_id} not found for WO {wo.id}")

        if getattr(variant, "material_id", None):
            return variant.material_id

        material = (
            await self._session.execute(
                select(MaterialModel).where(
                    MaterialModel.tenant_id == wo.tenant_id,
                    MaterialModel.code == variant.code,
                    MaterialModel.material_type == "finished",
                    MaterialModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if material is None:
            raise ValueError(
                f"Product {wo.product_id} has no finished-good material row"
            )
        return material.id

    async def _allocate_to_so_line(
        self,
        wo: WorkOrderModel,
        fg_material_id: uuid.UUID,
        net_qty: Decimal,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Increment allocated_quantity on the linked SO line.

        Returns True when a line was found and updated.
        """
        from datetime import datetime, timezone

        stmt = select(SalesOrderLineModel).where(
            SalesOrderLineModel.sales_order_id == wo.sales_order_id,
        )
        lines = (await self._session.execute(stmt)).scalars().all()

        target = None
        for line in lines:
            if line.work_order_id == wo.id:
                target = line
                break
            if line.product_id == wo.product_id:
                target = line
                break

        if target is None:
            return False

        already_allocated = Decimal(str(target.allocated_quantity or 0))
        ordered_qty = Decimal(str(target.quantity or 0))
        needed = ordered_qty - already_allocated
        if needed <= 0:
            return False  # already fully allocated

        add_qty = min(net_qty, needed)
        new_allocated = already_allocated + add_qty
        target.allocated_quantity = float(new_allocated)
        target.updated_at = datetime.now(timezone.utc)

        # Update line_status
        if new_allocated >= ordered_qty:
            target.line_status = "ALLOCATED"
        else:
            target.line_status = "PARTIAL"

        logger.info(
            "FGReceiveCommandHandler: SO line allocated_quantity updated",
            extra={
                "line_id": str(target.id),
                "add_qty": float(add_qty),
                "new_allocated": float(new_allocated),
            },
        )
        return True
