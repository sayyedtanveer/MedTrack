-- ============================================================================
-- MEDTRACK ERP - PRODUCTION DATABASE MIGRATION SCRIPT
-- Features: Subcontracting + Document Management
-- Date: 2026-09-26
-- 
-- IMPORTANT: Run this script in a transaction and test on staging first!
-- 
-- Usage:
--   BEGIN;
--   \i db_migration_prod_subcontract_documents.sql
--   -- Verify changes, then:
--   COMMIT;  -- or ROLLBACK; if issues found
-- ============================================================================

-- Set client encoding
SET client_encoding = 'UTF8';

-- ============================================================================
-- PART 1: SUBCONTRACTING TABLES
-- ============================================================================

-- ── 1.1 Subcontract Orders (Main Table) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS subcontract_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    order_number VARCHAR(40) NOT NULL,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    
    -- Output product details
    product_id UUID NOT NULL,
    product_type VARCHAR(20) NOT NULL DEFAULT 'variant',
    quantity NUMERIC(15, 3) NOT NULL,
    
    -- BOM reference (optional, for auto-loading components)
    bom_id UUID REFERENCES boms(id) ON DELETE SET NULL,
    
    due_date DATE,
    notes TEXT,
    
    -- Lifecycle status
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    
    -- Reception tracking
    output_batch_id UUID REFERENCES batches(id) ON DELETE SET NULL,
    received_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    
    -- Soft delete
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit fields
    created_by UUID,
    approved_by UUID,
    approved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    
    CONSTRAINT uq_subco_tenant_number UNIQUE (tenant_id, order_number),
    CONSTRAINT subcontract_orders_status_check CHECK (status IN (
        'draft', 
        'approved', 
        'materials_issued', 
        'partially_received', 
        'completed', 
        'cancelled'
    ))
);

CREATE INDEX IF NOT EXISTS ix_subco_supplier ON subcontract_orders(supplier_id);
CREATE INDEX IF NOT EXISTS ix_subco_tenant_status ON subcontract_orders(tenant_id, status);

COMMENT ON TABLE subcontract_orders IS 'Subcontract/Outside processing orders - one order per vendor per processing event';
COMMENT ON COLUMN subcontract_orders.status IS 'Lifecycle: draft → approved → materials_issued → partially_received → completed (or cancelled)';
COMMENT ON COLUMN subcontract_orders.product_id IS 'The processed/semi-finished product that will be returned';
COMMENT ON COLUMN subcontract_orders.product_type IS 'Type of product: variant, template, or material';

-- ── 1.2 Subcontract Order Lines (Component Requirements) ───────────────────
CREATE TABLE IF NOT EXISTS subcontract_order_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    subcontract_order_id UUID NOT NULL REFERENCES subcontract_orders(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    
    -- Quantity tracking
    required_quantity NUMERIC(15, 3) NOT NULL,
    issued_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    consumed_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    returned_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_sco_line_order ON subcontract_order_lines(subcontract_order_id);
CREATE INDEX IF NOT EXISTS ix_sco_line_tenant ON subcontract_order_lines(tenant_id);

COMMENT ON TABLE subcontract_order_lines IS 'Component requirements for subcontract orders - copied from BOM at approval';
COMMENT ON COLUMN subcontract_order_lines.required_quantity IS 'Total quantity required based on BOM';
COMMENT ON COLUMN subcontract_order_lines.issued_quantity IS 'Quantity issued to vendor';
COMMENT ON COLUMN subcontract_order_lines.consumed_quantity IS 'Actual consumption based on output produced (calculated)';
COMMENT ON COLUMN subcontract_order_lines.returned_quantity IS 'Quantity returned from vendor (unused material)';

-- ── 1.3 Subcontract Material Issues (Traceability) ─────────────────────────
CREATE TABLE IF NOT EXISTS subcontract_material_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    subcontract_order_id UUID NOT NULL REFERENCES subcontract_orders(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    
    -- Batch tracking
    batch_id UUID REFERENCES batches(id) ON DELETE SET NULL,
    batch_number VARCHAR(80),  -- For display/backward compat
    
    -- Quantities
    quantity NUMERIC(15, 3) NOT NULL,
    returned_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    
    -- Source location
    from_location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
    
    -- Audit
    issued_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    issued_by UUID
);

CREATE INDEX IF NOT EXISTS ix_sco_issue_order ON subcontract_material_issues(subcontract_order_id);
CREATE INDEX IF NOT EXISTS ix_sco_issue_tenant ON subcontract_material_issues(tenant_id);

COMMENT ON TABLE subcontract_material_issues IS 'Individual material issue transactions - supports multiple batches per material';
COMMENT ON COLUMN subcontract_material_issues.batch_id IS 'Proper batch UUID FK for traceability';
COMMENT ON COLUMN subcontract_material_issues.batch_number IS 'Display-friendly batch number';

-- ── 1.4 Subcontract Number Sequences ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS subcontract_number_sequences (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    current_value INTEGER NOT NULL DEFAULT 0
);

COMMENT ON TABLE subcontract_number_sequences IS 'Auto-increment sequences for subcontract order numbers per tenant';


-- ============================================================================
-- PART 2: DOCUMENT MANAGEMENT TABLES
-- ============================================================================

-- ── 2.1 File Attachments (Physical Files) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS file_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    cloudinary_public_id VARCHAR(500) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    uploaded_by_id UUID NOT NULL REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS ix_file_attachments_tenant_id ON file_attachments(tenant_id);

COMMENT ON TABLE file_attachments IS 'Physical file storage metadata - references Cloudinary for actual files';
COMMENT ON COLUMN file_attachments.cloudinary_public_id IS 'Unique identifier in Cloudinary storage';

-- ── 2.2 Technical Documents (Document Master) ───────────────────────────────
CREATE TABLE IF NOT EXISTS technical_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    document_number VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    document_category VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    
    CONSTRAINT uq_technical_doc_tenant_number UNIQUE (tenant_id, document_number)
);

