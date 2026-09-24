import uuid
from typing import List, Optional
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.infrastructure.persistence.models.technical_document_model import (
    TechnicalDocumentModel,
    DocumentRevisionModel,
    FileAttachmentModel,
    DocumentAssociationModel
)
from backend.app.application.documents.services.document_storage_service import DocumentStorageService
from backend.app.utils.file_validation import validate_upload, sanitize_filename

class TechnicalDocumentService:
    def __init__(self, session: AsyncSession, storage_service: DocumentStorageService):
        self.session = session
        self.storage_service = storage_service

    async def create_document(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        document_number: str,
        name: str,
        document_category: str,
        file: UploadFile,
        revision_code: str = "A",
        notes: str = ""
    ) -> TechnicalDocumentModel:
        # Validate and read file
        content = await validate_upload(file)
        safe_filename = sanitize_filename(file.filename or "upload.pdf")

        # Create TechnicalDocument
        doc = TechnicalDocumentModel(
            tenant_id=tenant_id,
            document_number=document_number,
            name=name,
            document_category=document_category
        )
        self.session.add(doc)
        await self.session.flush()

        # Create FileAttachment
        # We need to generate a cloudinary public id. The storage service expects entity_id, we will use revision UUID later, so generate it now.
        revision_id = uuid.uuid4()
        public_id = self.storage_service.generate_file_path(
            tenant_id=tenant_id,
            document_type="technical_documents",
            entity_id=revision_id,
            version_number=1, # We can use 1 or the rev code
            extension=safe_filename.split('.')[-1] if '.' in safe_filename else 'pdf'
        )
        
        # Upload to Cloudinary
        self.storage_service.save_pdf(content, public_id)
        
        attachment = FileAttachmentModel(
            tenant_id=tenant_id,
            file_name=safe_filename,
            file_size_bytes=len(content),
            content_type=file.content_type or "application/pdf",
            cloudinary_public_id=public_id,
            uploaded_by_id=user_id
        )
        self.session.add(attachment)
        await self.session.flush()
        
        # Create Revision
        rev = DocumentRevisionModel(
            id=revision_id,
            tenant_id=tenant_id,
            document_id=doc.id,
            file_attachment_id=attachment.id,
            revision_code=revision_code,
            status="APPROVED",
            notes=notes,
            created_by_id=user_id
        )
        self.session.add(rev)
        await self.session.flush()
        
        # Reload doc with relationships
        stmt = (
            select(TechnicalDocumentModel)
            .options(
                selectinload(TechnicalDocumentModel.revisions).selectinload(DocumentRevisionModel.file_attachment)
            )
            .where(TechnicalDocumentModel.id == doc.id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def associate_document(
        self,
        tenant_id: uuid.UUID,
        revision_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
        is_print_package_included: bool = False
    ) -> DocumentAssociationModel:
        assoc = DocumentAssociationModel(
            tenant_id=tenant_id,
            revision_id=revision_id,
            is_print_package_included=is_print_package_included
        )
        if target_type == "work_order":
            assoc.work_order_id = target_id
        elif target_type == "variant":
            assoc.variant_id = target_id
        elif target_type == "template":
            assoc.template_id = target_id
        else:
            raise ValueError("Invalid target_type")
            
        self.session.add(assoc)
        await self.session.flush()
        return assoc

    async def get_associations_for_entity(
        self,
        tenant_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID
    ) -> List[DocumentAssociationModel]:
        stmt = (
            select(DocumentAssociationModel)
            .options(
                selectinload(DocumentAssociationModel.revision).selectinload(DocumentRevisionModel.document),
                selectinload(DocumentAssociationModel.revision).selectinload(DocumentRevisionModel.file_attachment)
            )
            .where(DocumentAssociationModel.tenant_id == tenant_id)
        )
        if target_type == "work_order":
            stmt = stmt.where(DocumentAssociationModel.work_order_id == target_id)
        elif target_type == "variant":
            stmt = stmt.where(DocumentAssociationModel.variant_id == target_id)
        elif target_type == "template":
            stmt = stmt.where(DocumentAssociationModel.template_id == target_id)
            
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_revision(self, tenant_id: uuid.UUID, revision_id: uuid.UUID) -> Optional[DocumentRevisionModel]:
        stmt = (
            select(DocumentRevisionModel)
            .options(
                selectinload(DocumentRevisionModel.document),
                selectinload(DocumentRevisionModel.file_attachment)
            )
            .where(DocumentRevisionModel.id == revision_id)
            .where(DocumentRevisionModel.tenant_id == tenant_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_file_content(self, file_path: str) -> bytes:
        return self.storage_service.load_pdf(file_path)
