"""
InventoryService — canonical gateway for ALL stock mutations.

Rules:
  - ALL stock changes MUST go through this service.
  - Direct SQL stock updates or repository-level mutations are PROHIBITED.
  - SELECT FOR UPDATE is used for concurrency safety.
  - Negative stock is prevented.
  - Every mutation inserts an InventoryTransaction audit record.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.batch_model import BatchModel
from backend.app.infrastructure.persistence.models.inventory_reservation_model import InventoryReservationModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.inventory_management_models import StockLedgerModel
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel
from backend.app.domain.manufacturing.exceptions import InsufficientStockError
from backend.app.domain.inventory.entities.material_shortage import MaterialShortage, ShortageStatus

# Locations usable for internal manufacturing issue (not subcontractor / quarantine)
_INTERNAL_ISSUE_LOCATION_TYPES: frozenset[str] = frozenset(
    {"warehouse", "zone", "rack", "bin", "production"}
)

_BLOCKED_BATCH_STATUSES: frozenset[str] = frozenset(
    {
        "EXPIRED",
        "QUARANTINED",
        "QC_HOLD",
        "PICKING_HOLD",
        "DAMAGE_HOLD",
        "INVESTIGATION_HOLD",
    }
)

_ST_AVAILABLE = "available"
_ST_PENDING = "pending_inspection"
_ST_QUARANTINE = "quarantine"


class InventoryService:
    """Single authoritative point for stock reservation, issuance, and receipt."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── Internal helper ────────────────────────────────────────────────────────

    async def _lock_material(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> MaterialModel:
        """Acquire a row-level lock (SELECT FOR UPDATE) on the material."""
        stmt = (
            select(MaterialModel)
            .where(MaterialModel.id == material_id, MaterialModel.tenant_id == tenant_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Material {material_id} not found for tenant {tenant_id}")
        return model

    async def _lock_work_order(self, tenant_id: uuid.UUID, work_order_id: uuid.UUID) -> None:
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel

        stmt = (
            select(WorkOrderModel.id)
            .where(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        if (await self._session.execute(stmt)).scalar_one_or_none() is None:
            raise ValueError(f"Work order {work_order_id} not found")

    async def _log_transaction(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        transaction_type: str,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        reference_type: str,
        reference_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        remarks: Optional[str] = None,
        batch_id: Optional[uuid.UUID] = None,
        from_location_id: Optional[uuid.UUID] = None,
        to_location_id: Optional[uuid.UUID] = None,
    ) -> InventoryTransactionModel:
        tx = InventoryTransactionModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type=transaction_type,
            quantity=float(quantity),
            unit_id=unit_id,
            batch_id=batch_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            reference_type=reference_type,
            reference_id=reference_id,
            remarks=remarks,
            created_by=created_by,
        )
        self._session.add(tx)
        return tx

    async def _log_ledger(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        location_id: Optional[uuid.UUID],
        transaction_type: str,
        quantity_change: Decimal,
        unit_cost: Optional[float] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Append an immutable ledger row with running balance.

        Running balance = current sum of all StockLevelModel buckets for this material.
        This is called *after* bucket mutations so the balance is already updated.
        """
        running_balance = await self._sum_all_stock_levels(tenant_id, material_id)
        total_value: Optional[float] = None
        if unit_cost is not None:
            total_value = float(abs(quantity_change) * Decimal(str(unit_cost)))
        entry = StockLedgerModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=location_id,
            transaction_date=datetime.now(timezone.utc),
            transaction_type=transaction_type,
            quantity_change=float(quantity_change),
            running_balance=float(running_balance),
            unit_cost=unit_cost,
            total_value=total_value,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        self._session.add(entry)

    async def _default_warehouse_location(self, tenant_id: uuid.UUID) -> Optional[uuid.UUID]:
        stmt = (
            select(LocationModel.id)
            .where(
                LocationModel.tenant_id == tenant_id,
                LocationModel.type == "warehouse",
                LocationModel.is_deleted.is_(False),
                LocationModel.is_active.is_(True),
            )
            .limit(1)
        )
        r = await self._session.execute(stmt)
        row = r.scalar_one_or_none()
        return row

    async def _sum_available_internal(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(StockLevelModel.quantity), 0))
            .join(LocationModel, LocationModel.id == StockLevelModel.location_id)
            .where(
                StockLevelModel.tenant_id == tenant_id,
                StockLevelModel.material_id == material_id,
                StockLevelModel.stock_status == _ST_AVAILABLE,
                StockLevelModel.is_deleted.is_(False),
                LocationModel.type.in_(_INTERNAL_ISSUE_LOCATION_TYPES),
                LocationModel.is_deleted.is_(False),
            )
        )
        r = await self._session.execute(stmt)
        return Decimal(str(r.scalar_one()))

    async def _sum_all_stock_levels(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(StockLevelModel.quantity), 0))
            .where(
                StockLevelModel.tenant_id == tenant_id,
                StockLevelModel.material_id == material_id,
                StockLevelModel.is_deleted.is_(False),
            )
        )
        r = await self._session.execute(stmt)
        return Decimal(str(r.scalar_one()))

    async def _has_stock_levels(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> bool:
        stmt = select(StockLevelModel.id).where(
            StockLevelModel.tenant_id == tenant_id,
            StockLevelModel.material_id == material_id,
            StockLevelModel.is_deleted.is_(False),
        ).limit(1)
        r = await self._session.execute(stmt)
        return r.scalar_one_or_none() is not None

    async def _sync_material_total_from_buckets(self, material: MaterialModel) -> None:
        # The app-wide async session disables autoflush; flush bucket changes before
        # reading aggregate stock so material.current_stock stays authoritative.
        await self._session.flush()
        total = await self._sum_all_stock_levels(material.tenant_id, material.id)
        material.current_stock = float(total)

    async def _available_for_locked_material(self, material: MaterialModel) -> Decimal:
        """Return available stock after subtracting tenant-wide reservations."""
        if await self._has_stock_levels(material.tenant_id, material.id):
            on_hand = await self._sum_available_internal(material.tenant_id, material.id)
        else:
            on_hand = Decimal(str(material.current_stock))
        reserved = Decimal(str(material.reserved_stock))
        return max(Decimal("0"), on_hand - reserved)

    async def _lock_stock_level(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        location_id: uuid.UUID,
        stock_status: str,
    ) -> StockLevelModel:
        stmt = (
            select(StockLevelModel)
            .where(
                StockLevelModel.tenant_id == tenant_id,
                StockLevelModel.material_id == material_id,
                StockLevelModel.location_id == location_id,
                StockLevelModel.stock_status == stock_status,
                StockLevelModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        r = await self._session.execute(stmt)
        row = r.scalar_one_or_none()
        if row is None:
            row = StockLevelModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                material_id=material_id,
                location_id=location_id,
                stock_status=stock_status,
                quantity=0,
            )
            self._session.add(row)
            await self._session.flush()
            stmt2 = (
                select(StockLevelModel)
                .where(StockLevelModel.id == row.id)
                .with_for_update()
            )
            r2 = await self._session.execute(stmt2)
            row = r2.scalar_one()
        return row

    async def _deduct_available_internal(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
    ) -> Decimal:
        """Deduct from available buckets at internal locations. Returns amount still to deduct."""
        remaining = quantity
        stmt = (
            select(StockLevelModel)
            .join(LocationModel, LocationModel.id == StockLevelModel.location_id)
            .where(
                StockLevelModel.tenant_id == tenant_id,
                StockLevelModel.material_id == material_id,
                StockLevelModel.stock_status == _ST_AVAILABLE,
                StockLevelModel.is_deleted.is_(False),
                LocationModel.type.in_(_INTERNAL_ISSUE_LOCATION_TYPES),
                LocationModel.is_deleted.is_(False),
            )
            .with_for_update(of=StockLevelModel)
        )
        r = await self._session.execute(stmt)
        rows = r.scalars().all()
        for sl in rows:
            if remaining <= 0:
                break
            avail = Decimal(str(sl.quantity))
            take = min(avail, remaining)
            sl.quantity = float(avail - take)
            remaining -= take
        return remaining

    async def _add_bucket_quantity(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        location_id: uuid.UUID,
        stock_status: str,
        quantity: Decimal,
    ) -> None:
        sl = await self._lock_stock_level(tenant_id, material_id, location_id, stock_status)
        sl.quantity = float(Decimal(str(sl.quantity)) + quantity)

    async def _deduct_bucket_quantity(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        location_id: uuid.UUID,
        stock_status: str,
        quantity: Decimal,
    ) -> Decimal:
        sl = await self._lock_stock_level(tenant_id, material_id, location_id, stock_status)
        available = Decimal(str(sl.quantity))
        deducted = min(available, quantity)
        sl.quantity = float(available - deducted)
        return deducted

    async def _move_bucket_quantity(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        from_location_id: uuid.UUID,
        to_location_id: uuid.UUID,
        from_status: str,
        to_status: str,
        quantity: Decimal,
    ) -> None:
        src = await self._lock_stock_level(tenant_id, material_id, from_location_id, from_status)
        dst = await self._lock_stock_level(tenant_id, material_id, to_location_id, to_status)
        avail = Decimal(str(src.quantity))
        if quantity > avail:
            raise InsufficientStockError(
                f"Cannot move {quantity} from {from_status}: only {avail} on hand"
            )
        src.quantity = float(avail - quantity)
        dst.quantity = float(Decimal(str(dst.quantity)) + quantity)

    async def _lock_batch(self, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> BatchModel:
        stmt = (
            select(BatchModel)
            .where(
                BatchModel.id == batch_id,
                BatchModel.tenant_id == tenant_id,
                BatchModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        batch = result.scalar_one_or_none()
        if batch is None:
            raise ValueError(f"Batch {batch_id} not found for tenant {tenant_id}")
        return batch

    async def _lock_batch_by_number(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        batch_number: str,
    ) -> Optional[BatchModel]:
        stmt = (
            select(BatchModel)
            .where(
                BatchModel.tenant_id == tenant_id,
                BatchModel.material_id == material_id,
                BatchModel.batch_number == batch_number,
                BatchModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _candidate_batches(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        batch_id: Optional[uuid.UUID] = None,
    ) -> list[BatchModel]:
        stmt = select(BatchModel).where(
            BatchModel.tenant_id == tenant_id,
            BatchModel.material_id == material_id,
            BatchModel.is_deleted.is_(False),
            func.upper(BatchModel.status).notin_(_BLOCKED_BATCH_STATUSES),
        )
        if batch_id is not None:
            stmt = stmt.where(BatchModel.id == batch_id)
        stmt = stmt.order_by(
            BatchModel.expiry_date.is_(None),
            BatchModel.expiry_date.asc(),
            BatchModel.location_id.is_(None),
            BatchModel.location_id.asc(),
            BatchModel.created_at.asc(),
            BatchModel.id.asc(),
        ).with_for_update()
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _allocate_batch_quantities(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        batch_id: Optional[uuid.UUID] = None,
    ) -> list[tuple[BatchModel, Decimal]]:
        allocations: list[tuple[BatchModel, Decimal]] = []
        remaining = quantity
        for batch in await self._candidate_batches(
            tenant_id=tenant_id,
            material_id=material_id,
            batch_id=batch_id,
        ):
            free_qty = Decimal(str(batch.remaining_quantity if batch.remaining_quantity is not None else batch.quantity))
            free_qty -= Decimal(str(batch.reserved_quantity or 0))
            if free_qty <= 0:
                continue
            take = min(free_qty, remaining)
            allocations.append((batch, take))
            remaining -= take
            if remaining <= 0:
                break
        if remaining > 0:
            raise InsufficientStockError(
                f"Insufficient batch stock for {material_id}: short by {remaining}"
            )
        return allocations

    def _update_batch_status(self, batch: BatchModel) -> None:
        status = str(batch.status or "").upper()
        if status in _BLOCKED_BATCH_STATUSES:
            return

        remaining = Decimal(str(batch.remaining_quantity if batch.remaining_quantity is not None else batch.quantity))
        reserved = Decimal(str(batch.reserved_quantity or 0))
        consumed = Decimal(str(batch.consumed_quantity or 0))
        returned = Decimal(str(batch.returned_quantity or 0))

        if remaining <= 0:
            batch.status = "FULLY_CONSUMED"
        elif consumed > 0:
            batch.status = "PARTIALLY_CONSUMED"
        elif reserved > 0:
            batch.status = "RESERVED"
        elif returned > 0:
            batch.status = "RETURNED"
        else:
            batch.status = "AVAILABLE"
        batch.updated_at = datetime.now(timezone.utc)

    # ── Public API ──────────────────────────────────────────────────────────────

    async def add_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        to_location_id: Optional[uuid.UUID] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
        batch_id: Optional[uuid.UUID] = None,
        transaction_type: str = "in",
        reference_type: str = "manual",
    ) -> None:
        """Canonical manual stock increase."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        model = await self._lock_material(tenant_id, material_id)
        loc = to_location_id or await self._default_warehouse_location(tenant_id)
        if loc:
            await self._add_bucket_quantity(
                tenant_id=tenant_id,
                material_id=material_id,
                location_id=loc,
                stock_status=_ST_AVAILABLE,
                quantity=quantity,
            )
            await self._sync_material_total_from_buckets(model)
        else:
            model.current_stock = float(Decimal(str(model.current_stock)) + quantity)

        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type=transaction_type,
            quantity=quantity,
            unit_id=unit_id,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=created_by,
            remarks=remarks,
            batch_id=batch_id,
            to_location_id=loc,
        )
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            transaction_type=transaction_type.upper(),
            quantity_change=quantity,
            reference_type=reference_type,
            reference_id=reference_id,
        )

    async def remove_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        from_location_id: Optional[uuid.UUID] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
        batch_id: Optional[uuid.UUID] = None,
        transaction_type: str = "out",
        reference_type: str = "manual",
    ) -> None:
        """Canonical manual stock decrease."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        model = await self._lock_material(tenant_id, material_id)

        loc = from_location_id
        if await self._has_stock_levels(tenant_id, material_id):
            if loc is not None:
                deducted = await self._deduct_bucket_quantity(
                    tenant_id=tenant_id,
                    material_id=material_id,
                    location_id=loc,
                    stock_status=_ST_AVAILABLE,
                    quantity=quantity,
                )
                remaining = quantity - deducted
            else:
                remaining = await self._deduct_available_internal(tenant_id, material_id, quantity)
            if remaining > 0:
                raise InsufficientStockError(
                    f"Insufficient available stock for {material_id}: short by {remaining}"
                )
            await self._sync_material_total_from_buckets(model)
        else:
            current = Decimal(str(model.current_stock))
            reserved = Decimal(str(model.reserved_stock))
            available = current - reserved
            if quantity > available:
                raise InsufficientStockError(
                    f"Insufficient available stock for {material_id}: requested {quantity}, available {available}"
                )
            model.current_stock = float(current - quantity)

        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type=transaction_type,
            quantity=quantity,
            unit_id=unit_id,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=created_by,
            remarks=remarks,
            batch_id=batch_id,
            from_location_id=loc,
        )
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            transaction_type=transaction_type.upper(),
            quantity_change=-quantity,
            reference_type=reference_type,
            reference_id=reference_id,
        )

    async def adjust_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        new_quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        location_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> Decimal:
        """Canonical absolute stock adjustment. Returns signed delta."""
        if new_quantity < 0:
            raise ValueError("new_quantity cannot be negative")
        model = await self._lock_material(tenant_id, material_id)
        delta = new_quantity - Decimal(str(model.current_stock))
        if delta > 0:
            await self.add_stock(
                tenant_id=tenant_id,
                material_id=material_id,
                quantity=delta,
                unit_id=unit_id,
                created_by=created_by,
                to_location_id=location_id,
                remarks=remarks or f"Adjusted to {new_quantity}",
                transaction_type="adjustment",
                reference_type="adjustment",
            )
        elif delta < 0:
            await self.remove_stock(
                tenant_id=tenant_id,
                material_id=material_id,
                quantity=abs(delta),
                unit_id=unit_id,
                created_by=created_by,
                from_location_id=location_id,
                remarks=remarks or f"Adjusted to {new_quantity}",
                transaction_type="adjustment",
                reference_type="adjustment",
            )
        return delta

    async def add_batch_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        batch_number: str,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        expiry_date=None,
        to_location_id: Optional[uuid.UUID] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> BatchModel:
        """Canonical batch-tracked stock increase."""
        model = await self._lock_material(tenant_id, material_id)
        if not getattr(model, "is_batch_tracked", False):
            raise ValueError(f"Material '{model.code}' is not batch-tracked")
        batch = await self._lock_batch_by_number(
            tenant_id=tenant_id,
            material_id=material_id,
            batch_number=batch_number,
        )
        loc = to_location_id or await self._default_warehouse_location(tenant_id)
        if batch is None:
            batch = BatchModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                material_id=material_id,
                batch_number=batch_number,
                quantity=float(quantity),
                original_quantity=float(quantity),
                remaining_quantity=float(quantity),
                expiry_date=expiry_date,
                location_id=loc,
                status="AVAILABLE",
            )
            self._session.add(batch)
        else:
            batch.quantity = float(Decimal(str(batch.quantity or 0)) + quantity)
            batch.original_quantity = float(
                Decimal(str(batch.original_quantity if batch.original_quantity is not None else 0)) + quantity
            )
            batch.remaining_quantity = float(
                Decimal(str(batch.remaining_quantity if batch.remaining_quantity is not None else 0)) + quantity
            )
            if expiry_date is not None:
                batch.expiry_date = expiry_date
            if loc is not None:
                batch.location_id = loc
        self._update_batch_status(batch)

        await self.add_stock(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=quantity,
            unit_id=unit_id,
            created_by=created_by,
            to_location_id=loc,
            reference_id=reference_id,
            remarks=remarks or f"Batch IN - {batch_number}",
            batch_id=batch.id,
            transaction_type="in",
            reference_type="manual",
        )
        await self._session.flush()
        return batch

    async def remove_batch_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        batch_number: str,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        from_location_id: Optional[uuid.UUID] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> BatchModel:
        """Canonical batch-tracked stock decrease."""
        model = await self._lock_material(tenant_id, material_id)
        if not getattr(model, "is_batch_tracked", False):
            raise ValueError(f"Material '{model.code}' is not batch-tracked")
        batch = await self._lock_batch_by_number(
            tenant_id=tenant_id,
            material_id=material_id,
            batch_number=batch_number,
        )
        if batch is None:
            raise ValueError(f"Batch '{batch_number}' not found for material {material_id}")
        available = Decimal(str(batch.remaining_quantity if batch.remaining_quantity is not None else batch.quantity))
        if quantity > available:
            raise InsufficientStockError(
                f"Insufficient batch stock. Available: {available}, Requested: {quantity}"
            )
        batch.remaining_quantity = float(available - quantity)
        self._update_batch_status(batch)

        await self.remove_stock(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=quantity,
            unit_id=unit_id,
            created_by=created_by,
            from_location_id=from_location_id or batch.location_id,
            reference_id=reference_id,
            remarks=remarks or f"Batch OUT - {batch_number}",
            batch_id=batch.id,
            transaction_type="out",
            reference_type="manual",
        )
        await self._session.flush()
        return batch

    async def reserve_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        work_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
        batch_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Reserve stock (soft lock) when WO is released. Non-destructive."""
        reserved, shortage = await self.reserve_for_work_order(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=quantity,
            work_order_id=work_order_id,
            unit_id=unit_id,
            created_by=created_by,
            batch_id=batch_id,
        )
        if shortage > 0:
            raise InsufficientStockError(
                f"Cannot reserve {quantity}: only {reserved} available for {material_id}"
            )

    async def reserve_reference_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> None:
        """Reserve stock for a legacy non-WO reference without creating a WO reservation row."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        model = await self._lock_material(tenant_id, material_id)
        current = Decimal(str(model.current_stock or 0))
        reserved = Decimal(str(model.reserved_stock or 0))
        available = current - reserved
        if quantity > available:
            raise InsufficientStockError(
                f"Insufficient stock for {material_id}: requested {quantity}, available {available}"
            )
        model.reserved_stock = float(reserved + quantity)
        model.updated_at = datetime.now(timezone.utc)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="reserve",
            quantity=quantity,
            unit_id=unit_id,
            reference_type=reference_type or "manual",
            reference_id=reference_id,
            created_by=created_by,
            remarks=remarks or "Legacy stock reservation",
        )

    async def consume_reference_reservation(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        from_location_id: Optional[uuid.UUID] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> None:
        """Consume a legacy reservation through the canonical mutation path."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        model = await self._lock_material(tenant_id, material_id)
        if await self._has_stock_levels(tenant_id, material_id):
            remaining = quantity
            if from_location_id is not None:
                deducted = await self._deduct_bucket_quantity(
                    tenant_id=tenant_id,
                    material_id=material_id,
                    location_id=from_location_id,
                    stock_status=_ST_AVAILABLE,
                    quantity=quantity,
                )
                remaining -= deducted
            if remaining > 0:
                remaining = await self._deduct_available_internal(tenant_id, material_id, remaining)
            if remaining > 0:
                raise InsufficientStockError(
                    f"Insufficient available stock for {material_id}: short by {remaining}"
                )
            await self._sync_material_total_from_buckets(model)
        else:
            current = Decimal(str(model.current_stock or 0))
            if quantity > current:
                raise InsufficientStockError(
                    f"Insufficient stock for {material_id}: requested {quantity}, available {current}"
                )
            model.current_stock = float(current - quantity)

        reserved = Decimal(str(model.reserved_stock or 0))
        model.reserved_stock = float(max(Decimal("0"), reserved - quantity))
        model.updated_at = datetime.now(timezone.utc)
        ref_type = reference_type or "manual"
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="consume_reservation",
            quantity=quantity,
            unit_id=unit_id,
            reference_type=ref_type,
            reference_id=reference_id,
            created_by=created_by,
            remarks=remarks or "Legacy reservation consumed",
            from_location_id=from_location_id,
        )
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=from_location_id,
            transaction_type="CONSUME_RESERVATION",
            quantity_change=-quantity,
            reference_type=ref_type,
            reference_id=reference_id,
        )

    async def cancel_reference_reservation(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> None:
        """Release a reservation through the canonical mutation path via RESERVATION_RELEASE transaction."""
        if quantity <= 0:
            return
        model = await self._lock_material(tenant_id, material_id)
        reserved = Decimal(str(model.reserved_stock or 0))
        model.reserved_stock = float(max(Decimal("0"), reserved - quantity))
        model.updated_at = datetime.now(timezone.utc)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="RESERVATION_RELEASE",
            quantity=quantity,
            unit_id=unit_id,
            reference_type=reference_type or "manual",
            reference_id=reference_id,
            created_by=created_by,
            remarks=remarks or "Reservation released",
        )

    async def cancel_work_order_reservation(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        work_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        remarks: Optional[str] = None,
        batch_id: Optional[uuid.UUID] = None,
    ) -> Decimal:
        """Cancel unissued WO reservation quantity and return it to availability."""
        await self._lock_work_order(tenant_id, work_order_id)
        model = await self._lock_material(tenant_id, material_id)
        stmt = (
            select(InventoryReservationModel)
            .where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.reference_type == "work_order",
                InventoryReservationModel.reference_id == work_order_id,
                InventoryReservationModel.material_id == material_id,
                InventoryReservationModel.status.in_(("RESERVED", "PARTIALLY_ISSUED")),
            )
            .order_by(InventoryReservationModel.created_at)
            .with_for_update()
        )
        if batch_id is not None:
            stmt = stmt.where(InventoryReservationModel.batch_id == batch_id)
        reservations = (await self._session.execute(stmt)).scalars().all()

        cancelled_by_batch: dict[Optional[uuid.UUID], Decimal] = {}
        now = datetime.now(timezone.utc)
        for reservation in reservations:
            unissued = Decimal(str(reservation.quantity or 0)) - Decimal(str(reservation.issued_quantity or 0))
            if unissued <= 0:
                continue
            if reservation.batch_id is not None:
                batch = await self._lock_batch(tenant_id, reservation.batch_id)
                batch.reserved_quantity = float(
                    max(Decimal("0"), Decimal(str(batch.reserved_quantity or 0)) - unissued)
                )
                self._update_batch_status(batch)
            reservation.status = "ISSUED" if Decimal(str(reservation.issued_quantity or 0)) > 0 else "RETURNED"
            reservation.updated_at = now
            cancelled_by_batch[reservation.batch_id] = cancelled_by_batch.get(
                reservation.batch_id, Decimal("0")
            ) + unissued

        cancelled_qty = sum(cancelled_by_batch.values(), Decimal("0"))
        if cancelled_qty <= 0:
            return Decimal("0")

        reserved = Decimal(str(model.reserved_stock or 0))
        model.reserved_stock = float(max(Decimal("0"), reserved - cancelled_qty))
        model.updated_at = now
        for cancelled_batch_id, qty in cancelled_by_batch.items():
            await self._log_transaction(
                tenant_id=tenant_id,
                material_id=material_id,
                transaction_type="RESERVATION_RELEASE",
                quantity=qty,
                unit_id=unit_id,
                batch_id=cancelled_batch_id,
                reference_type="work_order",
                reference_id=work_order_id,
                created_by=created_by,
                remarks=remarks or f"Reservation released for WO {work_order_id}",
            )
        return cancelled_qty

    async def get_available_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> Decimal:
        """Read available, unreserved stock for a material."""
        model = await self._lock_material(tenant_id, material_id)
        return await self._available_for_locked_material(model)

    async def reserve_sales_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        sales_order_line_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
        sales_order_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Reserve finished goods for a sales order line without reducing on-hand stock.

        Creates both an inventory_transactions audit record (type=reserve) and an
        inventory_reservations row (reference_type=sales_order) as required by Req 14
        (Gap #2 — FG auto-reservation at SO confirm).

        SELECT FOR UPDATE on the materials row is acquired via _lock_material, satisfying
        Cross-Cutting Requirement A (optimistic locking).
        """
        model = await self._lock_material(tenant_id, material_id)
        available = await self._available_for_locked_material(model)
        if quantity > available:
            raise InsufficientStockError(
                f"Cannot reserve {quantity}: only {available} available for {material_id}"
            )
        model.reserved_stock = float(Decimal(str(model.reserved_stock)) + quantity)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="reserve",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="sales_order_line",
            reference_id=sales_order_line_id,
            created_by=created_by,
            remarks=f"Reserved for sales order line {sales_order_line_id}",
        )
        # Create an inventory_reservations record (Req 14.2, 14.4 — Gap #2).
        # reference_type is "sales_order" when the SO id is available; fall back to
        # "sales_order_line" so existing callers without so_id still work.
        ref_type = "sales_order" if sales_order_id is not None else "sales_order_line"
        ref_id = sales_order_id if sales_order_id is not None else sales_order_line_id
        reservation = InventoryReservationModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            reference_type=ref_type,
            reference_id=ref_id,
            material_id=material_id,
            quantity=float(quantity),
            status="RESERVED",
            unit_id=unit_id,
        )
        self._session.add(reservation)

    async def release_sales_reservation(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        sales_order_line_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
    ) -> None:
        """Release a sales reservation back to available stock.
        
        Creates a RESERVATION_RELEASE inventory transaction for audit trail (Req 18.1, 18.4).
        """
        model = await self._lock_material(tenant_id, material_id)
        reserved = Decimal(str(model.reserved_stock))
        released = min(quantity, reserved)
        model.reserved_stock = float(reserved - released)
        if released > 0:
            await self._log_transaction(
                tenant_id=tenant_id,
                material_id=material_id,
                transaction_type="RESERVATION_RELEASE",
                quantity=released,
                unit_id=unit_id,
                reference_type="sales_order_line",
                reference_id=sales_order_line_id,
                created_by=created_by,
                remarks=f"Released reservation for sales order line {sales_order_line_id}",
            )

    async def fulfill_sales_reservation(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        sales_order_line_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
    ) -> None:
        """Ship reserved goods: deduct physical stock and consume the reservation."""
        model = await self._lock_material(tenant_id, material_id)
        if await self._has_stock_levels(tenant_id, material_id):
            remaining = await self._deduct_available_internal(tenant_id, material_id, quantity)
            if remaining > 0:
                raise InsufficientStockError(
                    f"Insufficient available stock for {material_id}: short by {remaining}"
                )
            await self._sync_material_total_from_buckets(model)
        else:
            current = Decimal(str(model.current_stock))
            if quantity > current:
                raise InsufficientStockError(
                    f"Insufficient stock for {material_id}: requested {quantity}, available {current}"
                )
            model.current_stock = float(current - quantity)

        reserved = Decimal(str(model.reserved_stock))
        model.reserved_stock = float(max(Decimal("0"), reserved - quantity))
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="issue",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="sales_order_line",
            reference_id=sales_order_line_id,
            created_by=created_by,
            remarks=f"Shipped for sales order line {sales_order_line_id}",
        )
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=None,
            transaction_type="SALES_SHIPMENT",
            quantity_change=-quantity,
            reference_type="sales_order_line",
            reference_id=sales_order_line_id,
        )

    async def issue_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        work_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
        batch_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Physically issue material: decrease available stock and reserved_stock."""
        model = await self._lock_material(tenant_id, material_id)
        if await self._has_stock_levels(tenant_id, material_id):
            remaining = await self._deduct_available_internal(tenant_id, material_id, quantity)
            if remaining > 0:
                raise InsufficientStockError(
                    f"Insufficient available stock for {material_id}: "
                    f"short by {remaining} (pending inspection / quarantine not usable)"
                )
            await self._sync_material_total_from_buckets(model)
        else:
            current = Decimal(str(model.current_stock))
            if quantity > current:
                raise InsufficientStockError(
                    f"Insufficient stock for {material_id}: requested {quantity}, available {current}"
                )
            model.current_stock = float(current - quantity)
        reserved = Decimal(str(model.reserved_stock))
        model.reserved_stock = float(max(Decimal("0"), reserved - quantity))
        await self._log_transaction(
            tenant_id=tenant_id, material_id=material_id, transaction_type="issue",
            quantity=quantity, unit_id=unit_id, reference_type="work_order",
            reference_id=work_order_id, created_by=created_by,
            remarks=f"Issued for WO {work_order_id}",
            batch_id=batch_id,
        )
        # ── Stock Ledger ─────────────────────────────────────────────────────
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=None,
            transaction_type="ISSUE",
            quantity_change=-quantity,  # negative = reduction
            reference_type="work_order",
            reference_id=work_order_id,
        )

    async def issue_material_for_wo(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        transition_wo_status: bool = True,
        batch_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """Canonical WO material issue: stock mutation + WO line + reservation rows."""
        from datetime import datetime, timezone

        from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
        from backend.app.infrastructure.persistence.models.work_order_model import (
            WorkOrderMaterialModel,
            WorkOrderModel,
        )

        wo_stmt = select(WorkOrderModel).where(
            WorkOrderModel.id == work_order_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        ).with_for_update()
        wo = (await self._session.execute(wo_stmt)).scalar_one_or_none()
        if wo is None:
            raise ValueError(f"Work order {work_order_id} not found")

        mat_stmt = select(WorkOrderMaterialModel).where(
            WorkOrderMaterialModel.work_order_id == work_order_id,
            WorkOrderMaterialModel.material_id == material_id,
        )
        req = (await self._session.execute(mat_stmt)).scalar_one_or_none()
        if req is None:
            raise ValueError(f"Material {material_id} is not in the WO material requirements")

        remaining = Decimal(str(req.required_quantity)) - Decimal(str(req.issued_quantity))
        if quantity > remaining:
            raise ValueError(
                f"Cannot issue {quantity}: only {remaining} remaining for this material requirement"
            )

        # Update reservation rows (FIFO by created_at)
        await self._lock_material(tenant_id, material_id)
        res_stmt = (
            select(InventoryReservationModel)
            .where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.reference_type == "work_order",
                InventoryReservationModel.reference_id == work_order_id,
                InventoryReservationModel.material_id == material_id,
                InventoryReservationModel.status.in_(("RESERVED", "PARTIALLY_ISSUED", "ISSUED")),
            )
            .order_by(InventoryReservationModel.created_at)
            .with_for_update()
        )
        if batch_id is not None:
            res_stmt = res_stmt.where(InventoryReservationModel.batch_id == batch_id)
        reservations = (await self._session.execute(res_stmt)).scalars().all()
        reservable = sum(
            Decimal(str(res.quantity)) - Decimal(str(res.issued_quantity))
            for res in reservations
        )
        if quantity > reservable:
            raise ValueError(
                f"Cannot issue {quantity}: only {reservable} reserved and unissued for this material"
            )

        qty_left = quantity
        now = datetime.now(timezone.utc)
        for res in reservations:
            if qty_left <= 0:
                break
            res_qty = Decimal(str(res.quantity)) - Decimal(str(res.issued_quantity))
            if res_qty <= 0:
                continue
            issue_from_res = min(qty_left, res_qty)

            if res.batch_id is not None:
                batch = await self._lock_batch(tenant_id, res.batch_id)
                remaining_qty = Decimal(
                    str(batch.remaining_quantity if batch.remaining_quantity is not None else batch.quantity)
                )
                if issue_from_res > remaining_qty:
                    raise InsufficientStockError(
                        f"Cannot issue {issue_from_res} from batch {batch.batch_number}: only {remaining_qty} remains"
                    )
                batch.remaining_quantity = float(remaining_qty - issue_from_res)
                batch.reserved_quantity = float(
                    max(Decimal("0"), Decimal(str(batch.reserved_quantity or 0)) - issue_from_res)
                )
                self._update_batch_status(batch)

            await self.issue_stock(
                tenant_id=tenant_id,
                material_id=material_id,
                quantity=issue_from_res,
                work_order_id=work_order_id,
                unit_id=unit_id,
                created_by=created_by,
                batch_id=res.batch_id,
            )

            res.issued_quantity = float(Decimal(str(res.issued_quantity)) + issue_from_res)
            if Decimal(str(res.issued_quantity)) >= Decimal(str(res.quantity)):
                res.status = "ISSUED"
            else:
                res.status = "PARTIALLY_ISSUED"
            res.updated_at = now
            qty_left -= issue_from_res

        if qty_left > 0:
            raise ValueError(f"Unable to issue {qty_left}: no matching reservation remained")

        req.issued_quantity = float(Decimal(str(req.issued_quantity)) + quantity)

        new_wo_status = wo.status
        if transition_wo_status:
            all_materials = (
                await self._session.execute(
                    select(WorkOrderMaterialModel).where(
                        WorkOrderMaterialModel.work_order_id == work_order_id
                    )
                )
            ).scalars().all()
            all_issued = all(
                Decimal(str(m.issued_quantity)) >= Decimal(str(m.required_quantity))
                for m in all_materials
            )
            if all_issued and wo.status in (
                WorkOrderStatus.MATERIAL_RESERVED.value,
                WorkOrderStatus.MATERIAL_PENDING.value,
                WorkOrderStatus.MATERIAL_ISSUED.value,
            ):
                new_wo_status = WorkOrderStatus.MATERIAL_ISSUED.value
                wo.status = new_wo_status
                wo.updated_at = now

        return {
            "issued_quantity": float(req.issued_quantity),
            "remaining_quantity": float(remaining - quantity),
            "work_order_status": new_wo_status,
        }

    async def receive_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        work_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
        to_location_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Receive finished goods into stock after production (available at warehouse)."""
        model = await self._lock_material(tenant_id, material_id)
        loc = to_location_id or await self._default_warehouse_location(tenant_id)
        if loc:
            await self._add_bucket_quantity(
                tenant_id=tenant_id,
                material_id=material_id,
                location_id=loc,
                stock_status=_ST_AVAILABLE,
                quantity=quantity,
            )
            await self._sync_material_total_from_buckets(model)
        else:
            model.current_stock = float(Decimal(str(model.current_stock)) + quantity)
        await self._log_transaction(
            tenant_id=tenant_id, material_id=material_id, transaction_type="produce",
            quantity=quantity, unit_id=unit_id, reference_type="work_order",
            reference_id=work_order_id, created_by=created_by,
            remarks=f"Production receipt for WO {work_order_id}",
            to_location_id=loc,
        )
        # ── Stock Ledger ────────────────────────────────────────────────────
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            transaction_type="PRODUCTION_RECEIPT",
            quantity_change=quantity,
            reference_type="work_order",
            reference_id=work_order_id,
        )

    async def receive_purchase_receipt(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        purchase_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        warehouse_location_id: Optional[uuid.UUID] = None,
        unit_cost: Optional[float] = None,
    ) -> None:
        """GRN: receipt into warehouse; pending_inspection or available based on material flag."""
        model = await self._lock_material(tenant_id, material_id)
        loc = warehouse_location_id or await self._default_warehouse_location(tenant_id)
        if loc is None:
            raise ValueError("No warehouse location configured for this tenant")
        stock_status = _ST_PENDING if getattr(model, "inspection_required", False) else _ST_AVAILABLE
        await self._add_bucket_quantity(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            stock_status=stock_status,
            quantity=quantity,
        )
        await self._sync_material_total_from_buckets(model)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="receipt",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="purchase_receipt",
            reference_id=purchase_order_id,
            created_by=created_by,
            remarks="Goods receipt",
            to_location_id=loc,
        )
        # ── Stock Ledger (immutable audit) ───────────────────────────────────
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            transaction_type="RECEIPT",
            quantity_change=quantity,
            unit_cost=unit_cost,
            reference_type="purchase_order",
            reference_id=purchase_order_id,
        )

    async def reverse_purchase_receipt(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        purchase_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        warehouse_location_id: Optional[uuid.UUID] = None,
        reference_type: str = "purchase_receipt_reversal",
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> None:
        """Reverse a previously received purchase quantity through the canonical stock service."""
        model = await self._lock_material(tenant_id, material_id)
        loc = warehouse_location_id or await self._default_warehouse_location(tenant_id)

        if await self._has_stock_levels(tenant_id, material_id):
            if loc is None:
                raise ValueError("No warehouse location configured for this tenant")

            remaining = quantity
            preferred_statuses = [_ST_PENDING] if getattr(model, "inspection_required", False) else []
            preferred_statuses.extend([_ST_AVAILABLE, _ST_PENDING])

            for stock_status in preferred_statuses:
                if remaining <= 0:
                    break
                deducted = await self._deduct_bucket_quantity(
                    tenant_id=tenant_id,
                    material_id=material_id,
                    location_id=loc,
                    stock_status=stock_status,
                    quantity=remaining,
                )
                remaining -= deducted

            if remaining > 0:
                remaining = await self._deduct_available_internal(tenant_id, material_id, remaining)
            if remaining > 0:
                raise InsufficientStockError(
                    f"Cannot reverse receipt {quantity}: only {quantity - remaining} is still available"
                )

            await self._sync_material_total_from_buckets(model)
        else:
            current = Decimal(str(model.current_stock))
            if quantity > current:
                raise InsufficientStockError(
                    f"Cannot reverse receipt {quantity}: only {current} remains in stock"
                )
            model.current_stock = float(current - quantity)

        reversal_reference_id = reference_id or purchase_order_id
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="reverse_receipt",
            quantity=quantity,
            unit_id=unit_id,
            reference_type=reference_type,
            reference_id=reversal_reference_id,
            created_by=created_by,
            remarks=remarks or "Goods receipt reversal",
            from_location_id=loc,
        )
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            transaction_type="RECEIPT_REVERSAL",
            quantity_change=-quantity,
            reference_type=reference_type,
            reference_id=reversal_reference_id,
        )

    async def transfer_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        from_location_id: uuid.UUID,
        to_location_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> None:
        """Transfer available stock between two locations for the same material."""
        if from_location_id == to_location_id:
            raise ValueError("from_location_id and to_location_id must be different for a transfer")

        model = await self._lock_material(tenant_id, material_id)
        if not await self._has_stock_levels(tenant_id, material_id):
            current = Decimal(str(model.current_stock))
            if quantity > current:
                raise InsufficientStockError(
                    f"Cannot transfer {quantity}: only {current} available for {material_id}"
                )
            await self._add_bucket_quantity(
                tenant_id=tenant_id,
                material_id=material_id,
                location_id=from_location_id,
                stock_status=_ST_AVAILABLE,
                quantity=current,
            )
            await self._session.flush()
        await self._move_bucket_quantity(
            tenant_id=tenant_id,
            material_id=material_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            from_status=_ST_AVAILABLE,
            to_status=_ST_AVAILABLE,
            quantity=quantity,
        )
        await self._sync_material_total_from_buckets(model)

        transfer_reference_id = reference_id or uuid.uuid4()
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="transfer",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="inventory_transfer",
            reference_id=transfer_reference_id,
            created_by=created_by,
            remarks=remarks or "Inventory transfer",
            from_location_id=from_location_id,
            to_location_id=to_location_id,
        )
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=to_location_id,
            transaction_type="TRANSFER",
            quantity_change=Decimal("0"),
            reference_type="inventory_transfer",
            reference_id=transfer_reference_id,
        )

    async def inspection_pass_move_to_available(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        warehouse_location_id: uuid.UUID,
        inspection_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> None:
        model = await self._lock_material(tenant_id, material_id)
        await self._move_bucket_quantity(
            tenant_id=tenant_id,
            material_id=material_id,
            from_location_id=warehouse_location_id,
            to_location_id=warehouse_location_id,
            from_status=_ST_PENDING,
            to_status=_ST_AVAILABLE,
            quantity=quantity,
        )
        await self._sync_material_total_from_buckets(model)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="transfer",
            quantity=quantity,
            unit_id=cast(Optional[uuid.UUID], model.base_unit_id),
            reference_type="quality_inspection",
            reference_id=inspection_id,
            created_by=created_by,
            remarks="Inspection pass → available",
            from_location_id=warehouse_location_id,
            to_location_id=warehouse_location_id,
        )

    async def inspection_fail_move_to_quarantine(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        warehouse_location_id: uuid.UUID,
        quarantine_location_id: uuid.UUID,
        inspection_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> None:
        model = await self._lock_material(tenant_id, material_id)
        await self._move_bucket_quantity(
            tenant_id=tenant_id,
            material_id=material_id,
            from_location_id=warehouse_location_id,
            to_location_id=quarantine_location_id,
            from_status=_ST_PENDING,
            to_status=_ST_QUARANTINE,
            quantity=quantity,
        )
        await self._sync_material_total_from_buckets(model)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="transfer",
            quantity=quantity,
            unit_id=cast(Optional[uuid.UUID], model.base_unit_id),
            reference_type="quality_inspection",
            reference_id=inspection_id,
            created_by=created_by,
            remarks="Inspection fail → quarantine",
            from_location_id=warehouse_location_id,
            to_location_id=quarantine_location_id,
        )

    async def issue_to_subcontractor(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        from_location_id: uuid.UUID,
        subcontractor_location_id: uuid.UUID,
        subcontract_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
    ) -> None:
        """Transfer available stock from internal warehouse to subcontractor location."""
        model = await self._lock_material(tenant_id, material_id)
        remaining = await self._deduct_available_internal(tenant_id, material_id, quantity)
        if remaining > 0:
            raise InsufficientStockError(f"Insufficient available stock for subcontract issue: {remaining} short")
        await self._add_bucket_quantity(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=subcontractor_location_id,
            stock_status=_ST_AVAILABLE,
            quantity=quantity,
        )
        await self._sync_material_total_from_buckets(model)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="subcontract",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="subcontract_order",
            reference_id=subcontract_order_id,
            created_by=created_by,
            remarks="Issue to subcontractor",
            from_location_id=from_location_id,
            to_location_id=subcontractor_location_id,
        )

    async def receive_subcontract_finished_goods(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        warehouse_location_id: uuid.UUID,
        subcontract_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        created_by: uuid.UUID,
    ) -> None:
        """Receive finished goods into warehouse (available). Subcontractor WIP is tracked via issue lines."""
        model = await self._lock_material(tenant_id, material_id)
        await self._add_bucket_quantity(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=warehouse_location_id,
            stock_status=_ST_AVAILABLE,
            quantity=quantity,
        )
        await self._sync_material_total_from_buckets(model)
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="subcontract",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="subcontract_order",
            reference_id=subcontract_order_id,
            created_by=created_by,
            remarks="Receive finished goods from subcontractor",
            to_location_id=warehouse_location_id,
        )

    # ── Phase 2: Inventory Reservation System Extensions ───────────────────────

    async def reserve_for_work_order(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        work_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
        batch_id: Optional[uuid.UUID] = None,
    ) -> tuple[Decimal, Decimal]:
        """Reserve stock for work order with partial reservation handling.

        Returns: (reserved_qty, shortage_qty)
        """
        await self._lock_work_order(tenant_id, work_order_id)
        model = await self._lock_material(tenant_id, material_id)
        available = await self._available_for_locked_material(model)

        reserve_qty = min(quantity, available)
        batch_allocations: list[tuple[Optional[BatchModel], Decimal]] = []

        if reserve_qty > 0 and getattr(model, "is_batch_tracked", False):
            remaining_to_allocate = reserve_qty
            for batch in await self._candidate_batches(
                tenant_id=tenant_id,
                material_id=material_id,
                batch_id=batch_id,
            ):
                free_qty = Decimal(
                    str(batch.remaining_quantity if batch.remaining_quantity is not None else batch.quantity)
                )
                free_qty -= Decimal(str(batch.reserved_quantity or 0))
                if free_qty <= 0:
                    continue
                take = min(free_qty, remaining_to_allocate)
                batch_allocations.append((batch, take))
                remaining_to_allocate -= take
                if remaining_to_allocate <= 0:
                    break
            if remaining_to_allocate > 0:
                reserve_qty -= remaining_to_allocate
        elif reserve_qty > 0:
            batch_allocations.append((None, reserve_qty))

        shortage_qty = max(Decimal("0"), quantity - reserve_qty)

        if reserve_qty > 0:
            model.reserved_stock = float(Decimal(str(model.reserved_stock)) + reserve_qty)

            for batch, allocation_qty in batch_allocations:
                if batch is not None:
                    batch.reserved_quantity = float(
                        Decimal(str(batch.reserved_quantity or 0)) + allocation_qty
                    )
                    self._update_batch_status(batch)

                await self._log_transaction(
                    tenant_id=tenant_id,
                    material_id=material_id,
                    transaction_type="reserve",
                    quantity=allocation_qty,
                    unit_id=unit_id,
                    batch_id=batch.id if batch is not None else None,
                    reference_type="work_order",
                    reference_id=work_order_id,
                    created_by=created_by,
                    remarks=f"Reserved for WO {work_order_id}",
                )

                self._session.add(InventoryReservationModel(
                    tenant_id=tenant_id,
                    reference_type="work_order",
                    reference_id=work_order_id,
                    material_id=material_id,
                    batch_id=batch.id if batch is not None else None,
                    quantity=float(allocation_qty),
                    status="RESERVED",
                    unit_id=unit_id,
                    issued_quantity=0,
                    consumed_quantity=0,
                    returned_quantity=0,
                ))

        return reserve_qty, shortage_qty

    async def get_existing_reservation_qty_for_wo(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> Decimal:
        """Sum active reservation quantity for WO line (idempotent release)."""
        from backend.app.infrastructure.persistence.models.inventory_reservation_model import (
            InventoryReservationModel,
        )

        stmt = select(func.coalesce(func.sum(InventoryReservationModel.quantity), 0)).where(
            InventoryReservationModel.tenant_id == tenant_id,
            InventoryReservationModel.reference_type == "work_order",
            InventoryReservationModel.reference_id == work_order_id,
            InventoryReservationModel.material_id == material_id,
            InventoryReservationModel.status.in_(
                ("RESERVED", "PARTIALLY_ISSUED", "ISSUED", "PARTIALLY_CONSUMED", "CONSUMED", "RETURNED")
            ),
        )
        total = (await self._session.execute(stmt)).scalar()
        return Decimal(str(total or 0))

    async def create_shortage_record(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        required_quantity: Decimal,
        shortage_quantity: Decimal,
        created_by: uuid.UUID,
    ) -> None:
        """Create a material shortage record."""
        from backend.app.infrastructure.persistence.models.material_shortage_model import MaterialShortageModel

        available_qty = required_quantity - shortage_quantity
        existing = (
            await self._session.execute(
                select(MaterialShortageModel).where(
                    MaterialShortageModel.tenant_id == tenant_id,
                    MaterialShortageModel.work_order_id == work_order_id,
                    MaterialShortageModel.material_id == material_id,
                    MaterialShortageModel.status.in_(["open", "partial"]),
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            existing.required_quantity = float(required_quantity)
            existing.available_quantity = float(available_qty)
            existing.shortage_quantity = float(shortage_quantity)
            existing.updated_at = datetime.now(timezone.utc)
            return

        shortage = MaterialShortageModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            material_id=material_id,
            required_quantity=float(required_quantity),
            available_quantity=float(available_qty),
            shortage_quantity=float(shortage_quantity),
            status="open",
            created_by=created_by,
        )
        self._session.add(shortage)

    async def get_shortages_for_work_order(
        self,
        *,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
    ) -> list[MaterialShortage]:
        """Get all shortage records for a work order."""
        from backend.app.infrastructure.persistence.models.material_shortage_model import MaterialShortageModel

        stmt = select(MaterialShortageModel).where(
            MaterialShortageModel.tenant_id == tenant_id,
            MaterialShortageModel.work_order_id == work_order_id,
            MaterialShortageModel.status.in_(["open", "partial"]),
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        shortages = []
        for model in models:
            shortages.append(
                MaterialShortage(
                    id=model.id,
                    tenant_id=model.tenant_id,
                    work_order_id=model.work_order_id,
                    material_id=model.material_id,
                    required_quantity=Decimal(str(model.required_quantity)),
                    available_quantity=Decimal(str(model.available_quantity)),
                    shortage_quantity=Decimal(str(model.shortage_quantity)),
                    status=ShortageStatus(model.status),
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                )
            )
        return shortages

    async def get_pending_issues(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get pending material issue queue for storekeeper dashboard."""
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderMaterialModel

        # Include MATERIAL_PENDING because a WO can have partial reservations while shortages remain.
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

        pending_issues = []
        for wo in wos:
            # Get material requirements for this WO
            mat_stmt = select(WorkOrderMaterialModel).where(
                WorkOrderMaterialModel.work_order_id == wo.id
            )
            mat_result = await self._session.execute(mat_stmt)
            materials = mat_result.scalars().all()

            for mat in materials:
                remaining = Decimal(str(mat.required_quantity)) - Decimal(str(mat.issued_quantity))
                if remaining > 0:
                    material_model = (
                        await self._session.execute(
                            select(MaterialModel).where(
                                MaterialModel.id == mat.material_id,
                                MaterialModel.tenant_id == tenant_id,
                                MaterialModel.is_deleted.is_(False),
                            )
                        )
                    ).scalar_one_or_none()
                    res_rows = (
                        await self._session.execute(
                            select(InventoryReservationModel, BatchModel)
                            .outerjoin(BatchModel, BatchModel.id == InventoryReservationModel.batch_id)
                            .where(
                                InventoryReservationModel.tenant_id == tenant_id,
                                InventoryReservationModel.reference_type == "work_order",
                                InventoryReservationModel.reference_id == wo.id,
                                InventoryReservationModel.material_id == mat.material_id,
                                InventoryReservationModel.status.in_(
                                    (
                                        "RESERVED",
                                        "PARTIALLY_ISSUED",
                                        "ISSUED",
                                        "PARTIALLY_CONSUMED",
                                        "CONSUMED",
                                        "RETURNED",
                                    )
                                ),
                            )
                            .order_by(InventoryReservationModel.created_at)
                        )
                    ).all()
                    reserved_quantity = sum(Decimal(str(res.quantity or 0)) for res, _batch in res_rows)
                    issued_quantity = sum(Decimal(str(res.issued_quantity or 0)) for res, _batch in res_rows)
                    consumed_quantity = sum(Decimal(str(res.consumed_quantity or 0)) for res, _batch in res_rows)
                    returned_quantity = sum(Decimal(str(res.returned_quantity or 0)) for res, _batch in res_rows)
                    batch_numbers = [
                        batch.batch_number
                        for _res, batch in res_rows
                        if batch is not None and batch.batch_number
                    ]
                    batch_ids = [
                        res.batch_id
                        for res, _batch in res_rows
                        if res.batch_id is not None
                    ]
                    current_stock = (
                        Decimal(str(material_model.current_stock or 0))
                        if material_model is not None
                        else Decimal("0")
                    )
                    reserved_stock = (
                        Decimal(str(material_model.reserved_stock or 0))
                        if material_model is not None
                        else Decimal("0")
                    )
                    pending_issues.append({
                        "work_order_id": wo.id,
                        "wo_number": wo.wo_number,
                        "material_id": mat.material_id,
                        "material_code": material_model.code if material_model is not None else None,
                        "material_name": material_model.name if material_model is not None else None,
                        "batch_id": batch_ids[0] if batch_ids else None,
                        "batch_number": ", ".join(dict.fromkeys(batch_numbers)) if batch_numbers else None,
                        "required_quantity": mat.required_quantity,
                        "reserved_quantity": float(reserved_quantity),
                        "issued_quantity": mat.issued_quantity,
                        "consumed_quantity": float(consumed_quantity),
                        "returned_quantity": float(returned_quantity),
                        "remaining_quantity": float(remaining),
                        "available_quantity": float(max(Decimal("0"), current_stock - reserved_stock)),
                        "due_date": wo.due_date,
                        "status": wo.status,
                    })

        return pending_issues

    # ── Production Inventory Methods ─────────────────────────────────────────────

    async def consume_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        work_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
        batch_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Consume stock during production (ISSUED → CONSUMED).

        Stock was already reduced on issue; this records consumption and closes reservations.
        """
        await self._lock_work_order(tenant_id, work_order_id)
        model = await self._lock_material(tenant_id, material_id)
        model.updated_at = datetime.now(timezone.utc)

        qty_left = quantity
        stmt = (
            select(InventoryReservationModel)
            .where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.reference_type == "work_order",
                InventoryReservationModel.reference_id == work_order_id,
                InventoryReservationModel.material_id == material_id,
                InventoryReservationModel.status.in_(
                    ("ISSUED", "PARTIALLY_ISSUED", "PARTIALLY_CONSUMED", "RESERVED")
                ),
            )
            .order_by(InventoryReservationModel.created_at)
            .with_for_update()
        )
        if batch_id is not None:
            stmt = stmt.where(InventoryReservationModel.batch_id == batch_id)
        res_rows = (await self._session.execute(stmt)).scalars().all()
        total_issuable = sum(
            max(
                Decimal("0"),
                Decimal(str(res.issued_quantity or 0))
                - Decimal(str(res.consumed_quantity or 0))
                - Decimal(str(res.returned_quantity or 0)),
            )
            for res in res_rows
        )
        if quantity > total_issuable:
            raise ValueError(f"Cannot consume {quantity}: only {total_issuable} issued and unconsumed")

        consumed_by_batch: dict[Optional[uuid.UUID], Decimal] = {}
        for res in res_rows:
            if qty_left <= 0:
                break
            issuable = (
                Decimal(str(res.issued_quantity))
                - Decimal(str(res.consumed_quantity))
                - Decimal(str(res.returned_quantity or 0))
            )
            if issuable <= 0:
                continue
            take = min(qty_left, issuable)
            res.consumed_quantity = float(Decimal(str(res.consumed_quantity)) + take)
            if res.batch_id is not None:
                batch = await self._lock_batch(tenant_id, res.batch_id)
                batch.consumed_quantity = float(Decimal(str(batch.consumed_quantity or 0)) + take)
                self._update_batch_status(batch)
            if Decimal(str(res.consumed_quantity)) >= Decimal(str(res.quantity)):
                res.status = "CONSUMED"
            else:
                res.status = "PARTIALLY_CONSUMED"
            res.updated_at = datetime.now(timezone.utc)
            consumed_by_batch[res.batch_id] = consumed_by_batch.get(res.batch_id, Decimal("0")) + take
            qty_left -= take

        if qty_left > 0:
            raise ValueError(f"Cannot consume {quantity}: only {quantity - qty_left} issued and unconsumed")

        for consumed_batch_id, consumed_qty in consumed_by_batch.items():
            await self._log_transaction(
                tenant_id=tenant_id,
                material_id=material_id,
                transaction_type="CONSUME",
                quantity=consumed_qty,
                unit_id=unit_id,
                batch_id=consumed_batch_id,
                reference_type="work_order",
                reference_id=work_order_id,
                created_by=created_by,
                remarks=f"Production consumption for WO {work_order_id}",
            )
        
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=None,
            transaction_type="PRODUCTION_CONSUMPTION",
            quantity_change=-quantity,
            reference_type="work_order",
            reference_id=work_order_id,
        )

    async def receive_fg(
        self,
        *,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: Decimal,
        work_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
        to_location_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Receive finished goods after QC approval (QC_APPROVED → FG_RECEIVED).
        
        Inventory impact: Increases FG stock.
        """
        await self._lock_work_order(tenant_id, work_order_id)
        # Use product_id instead of material_id for FG
        model = await self._lock_material(tenant_id, product_id)
        existing_receipt = (
            await self._session.execute(
                select(InventoryTransactionModel.id).where(
                    InventoryTransactionModel.tenant_id == tenant_id,
                    InventoryTransactionModel.material_id == product_id,
                    InventoryTransactionModel.reference_type == "work_order",
                    InventoryTransactionModel.reference_id == work_order_id,
                    InventoryTransactionModel.transaction_type == "FG_RECEIPT",
                    InventoryTransactionModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if existing_receipt is not None:
            return False

        loc = to_location_id or await self._default_warehouse_location(tenant_id)
        
        if loc:
            await self._add_bucket_quantity(
                tenant_id=tenant_id,
                material_id=product_id,
                location_id=loc,
                stock_status=_ST_AVAILABLE,
                quantity=quantity,
            )
            await self._sync_material_total_from_buckets(model)
        else:
            model.current_stock = float(Decimal(str(model.current_stock)) + quantity)
        
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=product_id,
            transaction_type="FG_RECEIPT",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="work_order",
            reference_id=work_order_id,
            created_by=created_by,
            remarks=f"FG receipt for WO {work_order_id}",
            to_location_id=loc,
        )
        
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=product_id,
            location_id=loc,
            transaction_type="FG_RECEIPT",
            quantity_change=quantity,
            reference_type="work_order",
            reference_id=work_order_id,
        )
        return True

    async def reject_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        work_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
        reason: Optional[str] = None,
    ) -> None:
        """Reject stock (CONSUMED → REJECTED or ISSUED → REJECTED).
        
        Used for scrap/rejection during production or QC.
        """
        model = await self._lock_material(tenant_id, material_id)
        
        # Reduce current stock (scrap is removed from available stock)
        current = Decimal(str(model.current_stock))
        if current < quantity:
            raise InsufficientStockError(
                f"Cannot reject {quantity}: only {current} available"
            )
        model.current_stock = float(current - quantity)
        model.updated_at = datetime.now(timezone.utc)
        
        await self._log_transaction(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type="REJECT",
            quantity=quantity,
            unit_id=unit_id,
            reference_type="work_order",
            reference_id=work_order_id,
            created_by=created_by,
            remarks=reason or f"Stock rejection for WO {work_order_id}",
        )
        
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=None,
            transaction_type="REJECTION",
            quantity_change=-quantity,
            reference_type="work_order",
            reference_id=work_order_id,
        )

    async def return_stock(
        self,
        *,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        quantity: Decimal,
        work_order_id: uuid.UUID,
        unit_id: Optional[uuid.UUID] = None,
        created_by: uuid.UUID,
        batch_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Return issued stock back to available (ISSUED → RESERVED → AVAILABLE).
        
        Used when material is returned from work order.
        """
        if quantity <= 0:
            return

        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderMaterialModel

        await self._lock_work_order(tenant_id, work_order_id)
        model = await self._lock_material(tenant_id, material_id)
        loc = await self._default_warehouse_location(tenant_id)

        res_stmt = (
            select(InventoryReservationModel)
            .where(
                InventoryReservationModel.tenant_id == tenant_id,
                InventoryReservationModel.reference_type == "work_order",
                InventoryReservationModel.reference_id == work_order_id,
                InventoryReservationModel.material_id == material_id,
                InventoryReservationModel.status.in_(
                    ("ISSUED", "PARTIALLY_ISSUED", "PARTIALLY_CONSUMED", "CONSUMED", "RETURNED")
                ),
            )
            .order_by(InventoryReservationModel.created_at)
            .with_for_update()
        )
        if batch_id is not None:
            res_stmt = res_stmt.where(InventoryReservationModel.batch_id == batch_id)

        reservations = (await self._session.execute(res_stmt)).scalars().all()
        total_returnable = sum(
            max(
                Decimal("0"),
                Decimal(str(res.issued_quantity or 0))
                - Decimal(str(res.consumed_quantity or 0))
                - Decimal(str(res.returned_quantity or 0)),
            )
            for res in reservations
        )
        if quantity > total_returnable:
            raise ValueError(
                f"Cannot return {quantity}: only {total_returnable} issued, unconsumed, and unreturned"
            )

        qty_left = quantity
        returned_by_batch: dict[Optional[uuid.UUID], Decimal] = {}
        now = datetime.now(timezone.utc)
        for res in reservations:
            if qty_left <= 0:
                break
            returnable = (
                Decimal(str(res.issued_quantity or 0))
                - Decimal(str(res.consumed_quantity or 0))
                - Decimal(str(res.returned_quantity or 0))
            )
            if returnable <= 0:
                continue
            take = min(qty_left, returnable)
            res.returned_quantity = float(Decimal(str(res.returned_quantity or 0)) + take)

            consumed = Decimal(str(res.consumed_quantity or 0))
            returned = Decimal(str(res.returned_quantity or 0))
            issued = Decimal(str(res.issued_quantity or 0))
            if consumed <= 0 and returned >= issued:
                res.status = "RETURNED"
            elif consumed >= Decimal(str(res.quantity or 0)):
                res.status = "CONSUMED"
            elif consumed > 0:
                res.status = "PARTIALLY_CONSUMED"
            elif returned > 0:
                res.status = "PARTIALLY_ISSUED"
            res.updated_at = now

            if res.batch_id is not None:
                batch = await self._lock_batch(tenant_id, res.batch_id)
                current_remaining = Decimal(
                    str(batch.remaining_quantity if batch.remaining_quantity is not None else batch.quantity)
                )
                batch.remaining_quantity = float(current_remaining + take)
                batch.returned_quantity = float(Decimal(str(batch.returned_quantity or 0)) + take)
                self._update_batch_status(batch)

            returned_by_batch[res.batch_id] = returned_by_batch.get(res.batch_id, Decimal("0")) + take
            qty_left -= take

        if loc:
            await self._add_bucket_quantity(
                tenant_id=tenant_id,
                material_id=material_id,
                location_id=loc,
                stock_status=_ST_AVAILABLE,
                quantity=quantity,
            )
            await self._sync_material_total_from_buckets(model)
        else:
            model.current_stock = float(Decimal(str(model.current_stock)) + quantity)

        mat_req = (
            await self._session.execute(
                select(WorkOrderMaterialModel)
                .where(
                    WorkOrderMaterialModel.work_order_id == work_order_id,
                    WorkOrderMaterialModel.material_id == material_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if mat_req is not None:
            issued_qty = Decimal(str(mat_req.issued_quantity or 0))
            mat_req.issued_quantity = float(max(Decimal("0"), issued_qty - quantity))

        for returned_batch_id, returned_qty in returned_by_batch.items():
            await self._log_transaction(
                tenant_id=tenant_id,
                material_id=material_id,
                transaction_type="RETURN",
                quantity=returned_qty,
                unit_id=unit_id,
                batch_id=returned_batch_id,
                reference_type="work_order",
                reference_id=work_order_id,
                created_by=created_by,
                remarks=f"Material return for WO {work_order_id}",
                to_location_id=loc,
            )
        
        await self._log_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=loc,
            transaction_type="RETURN",
            quantity_change=quantity,
            reference_type="work_order",
            reference_id=work_order_id,
        )
