"""Document storage service for managing PDF files."""

from __future__ import annotations

import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional


class DocumentStorageService:
    """Service for storing and managing document PDF files."""

    def __init__(self, base_storage_path: str = "storage/documents"):
        """Initialize document storage service.
        
        Args:
            base_storage_path: Base directory for document storage
        """
        self.base_storage_path = Path(base_storage_path)
        self._ensure_base_directory()

    def _ensure_base_directory(self) -> None:
        """Ensure base storage directory exists."""
        self.base_storage_path.mkdir(parents=True, exist_ok=True)

    def _get_document_directory(
        self,
        tenant_id: uuid.UUID,
        document_type: str,
    ) -> Path:
        """Get the directory path for a document type.
        
        Args:
            tenant_id: Tenant UUID
            document_type: Type of document (work_order, purchase_order, etc.)
            
        Returns:
            Path to document directory
        """
        tenant_dir = self.base_storage_path / str(tenant_id)
        type_dir = tenant_dir / document_type
        type_dir.mkdir(parents=True, exist_ok=True)
        return type_dir

    def generate_file_path(
        self,
        tenant_id: uuid.UUID,
        document_type: str,
        entity_id: uuid.UUID,
        version_number: int,
        extension: str = "pdf",
    ) -> str:
        """Generate a unique file path for a document.
        
        Args:
            tenant_id: Tenant UUID
            document_type: Type of document
            entity_id: Entity UUID the document is for
            version_number: Document version number
            extension: File extension (default: pdf)
            
        Returns:
            Absolute file path
        """
        directory = self._get_document_directory(tenant_id, document_type)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{entity_id}_v{version_number}_{timestamp}.{extension}"
        file_path = directory / filename
        return str(file_path.absolute())

    def save_pdf(
        self,
        pdf_bytes: bytes,
        file_path: str,
    ) -> None:
        """Save PDF bytes to file.
        
        Args:
            pdf_bytes: PDF content as bytes
            file_path: Absolute file path to save to
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pdf_bytes)

    def load_pdf(
        self,
        file_path: str,
    ) -> bytes:
        """Load PDF bytes from file.
        
        Args:
            file_path: Absolute file path to load from
            
        Returns:
            PDF content as bytes
        """
        path = Path(file_path)
        return path.read_bytes()

    def delete_pdf(
        self,
        file_path: str,
    ) -> None:
        """Delete PDF file.
        
        Args:
            file_path: Absolute file path to delete
        """
        path = Path(file_path)
        if path.exists():
            path.unlink()
