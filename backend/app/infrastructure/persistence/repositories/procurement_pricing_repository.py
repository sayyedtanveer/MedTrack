"""
Repository implementations for procurement pricing (Infrastructure Layer).

Concrete implementations of domain repository interfaces using SQLAlchemy async ORM.
All queries enforce tenant isolation and soft delete filtering.
"""

import json
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.procurement.pricing.entities import (
    MaterialCostHistory,
    PriceOverrideRecord,
    StandardCostRevision,
    StandardCostRevisionStatus,
    SupplierPriceAgreement,
    SupplierPriceAgreementStatus,
)
from backend.app.domain.procurement.pricing.repositories import (
    IMaterialCostHistoryRepository,
    IPriceOverrideRecordRepository,
    IStandardCostRevisionRepository,
    ISupplierPriceAgreementRepository,
)
from backend.app.domain.procurement.pricing.value_objects import PricingTier
from backend.app.infrastructure.persistence.models.procurement_pricing_models import (
    MaterialCostHistoryModel,
    PriceOverrideRecordModel,
    StandardCostRevisionModel,
    SupplierPriceAgreementModel,
)
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from decimal import Decimal


class SupplierPriceAgreementRepository(ISupplierPriceAgreementRepository):
    """Repository implementation for supplier price agreements."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, tenant_id: UUID, agreement_id: UUID
    ) -> Optional[SupplierPriceAgreement]:
        """Get agreement by ID with tenant isolation and soft delete filter."""
        stmt = select(SupplierPriceAgreementModel).where(
            SupplierPriceAgreementModel.tenant_id == tenant_id,
            SupplierPriceAgreementModel.id == agreement_id,
            SupplierPriceAgreementModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def get_active_by_supplier_material(
        self, tenant_id: UUID, supplier_id: UUID, material_id: UUID
    ) -> Optional[SupplierPriceAgreement]:
        """Get an active agreement that is currently effective."""
        now = datetime.now(timezone.utc)
        stmt = select(SupplierPriceAgreementModel).where(
            SupplierPriceAgreementModel.tenant_id == tenant_id,
            SupplierPriceAgreementModel.supplier_id == supplier_id,
            SupplierPriceAgreementModel.material_id == material_id,
            SupplierPriceAgreementModel.status == SupplierPriceAgreementStatus.ACTIVE.value,
            SupplierPriceAgreementModel.effective_from <= now,
            or_(
                SupplierPriceAgreementModel.effective_to.is_(None),
                SupplierPriceAgreementModel.effective_to >= now,
            ),
            SupplierPriceAgreementModel.is_deleted.is_(False),
        ).order_by(desc(SupplierPriceAgreementModel.effective_from), desc(SupplierPriceAgreementModel.created_at))
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def find_overlapping(
        self,
        tenant_id: UUID,
        supplier_id: UUID,
        material_id: UUID,
        effective_from: datetime,
        effective_to: Optional[datetime],
        *,
        exclude_id: Optional[UUID] = None,
    ) -> Optional[SupplierPriceAgreement]:
        """Serialize interval checks per material and find overlapping agreements."""
        material_stmt = (
            select(MaterialModel.id)
            .where(
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.id == material_id,
                MaterialModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        material_id_found = (await self._session.execute(material_stmt)).scalar_one_or_none()
        if material_id_found is None:
            raise ValueError(f"Material {material_id} not found")

        supplier_stmt = select(SupplierModel.id).where(
            SupplierModel.tenant_id == tenant_id,
            SupplierModel.id == supplier_id,
            SupplierModel.is_deleted.is_(False),
            SupplierModel.is_active.is_(True),
        )
        if (await self._session.execute(supplier_stmt)).scalar_one_or_none() is None:
            raise ValueError(f"Supplier {supplier_id} not found")

        overlap_end = effective_to or datetime.max.replace(tzinfo=timezone.utc)
        conditions = [
            SupplierPriceAgreementModel.tenant_id == tenant_id,
            SupplierPriceAgreementModel.supplier_id == supplier_id,
            SupplierPriceAgreementModel.material_id == material_id,
            SupplierPriceAgreementModel.status != SupplierPriceAgreementStatus.CANCELLED.value,
            SupplierPriceAgreementModel.is_deleted.is_(False),
            SupplierPriceAgreementModel.effective_from <= overlap_end,
            or_(
                SupplierPriceAgreementModel.effective_to.is_(None),
                SupplierPriceAgreementModel.effective_to >= effective_from,
            ),
        ]
        if exclude_id is not None:
            conditions.append(SupplierPriceAgreementModel.id != exclude_id)

        result = await self._session.execute(
            select(SupplierPriceAgreementModel)
            .where(*conditions)
            .order_by(desc(SupplierPriceAgreementModel.effective_from))
            .with_for_update()
            .limit(1)
        )
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def list_by_supplier(
        self, tenant_id: UUID, supplier_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[SupplierPriceAgreement]:
        """List agreements for a supplier with pagination."""
        stmt = (
            select(SupplierPriceAgreementModel)
            .where(
                SupplierPriceAgreementModel.tenant_id == tenant_id,
                SupplierPriceAgreementModel.supplier_id == supplier_id,
                SupplierPriceAgreementModel.is_deleted.is_(False),
            )
            .order_by(desc(SupplierPriceAgreementModel.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_material(
        self, tenant_id: UUID, material_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[SupplierPriceAgreement]:
        """List agreements for a material from all suppliers."""
        stmt = (
            select(SupplierPriceAgreementModel)
            .where(
                SupplierPriceAgreementModel.tenant_id == tenant_id,
                SupplierPriceAgreementModel.material_id == material_id,
                SupplierPriceAgreementModel.is_deleted.is_(False),
            )
            .order_by(desc(SupplierPriceAgreementModel.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_tenant(
        self, tenant_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[SupplierPriceAgreement]:
        """List all agreements for tenant."""
        stmt = (
            select(SupplierPriceAgreementModel)
            .where(
                SupplierPriceAgreementModel.tenant_id == tenant_id,
                SupplierPriceAgreementModel.is_deleted.is_(False),
            )
            .order_by(desc(SupplierPriceAgreementModel.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_filtered(
        self,
        tenant_id: UUID,
        *,
        supplier_id: Optional[UUID] = None,
        material_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[SupplierPriceAgreement]:
        conditions = [
            SupplierPriceAgreementModel.tenant_id == tenant_id,
            SupplierPriceAgreementModel.is_deleted.is_(False),
        ]
        if supplier_id is not None:
            conditions.append(SupplierPriceAgreementModel.supplier_id == supplier_id)
        if material_id is not None:
            conditions.append(SupplierPriceAgreementModel.material_id == material_id)
        if status is not None:
            conditions.append(SupplierPriceAgreementModel.status == status.upper())

        stmt = (
            select(SupplierPriceAgreementModel)
            .where(*conditions)
            .order_by(desc(SupplierPriceAgreementModel.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(model) for model in result.scalars().all()]

    async def count_filtered(
        self,
        tenant_id: UUID,
        *,
        supplier_id: Optional[UUID] = None,
        material_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> int:
        conditions = [
            SupplierPriceAgreementModel.tenant_id == tenant_id,
            SupplierPriceAgreementModel.is_deleted.is_(False),
        ]
        if supplier_id is not None:
            conditions.append(SupplierPriceAgreementModel.supplier_id == supplier_id)
        if material_id is not None:
            conditions.append(SupplierPriceAgreementModel.material_id == material_id)
        if status is not None:
            conditions.append(SupplierPriceAgreementModel.status == status.upper())

        return int(
            await self._session.scalar(
                select(func.count()).select_from(SupplierPriceAgreementModel).where(*conditions)
            )
            or 0
        )

    async def save(self, agreement: SupplierPriceAgreement) -> SupplierPriceAgreement:
        """Insert or update agreement."""
        values = self._to_model(agreement)
        model = await self._session.get(SupplierPriceAgreementModel, agreement.id)
        if model is not None and model.tenant_id != agreement.tenant_id:
            raise ValueError("Supplier price agreement not found for tenant")
        if model is None:
            model = values
            self._session.add(model)
        else:
            for column in SupplierPriceAgreementModel.__table__.columns:
                setattr(model, column.name, getattr(values, column.name))
        await self._session.flush()
        return self._to_entity(model)

    async def delete(self, tenant_id: UUID, agreement_id: UUID) -> None:
        """Soft-delete agreement."""
        stmt = select(SupplierPriceAgreementModel).where(
            SupplierPriceAgreementModel.tenant_id == tenant_id,
            SupplierPriceAgreementModel.id == agreement_id,
            SupplierPriceAgreementModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        if model:
            model.is_deleted = True
            await self._session.flush()

    # ── Private conversion methods ──

    def _to_entity(self, model: SupplierPriceAgreementModel) -> SupplierPriceAgreement:
        """Convert ORM model to domain entity."""
        tiers = []
        if model.quantity_tier:
            try:
                tier_data = json.loads(model.quantity_tier)
                for tier_dict in tier_data:
                    tiers.append(
                        PricingTier(
                            min_quantity=Decimal(str(tier_dict["min_qty"])),
                            max_quantity=Decimal(str(tier_dict["max_qty"]))
                            if tier_dict.get("max_qty")
                            else None,
                            discount_percent=Decimal(str(tier_dict["discount_percent"])),
                        )
                    )
            except (json.JSONDecodeError, KeyError, ValueError):
                tiers = []

        return SupplierPriceAgreement(
            id=model.id,
            tenant_id=model.tenant_id,
            supplier_id=model.supplier_id,
            material_id=model.material_id,
            base_price=Decimal(str(model.base_price)),
            currency_code=model.currency_code,
            purchase_uom_id=model.purchase_uom_id,
            minimum_order_quantity=(
                Decimal(str(model.minimum_order_quantity))
                if model.minimum_order_quantity is not None
                else None
            ),
            effective_from=model.effective_from,
            effective_to=model.effective_to,
            quantity_tiers=tiers,
            notes=model.notes,
            status=SupplierPriceAgreementStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: SupplierPriceAgreement) -> SupplierPriceAgreementModel:
        """Convert domain entity to ORM model."""
        tier_json = None
        if entity.quantity_tiers:
            tier_data = [
                {
                    "min_qty": str(tier.min_quantity),
                    "max_qty": str(tier.max_quantity) if tier.max_quantity else None,
                    "discount_percent": str(tier.discount_percent),
                }
                for tier in entity.quantity_tiers
            ]
            tier_json = json.dumps(tier_data)

        return SupplierPriceAgreementModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            supplier_id=entity.supplier_id,
            material_id=entity.material_id,
            base_price=float(entity.base_price),
            currency_code=entity.currency_code,
            purchase_uom_id=entity.purchase_uom_id,
            minimum_order_quantity=entity.minimum_order_quantity,
            effective_from=entity.effective_from,
            effective_to=entity.effective_to,
            quantity_tier=tier_json,
            notes=entity.notes,
            status=entity.status.value,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class MaterialCostHistoryRepository(IMaterialCostHistoryRepository):
    """Repository implementation for cost history (immutable audit log)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_entry(self, history: MaterialCostHistory) -> MaterialCostHistory:
        """Append-only: insert new cost history record."""
        model = self._to_model(history)
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def list_by_material(
        self, tenant_id: UUID, material_id: UUID, limit: int = 100
    ) -> List[MaterialCostHistory]:
        """List cost history for material (newest first)."""
        stmt = (
            select(MaterialCostHistoryModel)
            .where(
                MaterialCostHistoryModel.tenant_id == tenant_id,
                MaterialCostHistoryModel.material_id == material_id,
            )
            .order_by(desc(MaterialCostHistoryModel.created_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_change_type(
        self, tenant_id: UUID, change_type: str, limit: int = 100
    ) -> List[MaterialCostHistory]:
        """List history entries by change type."""
        stmt = (
            select(MaterialCostHistoryModel)
            .where(
                MaterialCostHistoryModel.tenant_id == tenant_id,
                MaterialCostHistoryModel.change_type == change_type,
            )
            .order_by(desc(MaterialCostHistoryModel.created_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_id(
        self, tenant_id: UUID, history_id: UUID
    ) -> Optional[MaterialCostHistory]:
        """Get cost history record by ID."""
        stmt = select(MaterialCostHistoryModel).where(
            MaterialCostHistoryModel.tenant_id == tenant_id,
            MaterialCostHistoryModel.id == history_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    # ── Private conversion methods ──

    def _to_entity(self, model: MaterialCostHistoryModel) -> MaterialCostHistory:
        """Convert ORM model to domain entity."""
        return MaterialCostHistory(
            id=model.id,
            tenant_id=model.tenant_id,
            material_id=model.material_id,
            old_cost=Decimal(str(model.old_cost)) if model.old_cost else None,
            new_cost=Decimal(str(model.new_cost)),
            change_type=model.change_type,
            source_type=model.source_type,
            source_id=model.source_id,
            approved_by=model.approved_by,
            notes=model.notes,
            created_at=model.created_at,
        )

    def _to_model(self, entity: MaterialCostHistory) -> MaterialCostHistoryModel:
        """Convert domain entity to ORM model."""
        return MaterialCostHistoryModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            material_id=entity.material_id,
            old_cost=float(entity.old_cost) if entity.old_cost else None,
            new_cost=float(entity.new_cost),
            change_type=entity.change_type,
            source_type=entity.source_type,
            source_id=entity.source_id,
            approved_by=entity.approved_by,
            notes=entity.notes,
            created_at=entity.created_at,
        )


class StandardCostRevisionRepository(IStandardCostRevisionRepository):
    """Repository implementation for cost revision approvals."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, tenant_id: UUID, revision_id: UUID
    ) -> Optional[StandardCostRevision]:
        """Get revision by ID with tenant isolation and soft delete filter."""
        stmt = select(StandardCostRevisionModel).where(
            StandardCostRevisionModel.tenant_id == tenant_id,
            StandardCostRevisionModel.id == revision_id,
            StandardCostRevisionModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def get_by_id_for_update(
        self, tenant_id: UUID, revision_id: UUID
    ) -> Optional[StandardCostRevision]:
        """Lock a revision row while it is being approved or rejected."""
        stmt = (
            select(StandardCostRevisionModel)
            .where(
                StandardCostRevisionModel.tenant_id == tenant_id,
                StandardCostRevisionModel.id == revision_id,
                StandardCostRevisionModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def get_material_current_cost(
        self, tenant_id: UUID, material_id: UUID, *, lock: bool = False
    ) -> Optional[Decimal]:
        """Read a tenant-scoped material cost, optionally locking the material row."""
        stmt = select(MaterialModel.current_cost).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.id == material_id,
            MaterialModel.is_deleted.is_(False),
        )
        if lock:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        current_cost = result.scalar_one_or_none()
        return Decimal(str(current_cost)) if current_cost is not None else None

    async def update_material_current_cost(
        self,
        tenant_id: UUID,
        material_id: UUID,
        cost: Decimal,
        updated_by: UUID,
    ) -> bool:
        """Update approved standard cost on a locked, tenant-scoped material."""
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.id == material_id,
            MaterialModel.is_deleted.is_(False),
        ).with_for_update()
        result = await self._session.execute(stmt)
        material = result.scalars().first()
        if material is None:
            return False
        material.current_cost = cost
        material.updated_by = updated_by
        await self._session.flush()
        return True

    async def get_approved_cost(
        self, tenant_id: UUID, material_id: UUID
    ) -> Optional[StandardCostRevision]:
        """Return the latest approved revision for a material."""
        stmt = (
            select(StandardCostRevisionModel)
            .where(
                StandardCostRevisionModel.tenant_id == tenant_id,
                StandardCostRevisionModel.material_id == material_id,
                StandardCostRevisionModel.status == StandardCostRevisionStatus.APPROVED.value,
                StandardCostRevisionModel.is_deleted.is_(False),
            )
            .order_by(desc(StandardCostRevisionModel.approved_at), desc(StandardCostRevisionModel.created_at))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def list_by_material(
        self, tenant_id: UUID, material_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[StandardCostRevision]:
        """List revisions for a material (all statuses)."""
        stmt = (
            select(StandardCostRevisionModel)
            .where(
                StandardCostRevisionModel.tenant_id == tenant_id,
                StandardCostRevisionModel.material_id == material_id,
                StandardCostRevisionModel.is_deleted.is_(False),
            )
            .order_by(desc(StandardCostRevisionModel.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_pending(
        self, tenant_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[StandardCostRevision]:
        """List pending revisions awaiting approval."""
        stmt = (
            select(StandardCostRevisionModel)
            .where(
                StandardCostRevisionModel.tenant_id == tenant_id,
                StandardCostRevisionModel.status == StandardCostRevisionStatus.PENDING.value,
                StandardCostRevisionModel.is_deleted.is_(False),
            )
            .order_by(desc(StandardCostRevisionModel.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_pending(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(StandardCostRevisionModel).where(
            StandardCostRevisionModel.tenant_id == tenant_id,
            StandardCostRevisionModel.status == StandardCostRevisionStatus.PENDING.value,
            StandardCostRevisionModel.is_deleted.is_(False),
        )
        return int(await self._session.scalar(stmt) or 0)

    async def count_by_material(self, tenant_id: UUID, material_id: UUID) -> int:
        stmt = select(func.count()).select_from(StandardCostRevisionModel).where(
            StandardCostRevisionModel.tenant_id == tenant_id,
            StandardCostRevisionModel.material_id == material_id,
            StandardCostRevisionModel.is_deleted.is_(False),
        )
        return int(await self._session.scalar(stmt) or 0)

    async def list_by_requester(
        self, tenant_id: UUID, requester_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[StandardCostRevision]:
        """List revisions requested by a specific user."""
        stmt = (
            select(StandardCostRevisionModel)
            .where(
                StandardCostRevisionModel.tenant_id == tenant_id,
                StandardCostRevisionModel.requested_by == requester_id,
                StandardCostRevisionModel.is_deleted.is_(False),
            )
            .order_by(desc(StandardCostRevisionModel.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_tenant(
        self, tenant_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[StandardCostRevision]:
        """List all revisions for tenant."""
        stmt = (
            select(StandardCostRevisionModel)
            .where(
                StandardCostRevisionModel.tenant_id == tenant_id,
                StandardCostRevisionModel.is_deleted.is_(False),
            )
            .order_by(desc(StandardCostRevisionModel.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save(self, revision: StandardCostRevision) -> StandardCostRevision:
        """Insert or update revision."""
        values = self._to_model(revision)
        model = await self._session.get(StandardCostRevisionModel, revision.id)
        if model is not None and model.tenant_id != revision.tenant_id:
            raise ValueError("Standard cost revision not found for tenant")
        if model is None:
            model = values
            self._session.add(model)
        else:
            for column in StandardCostRevisionModel.__table__.columns:
                setattr(model, column.name, getattr(values, column.name))
        await self._session.flush()
        return self._to_entity(model)

    async def delete(self, tenant_id: UUID, revision_id: UUID) -> None:
        """Soft-delete revision."""
        stmt = select(StandardCostRevisionModel).where(
            StandardCostRevisionModel.tenant_id == tenant_id,
            StandardCostRevisionModel.id == revision_id,
            StandardCostRevisionModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        if model:
            model.is_deleted = True
            await self._session.flush()

    # ── Private conversion methods ──

    def _to_entity(self, model: StandardCostRevisionModel) -> StandardCostRevision:
        """Convert ORM model to domain entity."""
        return StandardCostRevision(
            id=model.id,
            tenant_id=model.tenant_id,
            material_id=model.material_id,
            requested_by=model.requested_by,
            requested_cost=Decimal(str(model.requested_cost)),
            current_cost=Decimal(str(model.current_cost)),
            reason=model.reason,
            notes=model.notes,
            status=StandardCostRevisionStatus(model.status),
            approved_by=model.approved_by,
            approved_at=model.approved_at,
            rejection_reason=model.rejection_reason,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: StandardCostRevision) -> StandardCostRevisionModel:
        """Convert domain entity to ORM model."""
        return StandardCostRevisionModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            material_id=entity.material_id,
            requested_by=entity.requested_by,
            requested_cost=float(entity.requested_cost),
            current_cost=float(entity.current_cost),
            reason=entity.reason,
            notes=entity.notes,
            status=entity.status.value,
            approved_by=entity.approved_by,
            approved_at=entity.approved_at,
            rejection_reason=entity.rejection_reason,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class PriceOverrideRecordRepository(IPriceOverrideRecordRepository):
    """Repository implementation for price override records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, tenant_id: UUID, record_id: UUID
    ) -> Optional[PriceOverrideRecord]:
        """Get override record by ID with tenant isolation and soft delete filter."""
        stmt = select(PriceOverrideRecordModel).where(
            PriceOverrideRecordModel.tenant_id == tenant_id,
            PriceOverrideRecordModel.id == record_id,
            PriceOverrideRecordModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def list_by_material(
        self, tenant_id: UUID, material_id: UUID, limit: int = 50
    ) -> List[PriceOverrideRecord]:
        """List override records for a material (newest first)."""
        stmt = (
            select(PriceOverrideRecordModel)
            .where(
                PriceOverrideRecordModel.tenant_id == tenant_id,
                PriceOverrideRecordModel.material_id == material_id,
                PriceOverrideRecordModel.is_deleted.is_(False),
            )
            .order_by(desc(PriceOverrideRecordModel.created_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_grn(
        self, tenant_id: UUID, grn_id: UUID
    ) -> List[PriceOverrideRecord]:
        """List overrides associated with a GRN."""
        stmt = (
            select(PriceOverrideRecordModel)
            .where(
                PriceOverrideRecordModel.tenant_id == tenant_id,
                PriceOverrideRecordModel.grn_id == grn_id,
                PriceOverrideRecordModel.is_deleted.is_(False),
            )
            .order_by(desc(PriceOverrideRecordModel.created_at))
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_override_reason(
        self, tenant_id: UUID, reason: str, limit: int = 50
    ) -> List[PriceOverrideRecord]:
        """List overrides by reason."""
        stmt = (
            select(PriceOverrideRecordModel)
            .where(
                PriceOverrideRecordModel.tenant_id == tenant_id,
                PriceOverrideRecordModel.override_reason == reason,
                PriceOverrideRecordModel.is_deleted.is_(False),
            )
            .order_by(desc(PriceOverrideRecordModel.created_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_tenant(
        self, tenant_id: UUID, limit: int = 100
    ) -> List[PriceOverrideRecord]:
        """List all override records for tenant (newest first)."""
        stmt = (
            select(PriceOverrideRecordModel)
            .where(
                PriceOverrideRecordModel.tenant_id == tenant_id,
                PriceOverrideRecordModel.is_deleted.is_(False),
            )
            .order_by(desc(PriceOverrideRecordModel.created_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save(self, record: PriceOverrideRecord) -> PriceOverrideRecord:
        """Insert new override record."""
        model = self._to_model(record)
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def delete(self, tenant_id: UUID, record_id: UUID) -> None:
        """Soft-delete override record."""
        stmt = select(PriceOverrideRecordModel).where(
            PriceOverrideRecordModel.tenant_id == tenant_id,
            PriceOverrideRecordModel.id == record_id,
            PriceOverrideRecordModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        if model:
            model.is_deleted = True
            await self._session.flush()

    # ── Private conversion methods ──

    def _to_entity(self, model: PriceOverrideRecordModel) -> PriceOverrideRecord:
        """Convert ORM model to domain entity."""
        return PriceOverrideRecord(
            id=model.id,
            tenant_id=model.tenant_id,
            material_id=model.material_id,
            grn_id=model.grn_id,
            suggested_price=Decimal(str(model.suggested_price)),
            override_price=Decimal(str(model.override_price)),
            override_reason=model.override_reason,
            override_by=model.override_by,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: PriceOverrideRecord) -> PriceOverrideRecordModel:
        """Convert domain entity to ORM model."""
        return PriceOverrideRecordModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            material_id=entity.material_id,
            grn_id=entity.grn_id,
            suggested_price=float(entity.suggested_price),
            override_price=float(entity.override_price),
            override_reason=entity.override_reason,
            override_by=entity.override_by,
            notes=entity.notes,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
