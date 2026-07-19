"""
File storage service for product images.
Supports local storage and S3 (future).
"""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import aiofiles


class FileStorageProvider(ABC):
    """Abstract base class for file storage implementations."""

    @abstractmethod
    async def upload(self, file_data: bytes, file_name: str, tenant_id: uuid.UUID) -> Tuple[str, int]:
        """
        Upload a file and return (file_path, file_size).
        
        Args:
            file_data: Binary content of the file
            file_name: Original file name
            tenant_id: Tenant ID for organizing files
            
        Returns:
            Tuple of (file_path, file_size_bytes)
        """
        pass

    @abstractmethod
    async def delete(self, file_path: str, tenant_id: uuid.UUID) -> bool:
        """Delete a file by path."""
        pass

    @abstractmethod
    async def get_url(self, file_path: str, tenant_id: uuid.UUID) -> str:
        """Get the URL/path for accessing the file."""
        pass


class LocalFileStorage(FileStorageProvider):
    """
    Local file system storage provider.
    Stores files in a local directory with tenant-based organization.
    """

    def __init__(self, base_path: str = "./uploads/product_images"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload(self, file_data: bytes, file_name: str, tenant_id: uuid.UUID) -> Tuple[str, int]:
        """Upload a file to local storage."""
        # Organize by tenant
        tenant_dir = self.base_path / str(tenant_id)
        tenant_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename to avoid collisions
        unique_name = f"{uuid.uuid4()}_{file_name}"
        file_path = tenant_dir / unique_name

        # Write file
        async with aiofiles.open(str(file_path), "wb") as f:
            await f.write(file_data)

        file_size = len(file_data)

        # Return relative path for storage in DB
        relative_path = f"product_images/{tenant_id}/{unique_name}"
        return relative_path, file_size

    async def delete(self, file_path: str, tenant_id: uuid.UUID) -> bool:
        """Delete a file from local storage."""
        full_path = self.base_path / file_path.replace(f"product_images/{tenant_id}/", "")
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    async def get_url(self, file_path: str, tenant_id: uuid.UUID) -> str:
        """Get the URL for accessing the file."""
        # For local files, return the relative path (or HTTP path if behind a web server)
        return f"/api/v1/files/{file_path}"


class S3FileStorage(FileStorageProvider):
    """
    AWS S3 storage provider (placeholder for future implementation).
    """

    def __init__(self, bucket_name: str, region: str = "us-east-1", prefix: str = "product-images"):
        self.bucket_name = bucket_name
        self.region = region
        self.prefix = prefix
        # boto3 client would be initialized here

    async def upload(self, file_data: bytes, file_name: str, tenant_id: uuid.UUID) -> Tuple[str, int]:
        """Upload a file to S3."""
        # Implementation would use boto3/aioboto3
        raise NotImplementedError("S3 storage not yet implemented")

    async def delete(self, file_path: str, tenant_id: uuid.UUID) -> bool:
        """Delete a file from S3."""
        raise NotImplementedError("S3 storage not yet implemented")

    async def get_url(self, file_path: str, tenant_id: uuid.UUID) -> str:
        """Get the S3 URL for accessing the file."""
        raise NotImplementedError("S3 storage not yet implemented")


# Global storage provider instance (configured at startup)
_storage_provider: Optional[FileStorageProvider] = None


def get_file_storage() -> FileStorageProvider:
    """Get the configured file storage provider."""
    global _storage_provider
    if _storage_provider is None:
        # Default to local storage
        _storage_provider = LocalFileStorage()
    return _storage_provider


def set_file_storage(provider: FileStorageProvider) -> None:
    """Configure the file storage provider."""
    global _storage_provider
    _storage_provider = provider
