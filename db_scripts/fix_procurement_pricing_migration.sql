-- ============================================================================
-- Procurement Pricing Phase 2 - Simple SQL-Only Setup
-- ============================================================================
-- Quick version without checks - assumes tables don't exist
-- Use this if you prefer direct SQL execution over Python script
-- ============================================================================

-- Step 1: Fix null operation_code values in operations table
UPDATE operations 
SET operation_code = 'OP-' || SUBSTRING(id::text, 1, 8)
WHERE operation_code IS NULL;

COMMIT;

-- Step 2: Create supplier_price_agreements table
CREATE TABLE IF NOT EXISTS supplier_price_agreements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    base_price NUMERIC(18, 6) NOT NULL,
    currency_code VARCHAR(3) NOT NULL,
    quantity_tier TEXT,
    effective_from TIMESTAMP WITH TIME ZONE NOT NULL,
    effective_to TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_supplier_price_agreements_tenant_supplier_material 
        UNIQUE (tenant_id, supplier_id, material_id)
);

CREATE INDEX IF NOT EXISTS ix_supplier_price_agreements_tenant_id 
    ON supplier_price_agreements(tenant_id);
CREATE INDEX IF NOT EXISTS ix_supplier_price_agreements_is_deleted 
    ON supplier_price_agreements(is_deleted);
CREATE INDEX IF NOT EXISTS ix_supplier_price_agreements_status 
    ON supplier_price_agreements(status);
CREATE INDEX IF NOT EXISTS ix_supplier_price_agreements_supplier_id 
    ON supplier_price_agreements(supplier_id);
CREATE INDEX IF NOT EXISTS ix_supplier_price_agreements_material_id 
    ON supplier_price_agreements(material_id);
CREATE INDEX IF NOT EXISTS ix_supplier_price_agreements_effective_from 
    ON supplier_price_agreements(effective_from);

COMMIT;

-- Step 3: Create standard_cost_revisions table
CREATE TABLE IF NOT EXISTS standard_cost_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    requested_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    requested_cost NUMERIC(18, 6) NOT NULL,
    current_cost NUMERIC(18, 6) NOT NULL,
    variance_percent NUMERIC(8, 2),
    reason VARCHAR(50) NOT NULL,
    notes TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_standard_cost_revisions_tenant_id 
    ON standard_cost_revisions(tenant_id);
CREATE INDEX IF NOT EXISTS ix_standard_cost_revisions_material_id 
    ON standard_cost_revisions(material_id);
CREATE INDEX IF NOT EXISTS ix_standard_cost_revisions_requested_by 
    ON standard_cost_revisions(requested_by);
CREATE INDEX IF NOT EXISTS ix_standard_cost_revisions_status 
    ON standard_cost_revisions(status);

COMMIT;

-- Step 4: Create material_cost_history table (audit log, insert-only)
CREATE TABLE IF NOT EXISTS material_cost_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    old_cost NUMERIC(18, 6),
    new_cost NUMERIC(18, 6) NOT NULL,
    change_type VARCHAR(30) NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    source_id VARCHAR(255),
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_material_cost_history_tenant_id 
    ON material_cost_history(tenant_id);
CREATE INDEX IF NOT EXISTS ix_material_cost_history_material_id 
    ON material_cost_history(material_id);
CREATE INDEX IF NOT EXISTS ix_material_cost_history_change_type 
    ON material_cost_history(change_type);
CREATE INDEX IF NOT EXISTS ix_material_cost_history_created_at 
    ON material_cost_history(created_at);

COMMIT;

-- Step 5: Create price_override_records table
CREATE TABLE IF NOT EXISTS price_override_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    grn_id UUID REFERENCES goods_receipt_notes(id) ON DELETE RESTRICT,
    suggested_price NUMERIC(18, 6) NOT NULL,
    override_price NUMERIC(18, 6) NOT NULL,
    variance_percent NUMERIC(8, 2),
    override_reason VARCHAR(50) NOT NULL,
    override_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    notes TEXT,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_price_override_records_tenant_id 
    ON price_override_records(tenant_id);
CREATE INDEX IF NOT EXISTS ix_price_override_records_material_id 
    ON price_override_records(material_id);
CREATE INDEX IF NOT EXISTS ix_price_override_records_override_by 
    ON price_override_records(override_by);
CREATE INDEX IF NOT EXISTS ix_price_override_records_created_at 
    ON price_override_records(created_at);

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

-- Check all tables exist
SELECT table_name, 
       (SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND information_schema.tables.table_name = table_name) as column_count
FROM information_schema.tables
WHERE table_schema = 'public' 
AND table_name IN (
    'supplier_price_agreements',
    'standard_cost_revisions', 
    'material_cost_history',
    'price_override_records'
)
ORDER BY table_name;

-- Check null operation_code values are fixed
SELECT COUNT(*) as null_operation_code_count FROM operations WHERE operation_code IS NULL;

-- Summary
SELECT '✅ Procurement Pricing Phase 2 tables setup complete!' as status;
