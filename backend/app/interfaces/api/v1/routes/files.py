from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_container
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.tenant_schemas import FileUploadResponse
from backend.app.utils.file_validation import validate_upload, sanitize_filename

router = APIRouter(prefix="/files", tags=["Files"])

VALID_CATEGORIES = {"invoices", "certificates", "documents", "images", "reports", "quality"}


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("documents:write"))],
    summary="Upload a file to tenant storage",
)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    category: str = "documents",
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Upload a file with validation (size, type, filename sanitization).
    
    Requirements: 43.4
    """
    if category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {sorted(VALID_CATEGORIES)}",
        )

    # Validate file size and content type
    content = await validate_upload(file)

    # Sanitize filename
    safe_filename = sanitize_filename(file.filename or "upload")

    container = get_container(request)
    result = await container.storage_service.save(
        file_content=content,
        original_filename=safe_filename,
        content_type=file.content_type or "application/octet-stream",
        tenant_id=tenant_id,
        category=category,
    )

    return FileUploadResponse(
        filename=result.filename,
        url=result.url,
        content_type=result.content_type,
        size_bytes=result.size_bytes,
        category=category,
    )
