"""
WorkOrderHandler — orchestrates all Work Order use cases.

Data flow: API → Command → Handler → Domain Entity + Services → Repository → DB
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.manufacturing.commands.work_order_commands import (
    CreateWorkOrderCommand, ReleaseWorkOrderCommand, StartWorkOrderCommand,
    AllocateMaterialsCommand,
    IssueMaterialCommand, RecordProductionCommand,
    CompleteWorkOrderCommand, CloseWorkOrderCommand,
    StartJobCardCommand, CompleteJobCardCommand,
    QCApproveCommand, QCRejectCommand, QCSendToReworkCommand, FGReceiveCommand,
)
from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.application.manufacturing.services.wo_number_service import WONumberService
from backend.app.application.inventory.services.inventory_reservation_service import InventoryReservationService
from backend.app.application.manufacturing.services.workflow_orchestration_service import WorkflowOrchestrationService
from backend.app.domain.manufacturing.entities.work_order import WorkOrder, WorkOrderStatus, WorkOrderPriority
from backend.app.domain.manufacturing.exceptions import BOMNotFoundError
from backend.app.domain.manufacturing.events.work_order_events import (
    WorkOrderReleased, WorkOrderStarted, WorkOrderCompleted, WorkOrderClosed,
)
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderModel, WorkOrderMaterialModel, JobCardModel, ProductionRecordModel
)
from backend.app.infrastructure.persistence.models.bom_model import BOMModel

logger = logging.getLogger(__name__)


class WorkOrderHandler:
    def __init__(self, session: AsyncSession, uow=None):
        self._session = session
        self._uow = uow  # Optional: UnitOfWork for emitting domain events
        self._inventory = InventoryService(session)
        self._reservation = InventoryReservationService(session)
        self._wo_number = WONumberService(session)
        self._workflow = WorkflowOrchestrationService(session)

    def with_uow(self, uow):
        """Fluent setter for UnitOfWork (for event emission)."""
        self._uow = uow
        return self

    def _emit_event(self, event) -> None:
        """Emit a domain event via UnitOfWork if available."""
        if self._uow is not None:
            self._uow.register_events([event])

    # ── Create ──────────────────────────────────────────────────────────────────

    async def handle_create(self, cmd: CreateWorkOrderCommand) -> uuid.UUID:
        # 1. Load BOM with lines + operations
        bom_stmt = (
            select(BOMModel)
            .options(selectinload(BOMModel.lines), selectinload(BOMModel.operations))
            .where(BOMModel.id == cmd.bom_id, BOMModel.tenant_id == cmd.tenant_id, BOMModel.is_deleted.is_(False))
        )
        result = await self._session.execute(bom_stmt)
        bom = result.scalar_one_or_none()
        if not bom:
            raise BOMNotFoundError(f"BOM {cmd.bom_id} not found or inactive")

        # 1.5. Validate Product is active
        from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
        variant_stmt = select(ItemVariantModel.is_active).where(
            ItemVariantModel.id == cmd.product_id,
            ItemVariantModel.tenant_id == cmd.tenant_id,
            ItemVariantModel.is_deleted.is_(False)
        )
        variant_result = await self._session.execute(variant_stmt)
        is_active = variant_result.scalar_one_or_none()
        if is_active is None:
            raise ValueError(f"Product {cmd.product_id} not found")
        if not is_active:
            raise ValueError("Inactive products cannot be used to create Work Orders.")

        # 2. Generate WO number (atomic)
        wo_number = await self._wo_number.generate(cmd.tenant_id)

        # 3. Create WO model
        wo = WorkOrderModel(
            id=uuid.uuid4(),
            wo_number=wo_number,
            tenant_id=cmd.tenant_id,
            product_id=cmd.product_id,
            bom_id=cmd.bom_id,
            planned_quantity=float(cmd.planned_quantity),
            produced_quantity=0,
            scrap_quantity=0,
            status=WorkOrderStatus.PLANNED,
            priority=WorkOrderPriority[cmd.priority],
            start_date=cmd.start_date,
            due_date=cmd.due_date,
            sales_order_id=cmd.sales_order_id,
            sales_order_line_id=cmd.sales_order_line_id,
            notes=cmd.notes,
            created_by=cmd.created_by,
        )
        self._session.add(wo)
        await self._session.flush()  # get wo.id

        # 4. Snapshot BOM lines → work_order_materials
        for line in bom.lines:
            if line.material_id and not line.is_deleted:
                scrap_factor = Decimal(str(getattr(line, "scrap_percentage", 0) or 0)) / Decimal("100")
                required_qty = Decimal(str(line.quantity)) * cmd.planned_quantity * (
                    Decimal("1") + scrap_factor
                )
                mat = WorkOrderMaterialModel(
                    work_order_id=wo.id,
                    material_id=line.material_id,
                    unit_id=line.unit_id,
                    required_quantity=float(required_qty),
                    issued_quantity=0,
                )
                self._session.add(mat)

        # 5. Snapshot BOM operations → job_cards
        for op in sorted(bom.operations, key=lambda o: o.sequence):
            if not op.is_deleted:
                jc = JobCardModel(
                    work_order_id=wo.id,
                    operation_id=op.operation_id,
                    sequence=op.sequence,
                    status="PENDING",
                )
                self._session.add(jc)

        # Keep the freshly snapshotted materials visible for same-transaction release planning.
        await self._session.flush()

        # 6. Auto-trigger MRP to generate procurement suggestions
        await self._trigger_mrp(tenant_id=cmd.tenant_id)

        return wo.id

    # ── Release ─────────────────────────────────────────────────────────────────

    async def handle_release(self, cmd: ReleaseWorkOrderCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)
        entity.release()
        wo.status = entity.status.value
        wo.updated_at = datetime.now(timezone.utc)

        wo.status = WorkOrderStatus.MATERIAL_PENDING.value
        await self._workflow.on_work_order_released(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
        )

        # Emit event for dashboard notifications
        self._emit_event(WorkOrderReleased(
            aggregate_id=wo.id,
            tenant_id=cmd.tenant_id,
            event_type="work_order.released",
            wo_id=str(wo.id),
            wo_number=wo.wo_number,
            product=str(wo.product_id),
        ))

    async def handle_allocate_materials(self, cmd: AllocateMaterialsCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        if wo.status != WorkOrderStatus.MATERIAL_PENDING.value:
            from backend.app.domain.manufacturing.entities.work_order import InvalidStatusTransitionError
            raise InvalidStatusTransitionError(f"Cannot allocate materials for WO in status {wo.status}")
            
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderMaterialModel
        from backend.app.application.manufacturing.services.inventory_service import InventoryService
        from backend.app.application.inventory.services.inventory_reservation_service import InventoryReservationService
        
        stmt = select(WorkOrderMaterialModel).where(
            WorkOrderMaterialModel.work_order_id == wo.id
        )
        wo_materials = (await self._session.execute(stmt)).scalars().all()
        
        inventory_svc = InventoryService(self._session)
        reservation_svc = InventoryReservationService(self._session)
        
        all_reserved = True
        
        for wom in wo_materials:
            required_qty = Decimal(str(wom.required_quantity or 0))
            issued_qty = Decimal(str(wom.issued_quantity or 0))
            remaining = required_qty - issued_qty
            if remaining <= 0:
                continue
                
            already_reserved = await inventory_svc.get_existing_reservation_qty_for_wo(
                tenant_id=cmd.tenant_id,
                work_order_id=wo.id,
                material_id=wom.material_id,
            )
            need_to_reserve = max(Decimal("0"), remaining - already_reserved)
            
            if need_to_reserve > 0:
                _reserved, shortage, _ = await reservation_svc.reserve_for_work_order(
                    tenant_id=cmd.tenant_id,
                    work_order_id=wo.id,
                    material_id=wom.material_id,
                    required_quantity=need_to_reserve,
                    unit_id=wom.unit_id,
                    created_by=wo.created_by,
                )
                if shortage > 0:
                    all_reserved = False
        
        if all_reserved:
            wo.status = WorkOrderStatus.MATERIAL_RESERVED.value
            wo.updated_at = datetime.now(timezone.utc)
            self._session.add(wo)

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
                PurchaseOrderModel.status.in_(["draft", "sent", "acknowledged", "partial"]),
                PurchaseOrderModel.is_deleted.is_(False),
                PurchaseOrderLineModel.material_id == material_id,
                PurchaseOrderLineModel.is_deleted.is_(False),
            )
        )
        return Decimal(str(result.scalar_one() or 0))

    async def _trigger_mrp(self, tenant_id: uuid.UUID) -> None:
        """Auto-trigger MRP to generate procurement suggestions on WO creation."""
        try:
            from backend.app.application.supply_chain.mrp_service import MRPService
            mrp_service = MRPService(self._session)
            await mrp_service.run(tenant_id=tenant_id)
            logger.info(
                "MRP auto-triggered on WO creation",
                extra={"tenant_id": str(tenant_id)}
            )
        except Exception as e:
            # Log but don't fail WO creation if MRP fails
            logger.warning(
                f"MRP auto-trigger failed on WO creation: {e}",
                extra={"tenant_id": str(tenant_id)}
            )

    async def _choose_supplier_for_material(self, tenant_id: uuid.UUID, material_id: uuid.UUID):
        from backend.app.infrastructure.persistence.models.supplier_model import (
            SupplierModel,
            SupplierPriceHistoryModel,
        )

        preferred = (
            await self._session.execute(
                select(SupplierModel)
                .join(SupplierPriceHistoryModel, SupplierPriceHistoryModel.supplier_id == SupplierModel.id)
                .where(
                    SupplierModel.tenant_id == tenant_id,
                    SupplierModel.is_active.is_(True),
                    SupplierModel.is_deleted.is_(False),
                    SupplierPriceHistoryModel.tenant_id == tenant_id,
                    SupplierPriceHistoryModel.material_id == material_id,
                )
                .order_by(
                    SupplierPriceHistoryModel.effective_from.desc(),
                    SupplierPriceHistoryModel.created_at.desc(),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if preferred is not None:
            return preferred

        from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel

        return (
            await self._session.execute(
                select(SupplierModel)
                .where(
                    SupplierModel.tenant_id == tenant_id,
                    SupplierModel.is_active.is_(True),
                    SupplierModel.is_deleted.is_(False),
                )
                .order_by(SupplierModel.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()

    # ── Start ───────────────────────────────────────────────────────────────────

    async def handle_start(self, cmd: StartWorkOrderCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        
        # Guard: Ensure explicit Job Card start is used if Job Cards exist (Rule 4, 11)
        jc_stmt = select(func.count()).where(JobCardModel.work_order_id == wo.id)
        jc_count = await self._session.scalar(jc_stmt)
        if jc_count > 0:
            raise ValueError("Work Order has Job Cards. Use 'Start Job Card' to begin production.")

        entity = self._to_entity(wo)
        entity.start()
        wo.status = entity.status.value
        wo.updated_at = datetime.now(timezone.utc)

        # Transition to IN_PRODUCTION (from MATERIAL_ISSUED)
        wo.status = WorkOrderStatus.IN_PRODUCTION.value
        wo.updated_at = datetime.now(timezone.utc)

        # Emit event for dashboard notifications
        self._emit_event(WorkOrderStarted(
            aggregate_id=wo.id,
            tenant_id=cmd.tenant_id,
            event_type="work_order.started",
            wo_id=str(wo.id),
            wo_number=wo.wo_number,
        ))

    # ── Issue Material ───────────────────────────────────────────────────────────

    async def handle_issue_material(self, cmd: IssueMaterialCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)

        # Must be MATERIAL_RESERVED or MATERIAL_ISSUED (for partial issues)
        if entity.status not in (WorkOrderStatus.MATERIAL_RESERVED, WorkOrderStatus.MATERIAL_ISSUED):
            from backend.app.domain.manufacturing.entities.work_order import InvalidStatusTransitionError
            raise InvalidStatusTransitionError(
                f"Cannot issue material with WO in status {entity.status}"
            )

        old_status = wo.status
        await self._inventory.issue_material_for_wo(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            material_id=cmd.material_id,
            quantity=cmd.quantity,
            unit_id=cmd.unit_id,
            created_by=cmd.issued_by,
            transition_wo_status=True,
        )

        # If WO transitioned to MATERIAL_ISSUED, notify operator (Req 23.8, 27.2)
        if wo.status == WorkOrderStatus.MATERIAL_ISSUED.value and old_status != WorkOrderStatus.MATERIAL_ISSUED.value:
            try:
                await self._workflow.notification_service.create_notification(
                    tenant_id=cmd.tenant_id,
                    notification_type="material_issued",
                    title=f"Materials Issued - WO {wo.wo_number}",
                    message=f"All BOM materials have been issued for Work Order {wo.wo_number}. Production can begin.",
                    reference_id=str(cmd.work_order_id),
                    reference_type="work_order",
                )
                # Also notify operator to start production (action notification)
                await self._workflow.notification_service.create_notification(
                    tenant_id=cmd.tenant_id,
                    notification_type="start_production_action",
                    title=f"Action Required: Start Production - WO {wo.wo_number}",
                    message=f"All materials issued for Work Order {wo.wo_number}. Production can now begin.",
                    reference_id=str(cmd.work_order_id),
                    reference_type="work_order",
                )
            except Exception as e:
                logger.warning("Failed to send material_issued notification", extra={"error": str(e)})

    # ── Record Production ────────────────────────────────────────────────────────

    async def handle_record_production(self, cmd: RecordProductionCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)

        if wo.status not in (WorkOrderStatus.IN_PRODUCTION.value, WorkOrderStatus.REWORK.value):
            raise ValueError(f"Production cannot be recorded because Work Order is in status: {wo.status}")

        all_jcs_stmt = select(JobCardModel).where(JobCardModel.work_order_id == wo.id)
        all_jcs = (await self._session.execute(all_jcs_stmt)).scalars().all()
        jc_count = len(all_jcs)

        is_final_operation = True
        jc = None
        if jc_count > 0:
            if cmd.job_card_id is None:
                # Legacy escape hatch: if all job cards are DONE and no production was recorded, allow WO-level recording.
                if all(j.status == "DONE" for j in all_jcs) and (wo.produced_quantity or 0) <= 0:
                    jc = max(all_jcs, key=lambda x: x.sequence)
                    cmd.job_card_id = jc.id
                else:
                    raise ValueError("Production must be associated with a specific Job Card.")
            
            if jc is None:
                jc = next((j for j in all_jcs if j.id == cmd.job_card_id), None)
            if not jc:
                raise ValueError(f"Job Card {cmd.job_card_id} not found in this Work Order.")
            
            # Allow recording if IN_PROGRESS, or if it's the legacy escape hatch scenario (already DONE)
            if jc.status != "IN_PROGRESS" and not (all(j.status == "DONE" for j in all_jcs) and (wo.produced_quantity or 0) <= 0):
                raise ValueError("Production cannot be recorded because this operation has not been started or is already completed.")
                
            max_seq = max(j.sequence for j in all_jcs)
            if jc.sequence < max_seq:
                is_final_operation = False

        rec = ProductionRecordModel(
            work_order_id=wo.id,
            produced_quantity=float(cmd.produced_quantity),
            scrap_quantity=float(cmd.scrap_quantity),
            recorded_by=cmd.recorded_by,
            notes=cmd.notes,
        )
        self._session.add(rec)
        await self._session.flush()

        new_produced = Decimal(str(wo.produced_quantity))
        if is_final_operation:
            new_produced += cmd.produced_quantity

        new_scrap = Decimal(str(wo.scrap_quantity)) + cmd.scrap_quantity
        
        wo.produced_quantity = float(new_produced)
        wo.scrap_quantity = float(new_scrap)
        wo.updated_at = datetime.now(timezone.utc)

        resolved_operation_id = cmd.operation_id
        if cmd.job_card_id is not None:
            # We already fetched jc in validation above, but we fetch it again safely
            jc = await self._get_job_card(cmd.job_card_id, wo.id, cmd.tenant_id)
            if resolved_operation_id is None:
                resolved_operation_id = jc.operation_id
            jc.produced_quantity = float(Decimal(str(jc.produced_quantity or 0)) + cmd.produced_quantity)
            jc.scrap_quantity = float(Decimal(str(jc.scrap_quantity or 0)) + cmd.scrap_quantity)
            if cmd.notes:
                timestamp = datetime.now(timezone.utc).isoformat()
                note = f"[{timestamp}] {cmd.notes}"
                jc.operator_notes = f"{jc.operator_notes}\n{note}" if jc.operator_notes else note

        # Resolve the finished-goods material_id. Older schemas do not have an
        # item_variant_id column, so mirror product search: first try a material
        # with the variant UUID, then a finished material with the variant code.
        from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
        from backend.app.infrastructure.persistence.models.material_model import MaterialModel

        mat_stmt = select(MaterialModel).where(
            MaterialModel.id == wo.product_id,
            MaterialModel.tenant_id == wo.tenant_id,
            MaterialModel.is_deleted.is_(False),
        ).limit(1)
        mat_result = await self._session.execute(mat_stmt)
        fg_material = mat_result.scalar_one_or_none()

        if fg_material is None:
            variant_stmt = select(ItemVariantModel).where(
                ItemVariantModel.id == wo.product_id,
                ItemVariantModel.tenant_id == wo.tenant_id,
                ItemVariantModel.is_deleted.is_(False),
            ).limit(1)
            variant_result = await self._session.execute(variant_stmt)
            variant = variant_result.scalar_one_or_none()

            if variant is not None:
                if getattr(variant, "material_id", None):
                    mapped_stmt = select(MaterialModel).where(
                        MaterialModel.id == variant.material_id,
                        MaterialModel.tenant_id == wo.tenant_id,
                        MaterialModel.is_deleted.is_(False),
                    ).limit(1)
                    mapped_result = await self._session.execute(mapped_stmt)
                    fg_material = mapped_result.scalar_one_or_none()

                if fg_material is None:
                    code_stmt = select(MaterialModel).where(
                        MaterialModel.tenant_id == wo.tenant_id,
                        MaterialModel.code == variant.code,
                        MaterialModel.material_type == "finished",
                        MaterialModel.is_deleted.is_(False),
                    ).limit(1)
                    code_result = await self._session.execute(code_stmt)
                    fg_material = code_result.scalar_one_or_none()

        from backend.app.application.manufacturing.services.production_posting_service import (
            ProductionPostingService,
        )

        await ProductionPostingService(self._session).post_production_consumption(
            tenant_id=cmd.tenant_id,
            work_order_id=wo.id,
            produced_delta=cmd.produced_quantity,
            scrap_delta=cmd.scrap_quantity,
            production_record_id=rec.id,
            recorded_by=cmd.recorded_by,
            operation_id=resolved_operation_id,
        )
        # FG receipt occurs once on QC approval (WorkflowOrchestrationService.on_qc_approved)

    # ── Complete ─────────────────────────────────────────────────────────────────

    async def handle_complete(self, cmd: CompleteWorkOrderCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)
        
        from backend.app.domain.manufacturing.exceptions import MaterialNotIssuedError
        
        # The frontend calls /complete to Submit for QC
        if entity.status == WorkOrderStatus.IN_PRODUCTION:
            if wo.produced_quantity <= 0:
                raise MaterialNotIssuedError("Cannot submit for QC: no production has been recorded.")

            # Guard: Ensure all Job Cards are DONE (Rule 8, 10)
            jc_stmt = select(JobCardModel.status).where(JobCardModel.work_order_id == wo.id)
            jc_statuses = (await self._session.execute(jc_stmt)).scalars().all()
            if jc_statuses and any(status != "DONE" for status in jc_statuses):
                raise ValueError("Complete all manufacturing operations before sending this Work Order to Quality.")

            entity.submit_for_qc()
        else:
            entity.complete()  # raises MaterialNotIssuedError if produced_qty == 0
            
        wo.status = entity.status.value
        wo.updated_at = datetime.now(timezone.utc)

        # Emit event for dashboard notifications
        self._emit_event(WorkOrderCompleted(
            aggregate_id=wo.id,
            tenant_id=cmd.tenant_id,
            event_type="work_order.completed",
            wo_id=str(wo.id),
            wo_number=wo.wo_number,
            produced_qty=float(wo.produced_quantity),
        ))

    async def _reserve_produced_goods_for_sales(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order: WorkOrderModel,
        finished_material_id: uuid.UUID,
        produced_quantity: Decimal,
        recorded_by: uuid.UUID,
    ) -> None:
        """Allocate newly produced finished goods back to the linked sales line."""
        if not work_order.sales_order_line_id:
            return

        from backend.app.infrastructure.persistence.models.sales_models import (
            SalesOrderLineModel,
            SalesOrderModel,
        )

        line_result = await self._session.execute(
            select(SalesOrderLineModel).where(
                SalesOrderLineModel.id == work_order.sales_order_line_id,
            )
        )
        line = line_result.scalar_one_or_none()
        if line is None:
            return

        backorder_qty = Decimal(str(line.backorder_quantity or 0))
        reserve_qty = min(produced_quantity, backorder_qty)
        if reserve_qty <= 0:
            return

        await self._inventory.reserve_sales_stock(
            tenant_id=tenant_id,
            material_id=finished_material_id,
            quantity=reserve_qty,
            sales_order_line_id=line.id,
            unit_id=line.uom_id,
            created_by=recorded_by,
        )

        line.allocated_quantity = float(Decimal(str(line.allocated_quantity or 0)) + reserve_qty)
        line.backorder_quantity = float(max(Decimal("0"), backorder_qty - reserve_qty))
        line.status = "allocated" if Decimal(str(line.backorder_quantity or 0)) <= 0 else "backorder"
        line.updated_at = datetime.now(timezone.utc)

        order = await self._session.get(SalesOrderModel, line.sales_order_id)
        if order is None or order.tenant_id != tenant_id:
            return

        lines = (
            await self._session.execute(
                select(SalesOrderLineModel).where(SalesOrderLineModel.sales_order_id == order.id)
            )
        ).scalars().all()
        all_allocated = bool(lines) and all(
            Decimal(str(order_line.allocated_quantity or 0)) >= Decimal(str(order_line.quantity or 0))
            for order_line in lines
        )
        if all_allocated:
            order.status = "READY"
        elif order.status in ("CONFIRMED", "PROCESSING"):
            order.status = "PRODUCTION"
        order.updated_at = datetime.now(timezone.utc)

    # ── Close ────────────────────────────────────────────────────────────────────

    async def handle_close(self, cmd: CloseWorkOrderCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)
        entity.close()
        wo.status = entity.status.value
        wo.updated_at = datetime.now(timezone.utc)

        # Emit event for dashboard notifications
        self._emit_event(WorkOrderClosed(
            aggregate_id=wo.id,
            tenant_id=cmd.tenant_id,
            event_type="work_order.closed",
            wo_id=str(wo.id),
            wo_number=wo.wo_number,
        ))

    # ── QC Operations ─────────────────────────────────────────────────────────────

    async def handle_qc_approve(self, cmd: QCApproveCommand) -> None:
        """Approve QC inspection and transition to FG_RECEIVED with automatic FG stock increase."""
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)

        if entity.status != WorkOrderStatus.QC_PENDING:
            from backend.app.domain.manufacturing.entities.work_order import InvalidStatusTransitionError
            raise InvalidStatusTransitionError(
                f"Cannot approve QC: WO must be in QC_PENDING status, current: {entity.status}"
            )

        wo.status = WorkOrderStatus.QC_APPROVED.value
        wo.updated_at = datetime.now(timezone.utc)

        # Automatically increase FG stock after QC approval
        # This is done via WorkflowOrchestrationService to ensure consistency
        from backend.app.application.manufacturing.services.workflow_orchestration_service import WorkflowOrchestrationService
        workflow_service = WorkflowOrchestrationService(self._session)
        await workflow_service.on_qc_approved(
            tenant_id=cmd.tenant_id,
            work_order_id=cmd.work_order_id,
            received_by=cmd.approved_by,
        )

    async def handle_qc_reject(self, cmd: QCRejectCommand) -> None:
        """Reject QC inspection and transition to REWORK or REJECTED."""
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)

        if entity.status != WorkOrderStatus.QC_PENDING:
            from backend.app.domain.manufacturing.entities.work_order import InvalidStatusTransitionError
            raise InvalidStatusTransitionError(
                f"Cannot reject QC: WO must be in QC_PENDING status, current: {entity.status}"
            )

        if cmd.send_to_rework:
            wo.status = WorkOrderStatus.REWORK.value
        else:
            wo.status = WorkOrderStatus.REJECTED.value
        wo.updated_at = datetime.now(timezone.utc)

        # Notify production supervisor about QC failure (Req 23.3)
        try:
            await self._workflow.notification_service.create_notification(
                tenant_id=cmd.tenant_id,
                notification_type="qc_failed",
                title=f"QC Failed - WO {wo.wo_number}",
                message=f"Quality inspection failed for Work Order {wo.wo_number}. Reason: {getattr(cmd, 'reason', 'N/A')}",
                reference_id=str(cmd.work_order_id),
                reference_type="work_order",
            )
        except Exception as e:
            logger.warning("Failed to send qc_failed notification", extra={"error": str(e)})

    async def handle_qc_send_to_rework(self, cmd: QCSendToReworkCommand) -> None:
        """Send rejected WO to rework."""
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)

        if entity.status != WorkOrderStatus.REJECTED:
            from backend.app.domain.manufacturing.entities.work_order import InvalidStatusTransitionError
            raise InvalidStatusTransitionError(
                f"Cannot send to rework: WO must be in REJECTED status, current: {entity.status}"
            )

        wo.status = WorkOrderStatus.REWORK.value
        wo.updated_at = datetime.now(timezone.utc)

    async def handle_fg_receive(self, cmd: FGReceiveCommand) -> None:
        """Receive finished goods after QC approval and transition to COMPLETED."""
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        entity = self._to_entity(wo)

        entity.require_qc_approved()

        wo.status = WorkOrderStatus.FG_RECEIVED.value
        wo.updated_at = datetime.now(timezone.utc)

        # Call workflow orchestration to update sales order to READY_FOR_DISPATCH
        try:
            await self._workflow.on_work_order_completed(
                tenant_id=cmd.tenant_id,
                work_order_id=cmd.work_order_id,
            )
            logger.info(
                "Workflow orchestration called after FG receive",
                extra={"work_order_id": str(cmd.work_order_id)}
            )
        except Exception as e:
            logger.warning(
                "Failed to call workflow orchestration after FG receive",
                extra={"work_order_id": str(cmd.work_order_id), "error": str(e)}
            )

    # ── Job Card ─────────────────────────────────────────────────────────────────

    async def handle_start_job_card(self, cmd: StartJobCardCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        
        if wo.status not in ("MATERIAL_ISSUED", "IN_PRODUCTION", "REWORK"):
            raise ValueError(f"Cannot start Job Card: Work Order materials must be issued first. Current status: {wo.status}")

        if wo.status == "MATERIAL_ISSUED":
            wo.status = "IN_PRODUCTION"
            wo.updated_at = datetime.now(timezone.utc)

        all_jcs_stmt = select(JobCardModel).where(JobCardModel.work_order_id == wo.id).order_by(JobCardModel.sequence)
        all_jcs = (await self._session.execute(all_jcs_stmt)).scalars().all()

        target_jc = next((jc for jc in all_jcs if jc.id == cmd.job_card_id), None)
        if not target_jc:
            raise ValueError(f"Job Card {cmd.job_card_id} not found")

        if target_jc.status != "PENDING":
            raise ValueError(f"Job card is already {target_jc.status}")

        for jc in all_jcs:
            if jc.sequence < target_jc.sequence and jc.status != "DONE":
                raise ValueError(f"Complete OP-{jc.sequence} before starting OP-{target_jc.sequence}.")

        target_jc.status = "IN_PROGRESS"
        target_jc.started_at = datetime.now(timezone.utc)
        if cmd.assigned_to:
            target_jc.assigned_to = cmd.assigned_to

    async def handle_complete_job_card(self, cmd: CompleteJobCardCommand) -> None:
        wo = await self._get_wo(cmd.work_order_id, cmd.tenant_id)
        if wo.status not in ("IN_PRODUCTION", "QC_PENDING", "QC_APPROVED", "QC_REJECTED", "COMPLETED", "CLOSED"):
            wo.status = "IN_PRODUCTION"
            wo.updated_at = datetime.now(timezone.utc)

        stmt = select(JobCardModel).where(
            JobCardModel.id == cmd.job_card_id, JobCardModel.work_order_id == cmd.work_order_id
        )
        result = await self._session.execute(stmt)
        jc = result.scalar_one_or_none()
        if not jc:
            raise ValueError(f"Job Card {cmd.job_card_id} not found")

        if jc.status != "IN_PROGRESS":
            raise ValueError(f"Job card must be IN_PROGRESS to complete, current: {jc.status}")
        jc.status = "DONE"
        jc.completed_at = datetime.now(timezone.utc)
        if cmd.remarks:
            jc.remarks = cmd.remarks
        for attr, value in {
            "produced_quantity": cmd.produced_quantity,
            "scrap_quantity": cmd.scrap_quantity,
            "rework_quantity": cmd.rework_quantity,
            "rejected_quantity": cmd.rejected_quantity,
        }.items():
            if value is not None:
                setattr(jc, attr, float(value))
        if cmd.operator_notes:
            timestamp = datetime.now(timezone.utc).isoformat()
            note = f"[{timestamp}] {cmd.operator_notes}"
            jc.operator_notes = f"{jc.operator_notes}\n{note}" if jc.operator_notes else note

    # ── Helpers ──────────────────────────────────────────────────────────────────

    async def _get_wo(self, work_order_id: uuid.UUID, tenant_id: uuid.UUID) -> WorkOrderModel:
        # SELECT FOR UPDATE: prevents concurrent status-transition race conditions
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        wo = result.scalar_one_or_none()
        if not wo:
            raise ValueError(f"Work Order {work_order_id} not found")
        return wo

    async def _get_job_card(self, jc_id: uuid.UUID, wo_id: uuid.UUID, tenant_id: uuid.UUID) -> JobCardModel:
        # Validate tenant via WO ownership
        await self._get_wo(wo_id, tenant_id)
        stmt = select(JobCardModel).where(
            JobCardModel.id == jc_id, JobCardModel.work_order_id == wo_id
        )
        result = await self._session.execute(stmt)
        jc = result.scalar_one_or_none()
        if not jc:
            raise ValueError(f"Job Card {jc_id} not found")
        return jc

    def _to_entity(self, model: WorkOrderModel) -> WorkOrder:
        return WorkOrder(
            id=model.id,
            tenant_id=model.tenant_id,
            wo_number=model.wo_number,
            product_id=model.product_id,
            bom_id=model.bom_id,
            planned_quantity=Decimal(str(model.planned_quantity)),
            produced_quantity=Decimal(str(model.produced_quantity)),
            scrap_quantity=Decimal(str(model.scrap_quantity)),
            start_date=model.start_date,
            due_date=model.due_date,
            status=WorkOrderStatus(model.status),
            priority=WorkOrderPriority(model.priority),
            sales_order_id=model.sales_order_id,
            sales_order_line_id=model.sales_order_line_id,
            notes=model.notes,
            created_by=model.created_by,
        )
