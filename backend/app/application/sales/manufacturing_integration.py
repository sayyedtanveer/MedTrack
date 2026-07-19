"""Integration bridge connecting Sales to Manufacturing for automatic Work Order creation."""
import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from backend.app.application.manufacturing.commands.work_order_commands import CreateWorkOrderCommand, ReleaseWorkOrderCommand
from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
from backend.app.domain.shared.domain_event import DomainEvent
from dataclasses import dataclass
from sqlalchemy import func, select


@dataclass(frozen=True)
class WorkOrderReleasedEvent(DomainEvent):
    wo_id: str
    wo_number: str
    product: str

logger = logging.getLogger(__name__)


class SalesManufacturingIntegrationService:
    """
    Implements the manufacturing_service interface required by InventoryReservationService.
    Bridges the Sales domain and Manufacturing domain.
    """

    def __init__(self, wo_handler: WorkOrderHandler, uow=None, created_by: Optional[UUID] = None):
        self.wo_handler = wo_handler
        self.event_dispatcher = None
        self._uow = uow
        self.created_by = created_by
        if uow:
            self.wo_handler.with_uow(uow)

    def with_event_dispatcher(self, dispatcher):
        """Fluent helper to attach an EventDispatcher for immediate notifications."""
        self.event_dispatcher = dispatcher
        return self

    async def create_work_order(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
        quantity: Decimal,
        uom_id: UUID,
        due_date,
        sales_order_id: UUID,
        sales_order_line_id: UUID,
    ) -> Optional[UUID]:
        """
        Creates a Work Order to fulfill a Sales shortage.
        Assumes product_id is an item_variant with a default BOM.
        """
        try:
            bom, work_order_product_id = await self._resolve_active_bom(
                tenant_id=tenant_id,
                product_id=product_id,
                product_type=product_type,
            )

            if not bom:
                logger.warning(f"No active BOM found for product {product_id}. Cannot auto-create Work Order.")
                return None

            # Calculate start date as due_date - 7 days (simple heuristic for now)
            start_date = due_date - timedelta(days=7)
            actor_id = await self._resolve_actor_id(tenant_id)

            cmd = CreateWorkOrderCommand(
                tenant_id=tenant_id,
                product_id=work_order_product_id,
                bom_id=bom.id,
                planned_quantity=quantity,
                start_date=start_date,
                due_date=due_date,
                priority="HIGH",  # Shortages are high priority
                sales_order_id=sales_order_id,
                sales_order_line_id=sales_order_line_id,
                created_by=actor_id,
                notes=f"Auto-generated for Sales shortage."
            )
            wo_id = await self.wo_handler.handle_create(cmd)

            # Immediately release the WO so production can start and materials can be reserved
            try:
                await self.wo_handler.handle_release(ReleaseWorkOrderCommand(tenant_id=tenant_id, work_order_id=wo_id))
            except Exception:
                # Non-fatal: if release fails, still return the created WO id
                logger.exception("Failed to auto-release WO %s", wo_id)

            # Build and publish a lightweight domain event if dispatcher is available
            if self.event_dispatcher is not None:
                try:
                    # Fetch WO number for notification
                    from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
                    from sqlalchemy import select

                    stmt = select(WorkOrderModel).where(WorkOrderModel.id == wo_id).limit(1)
                    res = await self.wo_handler._session.execute(stmt)
                    wo_model = res.scalar_one_or_none()
                    wo_number = getattr(wo_model, "wo_number", "") if wo_model else ""

                    event = WorkOrderReleasedEvent(
                        aggregate_id=wo_id,
                        tenant_id=tenant_id,
                        event_type="work_order.released",
                        wo_id=str(wo_id),
                        wo_number=wo_number,
                        product=str(product_id),
                    )
                    await self.event_dispatcher.dispatch(event)
                except Exception:
                    logger.exception("Failed to publish work order.released event for WO %s", wo_id)

            logger.info(f"Successfully auto-created Work Order {wo_id} for Sales shortage.")
            return wo_id

        except Exception as e:
            logger.error(f"Auto Work Order creation failed for product {product_id}: {str(e)}")
            return None

    async def _resolve_active_bom(
        self,
        *,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
    ):
        """Resolve the active BOM for a sales product using current schema first."""
        session = self.wo_handler._session
        from backend.app.infrastructure.persistence.models.bom_model import BOMModel
        from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel

        variant_id = await self._resolve_variant_id_for_product(
            tenant_id=tenant_id,
            product_id=product_id,
            product_type=product_type,
        )
        if variant_id is None:
            return None, product_id

        stmt = (
            select(BOMModel)
            .where(
                BOMModel.tenant_id == tenant_id,
                BOMModel.variant_id == variant_id,
                BOMModel.is_active.is_(True),
                BOMModel.is_deleted.is_(False),
            )
            .order_by(BOMModel.updated_at.desc(), BOMModel.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        bom = result.scalar_one_or_none()
        if bom is not None:
            return bom, variant_id

        variant = (
            await session.execute(
                select(ItemVariantModel).where(
                    ItemVariantModel.id == variant_id,
                    ItemVariantModel.tenant_id == tenant_id,
                    ItemVariantModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if variant is None or variant.template_id is None:
            return None, variant_id

        template_bom_result = await session.execute(
            select(BOMModel)
            .where(
                BOMModel.tenant_id == tenant_id,
                BOMModel.template_id == variant.template_id,
                BOMModel.is_active.is_(True),
                BOMModel.is_deleted.is_(False),
            )
            .order_by(BOMModel.updated_at.desc(), BOMModel.created_at.desc())
            .limit(1)
        )
        return template_bom_result.scalar_one_or_none(), variant_id

    async def _resolve_variant_id_for_product(
        self,
        *,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
    ) -> Optional[UUID]:
        """Resolve the variant that should drive BOM/work-order execution."""
        session = self.wo_handler._session
        from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
        from backend.app.infrastructure.persistence.models.material_model import MaterialModel

        if str(product_type).lower() == "variant":
            variant = (
                await session.execute(
                    select(ItemVariantModel.id).where(
                        ItemVariantModel.id == product_id,
                        ItemVariantModel.tenant_id == tenant_id,
                        ItemVariantModel.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if variant is not None:
                return variant

        material = (
            await session.execute(
                select(MaterialModel).where(
                    MaterialModel.id == product_id,
                    MaterialModel.tenant_id == tenant_id,
                    MaterialModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if material is None:
            return None

        variant = (
            await session.execute(
                select(ItemVariantModel.id).where(
                    ItemVariantModel.tenant_id == tenant_id,
                    ItemVariantModel.code == material.code,
                    ItemVariantModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        return variant

    async def _resolve_actor_id(self, tenant_id: UUID) -> UUID:
        if self.created_by:
            return self.created_by

        from backend.app.infrastructure.persistence.models.user_model import UserModel

        session = self.wo_handler._session
        actor_id = (
            await session.execute(
                select(UserModel.id)
                .where(
                    UserModel.tenant_id == tenant_id,
                    UserModel.is_active.is_(True),
                    UserModel.is_deleted.is_(False),
                )
                .order_by(UserModel.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return actor_id or UUID(int=0)

    async def _create_shortage_requests_and_purchase_orders(
        self,
        *,
        tenant_id: UUID,
        work_order_id: UUID,
        required_by: date,
        created_by: UUID,
    ) -> None:
        """Create material requests and supplier POs for WO raw-material shortages."""
        from backend.app.application.supply_chain.po_number_service import PONumberService
        from backend.app.infrastructure.persistence.models.material_model import MaterialModel
        from backend.app.infrastructure.persistence.models.material_request_model import MaterialRequestModel
        from backend.app.infrastructure.persistence.models.purchase_order_model import (
            PurchaseOrderLineModel,
            PurchaseOrderModel,
        )
        from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderMaterialModel

        session = self.wo_handler._session
        material_rows = (
            await session.execute(
                select(WorkOrderMaterialModel, MaterialModel)
                .join(MaterialModel, MaterialModel.id == WorkOrderMaterialModel.material_id)
                .where(
                    WorkOrderMaterialModel.work_order_id == work_order_id,
                    MaterialModel.tenant_id == tenant_id,
                    MaterialModel.is_deleted.is_(False),
                )
            )
        ).all()

        if not material_rows:
            return

        po_number_service = PONumberService(session)
        for requirement, material in material_rows:
            required_qty = Decimal(str(requirement.required_quantity))
            available_qty = max(
                Decimal("0"),
                Decimal(str(material.current_stock or 0)) - Decimal(str(material.reserved_stock or 0)),
            )
            incoming_qty = await self._open_po_quantity(tenant_id, material.id)
            shortage_qty = required_qty - available_qty - incoming_qty

            if shortage_qty <= 0:
                continue

            existing_request = (
                await session.execute(
                    select(MaterialRequestModel).where(
                        MaterialRequestModel.tenant_id == tenant_id,
                        MaterialRequestModel.item_id == material.id,
                        MaterialRequestModel.item_type == "material",
                        MaterialRequestModel.source_ref_type == "work_order",
                        MaterialRequestModel.source_ref_id == work_order_id,
                        MaterialRequestModel.status == "open",
                        MaterialRequestModel.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()

            if existing_request:
                existing_required = Decimal(str(existing_request.required_quantity))
                if shortage_qty > existing_required:
                    existing_request.required_quantity = float(shortage_qty)
                    existing_request.required_by = required_by
                continue

            material_request = MaterialRequestModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                item_id=material.id,
                item_type="material",
                required_quantity=float(shortage_qty),
                fulfilled_quantity=0,
                required_by=required_by,
                status="open",
                source_ref_type="work_order",
                source_ref_id=work_order_id,
            )
            session.add(material_request)

            supplier = await self._choose_supplier(tenant_id, material.id)
            if supplier is None:
                logger.warning(
                    "WO %s has raw-material shortage for %s but no active supplier exists.",
                    work_order_id,
                    material.id,
                )
                continue

            unit_price = Decimal(str(material.current_cost or 0))
            line_total = shortage_qty * unit_price
            po_number = await po_number_service.generate(tenant_id)
            po = PurchaseOrderModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                po_number=po_number,
                supplier_id=supplier.id,
                order_date=date.today(),
                expected_delivery=required_by,
                status="sent",
                total_amount=float(line_total),
                notes=f"Auto-created for WO {work_order_id} raw-material shortage.",
                created_by=created_by,
            )
            session.add(po)
            await session.flush()
            session.add(
                PurchaseOrderLineModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    purchase_order_id=po.id,
                    material_id=material.id,
                    quantity=float(shortage_qty),
                    received_quantity=0,
                    unit_price=float(unit_price),
                    line_total=float(line_total),
                )
            )

    async def _open_po_quantity(self, tenant_id: UUID, material_id: UUID) -> Decimal:
        from backend.app.infrastructure.persistence.models.purchase_order_model import (
            PurchaseOrderLineModel,
            PurchaseOrderModel,
        )

        result = await self.wo_handler._session.execute(
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

    async def _choose_supplier(self, tenant_id: UUID, material_id: UUID):
        from backend.app.infrastructure.persistence.models.supplier_model import (
            SupplierModel,
            SupplierPriceHistoryModel,
        )

        preferred = (
            await self.wo_handler._session.execute(
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

        return (
            await self.wo_handler._session.execute(
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