CREATE INDEX IF NOT EXISTS ix_technical_documents_tenant_id ON technical_documents(tenant_id);

COMMENT ON TABLE technical_documents IS 'Document master records - one per unique document';
COMMENT ON COLUMN technical_documents.document_category IS 'Category: drawing, specification, procedure, instruction, etc.';

-- ── 2.3 Document Revisions (Version Control) ────────────────────────────────
CREATE TABLE IF NOT EXISTS document_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    document_id UUID NOT NULL REFERENCES technical_documents(id) ON DELETE CASCADE,
    file_attachment_id UUID NOT NULL REFERENCES file_attachments(id) ON DELETE RESTRICT,
    revision_code VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    notes VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    created_by_id UUID NOT NULL REFERENCES users(id),
    
    CONSTRAINT uq_doc_revision_code UNIQUE (tenant_id, document_id, revision_code)
);

CREATE INDEX IF NOT EXISTS ix_document_revisions_tenant_id ON document_revisions(tenant_id);

COMMENT ON TABLE document_revisions IS 'Document version history - one row per revision';
COMMENT ON COLUMN document_revisions.revision_code IS 'Revision identifier: A, B, C, or R01, R02, etc.';
COMMENT ON COLUMN document_revisions.status IS 'Status: DRAFT, APPROVED, OBSOLETE';

