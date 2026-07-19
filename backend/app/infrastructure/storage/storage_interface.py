from __future__ import annotations

import uuid
from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StorageResult:
    """Returned by IStorageService.save()."""
    file_path: str        # Absolute or relative path on disk
    url: str              # URL for HTTP access (e.g. /uploads/...)
    filename: str         # Original sanitized filename
    content_type: str
    size_bytes: int


class IStorageService:
    """
    Abstract file storage interface.

    Swap LocalStorageService with S3StorageService or GCSStorageService
    by registering a different implementation in the DI Container.
    """

    VALID_CATEGORIES = frozenset({
        "invoices", "certificates", "documents",
        "images", "reports", "quality",
    })

    @abstractmethod
    async def save(
        self,
        file_content: bytes,
        original_filename: str,
        content_type: str,
        tenant_id: uuid.UUID,
        category: str = "documents",
    ) -> StorageResult: ...

    @abstractmethod
    async def delete(self, file_path: str) -> None: ...

    @abstractmethod
    def get_url(self, file_path: str) -> str: ...
