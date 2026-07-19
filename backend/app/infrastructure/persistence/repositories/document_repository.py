"""Document repository implementation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.documents.repositories.document_repository_interface import IDocumentRepository
from backend.app.domain.documents.entities.document import Document
from backend.app.infrastructure.persistence.models.document_model import DocumentModel


class DocumentRepository(IDocumentRepository):
    """SQLAlchemy implementation of document repository."""

    def __init__(self, session: AsyncSession):
        """Initialize document repository.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def save(self, document: Document) -> Document:
        """Save a new document.
        
        Args:
            document: Document entity to save
            
        Returns:
            Saved document entity
        """
        model = DocumentModel(
            id=document.id,
            tenant_id=document.tenant_id,
            document_type=document.document_type,
            entity_id=document.entity_id,
            version_number=document.version_number,
            file_path=document.file_path,
            generated_by=document.generated_by,
            generated_at=document.generated_at,
            is_deleted=document.is_deleted,
            deleted_at=document.deleted_at,
        )
        
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        
        return self._model_to_entity(model)

    async def find_by_id(self, document_id: uuid.UUID) -> Optional[Document]:
        """Find a document by ID.
        
        Args:
            document_id: Document UUID
            
        Returns:
            Document entity if found, None otherwise
        """
        stmt = select(DocumentModel).where(
            DocumentModel.id == document_id,
            DocumentModel.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            return self._model_to_entity(model)
        return None

    async def find_latest_version(
        self,
        tenant_id: uuid.UUID,
        document_type: str,
        entity_id: uuid.UUID,
    ) -> Optional[Document]:
        """Find the latest version of a document.
        
        Args:
            tenant_id: Tenant UUID
            document_type: Type of document
            entity_id: Entity UUID
            
        Returns:
            Latest document version if found, None otherwise
        """
        stmt = (
            select(DocumentModel)
            .where(
                DocumentModel.tenant_id == tenant_id,
                DocumentModel.document_type == document_type,
                DocumentModel.entity_id == entity_id,
                DocumentModel.is_deleted.is_(False),
            )
            .order_by(desc(DocumentModel.version_number))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            return self._model_to_entity(model)
        return None

    async def list_versions(
        self,
        tenant_id: uuid.UUID,
        document_type: str,
        entity_id: uuid.UUID,
    ) -> List[Document]:
        """List all versions of a document.
        
        Args:
            tenant_id: Tenant UUID
            document_type: Type of document
            entity_id: Entity UUID
            
        Returns:
            List of document versions, ordered by version number (newest first)
        """
        stmt = (
            select(DocumentModel)
            .where(
                DocumentModel.tenant_id == tenant_id,
                DocumentModel.document_type == document_type,
                DocumentModel.entity_id == entity_id,
                DocumentModel.is_deleted.is_(False),
            )
            .order_by(desc(DocumentModel.version_number))
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]

    async def soft_delete(self, document_id: uuid.UUID) -> None:
        """Soft delete a document.
        
        Args:
            document_id: Document UUID
        """
        stmt = select(DocumentModel).where(DocumentModel.id == document_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            model.is_deleted = True
            model.deleted_at = datetime.now(timezone.utc)
            await self.session.flush()

    def _model_to_entity(self, model: DocumentModel) -> Document:
        """Convert DocumentModel to Document entity.
        
        Args:
            model: DocumentModel instance
            
        Returns:
            Document entity
        """
        return Document(
            id=model.id,
            tenant_id=model.tenant_id,
            document_type=model.document_type,
            entity_id=model.entity_id,
            version_number=model.version_number,
            file_path=model.file_path,
            generated_by=model.generated_by,
            generated_at=model.generated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )
