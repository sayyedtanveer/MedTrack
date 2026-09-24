"""Main document generation service orchestrator."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.documents.services.template_service import TemplateService
from backend.app.application.documents.services.pdf_generation_service import PDFGenerationService
from backend.app.application.documents.services.document_storage_service import DocumentStorageService
from backend.app.domain.documents.entities.document import Document
from backend.app.domain.documents.repositories.document_repository_interface import IDocumentRepository


class DocumentGenerationService:
    """Main service for generating documents with versioning."""

    def __init__(
        self,
        template_service: TemplateService,
        pdf_service: PDFGenerationService,
        storage_service: DocumentStorageService,
        document_repository: IDocumentRepository,
    ):
        """Initialize document generation service.
        
        Args:
            template_service: Jinja2 template rendering service
            pdf_service: WeasyPrint PDF generation service
            storage_service: Document file storage service
            document_repository: Document persistence repository
        """
        self.template_service = template_service
        self.pdf_service = pdf_service
        self.storage_service = storage_service
        self.document_repository = document_repository

    async def generate_document(
        self,
        tenant_id: uuid.UUID,
        document_type: str,
        entity_id: uuid.UUID,
        template_context: Dict[str, Any],
        generated_by: uuid.UUID,
        force_regenerate: bool = False,
    ) -> Document:
        """Generate a document PDF with versioning.

        Args:
            tenant_id: Tenant UUID
            document_type: Type of document (work_order, purchase_order, etc.)
            entity_id: Entity UUID the document is for
            template_context: Context data for template rendering
            generated_by: User UUID who is generating the document
            force_regenerate: If True, create new version even if latest exists

        Returns:
            Generated document entity
        """
        # Check if latest version exists
        if not force_regenerate:
            latest = await self.document_repository.find_latest_version(
                tenant_id, document_type, entity_id
            )
            if latest:
                return latest

        # Determine version number
        latest = await self.document_repository.find_latest_version(
            tenant_id, document_type, entity_id
        )
        version_number = (latest.version_number + 1) if latest else 1

        # Render HTML template
        template_path = self.template_service.get_template_path(document_type)
        html_content = self.template_service.render_template(template_path, template_context)

        # Generate file path
        file_path = self.storage_service.generate_file_path(
            tenant_id, document_type, entity_id, version_number
        )

        # Generate PDF and save to Cloudinary storage
        # This will raise a RuntimeError if WeasyPrint is unavailable or Cloudinary upload fails.
        # We explicitly allow this to propagate to prevent creating phantom document records.
        pdf_bytes = self.pdf_service.generate_pdf_from_html(html_content)
        self.storage_service.save_pdf(pdf_bytes, file_path)

        # Create document entity
        document = Document(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            document_type=document_type,
            entity_id=entity_id,
            version_number=version_number,
            file_path=file_path,
            generated_by=generated_by,
            generated_at=datetime.utcnow(),
            is_deleted=False,
            deleted_at=None,
        )

        # Save to repository
        saved_document = await self.document_repository.save(document)

        return saved_document

    async def get_document_pdf(
        self,
        document_id: uuid.UUID,
    ) -> bytes:
        """Get PDF bytes for a document.
        
        Args:
            document_id: Document UUID
            
        Returns:
            PDF content as bytes
        """
        document = await self.document_repository.find_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        return self.storage_service.load_pdf(document.file_path)

    async def list_document_versions(
        self,
        tenant_id: uuid.UUID,
        document_type: str,
        entity_id: uuid.UUID,
    ):
        """List all versions of a document.
        
        Args:
            tenant_id: Tenant UUID
            document_type: Type of document
            entity_id: Entity UUID
            
        Returns:
            List of document versions
        """
        return await self.document_repository.list_versions(
            tenant_id, document_type, entity_id
        )

    async def generate_document_package(
        self,
        base_pdf_bytes: bytes,
        attachment_bytes_list: list[bytes]
    ) -> bytes:
        """Merge a base PDF with a list of attachment PDFs.
        
        Args:
            base_pdf_bytes: The generated Work Order PDF bytes.
            attachment_bytes_list: A list of PDF bytes for attachments.
            
        Returns:
            Merged PDF bytes.
        """
        import io
        from pypdf import PdfWriter, PdfReader

        writer = PdfWriter()
        
        # Add base document
        base_reader = PdfReader(io.BytesIO(base_pdf_bytes))
        for page in base_reader.pages:
            writer.add_page(page)
            
        # Add attachments
        for att_bytes in attachment_bytes_list:
            try:
                att_reader = PdfReader(io.BytesIO(att_bytes))
                for page in att_reader.pages:
                    writer.add_page(page)
            except Exception as e:
                # Log error but continue with other attachments
                import logging
                logging.getLogger(__name__).warning(f"Failed to merge an attachment: {e}")
                
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
