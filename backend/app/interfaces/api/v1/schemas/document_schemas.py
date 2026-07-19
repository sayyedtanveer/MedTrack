"""Document API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class DocumentGenerateRequest(BaseModel):
    """Request schema for generating a document."""
    
    force_regenerate: bool = Field(default=False, description="Force regeneration even if latest version exists")


class DocumentResponse(BaseModel):
    """Response schema for document metadata."""
    
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

    class Config:
        from_attributes = True


class DocumentVersionResponse(BaseModel):
    """Response schema for document version list."""
    
    id: uuid.UUID
    version_number: int
    generated_by: Optional[uuid.UUID]
    generated_at: datetime
    file_path: str

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response schema for listing document versions."""
    
    document_type: str
    entity_id: uuid.UUID
    versions: List[DocumentVersionResponse]
    total: int


class SignatureData(BaseModel):
    """Schema for signature metadata."""
    
    name: str
    timestamp: datetime
    signature_image_url: Optional[str] = None


class WorkOrderPrintContext(BaseModel):
    """Context data for Work Order PDF generation."""
    
    work_order: dict
    materials: List[dict]
    operations: List[dict]
    signatures: dict
    tenant: dict
