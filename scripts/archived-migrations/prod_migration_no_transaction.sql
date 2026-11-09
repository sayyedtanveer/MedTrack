-- ============================================================================
-- MEDTRACK ERP - PRODUCTION MIGRATION SCRIPT (No Transaction Wrapper)
-- Run Date: 2026-09-26
-- Features: Subcontracting + Document Management
-- 
-- This version runs without explicit transaction wrapper for better error recovery
-- Each statement commits automatically (autocommit mode)
-- ============================================================================

SET client_encoding = 'UTF8';

DO $$ BEGIN
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Starting MedTrack ERP Production Migration';
    RAISE NOTICE 'Features: Subcontracting + Document Management';
    RAISE NOTICE '============================================================================';
END $$;

DO $$ BEGIN RAISE NOTICE 'Step 1/6: Creating Subcontracting Tables...'; END $$;

-- ── Subcontract Orders ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subcontract_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    order_number VARCHAR(40) NOT NULL,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    product_id UUID NOT NULL,
    product_type VARCHAR(20) NOT NULL DEFAULT 'variant',
    quantity NUMERIC(15, 3) NOT NULL,
    bom_id UUID REFERENCES boms(id) ON DELETE SET NULL,
    due_date DATE,
    notes TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    output_batch_id UUID REFERENCES batches(id) ON DELETE SET NULL,
    received_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_by UUID,
    approved_by UUID,
    approved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_subco_tenant_number UNIQUE (tenant_id, order_number)
);

CREATE INDEX IF NOT EXISTS ix_subco_supplier ON subcontract_orders(supplier_id);
CREATE INDEX IF NOT EXISTS ix_subco_tenant_status ON subcontract_orders(tenant_id, status);

-- ── Subcontract Order Lines ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subcontract_order_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    subcontract_order_id UUID NOT NULL REFERENCES subcontract_orders(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    required_quantity NUMERIC(15, 3) NOT NULL,
    issued_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    consumed_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    returned_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_sco_line_order ON subcontract_order_lines(subcontract_order_id);
CREATE INDEX IF NOT EXISTS ix_sco_line_tenant ON subcontract_order_lines(tenant_id);

-- ── Subcontract Material Issues ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subcontract_material_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    subcontract_order_id UUID NOT NULL REFERENCES subcontract_orders(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    batch_id UUID REFERENCES batches(id) ON DELETE SET NULL,
    batch_number VARCHAR(80),
    quantity NUMERIC(15, 3) NOT NULL,
    returned_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    from_location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
    issued_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    issued_by UUID
);

CREATE INDEX IF NOT EXISTS ix_sco_issue_order ON subcontract_material_issues(subcontract_order_id);
CREATE INDEX IF NOT EXISTS ix_sco_issue_tenant ON subcontract_material_issues(tenant_id);

-- ── Subcontract Number Sequences ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subcontract_number_sequences (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    current_value INTEGER NOT NULL DEFAULT 0
);

DO $$ BEGIN RAISE NOTICE 'Step 2/6: Creating Supporting Tables...'; END $$;

-- ── Work Order Lines (Create FIRST - needed by document_associations) ──────
CREATE TABLE IF NOT EXISTS work_order_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    work_order_id UUID NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    operation_id UUID,  -- Nullable, no FK constraint (routing_operations may not exist)
    operation_name VARCHAR(255) NOT NULL,
    work_center_id UUID,  -- Nullable, no FK constraint (work_centers may not exist)
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

DO $$ BEGIN RAISE NOTICE 'Step 3/6: Creating Document Management Tables...'; END $$;

-- ── File Attachments ────────────────────────────────────────────────────────
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

-- ── Technical Documents ─────────────────────────────────────────────────────
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

-- ── Document Revisions ──────────────────────────────────────────────────────
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

-- ── Document Associations ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS document_associations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    revision_id UUID NOT NULL REFERENCES document_revisions(id) ON DELETE RESTRICT,
    work_order_id UUID REFERENCES work_orders(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES item_variants(id) ON DELETE CASCADE,
    template_id UUID REFERENCES item_templates(id) ON DELETE CASCADE,
    is_print_package_included BOOLEAN NOT NULL DEFAULT false,
    show_on_wo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Add work_order_line_id column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'document_associations' 
        AND column_name = 'work_order_line_id'
    ) THEN
        ALTER TABLE document_associations 
        ADD COLUMN work_order_line_id UUID REFERENCES work_order_lines(id) ON DELETE CASCADE;
        RAISE NOTICE '  ✓ Added work_order_line_id column to document_associations';
    ELSE
        RAISE NOTICE '  ✓ work_order_line_id column already exists in document_associations';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_document_associations_tenant_id ON document_associations(tenant_id);
CREATE INDEX IF NOT EXISTS ix_document_associations_work_order_id ON document_associations(work_order_id);
CREATE INDEX IF NOT EXISTS ix_document_associations_work_order_line_id ON document_associations(work_order_line_id);
CREATE INDEX IF NOT EXISTS ix_document_associations_variant_id ON document_associations(variant_id);

DO $$ BEGIN RAISE NOTICE 'Step 4/6: Adding Additional Columns...'; END $$;

-- Add work_order_line_id to work_order_materials if missing
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
        RAISE NOTICE '  ✓ Added work_order_line_id column to work_order_materials';
    ELSE
        RAISE NOTICE '  ✓ work_order_line_id column already exists in work_order_materials';
    END IF;
END $$;

DO $$ BEGIN RAISE NOTICE 'Step 5/6: Updating Constraints...'; END $$;

-- Fix subcontract_orders status constraint
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'subcontract_orders_status_check'
        AND table_name = 'subcontract_orders'
    ) THEN
        ALTER TABLE subcontract_orders DROP CONSTRAINT subcontract_orders_status_check;
    END IF;
    
    ALTER TABLE subcontract_orders 
    ADD CONSTRAINT subcontract_orders_status_check 
    CHECK (status IN ('draft', 'approved', 'materials_issued', 'partially_received', 'completed', 'cancelled'));
    
    RAISE NOTICE '  ✓ Updated subcontract_orders status constraint';
