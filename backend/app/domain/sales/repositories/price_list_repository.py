"""Price List Repository."""

from typing import Type
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from backend.app.domain.sales.entities.price_list import PriceList, PriceListLine
from backend.app.domain.sales.exceptions import (
    InvalidProductTypeError,
    ProductInactiveError,
    ProductNotFoundError,
)
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.sales_models import (
    PriceListLineModel,
    PriceListModel,
)
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class PriceListRepository(BaseRepository):
    """Repository for PriceList aggregate root."""

    def _model_class(self) -> Type[PriceListModel]:
        """Return the SQLAlchemy model class."""
        return PriceListModel

    def _to_entity(self, model: PriceListModel) -> PriceList | None:
        """Convert ORM model to domain entity."""
        if not model:
            return None

        lines = [
            PriceListLine(
                id=line.id,
                price_list_id=model.id,
                product_id=line.product_id,
                product_type=line.product_type,
                unit_price=line.unit_price,
                created_at=line.created_at,
                updated_at=line.updated_at,
            )
            for line in (model.lines or [])
        ]

        return PriceList(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            is_default=model.is_default,
            is_active=model.is_active,
            valid_from=model.valid_from,
            valid_to=model.valid_to,
            lines=lines,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: PriceList) -> PriceListModel:
        """Convert domain entity to ORM model."""
        return PriceListModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            name=entity.name,
            is_default=entity.is_default,
            is_active=entity.is_active,
            valid_from=entity.valid_from,
            valid_to=entity.valid_to,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            lines=[
                PriceListLineModel(
                    id=line.id,
                    price_list_id=entity.id,
                    product_id=line.product_id,
                    product_type=line.product_type,
                    unit_price=line.unit_price,
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
        enrich: bool = True,
    ) -> PriceList | None:
        """Get a price list aggregate with pricing lines loaded."""
        stmt = (
            select(self._model_class())
            .options(selectinload(PriceListModel.lines))
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
        if entity and enrich:
            await self._enrich_lines_with_product_metadata(entity.lines, tenant_id)
        return entity

    async def get_by_id_for_update(
        self,
        id: UUID,
        tenant_id: UUID,
    ) -> PriceList | None:
        """Get a price list aggregate with row-level lock (FOR UPDATE) for concurrent line mutations."""
        stmt = (
            select(self._model_class())
            .options(selectinload(PriceListModel.lines))
            .where(
                self._model_class().id == id,
                self._model_class().tenant_id == tenant_id,
                self._model_class().is_deleted.is_(False),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def validate_product_for_pricing(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
    ) -> None:
        """Validate product exists, is active, belongs to tenant, and matches product_type.

        Strictly prevents leaking cross-tenant records by returning generic ProductNotFoundError.
        """
        if product_type == "variant":
            stmt = select(ItemVariantModel).where(
                ItemVariantModel.id == product_id,
                ItemVariantModel.tenant_id == tenant_id,
                ItemVariantModel.is_deleted.is_(False),
            )
            result = await self._session.execute(stmt)
            variant = result.scalar_one_or_none()
            if not variant:
                raise ProductNotFoundError(product_id)
            if not variant.is_active:
                raise ProductInactiveError(variant.code)
            return

        elif product_type == "finished_product":
            stmt = select(MaterialModel).where(
                MaterialModel.id == product_id,
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.is_deleted.is_(False),
            )
            result = await self._session.execute(stmt)
            material = result.scalar_one_or_none()
            if not material:
                raise ProductNotFoundError(product_id)
            if material.material_type != "finished":
                raise InvalidProductTypeError(material.code, material.material_type)
            if not material.is_active:
                raise ProductInactiveError(material.code)
            return

        raise ValueError(f"Invalid product type '{product_type}'. Must be 'variant' or 'finished_product'.")

    async def _enrich_lines_with_product_metadata(
        self,
        lines: list[PriceListLine],
        tenant_id: UUID,
    ) -> None:
        """Batch-enrich price list lines with SKU, name, and UOM.

        Handles active, inactive, soft-deleted, and orphaned lines.
        
        Enrichment Strategy:
        1. Initial batch queries: variant_ids → variants, material_ids → materials
        2. Fallback cross-type queries: Handle cases where product_type was misclassified
           in legacy data by re-querying unmatched IDs as the alternate type.
        3. UOM resolution: Batch query all referenced UOM records.
        4. Metadata population: Assign enriched fields (code, name, UOM, is_orphaned, is_inactive).
        
        All queries include tenant_id filter to maintain strict multi-tenant isolation.
        """
        if not lines:
            return

        from backend.app.infrastructure.logging import get_logger
        logger = get_logger(__name__)

        variant_ids: set[UUID] = set()
        material_ids: set[UUID] = set()

        for line in lines:
            ptype = str(getattr(line, "product_type", "")).lower()
            if ptype == "variant":
                variant_ids.add(line.product_id)
            elif ptype == "finished_product":
                material_ids.add(line.product_id)
            else:
                variant_ids.add(line.product_id)

        variant_map: dict[UUID, ItemVariantModel] = {}
        material_map: dict[UUID, MaterialModel] = {}
        uom_ids: set[UUID] = set()

        # ─────────────────────────────────────────────────────────────────────
        # Batch 1: Query variants by their declared product_type
        # ─────────────────────────────────────────────────────────────────────
        if variant_ids:
            stmt = select(ItemVariantModel).where(
                ItemVariantModel.id.in_(variant_ids),
                ItemVariantModel.tenant_id == tenant_id,
            )
            res = await self._session.execute(stmt)
            for v in res.scalars().all():
                variant_map[v.id] = v
                if v.base_unit_id:
                    uom_ids.add(v.base_unit_id)

        # ─────────────────────────────────────────────────────────────────────
        # Batch 2: Query materials by their declared product_type
        # ─────────────────────────────────────────────────────────────────────
        if material_ids:
            stmt = select(MaterialModel).where(
                MaterialModel.id.in_(material_ids),
                MaterialModel.tenant_id == tenant_id,
            )
            res = await self._session.execute(stmt)
            for m in res.scalars().all():
                material_map[m.id] = m
                if m.base_unit_id:
                    uom_ids.add(m.base_unit_id)

        # ─────────────────────────────────────────────────────────────────────
        # Batch 3 & 4: Fallback cross-type queries for misclassified products
        # ─────────────────────────────────────────────────────────────────────
        # This handles legacy data where product_type in a PriceListLine may not
        # accurately reflect the actual entity type. For example, a line recorded
        # as product_type='variant' might actually point to a finished_product.
        # We attempt recovery by re-querying unmatched IDs in the opposite type.
        
        missing_v = variant_ids - set(variant_map.keys())
        if missing_v:
            logger.warning(
                "Enrichment fallback: Re-querying as materials (product_type mismatch)",
                extra={
                    "tenant_id": str(tenant_id),
                    "misclassified_variant_ids": [str(uid) for uid in missing_v],
                    "count": len(missing_v),
                },
            )
            stmt = select(MaterialModel).where(
                MaterialModel.id.in_(missing_v),
                MaterialModel.tenant_id == tenant_id,
            )
            res = await self._session.execute(stmt)
            for m in res.scalars().all():
                material_map[m.id] = m
                if m.base_unit_id:
                    uom_ids.add(m.base_unit_id)

        missing_m = material_ids - set(material_map.keys())
        if missing_m:
            logger.warning(
                "Enrichment fallback: Re-querying as variants (product_type mismatch)",
                extra={
                    "tenant_id": str(tenant_id),
                    "misclassified_material_ids": [str(uid) for uid in missing_m],
                    "count": len(missing_m),
                },
            )
            stmt = select(ItemVariantModel).where(
                ItemVariantModel.id.in_(missing_m),
                ItemVariantModel.tenant_id == tenant_id,
            )
            res = await self._session.execute(stmt)
            for v in res.scalars().all():
                variant_map[v.id] = v
                if v.base_unit_id:
                    uom_ids.add(v.base_unit_id)

        # ─────────────────────────────────────────────────────────────────────
        # Batch 5: Query UOMs for all referenced base_unit_id
        # ─────────────────────────────────────────────────────────────────────
        uom_map: dict[UUID, UnitOfMeasureModel] = {}
        if uom_ids:
            stmt = select(UnitOfMeasureModel).where(
                UnitOfMeasureModel.id.in_(uom_ids),
                UnitOfMeasureModel.tenant_id == tenant_id,
            )
            res = await self._session.execute(stmt)
            for u in res.scalars().all():
                uom_map[u.id] = u

        # ─────────────────────────────────────────────────────────────────────
        # Batch 6: Populate line metadata
        # ─────────────────────────────────────────────────────────────────────
        for line in lines:
            ptype = str(getattr(line, "product_type", "")).lower()
            product = None
            if ptype == "variant":
                product = variant_map.get(line.product_id) or material_map.get(line.product_id)
            else:
                product = material_map.get(line.product_id) or variant_map.get(line.product_id)

            if product is not None:
                line.product_code = product.code
                line.product_name = product.name
                line.is_inactive = not getattr(product, "is_active", True)
                line.is_orphaned = getattr(product, "is_deleted", False)
                uom_id = getattr(product, "base_unit_id", None)
                uom = uom_map.get(uom_id) if uom_id else None
                line.uom_code = uom.code if uom else None
                line.uom_name = uom.name if uom else None
            else:
                # Product not found in either variant or material tables
                # Mark as orphaned to signal data quality issue in UI
                line.product_code = None
                line.product_name = "Unknown Product"
                line.uom_code = None
                line.uom_name = None
                line.is_orphaned = True
                line.is_inactive = False
                logger.warning(
                    "Enrichment failed: Product not found in any source",
                    extra={
                        "tenant_id": str(tenant_id),
                        "product_id": str(line.product_id),
                        "product_type": ptype,
                    },
                )

    async def find_default(
        self,
        tenant_id: UUID,
        include_inactive: bool = False,
    ) -> list[PriceList]:
        """Find default price lists for a tenant."""
        stmt = (
            select(self._model_class())
            .options(selectinload(PriceListModel.lines))
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().is_default.is_(True),
                self._model_class().is_deleted.is_(False),
            )
        )

        if not include_inactive:
            stmt = stmt.where(self._model_class().is_active.is_(True))

        stmt = stmt.order_by(self._model_class().valid_from.desc())

        result = await self._session.execute(stmt)
        models = result.scalars().unique().all()
        return [self._to_entity(m) for m in models]

    async def find_by_client(
        self,
        tenant_id: UUID,
        client_id: UUID,
        include_inactive: bool = False,
    ) -> list[PriceList]:
        """Find the client's assigned default price list (0 or 1 result).

        Step 1: look up the client's default_price_list_id from sales_clients.
        Step 2: if found, load the PriceList aggregate with lines.
        Returns a list with 0 or 1 elements.
        """
        from backend.app.infrastructure.persistence.models.sales_models import ClientModel

        # Step 1: fetch the FK from the client row
        client_stmt = select(ClientModel.default_price_list_id).where(
            ClientModel.id == client_id,
            ClientModel.tenant_id == tenant_id,
            ClientModel.is_deleted.is_(False),
        )
        result = await self._session.execute(client_stmt)
        price_list_id = result.scalar_one_or_none()

        if not price_list_id:
            return []

        # Step 2: load the referenced PriceList aggregate with lines
        stmt = (
            select(PriceListModel)
            .options(selectinload(PriceListModel.lines))
            .where(
                PriceListModel.id == price_list_id,
                PriceListModel.tenant_id == tenant_id,
                PriceListModel.is_deleted.is_(False),
            )
        )
        if not include_inactive:
            stmt = stmt.where(PriceListModel.is_active.is_(True))

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return [self._to_entity(model)] if model else []

    async def unset_all_defaults(self, tenant_id: UUID, exclude_id: UUID) -> None:
        """Atomically unset is_default on all price lists for a tenant except one.

        Used when promoting a new default to ensure the single-default invariant.
        """
        stmt = (
            update(PriceListModel)
            .where(
                PriceListModel.tenant_id == tenant_id,
                PriceListModel.id != exclude_id,
                PriceListModel.is_default.is_(True),
                PriceListModel.is_deleted.is_(False),
            )
            .values(is_default=False)
        )
        await self._session.execute(stmt)

    async def find_by_exact_name(
        self,
        tenant_id: UUID,
        name: str,
        exclude_id: UUID | None = None,
    ) -> PriceList | None:
        """Find a price list matching a name exactly (case-insensitive), optionally excluding one ID."""
        stmt = (
            select(PriceListModel)
            .options(selectinload(PriceListModel.lines))
            .where(
                PriceListModel.tenant_id == tenant_id,
                PriceListModel.name.ilike(name),
                PriceListModel.is_deleted.is_(False),
            )
        )
        if exclude_id is not None:
            stmt = stmt.where(PriceListModel.id != exclude_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_by_name(
        self,
        tenant_id: UUID,
        name: str,
        include_inactive: bool = False,
    ) -> list[PriceList]:
        """Find price lists by name."""
        stmt = (
            select(self._model_class())
            .options(selectinload(PriceListModel.lines))
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().name.ilike(f"%{name}%"),
                self._model_class().is_deleted.is_(False),
            )
        )

        if not include_inactive:
            stmt = stmt.where(self._model_class().is_active.is_(True))

        stmt = stmt.order_by(self._model_class().name.asc())

        result = await self._session.execute(stmt)
        models = result.scalars().unique().all()
        return [self._to_entity(m) for m in models]

    async def find_active_on_date(
        self,
        tenant_id: UUID,
        check_date,
        is_default: bool | None = None,
    ) -> list[PriceList]:
        """Find price lists active on a specific date."""
        stmt = (
            select(self._model_class())
            .options(selectinload(PriceListModel.lines))
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
                self._model_class().valid_from <= check_date,
            )
        )

        stmt = stmt.where(
            (self._model_class().valid_to.is_(None))
            | (self._model_class().valid_to >= check_date)
        )

        if is_default is not None:
            stmt = stmt.where(self._model_class().is_default.is_(is_default))

        stmt = stmt.order_by(self._model_class().is_default.desc())

        result = await self._session.execute(stmt)
        models = result.scalars().unique().all()
        return [self._to_entity(m) for m in models]
