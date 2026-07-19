-- Manual SQL script for Phase 7 Document Generation System Migration
-- Run this directly against your PostgreSQL database

-- Add branding fields to tenants table
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS company_name VARCHAR(255);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS gst_number VARCHAR(50);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS phone VARCHAR(50);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS footer_text TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS signature_image_url VARCHAR(500);

-- Add item_code column to materials table
ALTER TABLE materials ADD COLUMN IF NOT EXISTS item_code VARCHAR(50);

-- Add quotation_number column to supplier_quotations table
ALTER TABLE supplier_quotations ADD COLUMN IF NOT EXISTS quotation_number VARCHAR(40) NOT NULL DEFAULT '';

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1,
    file_path VARCHAR(500) NOT NULL,
    generated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for documents table
CREATE INDEX IF NOT EXISTS ix_documents_tenant_id ON documents(tenant_id);
CREATE INDEX IF NOT EXISTS ix_documents_entity ON documents(document_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_documents_is_deleted ON documents(is_deleted);
