"""Document repository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Optional, List

from backend.app.domain.documents.entities.document import Document


class IDocumentRepository(ABC):
    """Repository interface for document persistence operations."""

    @abstractmethod
    async def save(self, document: Document) -> Document:
        """Save a new document."""
        pass

    @abstractmethod
    async def find_by_id(self, document_id: uuid.UUID) -> Optional[Document]:
        """Find a document by ID."""
        pass

    @abstractmethod
    async def find_latest_version(
        self,
        tenant_id: uuid.UUID,
        document_type: str,
        entity_id: uuid.UUID,
    ) -> Optional[Document]:
        """Find the latest version of a document."""
        pass

    @abstractmethod
    async def list_versions(
        self,
        tenant_id: uuid.UUID,
        document_type: str,
        entity_id: uuid.UUID,
    ) -> List[Document]:
        """List all versions of a document."""
        pass

    @abstractmethod
    async def soft_delete(self, document_id: uuid.UUID) -> None:
        """Soft delete a document."""
        pass
