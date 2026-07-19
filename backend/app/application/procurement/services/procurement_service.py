"""
Procurement Recovery Service — Full procurement loop from shortage to material availability.

This service implements the procurement recovery loop (Requirements 17.1–17.8, 29.2, 29.3):
1. Auto-creation of Purchase Requisitions when WO enters MATERIAL_PENDING
   (shortage_quantity = required - available per BOM line) — handled by WorkflowOrchestrationService.on_work_order_released
2. PR approval → auto-PO creation linked to original requisition
3. GRN + incoming QC → inventory update → auto-reserve for pending WO → transition WO to MATERIAL_RESERVED
   — triggered via WorkflowOrchestrationService.on_goods_received
4. Incoming QC failure → notification to procurement
5. PR rejection → notification to planner
"""
from __future__ import annotations

import uuid
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.infrastructure.persistence.models.purchase_requisition_model import PurchaseRequisitionModel
from backend.app.infrastructure.persistence.models.purchase_order_model import (
    PurchaseOrderModel,
    PurchaseOrderLineModel,
)
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.grn_model import GoodsReceiptNoteModel, GRNLineModel
from backend.app.application.notifications.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ProcurementService:
    """
    Service for managing the procurement recovery loop.

    Coordinates:
    - Purchase Requisition approval/rejection
    - Auto-PO creation on PR approval
    - GRN incoming QC pass/fail handling
    - Notification dispatch for procurement events
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.notification_service = NotificationService(session)

    # ─── PR Approval → Auto-PO Creation (Req 17.3) ──────────────────────────

    async def approve_requisition(
        self,
        tenant_id: uuid.UUID,
        requisition_id: uuid.UUID,
        approved_by: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Approve a Purchase Requisition and automatically create a Purchase Order.

        Requirements 17.3:
        - When a PR is approved, auto-create a PO for the approved materials
        - Link the PO back to the original requisition
        - Set PO status to SENT_TO_SUPPLIER (i.e. 'sent' in domain terms)

        Returns dict with PR and PO details.
        """
        # Fetch the PR
        stmt = select(PurchaseRequisitionModel).where(
            and_(
                PurchaseRequisitionModel.id == requisition_id,
                PurchaseRequisitionModel.tenant_id == tenant_id,
                PurchaseRequisitionModel.is_deleted.is_(False),
            )
        )
        pr = (await self.session.execute(stmt)).scalar_one_or_none()
        if pr is None:
            raise ValueError(f"Purchase Requisition {requisition_id} not found")

        if pr.status != "PENDING_APPROVAL":
            raise ValueError(
                f"Cannot approve requisition in status '{pr.status}'. "
                f"Only PENDING_APPROVAL requisitions can be approved."
            )

        # Update PR status to APPROVED
        pr.status = "APPROVED"
        pr.approved_by = approved_by
        pr.updated_at = datetime.now(timezone.utc)

        # Find preferred supplier for the material
        material = (await self.session.execute(
            select(MaterialModel).where(
                and_(
                    MaterialModel.id == pr.material_id,
                    MaterialModel.tenant_id == tenant_id,
                )
            )
        )).scalar_one_or_none()

        supplier_id = None
        if material and hasattr(material, "preferred_supplier_id"):
            supplier_id = material.preferred_supplier_id

        if supplier_id is None:
            # Fallback: try to find any supplier from supplier_price_history
            from sqlalchemy import text
            result = await self.session.execute(
                text("""
                    SELECT supplier_id FROM supplier_price_history
                    WHERE tenant_id = :tid AND material_id = :mid
                    ORDER BY effective_from DESC
                    LIMIT 1
                """),
                {"tid": str(tenant_id), "mid": str(pr.material_id)},
            )
            row = result.first()
            if row:
                supplier_id = row[0] if isinstance(row[0], uuid.UUID) else uuid.UUID(str(row[0]))

        if supplier_id is None:
            # If still no supplier, find the first active supplier for this tenant
            from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
            supplier_result = await self.session.execute(
                select(SupplierModel.id).where(
                    and_(
                        SupplierModel.tenant_id == tenant_id,
                        SupplierModel.is_active.is_(True),
                        SupplierModel.is_deleted.is_(False),
                    )
                ).limit(1)
            )
            supplier_row = supplier_result.scalar_one_or_none()
            if supplier_row:
                supplier_id = supplier_row
            else:
                raise ValueError(
                    f"No supplier found for material {pr.material_id}. "
                    "Cannot create Purchase Order without a supplier."
                )

        # Create Purchase Order (Req 17.3: auto-PO on PR approval)
        po_number = f"PO-{uuid.uuid4().hex[:8].upper()}"
        shortage_qty = Decimal(str(pr.shortage_quantity))

        po = PurchaseOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            po_number=po_number,
            supplier_id=supplier_id,
            order_date=date.today(),
            expected_delivery=None,  # To be set by procurement team
            status="sent",  # SENT_TO_SUPPLIER per Req 17.3
            total_amount=0,  # Will be updated when supplier provides pricing
            notes=f"Auto-created from Purchase Requisition {pr.requisition_number}",
            created_by=approved_by,
        )
        self.session.add(po)
        await self.session.flush()

        # Create PO line for the material
        po_line = PurchaseOrderLineModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            purchase_order_id=po.id,
            material_id=pr.material_id,
            quantity=float(shortage_qty),
            received_quantity=0,
            unit_price=0,  # To be confirmed by supplier
            line_total=0,
        )
        self.session.add(po_line)

        # Link the PO back to the PR and update status to PO_CREATED
        pr.linked_po_id = po.id
        pr.status = "PO_CREATED"
        pr.updated_at = datetime.now(timezone.utc)

        await self.session.flush()

        logger.info(
            "PR approved and PO created",
            extra={
                "tenant_id": str(tenant_id),
                "requisition_id": str(requisition_id),
                "po_id": str(po.id),
                "po_number": po_number,
                "material_id": str(pr.material_id),
                "shortage_quantity": float(shortage_qty),
            },
        )

        return {
            "requisition_id": str(requisition_id),
            "requisition_number": pr.requisition_number,
            "status": pr.status,
            "purchase_order_id": str(po.id),
            "po_number": po_number,
            "supplier_id": str(supplier_id),
            "material_id": str(pr.material_id),
            "quantity": float(shortage_qty),
            "message": "Purchase Requisition approved and Purchase Order created",
        }

    # ─── PR Rejection → Notification (Req 17.8) ─────────────────────────────

    async def reject_requisition(
        self,
        tenant_id: uuid.UUID,
        requisition_id: uuid.UUID,
        rejected_by: uuid.UUID,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reject a Purchase Requisition and notify the planner.

        Requirement 17.8:
        - If a purchase requisition is rejected during approval, create a
          notification of type "requisition_rejected" for users with the
          planner role, including the work order number and material details.
        - The work order SHALL remain in MATERIAL_PENDING status.
        """
        stmt = select(PurchaseRequisitionModel).where(
            and_(
                PurchaseRequisitionModel.id == requisition_id,
                PurchaseRequisitionModel.tenant_id == tenant_id,
                PurchaseRequisitionModel.is_deleted.is_(False),
            )
        )
        pr = (await self.session.execute(stmt)).scalar_one_or_none()
        if pr is None:
            raise ValueError(f"Purchase Requisition {requisition_id} not found")

        if pr.status != "PENDING_APPROVAL":
            raise ValueError(
                f"Cannot reject requisition in status '{pr.status}'. "
                f"Only PENDING_APPROVAL requisitions can be rejected."
            )

        # Update PR status to REJECTED
        pr.status = "REJECTED"
        pr.approved_by = rejected_by  # Track who rejected
        pr.updated_at = datetime.now(timezone.utc)

        await self.session.flush()

        # Send notification to planner (Req 17.8)
        await self.notification_service.notify_requisition_rejected(
            tenant_id=tenant_id,
            requisition_id=requisition_id,
            requisition_number=pr.requisition_number,
        )

        logger.info(
            "PR rejected and planner notified",
            extra={
                "tenant_id": str(tenant_id),
                "requisition_id": str(requisition_id),
                "requisition_number": pr.requisition_number,
                "reason": reason,
            },
        )

        return {
            "requisition_id": str(requisition_id),
            "requisition_number": pr.requisition_number,
            "status": "REJECTED",
            "reason": reason,
            "message": "Purchase Requisition rejected. Planner notified.",
        }

    # ─── GRN Incoming QC Pass → Trigger on_goods_received (Req 17.4, 17.5, 17.6) ─

    async def handle_incoming_qc_passed(
        self,
        tenant_id: uuid.UUID,
        grn_id: uuid.UUID,
        approved_by: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Handle incoming QC pass for received goods.

        Requirements 17.4, 17.5, 17.6:
        - When incoming QC is approved, update material inventory with received quantity
        - Mark GRN as QC_PASSED (inspected status)
        - Trigger on_goods_received() for each line to auto-reserve for pending WOs
          and transition WOs from MATERIAL_PENDING to MATERIAL_RESERVED

        This is called after GRN receipt + incoming QC inspection approval.
        """
        # Fetch GRN with lines
        stmt = (
            select(GoodsReceiptNoteModel)
            .options(selectinload(GoodsReceiptNoteModel.lines))
            .where(
                and_(
                    GoodsReceiptNoteModel.id == grn_id,
                    GoodsReceiptNoteModel.tenant_id == tenant_id,
                    GoodsReceiptNoteModel.is_deleted.is_(False),
                )
            )
        )
        grn = (await self.session.execute(stmt)).scalar_one_or_none()
        if grn is None:
            raise ValueError(f"GRN {grn_id} not found")

        if grn.status not in ("received", "in_inspection"):
            raise ValueError(
                f"GRN is in status '{grn.status}'. "
                f"Expected 'received' or 'in_inspection' for QC approval."
            )

        # Mark GRN as inspected (QC passed)
        grn.status = "inspected"
        grn.updated_by = approved_by
        grn.updated_at = datetime.now(timezone.utc)

        # Trigger on_goods_received for each accepted line
        from backend.app.application.manufacturing.services.workflow_orchestration_service import (
            WorkflowOrchestrationService,
        )
        orchestration = WorkflowOrchestrationService(self.session)

        transitioned_wos = []
        for line in grn.lines:
            if line.is_deleted:
                continue
            accepted_qty = Decimal(str(line.accepted_quantity or line.received_quantity))
            if accepted_qty <= 0:
                continue

            result = await orchestration.on_goods_received(
                tenant_id=tenant_id,
                purchase_order_id=grn.purchase_order_id,
                material_id=line.material_id,
                quantity=accepted_qty,
            )
            transitioned_wos.extend(result.get("wos_transitioned", []))

        await self.session.flush()

        logger.info(
            "Incoming QC passed — goods received into inventory and pending WOs checked",
            extra={
                "tenant_id": str(tenant_id),
                "grn_id": str(grn_id),
                "transitioned_wos": transitioned_wos,
            },
        )

        return {
            "grn_id": str(grn_id),
            "status": "inspected",
            "purchase_order_id": str(grn.purchase_order_id),
            "transitioned_wos": transitioned_wos,
            "message": "Incoming QC passed. Inventory updated and pending WOs checked.",
        }

    # ─── GRN Incoming QC Failure → Notification (Req 17.7) ───────────────────

    async def handle_incoming_qc_failed(
        self,
        tenant_id: uuid.UUID,
        grn_id: uuid.UUID,
        rejected_by: uuid.UUID,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle incoming QC failure for received goods.

        Requirement 17.7:
        - If incoming QC rejects the received materials, create a notification
          of type "incoming_qc_failed" for users with procurement permissions,
          including the PO number, material name, and rejected quantity.
        - The work order SHALL remain in MATERIAL_PENDING status.
        """
        # Fetch GRN with lines
        stmt = (
            select(GoodsReceiptNoteModel)
            .options(selectinload(GoodsReceiptNoteModel.lines))
            .where(
                and_(
                    GoodsReceiptNoteModel.id == grn_id,
                    GoodsReceiptNoteModel.tenant_id == tenant_id,
                    GoodsReceiptNoteModel.is_deleted.is_(False),
                )
            )
        )
        grn = (await self.session.execute(stmt)).scalar_one_or_none()
        if grn is None:
            raise ValueError(f"GRN {grn_id} not found")

        if grn.status not in ("received", "in_inspection"):
            raise ValueError(
                f"GRN is in status '{grn.status}'. "
                f"Expected 'received' or 'in_inspection' for QC rejection."
            )

        # Mark GRN as rejected
        grn.status = "rejected"
        grn.updated_by = rejected_by
        grn.updated_at = datetime.now(timezone.utc)

        # Update lines with rejection
        for line in grn.lines:
            if line.is_deleted:
                continue
            line.rejected_quantity = float(line.received_quantity)
            line.accepted_quantity = 0

        await self.session.flush()

        # Get material name(s) for notification
        material_names = []
        for line in grn.lines:
            if line.is_deleted:
                continue
            mat = (await self.session.execute(
                select(MaterialModel.name).where(MaterialModel.id == line.material_id)
            )).scalar_one_or_none()
            if mat:
                material_names.append(mat)

        material_name_str = ", ".join(material_names) if material_names else "Unknown material"

        # Send notification to procurement (Req 17.7)
        await self.notification_service.notify_incoming_qc_failed(
            tenant_id=tenant_id,
            purchase_order_id=grn.purchase_order_id,
            material_name=material_name_str,
        )

        logger.info(
            "Incoming QC failed — procurement notified",
            extra={
                "tenant_id": str(tenant_id),
                "grn_id": str(grn_id),
                "purchase_order_id": str(grn.purchase_order_id),
                "material_names": material_names,
                "reason": reason,
            },
        )

        return {
            "grn_id": str(grn_id),
            "status": "rejected",
            "purchase_order_id": str(grn.purchase_order_id),
            "material_names": material_names,
            "reason": reason,
            "message": "Incoming QC failed. Procurement team notified. WO remains in MATERIAL_PENDING.",
        }

    # ─── Helper: Get requisition details ─────────────────────────────────────

    async def get_requisition(
        self,
        tenant_id: uuid.UUID,
        requisition_id: uuid.UUID,
    ) -> Optional[PurchaseRequisitionModel]:
        """Get a purchase requisition by ID."""
        stmt = select(PurchaseRequisitionModel).where(
            and_(
                PurchaseRequisitionModel.id == requisition_id,
                PurchaseRequisitionModel.tenant_id == tenant_id,
                PurchaseRequisitionModel.is_deleted.is_(False),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_pending_requisitions(
        self,
        tenant_id: uuid.UUID,
    ) -> list[PurchaseRequisitionModel]:
        """Get all pending approval requisitions for a tenant."""
        stmt = select(PurchaseRequisitionModel).where(
            and_(
                PurchaseRequisitionModel.tenant_id == tenant_id,
                PurchaseRequisitionModel.status == "PENDING_APPROVAL",
                PurchaseRequisitionModel.is_deleted.is_(False),
            )
        ).order_by(PurchaseRequisitionModel.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())
