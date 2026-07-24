"""Price List Repository."""

from typing import Type
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from backend.app.domain.sales.entities.price_list import PriceList, PriceListLine
from backend.app.infrastructure.persistence.models.sales_models import (
    PriceListLineModel,
    PriceListModel,
)
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
        return self._to_entity(model) if model else None

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
