"""Sales Order Repository."""

from datetime import date
from typing import Type
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.app.domain.sales.entities.sales_order import SalesOrder
from backend.app.domain.sales.entities.sales_order_line import SalesOrderLine
from backend.app.domain.sales.value_objects import LineStatus, OrderStatus
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderLineModel,
    SalesOrderModel,
)
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class SalesOrderRepository(BaseRepository):
    """Repository for SalesOrder aggregate root."""

    def _model_class(self) -> Type[SalesOrderModel]:
        """Return the SQLAlchemy model class."""
        return SalesOrderModel

    def _to_entity(self, model: SalesOrderModel) -> SalesOrder:
        """Convert ORM model → domain entity."""
        if not model:
            return None
        lines = [
            SalesOrderLine(
                id=line.id,
                order_id=model.id,
                product_id=line.product_id,
                product_type=line.product_type,
                uom_id=line.uom_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rate=line.tax_rate,
                status=line.status,
                allocated_quantity=line.allocated_quantity,
                shipped_quantity=line.shipped_quantity,
                backorder_quantity=line.backorder_quantity,
                tax_amount=line.tax_amount,
                line_total=line.line_total,
                work_order_id=line.work_order_id,
                notes=line.notes,
                shortfall_quantity=getattr(line, "shortfall_quantity", 0) or 0,
                production_required=getattr(line, "production_required", False) or False,
                created_at=line.created_at,
                updated_at=line.updated_at,
            )
            for line in (model.lines or [])
        ]
        return SalesOrder(
            id=model.id,
            tenant_id=model.tenant_id,
            order_number=model.order_number,
            client_id=model.client_id,
            order_date=model.order_date,
            delivery_date=model.delivery_date,
            status=model.status,
            payment_status=model.payment_status,
            subtotal=model.subtotal,
            discount_amount=model.discount_amount,
            tax_amount=model.tax_amount,
            grand_total=model.grand_total,
            notes=model.notes,
            created_by=model.created_by,
            approver_id=model.approver_id,
            submitted_at=model.submitted_at,
            approved_at=model.approved_at,
            rejected_at=model.rejected_at,
            approval_notes=model.approval_notes,
            lines=lines,
            is_active=model.is_active,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def _enrich_orders(
        self,
        entities: list[SalesOrder],
        models: list[SalesOrderModel],
    ) -> list[SalesOrder]:
        if not entities:
            return entities

        variant_ids: set[UUID] = set()
        material_ids: set[UUID] = set()
        uom_ids: set[UUID] = set()

        for entity in entities:
            for line in entity.lines:
                product_type = str(getattr(line, "product_type", "")).lower()
                if product_type == "variant":
                    variant_ids.add(line.product_id)
                else:
                    material_ids.add(line.product_id)
                uom_ids.add(line.uom_id)

        variant_map = {}
        material_map = {}
        uom_map = {}

        if variant_ids:
            result = await self._session.execute(
                select(ItemVariantModel).where(ItemVariantModel.id.in_(variant_ids))
            )
            variant_map = {row.id: row for row in result.scalars().all()}

        all_material_ids = material_ids | variant_ids
        if all_material_ids:
            result = await self._session.execute(
                select(MaterialModel).where(
                    MaterialModel.id.in_(all_material_ids),
                    MaterialModel.is_deleted.is_(False),
                )
            )
            material_map = {row.id: row for row in result.scalars().all()}

        if uom_ids:
            result = await self._session.execute(
                select(UnitOfMeasureModel).where(UnitOfMeasureModel.id.in_(uom_ids))
            )
            uom_map = {row.id: row for row in result.scalars().all()}

        model_by_id = {model.id: model for model in models}

        for entity in entities:
            model = model_by_id.get(entity.id)
            if model and model.client is not None:
                entity.client_name = model.client.name
                entity.client_code = model.client.code

            summary_parts: list[str] = []
            for index, line in enumerate(entity.lines):
                product_type = str(getattr(line, "product_type", "")).lower()
                preferred = variant_map.get(line.product_id) if product_type == "variant" else material_map.get(line.product_id)
                fallback = material_map.get(line.product_id) if preferred is None else preferred
                product = preferred or fallback

                if product is not None:
                    line.product_name = product.name
                    line.product_code = product.code
                else:
                    line.product_name = f"Product {str(line.product_id)[:8]}"
                    line.product_code = None

                uom = uom_map.get(line.uom_id)
                line.uom_code = uom.code if uom else None
                line.uom_name = uom.name if uom else None

                if index < 2:
                    summary_parts.append(f"{line.product_name} x{line.quantity.normalize()}")

            if len(entity.lines) > 2:
                summary_parts.append(f"+{len(entity.lines) - 2} more")
            entity.item_summary = ", ".join(summary_parts) if summary_parts else "No line items"

        return entities

    def _to_model(self, entity: SalesOrder) -> SalesOrderModel:
        """Convert domain entity → ORM model."""
        return SalesOrderModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            order_number=str(entity.order_number),
            client_id=entity.client_id,
            order_date=entity.order_date.isoformat(),
            delivery_date=entity.delivery_date.isoformat(),
            status=entity.status.name,
            payment_status=entity.payment_status.name,
            subtotal=entity.subtotal,
            discount_amount=entity.discount_amount,
            tax_amount=entity.tax_amount,
            grand_total=entity.grand_total,
            notes=entity.notes,
            created_by=entity.created_by,
            approver_id=entity.approver_id,
            submitted_at=entity.submitted_at,
            approved_at=entity.approved_at,
            rejected_at=entity.rejected_at,
            approval_notes=entity.approval_notes,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            lines=[
                SalesOrderLineModel(
                    id=line.id,
                    sales_order_id=entity.id,
                    product_id=line.product_id,
                    product_type=line.product_type,
                    uom_id=line.uom_id,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    tax_rate=line.tax_rate,
                    tax_amount=line.tax_amount,
                    line_total=line.line_total,
                    allocated_quantity=line.allocated_quantity,
                    shipped_quantity=line.shipped_quantity,
                    backorder_quantity=line.backorder_quantity,
                    work_order_id=line.work_order_id,
                    status=line.status.value if isinstance(line.status, LineStatus) else str(line.status),
                    notes=line.notes,
                    shortfall_quantity=float(getattr(line, "shortfall_quantity", 0) or 0),
                    production_required=bool(getattr(line, "production_required", False)),
                    created_at=line.created_at,
                    updated_at=line.updated_at,
                )
                for line in entity.lines
            ],
        )

    async def get_by_id(
        self,
        id: UUID,
        tenant_id: UUID,
    ) -> SalesOrder | None:
        """Get a sales order aggregate with its line collection loaded."""
        stmt = (
            select(self._model_class())
            .options(
                selectinload(SalesOrderModel.lines),
                selectinload(SalesOrderModel.client),
            )
            .where(
                self._model_class().id == id,
                self._model_class().tenant_id == tenant_id,
                self._model_class().is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        entity = self._to_entity(model)
        enriched = await self._enrich_orders([entity], [model])
        return enriched[0]

    async def get_next_sequence(self, tenant_id: UUID, date: date) -> int:
        """Return the next SO sequence for the tenant and order date."""
        prefix = f"SO-{date.strftime('%Y%m%d')}-"
        stmt = (
            select(self._model_class().order_number)
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().order_number.like(f"{prefix}%"),
                self._model_class().is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        max_sequence = 0
        for order_number in result.scalars().all():
            try:
                max_sequence = max(max_sequence, int(str(order_number).split("-")[-1]))
            except (TypeError, ValueError):
                continue
        return max_sequence + 1

    async def get_by_order_number(
        self,
        tenant_id: UUID,
        order_number: str,
    ) -> SalesOrder | None:
        """
        Get order by order number (unique per tenant).
        
        Args:
            tenant_id: Tenant ID
            order_number: Order number string
            
        Returns:
            SalesOrder or None if not found
        """
        stmt = (
            select(self._model_class())
            .options(
                selectinload(SalesOrderModel.lines),
                selectinload(SalesOrderModel.client),
            )
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().order_number == order_number,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        entity = self._to_entity(model)
        enriched = await self._enrich_orders([entity], [model])
        return enriched[0]

    async def find_by_client(
        self,
        tenant_id: UUID,
        client_id: UUID,
        status: OrderStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SalesOrder]:
        """
        Find orders for a client.
        
        Args:
            tenant_id: Tenant ID
            client_id: Client ID
            status: Filter by status (optional)
            limit: Result limit
            offset: Result offset
            
        Returns:
            List of sales orders
        """
        stmt = (
            select(self._model_class())
            .options(
                selectinload(SalesOrderModel.lines),
                selectinload(SalesOrderModel.client),
            )
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().client_id == client_id,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
        )
        
        if status:
            status_value = status.name if isinstance(status, OrderStatus) else str(status).upper()
            stmt = stmt.where(self._model_class().status == status_value)
        
        stmt = stmt.order_by(self._model_class().order_date.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        entities = [self._to_entity(m) for m in models]
        return await self._enrich_orders(entities, list(models))

    async def find_all(
        self,
        tenant_id: UUID,
        status: OrderStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SalesOrder]:
        """
        Find all orders for a tenant.
        
        Args:
            tenant_id: Tenant ID
            status: Filter by status (optional)
            limit: Result limit
            offset: Result offset
            
        Returns:
            List of sales orders
        """
        stmt = (
            select(self._model_class())
            .options(
                selectinload(SalesOrderModel.lines),
                selectinload(SalesOrderModel.client),
            )
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
        )
        
        if status:
            status_value = status.name if isinstance(status, OrderStatus) else str(status).upper()
            stmt = stmt.where(self._model_class().status == status_value)
        
        stmt = stmt.order_by(self._model_class().order_date.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        entities = [self._to_entity(m) for m in models]
        return await self._enrich_orders(entities, list(models))

    async def find_by_date_range(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        status: OrderStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SalesOrder]:
        """
        Find orders within date range.
        
        Args:
            tenant_id: Tenant ID
            start_date: Start date
            end_date: End date
            status: Filter by status (optional)
            limit: Result limit
            offset: Result offset
            
        Returns:
            List of sales orders
        """
        stmt = (
            select(self._model_class())
            .options(
                selectinload(SalesOrderModel.lines),
                selectinload(SalesOrderModel.client),
            )
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().order_date >= str(start_date),
                self._model_class().order_date <= str(end_date),
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
        )
        
        if status:
            status_value = status.name if isinstance(status, OrderStatus) else str(status).upper()
            stmt = stmt.where(self._model_class().status == status_value)
        
        stmt = stmt.order_by(self._model_class().order_date.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        entities = [self._to_entity(m) for m in models]
        return await self._enrich_orders(entities, list(models))

    async def find_by_delivery_date_range(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        statuses: list[OrderStatus] | None = None,
    ) -> list[SalesOrder]:
        """
        Find orders due for delivery within date range.
        
        Args:
            tenant_id: Tenant ID
            start_date: Start delivery date
            end_date: End delivery date
            statuses: List of statuses to filter (optional)
            
        Returns:
            List of sales orders
        """
        stmt = (
            select(self._model_class())
            .options(
                selectinload(SalesOrderModel.lines),
                selectinload(SalesOrderModel.client),
            )
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().delivery_date >= str(start_date),
                self._model_class().delivery_date <= str(end_date),
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
        )
        
        if statuses:
            status_values = [s.name if isinstance(s, OrderStatus) else str(s).upper() for s in statuses]
            stmt = stmt.where(self._model_class().status.in_(status_values))
        
        stmt = stmt.order_by(self._model_class().delivery_date.asc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        entities = [self._to_entity(m) for m in models]
        return await self._enrich_orders(entities, list(models))

    async def count_by_status(
        self,
        tenant_id: UUID,
    ) -> dict[str, int]:
        """
        Count orders by status.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Dictionary mapping status to count
        """
        stmt = (
            select(
                self._model_class().status,
                func.count(self._model_class().id).label("count")
            )
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
            .group_by(self._model_class().status)
        )
        
        result = await self._session.execute(stmt)
        rows = result.all()
        return {status: count for status, count in rows}

    async def find_pending_confirmation(
        self,
        tenant_id: UUID,
        limit: int = 50,
    ) -> list[SalesOrder]:
        """
        Find orders in DRAFT status waiting for confirmation.
        
        Args:
            tenant_id: Tenant ID
            limit: Result limit
            
        Returns:
            List of draft orders
        """
        stmt = (
            select(self._model_class())
            .options(
                selectinload(SalesOrderModel.lines),
                selectinload(SalesOrderModel.client),
            )
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().status == OrderStatus.DRAFT.name,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
            .order_by(self._model_class().created_at.asc())
            .limit(limit)
        )
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        entities = [self._to_entity(m) for m in models]
        return await self._enrich_orders(entities, list(models))


