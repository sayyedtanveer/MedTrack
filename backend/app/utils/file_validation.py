"""File upload validation utilities.
Requirements: 43.4
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")) * 1024 * 1024


def sanitize_filename(filename: str) -> str:
    """Remove path traversal and dangerous characters from filename."""
    # Remove directory traversal
    filename = Path(filename).name
    # Keep only safe characters
    filename = re.sub(r"[^\w\-. ]", "_", filename)
    # Collapse multiple underscores
    filename = re.sub(r"_+", "_", filename)
    return filename.strip("._")


async def validate_upload(file: UploadFile, allowed_types: Optional[set] = None) -> bytes:
    """Read and validate an uploaded file. Returns file bytes.

    Validates:
    - File size does not exceed MAX_UPLOAD_SIZE_BYTES (default 10 MB)
    - Content type is in the allowed set

    Args:
        file: The UploadFile from FastAPI.
        allowed_types: Optional set of MIME types. Defaults to ALLOWED_MIME_TYPES.

    Returns:
        Raw file bytes.

    Raises:
        HTTPException 413 if file is too large.
        HTTPException 415 if content type is not allowed.

    Requirements: 43.4
    """
    if allowed_types is None:
        allowed_types = ALLOWED_MIME_TYPES

    # Read content
    content = await file.read()

    # Check size
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum allowed size of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB",
        )

    # Validate content type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail=(
                f"File type '{content_type}' is not allowed. "
                f"Allowed types: {', '.join(sorted(allowed_types))}"
            ),
        )

    return content
