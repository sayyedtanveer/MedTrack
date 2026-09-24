import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class TechnicalDocumentBase(BaseModel):
    document_number: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    document_category: str = Field(..., max_length=50)

class TechnicalDocumentCreate(TechnicalDocumentBase):
    pass

class FileAttachmentResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    file_size_bytes: int
    content_type: str
    created_at: datetime
    uploaded_by_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)

class DocumentRevisionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    file_attachment_id: uuid.UUID
    revision_code: str
    status: str
    notes: Optional[str] = None
    created_at: datetime
    created_by_id: uuid.UUID
    file_attachment: Optional[FileAttachmentResponse] = None
    document: Optional[TechnicalDocumentBase] = None

    model_config = ConfigDict(from_attributes=True)

class TechnicalDocumentResponse(TechnicalDocumentBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    revisions: List[DocumentRevisionResponse] = []

    model_config = ConfigDict(from_attributes=True)

class DocumentAssociationCreate(BaseModel):
    revision_id: uuid.UUID
    target_type: str = Field(..., description="'work_order', 'variant', or 'template'")
    target_id: uuid.UUID
    is_print_package_included: bool = False

class DocumentAssociationResponse(BaseModel):
    id: uuid.UUID
    revision_id: uuid.UUID
    work_order_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    is_print_package_included: bool
    created_at: datetime
    revision: Optional[DocumentRevisionResponse] = None

    model_config = ConfigDict(from_attributes=True)
