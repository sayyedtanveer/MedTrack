"""Document entity for generated PDFs with versioning."""

from __future__ import annotations

import uuid
from datetime import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class Signature:
    """Signature metadata for documents."""
    name: str
    timestamp: datetime
    signature_image_url: Optional[str] = None


@dataclass
class Document:
    """Generated document entity with versioning and audit trail."""
    
    id: uuid.UUID
    tenant_id: uuid.UUID
    document_type: str
    entity_id: uuid.UUID
    version_number: int
    file_path: str
    generated_by: Optional[uuid.UUID]
    generated_at: datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    
    def increment_version(self) -> "Document":
        """Create a new version of this document."""
        return Document(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            document_type=self.document_type,
            entity_id=self.entity_id,
            version_number=self.version_number + 1,
            file_path="",  # Will be set after generation
            generated_by=self.generated_by,
            generated_at=datetime.utcnow(),
            is_deleted=False,
            deleted_at=None,
        )
