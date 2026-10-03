from decimal import Decimal
import uuid
from typing import List, Optional, cast
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.infrastructure.persistence.models.subcontract_model import SubcontractOrderModel, SubcontractOrderLineModel
from backend.app.infrastructure.persistence.models.bom_model import BOMModel
from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.domain.subcontracting.entities.subcontract_order import SubcontractOrderStatus

class SubcontractOrderService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._inv_service = InventoryService(session)

    async def create_order_with_bom(
        self,
        tenant_id: uuid.UUID,
        order_number: str,
        supplier_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: Decimal,
        bom_id: Optional[uuid.UUID],
        source_location_id: uuid.UUID,
        vendor_location_id: uuid.UUID,
        expected_return_date: Optional[datetime],
        created_by: uuid.UUID,
    ) -> SubcontractOrderModel:
        # Load BOM
        if bom_id is None:
            raise ValueError("bom_id is required")
        bom = await self._session.get(BOMModel, bom_id)
        if not bom or bom.tenant_id != tenant_id:
            raise ValueError("BOM not found")

        # Create Order
        order = SubcontractOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            order_number=order_number,
            supplier_id=supplier_id,
            product_id=product_id,
            product_type="variant",
            quantity=float(quantity),
            source_location_id=source_location_id,
            vendor_location_id=vendor_location_id,
            expected_return_date=expected_return_date,
            status=SubcontractOrderStatus.DRAFT.value,
            created_by=created_by,
        )
        self._session.add(order)

        # Create Component Lines (Snapshot)
        # Handle lazy loaded lines or query them
        for line in await bom.awaitable_attrs.lines:
            req_qty = Decimal(str(line.quantity)) * quantity
            sol = SubcontractOrderLineModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                subcontract_order_id=order.id,
                material_id=cast(uuid.UUID, line.material_id or line.template_id or line.variant_id),  # Simplification for demo
                required_quantity=float(req_qty),
                issued_quantity=0.0,
                returned_quantity=0.0,
                scrap_quantity=0.0,
            )
            self._session.add(sol)

        await self._session.flush()
        return order

    async def approve_order(self, tenant_id: uuid.UUID, order_id: uuid.UUID) -> None:
        order = await self._session.get(SubcontractOrderModel, order_id)
        if not order:
            raise ValueError("Order not found")
        if order.status != SubcontractOrderStatus.DRAFT.value:
            raise ValueError("Can only approve draft orders")
        order.status = SubcontractOrderStatus.APPROVED.value
        await self._session.flush()

    async def issue_batch(
        self,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        line_id: uuid.UUID,
        batch_number: str,
        quantity: Decimal,
        created_by: uuid.UUID,
    ) -> None:
        order = await self._session.get(SubcontractOrderModel, order_id)
        if not order:
            raise ValueError("Order not found")
        if order.status not in (SubcontractOrderStatus.APPROVED.value, SubcontractOrderStatus.MATERIALS_ISSUED.value):
            raise ValueError("Invalid order status for issue")
        
        line = await self._session.get(SubcontractOrderLineModel, line_id)
        if not line:
            raise ValueError("Line not found")
        if line.subcontract_order_id != order.id:
            raise ValueError("Line mismatch")

        # 1. Remove from source warehouse using InventoryService's batch mechanism
        batch = await self._inv_service.remove_batch_stock(
            tenant_id=tenant_id,
            material_id=line.material_id,
            batch_number=batch_number,
            quantity=quantity,
            unit_id=None,
            created_by=created_by,
            from_location_id=order.source_location_id,
            reference_id=order.id,
            remarks=f"Subcontract Issue {order.order_number}",
        )
        # Update trans type (workaround for specific enum if needed)
        # 2. Add to vendor location
        await self._inv_service.add_batch_stock(
            tenant_id=tenant_id,
            material_id=line.material_id,
            batch_number=batch_number,
            quantity=quantity,
            unit_id=None,
            created_by=created_by,
            to_location_id=order.vendor_location_id,
            reference_id=order.id,
            remarks=f"Subcontract Vendor WIP {order.order_number}",
        )
        
        line.issued_quantity += float(quantity)
        order.status = SubcontractOrderStatus.MATERIALS_ISSUED.value
        await self._session.flush()

    async def receive_output(
        self,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        output_batch_number: str,
        quantity: Decimal,
        created_by: uuid.UUID,
    ) -> None:
        order = await self._session.get(SubcontractOrderModel, order_id)
        if not order:
            raise ValueError("Order not found")
        if order.status not in (SubcontractOrderStatus.MATERIALS_ISSUED.value, SubcontractOrderStatus.PARTIALLY_RECEIVED.value):
            raise ValueError("Invalid order status for receipt")

        # Add output batch stock to source location
        await self._inv_service.add_batch_stock(
            tenant_id=tenant_id,
            material_id=order.product_id,
            batch_number=output_batch_number,
            quantity=quantity,
            unit_id=None,
            created_by=created_by,
            to_location_id=order.source_location_id,
            reference_id=order.id,
            remarks=f"Subcontract Receipt {order.order_number}",
        )

        # Determine completion
        # For simplicity, assuming if total received is >= planned qty, it's completed.
        # Here we just mark completed.
        order.status = SubcontractOrderStatus.COMPLETED.value
        await self._session.flush()
