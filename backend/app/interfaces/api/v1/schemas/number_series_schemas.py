"""Pydantic schemas for Number Series configuration API."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Prefix validation ──────────────────────────────────────────────────────────
PREFIX_PATTERN = re.compile(r"^[A-Z0-9]+$")


class NumberSeriesConfigResponse(BaseModel):
    """Response schema for a number series config entry."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    entity_type: str
    auto_generate: bool
    manual_override: str
    prefix: str
    include_abbreviation: bool
    abbreviation_length: int
    sequence_length: int
    separator: str
    lock_after_save: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateNumberSeriesConfigRequest(BaseModel):
    """Request schema for updating a number series config."""

    auto_generate: Optional[bool] = None
    manual_override: Optional[str] = Field(None, pattern="^(never|admin_only|always)$")
    prefix: Optional[str] = Field(None, min_length=0, max_length=10)
    include_abbreviation: Optional[bool] = None
    abbreviation_length: Optional[int] = Field(None, ge=2, le=6)
    sequence_length: Optional[int] = Field(None, ge=4, le=10)
    separator: Optional[str] = Field(None, max_length=5)
    lock_after_save: Optional[bool] = None

    @field_validator("prefix", mode="before")
    @classmethod
    def validate_prefix(cls, v):
        if v is None or v == "":
            return v
        if not PREFIX_PATTERN.match(v):
            raise ValueError("Prefix must contain only uppercase alphanumeric characters")
        return v


class NumberSeriesPrefixResponse(BaseModel):
    """Response schema for a sub-type prefix mapping."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    entity_type: str
    sub_type: str
    prefix: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdatePrefixRequest(BaseModel):
    """Request schema for updating a sub-type prefix."""

    prefix: str = Field(..., min_length=1, max_length=10)

    @field_validator("prefix")
    @classmethod
    def validate_prefix_format(cls, v):
        if not PREFIX_PATTERN.match(v):
            raise ValueError(
                "Prefix must contain only uppercase alphanumeric characters (A-Z, 0-9)"
            )
        return v


class CodePreviewResponse(BaseModel):
    """Response schema for code format preview."""

    preview: str
    format_pattern: str


class NumberSeriesAuditLogResponse(BaseModel):
    """Response schema for an audit log entry."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    entity_type: str
    event_type: str
    entity_id: Optional[uuid.UUID] = None
    generated_code: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    user_id: uuid.UUID
    timestamp: datetime
    metadata_json: Optional[str] = None

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Paginated response for audit log entries."""

    items: List[NumberSeriesAuditLogResponse]
    total: int
    page: int
    page_size: int
