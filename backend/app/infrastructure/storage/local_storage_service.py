from __future__ import annotations

import mimetypes
import os
import uuid
from pathlib import Path

import aiofiles

from backend.app.infrastructure.storage.storage_interface import IStorageService, StorageResult


class LocalStorageService(IStorageService):
    """
    Saves uploaded files to the local filesystem.

    Directory layout:
        UPLOAD_DIR/{tenant_id}/{category}/{uuid}_{sanitized_filename}

    Returns a relative URL:
        /uploads/{tenant_id}/{category}/{uuid}_{sanitized_filename}

    Swap for S3StorageService later by replacing this class in the Container.
    """

    def __init__(self, upload_dir: str, base_url: str = "") -> None:
        self._upload_dir = Path(upload_dir).resolve()
        self._base_url = base_url.rstrip("/")

    async def save(
        self,
        file_content: bytes,
        original_filename: str,
        content_type: str,
        tenant_id: uuid.UUID,
        category: str = "documents",
    ) -> StorageResult:
        if category not in self.VALID_CATEGORIES:
            category = "documents"

        # Sanitize filename
        safe_name = "".join(
            c if c.isalnum() or c in (".", "-", "_") else "_"
            for c in original_filename
        )
        unique_name = f"{uuid.uuid4().hex}_{safe_name}"

        # Ensure directory exists
        target_dir = self._upload_dir / str(tenant_id) / category
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / unique_name

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        relative = f"{tenant_id}/{category}/{unique_name}"
        return StorageResult(
            file_path=str(file_path),
            url=f"/uploads/{relative}",
            filename=unique_name,
            content_type=content_type,
            size_bytes=len(file_content),
        )

    async def delete(self, file_path: str) -> None:
        path = Path(file_path)
        if path.exists():
            path.unlink()

    def get_url(self, file_path: str) -> str:
        # Convert absolute path back to relative URL
        try:
            rel = Path(file_path).relative_to(self._upload_dir)
            return f"/uploads/{rel.as_posix()}"
        except ValueError:
            return file_path