EXCEPTION WHEN duplicate_object THEN
    RAISE NOTICE '  ✓ Constraint already correct';
END $$;

-- Add document association constraint
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'ck_document_association_target_exactly_one'
        AND table_name = 'document_associations'
    ) THEN
        ALTER TABLE document_associations
        ADD CONSTRAINT ck_document_association_target_exactly_one CHECK (
            (work_order_id IS NOT NULL AND variant_id IS NULL AND template_id IS NULL) OR
            (work_order_id IS NULL AND variant_id IS NOT NULL AND template_id IS NULL) OR
            (work_order_id IS NULL AND variant_id IS NULL AND template_id IS NOT NULL)
        );
        RAISE NOTICE '  ✓ Added document association constraint';
    ELSE
        RAISE NOTICE '  ✓ Document association constraint already exists';
    END IF;
EXCEPTION WHEN duplicate_object THEN
    RAISE NOTICE '  ✓ Constraint already exists';
END $$;

-- Ensure consumed_quantity exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_order_lines' 
        AND column_name = 'consumed_quantity'
    ) THEN
        ALTER TABLE subcontract_order_lines 
        ADD COLUMN consumed_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0;
        RAISE NOTICE '  ✓ Added consumed_quantity column to subcontract_order_lines';
    ELSE
        RAISE NOTICE '  ✓ consumed_quantity column already exists';
    END IF;
END $$;

DO $$ BEGIN RAISE NOTICE 'Step 6/6: Running Verification...'; END $$;

-- Verification queries
DO $$ 
DECLARE
    table_count INTEGER;
    index_count INTEGER;
    orphan_count INTEGER;
BEGIN
    -- Check table count
    SELECT COUNT(*) INTO table_count
    FROM pg_tables 
    WHERE tablename IN (
        'subcontract_orders', 'subcontract_order_lines', 
        'subcontract_material_issues', 'subcontract_number_sequences',
        'file_attachments', 'technical_documents', 
        'document_revisions', 'document_associations'
    );
    
    IF table_count <> 8 THEN
        RAISE WARNING 'Table count: Expected 8, Found %', table_count;
    ELSE
        RAISE NOTICE '  ✓ All 8 tables verified';
    END IF;
    
    -- Check for orphaned records
    SELECT 
        (SELECT COUNT(*) FROM subcontract_order_lines sol
         LEFT JOIN subcontract_orders so ON sol.subcontract_order_id = so.id
         WHERE so.id IS NULL) +
        (SELECT COUNT(*) FROM subcontract_material_issues smi
         LEFT JOIN subcontract_orders so ON smi.subcontract_order_id = so.id
         WHERE so.id IS NULL) +
        (SELECT COUNT(*) FROM document_associations da
         LEFT JOIN document_revisions dr ON da.revision_id = dr.id
         WHERE dr.id IS NULL)
    INTO orphan_count;
    
    IF orphan_count > 0 THEN
        RAISE WARNING 'Found % orphaned records', orphan_count;
    ELSE
        RAISE NOTICE '  ✓ No orphaned records';
    END IF;
    
    -- Check index count
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE tablename IN (
        'subcontract_orders', 'subcontract_order_lines',
        'subcontract_material_issues', 'file_attachments',
        'technical_documents', 'document_revisions',
        'document_associations', 'work_order_lines'
    );
    
    RAISE NOTICE '  ✓ Created/verified % indexes', index_count;
END $$;

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '✅ Migration Completed Successfully!';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables Created/Updated:';
    RAISE NOTICE '  ✓ subcontract_orders';
    RAISE NOTICE '  ✓ subcontract_order_lines';
    RAISE NOTICE '  ✓ subcontract_material_issues';
    RAISE NOTICE '  ✓ subcontract_number_sequences';
    RAISE NOTICE '  ✓ file_attachments';
    RAISE NOTICE '  ✓ technical_documents';
    RAISE NOTICE '  ✓ document_revisions';
    RAISE NOTICE '  ✓ document_associations';
    RAISE NOTICE '  ✓ work_order_lines';
    RAISE NOTICE '';
    RAISE NOTICE 'Post-Migration Checklist:';
    RAISE NOTICE '  1. Restart application servers';
    RAISE NOTICE '  2. Test subcontract order creation';
    RAISE NOTICE '  3. Test document upload';
    RAISE NOTICE '  4. Monitor application logs';
    RAISE NOTICE '  5. Verify user access';
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
END $$;