-- ── 2.4 Document Associations (Links to Entities) ───────────────────────────
CREATE TABLE IF NOT EXISTS document_associations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    revision_id UUID NOT NULL REFERENCES document_revisions(id) ON DELETE RESTRICT,
    
    -- Association targets (exactly one must be non-null)
    work_order_id UUID REFERENCES work_orders(id) ON DELETE CASCADE,
    work_order_line_id UUID REFERENCES work_order_lines(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES item_variants(id) ON DELETE CASCADE,
    template_id UUID REFERENCES item_templates(id) ON DELETE CASCADE,
    
    -- Display flags
    is_print_package_included BOOLEAN NOT NULL DEFAULT false,
    show_on_wo BOOLEAN NOT NULL DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    
    CONSTRAINT ck_document_association_target_exactly_one CHECK (
        (work_order_id IS NOT NULL AND variant_id IS NULL AND template_id IS NULL) OR
        (work_order_id IS NULL AND variant_id IS NOT NULL AND template_id IS NULL) OR
        (work_order_id IS NULL AND variant_id IS NULL AND template_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS ix_document_associations_tenant_id ON document_associations(tenant_id);
CREATE INDEX IF NOT EXISTS ix_document_associations_work_order_id ON document_associations(work_order_id);
CREATE INDEX IF NOT EXISTS ix_document_associations_work_order_line_id ON document_associations(work_order_line_id);
CREATE INDEX IF NOT EXISTS ix_document_associations_variant_id ON document_associations(variant_id);

COMMENT ON TABLE document_associations IS 'Links documents to work orders, variants, or templates';
COMMENT ON COLUMN document_associations.is_print_package_included IS 'Include in print package generation';
COMMENT ON COLUMN document_associations.show_on_wo IS 'Display on work order detail page';


-- ============================================================================
-- PART 3: SUPPORTING TABLES / MODIFICATIONS
-- ============================================================================

-- ── 3.1 Work Order Lines (Required for document associations) ───────────────
-- This table may already exist if created by Base.metadata.create_all()
-- Safe to run - will skip if exists
CREATE TABLE IF NOT EXISTS work_order_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    work_order_id UUID NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    operation_id UUID REFERENCES routing_operations(id) ON DELETE RESTRICT,
    operation_name VARCHAR(255) NOT NULL,
    work_center_id UUID REFERENCES work_centers(id) ON DELETE RESTRICT,
    sequence_number INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    planned_start_time TIMESTAMP WITH TIME ZONE,
    planned_end_time TIMESTAMP WITH TIME ZONE,
    actual_start_time TIMESTAMP WITH TIME ZONE,
    actual_end_time TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_work_order_lines_work_order_id ON work_order_lines(work_order_id);
CREATE INDEX IF NOT EXISTS ix_work_order_lines_tenant_id ON work_order_lines(tenant_id);

-- Add work_order_line_id to work_order_materials if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'work_order_materials' 
        AND column_name = 'work_order_line_id'
    ) THEN
        ALTER TABLE work_order_materials 
        ADD COLUMN work_order_line_id UUID REFERENCES work_order_lines(id) ON DELETE CASCADE;
        
        CREATE INDEX ix_wo_mat_line ON work_order_materials(work_order_line_id);
    END IF;
END $$;


-- ============================================================================
-- PART 4: DATA VALIDATION & CONSTRAINTS
-- ============================================================================

-- Ensure status constraint is correct on subcontract_orders
DO $$ 
BEGIN
    -- Drop old constraint if exists
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'subcontract_orders_status_check'
        AND table_name = 'subcontract_orders'
    ) THEN
        ALTER TABLE subcontract_orders DROP CONSTRAINT subcontract_orders_status_check;
    END IF;
    
    -- Add correct constraint
    ALTER TABLE subcontract_orders 
    ADD CONSTRAINT subcontract_orders_status_check 
    CHECK (status IN (
        'draft', 
        'approved', 
        'materials_issued', 
        'partially_received', 
        'completed', 
        'cancelled'
    ));
END $$;

-- Ensure consumed_quantity column exists on subcontract_order_lines
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_order_lines' 
        AND column_name = 'consumed_quantity'
    ) THEN
        ALTER TABLE subcontract_order_lines 
        ADD COLUMN consumed_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0;
        
        COMMENT ON COLUMN subcontract_order_lines.consumed_quantity IS 
            'Actual consumption calculated as: output_received × (bom_requirement / order_output_qty)';
    END IF;
END $$;


-- ============================================================================
-- PART 5: VERIFICATION QUERIES
-- ============================================================================

-- Run these after migration to verify everything is correct:
/*

-- Check subcontract tables exist
SELECT 
    schemaname, tablename, tableowner 
FROM pg_tables 
WHERE tablename IN (
    'subcontract_orders',
    'subcontract_order_lines',
    'subcontract_material_issues',
    'subcontract_number_sequences'
)
ORDER BY tablename;

-- Check document tables exist
SELECT 
    schemaname, tablename, tableowner 
FROM pg_tables 
WHERE tablename IN (
    'file_attachments',
    'technical_documents',
    'document_revisions',
    'document_associations'
)
ORDER BY tablename;

-- Check indexes
SELECT 
    schemaname, tablename, indexname 
FROM pg_indexes 
WHERE tablename LIKE 'subcontract%' OR tablename LIKE '%document%' OR tablename = 'file_attachments'
ORDER BY tablename, indexname;

-- Check constraints
SELECT 
    tc.table_name, tc.constraint_name, tc.constraint_type
FROM information_schema.table_constraints tc
WHERE tc.table_name IN (
    'subcontract_orders', 'subcontract_order_lines', 
    'document_associations', 'technical_documents'
)
ORDER BY tc.table_name, tc.constraint_type;

-- Check foreign keys
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name LIKE 'subcontract%'
ORDER BY tc.table_name, kcu.column_name;

*/


-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Display success message
DO $$ 
BEGIN
    RAISE NOTICE '✅ Migration completed successfully!';
    RAISE NOTICE 'Tables created/updated:';
    RAISE NOTICE '  - subcontract_orders';
    RAISE NOTICE '  - subcontract_order_lines';
    RAISE NOTICE '  - subcontract_material_issues';
    RAISE NOTICE '  - subcontract_number_sequences';
    RAISE NOTICE '  - file_attachments';
    RAISE NOTICE '  - technical_documents';
    RAISE NOTICE '  - document_revisions';
    RAISE NOTICE '  - document_associations';
    RAISE NOTICE '  - work_order_lines';
    RAISE NOTICE '';
    RAISE NOTICE 'Please run verification queries (see end of script)';
    RAISE NOTICE 'If everything looks good: COMMIT;';
    RAISE NOTICE 'If issues found: ROLLBACK;';
END $$;
