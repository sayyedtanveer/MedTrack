from __future__ import annotations

import uuid

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from backend.app.config import settings
from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_container
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.tenant_schemas import FileUploadResponse
from backend.app.utils.file_validation import validate_upload, sanitize_filename

router = APIRouter(prefix="/files", tags=["Files"])

VALID_CATEGORIES = {"invoices", "certificates", "documents", "images", "reports", "quality"}


@router.post(
    "/upload-logo",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Upload a logo/image to Cloudinary and return its CDN URL",
)
async def upload_file_cloudinary(
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Upload an image to Cloudinary and return the CDN URL.

    Returns { url: str } compatible with tenantService.uploadLogo().
    Allowed types: image/png, image/jpeg, image/webp. Max 10 MB.
    """
    ALLOWED_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    MAX_SIZE = 10 * 1024 * 1024  # 10 MB

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type '{file.content_type}' not allowed. Use PNG, JPEG, or WebP.",
        )

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File exceeds maximum size of 10 MB.",
        )

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )

    try:
        result = cloudinary.uploader.upload(
            content,
            folder=f"medtrack/{tenant_id}",
            resource_type="image",
            use_filename=True,
            unique_filename=True,
            overwrite=False,
        )
        return {"url": result["secure_url"]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cloudinary upload failed: {str(e)}",
        )


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

    content = await validate_upload(file)
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
