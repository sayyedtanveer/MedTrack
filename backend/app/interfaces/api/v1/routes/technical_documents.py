import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id, get_container
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.technical_document_schemas import (
    TechnicalDocumentResponse,
    DocumentAssociationResponse,
    DocumentAssociationCreate
)
from backend.app.application.documents.services.technical_document_service import TechnicalDocumentService

router = APIRouter(prefix="/technical-documents", tags=["Technical Documents"])

def get_tech_doc_service(request: Request) -> TechnicalDocumentService:
    container = get_container(request)
    session_factory = container.session_factory
    # We can't directly inject session here without context manager, so we use the request state session if available
    # Or create a dependency for session. Let's use FastAPI's dependency injection properly.
    return container # we will extract session from Depends below

@router.post(
    "",
    response_model=TechnicalDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("documents:write"))],
    summary="Create a new technical document and upload its first revision",
)
async def create_technical_document(
    request: Request,
    document_number: str = Form(...),
    name: str = Form(...),
    document_category: str = Form(...),
    revision_code: str = Form("A"),
    notes: str = Form(""),
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.documents.services.document_storage_service import DocumentStorageService
        service = TechnicalDocumentService(session, DocumentStorageService())
        try:
            doc = await service.create_document(
                tenant_id=tenant_id,
                user_id=user_id,
                document_number=document_number,
                name=name,
                document_category=document_category,
                file=file,
                revision_code=revision_code,
                notes=notes
            )
            await session.commit()
            return doc
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/associations",
    response_model=DocumentAssociationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("documents:write"))],
    summary="Associate a document revision with an entity",
)
async def associate_document(
    request: Request,
    data: DocumentAssociationCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.documents.services.document_storage_service import DocumentStorageService
        service = TechnicalDocumentService(session, DocumentStorageService())
        try:
            assoc = await service.associate_document(
                tenant_id=tenant_id,
                revision_id=data.revision_id,
                target_type=data.target_type,
                target_id=data.target_id,
                is_print_package_included=data.is_print_package_included
            )
            await session.commit()
            
            # Need to reload association to include revision
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from backend.app.infrastructure.persistence.models.technical_document_model import DocumentAssociationModel, DocumentRevisionModel
            
            stmt = (
                select(DocumentAssociationModel)
                .options(
                    selectinload(DocumentAssociationModel.revision).selectinload(DocumentRevisionModel.document),
                    selectinload(DocumentAssociationModel.revision).selectinload(DocumentRevisionModel.file_attachment)
                )
                .where(DocumentAssociationModel.id == assoc.id)
            )
            result = await session.execute(stmt)
            return result.scalars().first()
            
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

@router.get(
    "/associations/{target_type}/{target_id}",
    response_model=List[DocumentAssociationResponse],
    dependencies=[Depends(require_permission("documents:read"))],
    summary="List document associations for an entity",
)
async def get_associations(
    request: Request,
    target_type: str,
    target_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.documents.services.document_storage_service import DocumentStorageService
        service = TechnicalDocumentService(session, DocumentStorageService())
        associations = await service.get_associations_for_entity(
            tenant_id=tenant_id,
            target_type=target_type,
            target_id=target_id
        )
        return associations

@router.get(
    "/revisions/{revision_id}/download",
    dependencies=[Depends(require_permission("documents:read"))],
    summary="Download a technical document revision",
)
async def download_revision(
    request: Request,
    revision_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    from fastapi.responses import Response
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.documents.services.document_storage_service import DocumentStorageService
        service = TechnicalDocumentService(session, DocumentStorageService())
        
        try:
            rev = await service.get_revision(tenant_id, revision_id)
            if not rev or not rev.file_attachment:
                raise HTTPException(status_code=404, detail="Revision or attachment not found")
                
            pdf_bytes = await service.get_file_content(rev.file_attachment.cloudinary_public_id)
            return Response(
                content=pdf_bytes,
                media_type=rev.file_attachment.content_type or "application/pdf",
                headers={
                    "Content-Disposition": f'inline; filename="{rev.file_attachment.file_name}"'
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=400, detail=str(e))
