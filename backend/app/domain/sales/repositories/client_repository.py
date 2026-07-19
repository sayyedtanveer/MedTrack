"""Client Repository."""

from typing import Type
from uuid import UUID

from sqlalchemy import or_, select

from backend.app.domain.sales.entities.client import Client
from backend.app.infrastructure.persistence.models.sales_models import ClientModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class ClientRepository(BaseRepository):
    """Repository for Client aggregate root."""

    def _model_class(self) -> Type[ClientModel]:
        """Return the SQLAlchemy model class."""
        return ClientModel

    def _to_entity(self, model: ClientModel) -> Client:
        """Convert ORM model → domain entity."""
        if not model:
            return None
        return Client(
            id=model.id,
            tenant_id=model.tenant_id,
            code=model.code,
            name=model.name,
            email=model.email,
            phone=model.phone,
            address=model.address,
            gst_number=model.gst_number,
            payment_terms_days=model.payment_terms_days,
            is_active=model.is_active,
            credit_limit=model.credit_limit,
            credit_used=model.credit_used,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Client) -> ClientModel:
        """Convert domain entity → ORM model."""
        return ClientModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            code=entity.code,
            name=entity.name,
            email=entity.email,
            phone=entity.phone,
            address=entity.address,
            gst_number=entity.gst_number,
            payment_terms_days=entity.payment_terms_days,
            is_active=entity.is_active,
            credit_limit=entity.credit_limit,
            credit_used=entity.credit_used,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_code(self, tenant_id: UUID, code: str) -> Client | None:
        """
        Get client by code.
        
        Args:
            tenant_id: Tenant ID
            code: Client code
            
        Returns:
            Client or None if not found
        """
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().code == code,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_by_status(
        self,
        tenant_id: UUID,
        is_active: bool = True,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Client]:
        """
        Find clients by active status.
        
        Args:
            tenant_id: Tenant ID
            is_active: Whether to find active or inactive clients
            limit: Result limit
            offset: Result offset
            
        Returns:
            List of clients
        """
        filters = [
            self._model_class().tenant_id == tenant_id,
            self._model_class().is_active.is_(is_active),
            self._model_class().is_deleted.is_(False),
        ]
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    self._model_class().code.ilike(pattern),
                    self._model_class().name.ilike(pattern),
                    self._model_class().email.ilike(pattern),
                )
            )

        stmt = (
            select(self._model_class())
            .where(*filters)
            .order_by(self._model_class().created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def find_with_high_credit_usage(
        self,
        tenant_id: UUID,
        threshold_percent: float = 80.0,
    ) -> list[Client]:
        """
        Find clients using more than threshold % of their credit limit.
        
        Args:
            tenant_id: Tenant ID
            threshold_percent: Percentage threshold (0-100)
            
        Returns:
            List of clients with high credit usage
        """
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().is_active.is_(True),
                self._model_class().is_deleted.is_(False),
                self._model_class().credit_limit.isnot(None),
            )
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        high_usage = []
        for model in models:
            client = self._to_entity(model)
            if client.credit_limit and client.credit_limit > 0:
                usage_percent = (float(client.credit_used) / float(client.credit_limit)) * 100
                if usage_percent >= threshold_percent:
                    high_usage.append(client)
        
        return high_usage


