"""Document storage service for managing PDF files via Cloudinary."""

from __future__ import annotations

import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import httpx

import cloudinary
import cloudinary.uploader
import cloudinary.utils
from backend.app.config import settings

logger = logging.getLogger(__name__)

class DocumentStorageService:
    """Service for storing and managing document PDF files on Cloudinary."""

    def __init__(self, base_storage_path: str = "storage/documents"):
        """Initialize document storage service.
        
        Args:
            base_storage_path: Base directory for legacy local document storage
        """
        self.base_storage_path = Path(base_storage_path)
        # Ensure Cloudinary is configured
        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
        )

    def _is_legacy_local_path(self, file_path: str) -> bool:
        """Check if a file path is a legacy local filesystem path."""
        # Strict prefix detection per architectural plan
        return file_path.startswith("/") or file_path.startswith("C:\\") or file_path.startswith("storage/")

    def generate_file_path(
        self,
        tenant_id: uuid.UUID,
        document_type: str,
        entity_id: uuid.UUID,
        version_number: int,
        extension: str = "pdf",
    ) -> str:
        """Generate a Cloudinary public_id for a document.
        
        Args:
            tenant_id: Tenant UUID
            document_type: Type of document
            entity_id: Entity UUID the document is for
            version_number: Document version number
            extension: File extension (default: pdf)
            
        Returns:
            Cloudinary public_id (e.g. medtrack/{tenant_id}/{document_type}/{entity_id}_v{version}_{timestamp}.pdf)
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{entity_id}_v{version_number}_{timestamp}.{extension}"
        # Cloudinary requires the extension in the public_id for raw assets
        public_id = f"medtrack/{tenant_id}/{document_type}/{filename}"
        return public_id

    def save_pdf(
        self,
        pdf_bytes: bytes,
        file_path: str,
    ) -> None:
        """Upload PDF bytes to Cloudinary.
        
        Args:
            pdf_bytes: PDF content as bytes
            file_path: Cloudinary public_id to use
            
        Raises:
            RuntimeError: If upload to Cloudinary fails
        """
        try:
            result = cloudinary.uploader.upload(
                pdf_bytes,
                resource_type="raw",
                type="private",
                public_id=file_path,
                format="pdf"
            )
            logger.info(f"Successfully uploaded PDF to Cloudinary: {file_path}")
        except Exception as e:
            logger.error(f"Cloudinary upload failed for {file_path}: {str(e)}")
            raise RuntimeError(f"Failed to upload document to Cloudinary: {str(e)}") from e

    def load_pdf(
        self,
        file_path: str,
    ) -> bytes:
        """Load PDF bytes from Cloudinary or local legacy fallback.
        
        Args:
            file_path: Cloudinary public_id or absolute local file path
            
        Returns:
            PDF content as bytes
            
        Raises:
            FileNotFoundError: If the file does not exist locally (for legacy)
            RuntimeError: If the Cloudinary download fails
        """
        if self._is_legacy_local_path(file_path):
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Legacy local PDF file missing: {file_path}")
            return path.read_bytes()

        # Generate a signed URL for backend-only access
        try:
            url = cloudinary.utils.private_download_url(
                file_path,
                format="pdf",
                resource_type="raw",
                type="private"
            )
            
            # Safely log the URL without exposing secrets or signatures
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            safe_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?***redacted***"
            logger.info(f"Downloading from Cloudinary URL: {safe_url}")
            logger.info(f"Parameters matched for download: public_id='{file_path}', format='pdf', resource_type='raw', type='private'")
            
            # Fetch the bytes synchronously using httpx
            with httpx.Client() as client:
                response = client.get(url)
                
                # Check 200 explicitly and report body on failure
                if response.status_code != 200:
                    error_details = f"Cloudinary HTTP {response.status_code} - Body: {response.text}"
                    logger.error(f"Download failed: {error_details}")
                    raise RuntimeError(f"Cloudinary download error: {error_details}")
                
                # Verify PDF signatures
                content_type = response.headers.get('content-type', '')
                if 'application/pdf' not in content_type:
                    logger.warning(f"Expected application/pdf, but got Content-Type: {content_type}")
                
                content = response.content
                if not content.startswith(b'%PDF'):
                    logger.warning(f"Downloaded file does not start with %PDF marker! First 20 bytes: {content[:20]}")
                    
                return content
                
        except Exception as e:
            logger.error(f"Exception during Cloudinary download for {file_path}: {str(e)}")
            raise RuntimeError(f"Failed to download document from Cloudinary: {str(e)}") from e

    def delete_pdf(
        self,
        file_path: str,
    ) -> None:
        """Delete PDF file from Cloudinary or local legacy fallback.
        
        Args:
            file_path: Cloudinary public_id or absolute local file path
        """
        if self._is_legacy_local_path(file_path):
            path = Path(file_path)
            if path.exists():
                path.unlink()
            return

        try:
            cloudinary.uploader.destroy(
                file_path,
                resource_type="raw",
                type="private"
            )
            logger.info(f"Successfully deleted PDF from Cloudinary: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete PDF from Cloudinary for {file_path}: {str(e)}")
