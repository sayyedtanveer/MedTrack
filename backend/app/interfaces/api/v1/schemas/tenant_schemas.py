from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import uuid


class UpdateTenantRequest(BaseModel):
    """PATCH semantics — all fields optional."""
    company_name: Optional[str] = Field(None, max_length=255)
    gst_number: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=1000)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    footer_text: Optional[str] = None
    currency_code: Optional[str] = Field(None, max_length=10)
    currency_symbol: Optional[str] = Field(None, max_length=5)
    timezone: Optional[str] = Field(None, max_length=100)
    default_warehouse_name: Optional[str] = Field(None, max_length=100)


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    is_active: bool
    company_name: Optional[str] = None
    gst_number: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    footer_text: Optional[str] = None
    currency_code: Optional[str] = None
    currency_symbol: Optional[str] = None
    timezone: Optional[str] = None
    default_warehouse_name: Optional[str] = None


class FileUploadResponse(BaseModel):
    filename: str
    url: str
    content_type: str
    size_bytes: int
    category: str
