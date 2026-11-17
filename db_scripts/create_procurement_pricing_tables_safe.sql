-- ============================================================================
-- Procurement Pricing Phase 2 - Safe Table Creation Script
-- ============================================================================
-- This script ONLY creates tables if they don't already exist
-- Safe for repeated execution - will skip existing tables
-- ============================================================================

-- 1. Fix null operation_code values (prerequisite for migration)
UPDATE operations 
SET operation_code = 'OP-' || SUBSTRING(id::text, 1, 8)
WHERE operation_code IS NULL;

-- ============================================================================
-- TABLE 1: supplier_price_agreements
-- ============================================================================
-- Supplier pricing agreement contracts (e.g., volume discounts, effective dates)
-- State Machine: DRAFT → PENDING → APPROVED → ACTIVE → EXPIRED/CANCELLED

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'supplier_price_agreements'
    ) THEN
        CREATE TABLE supplier_price_agreements (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
            material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
            
            -- Agreement status
            status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' 
                CHECK (status IN ('DRAFT', 'PENDING', 'APPROVED', 'ACTIVE', 'EXPIRED', 'CANCELLED')),
            
            -- Pricing details
            base_price NUMERIC(18, 6) NOT NULL,
            currency_code VARCHAR(3) NOT NULL,  -- ISO 4217 (USD, INR, EUR)
            quantity_tier TEXT,  -- JSON array of tiered pricing
            
            -- Agreement validity
            effective_from TIMESTAMP WITH TIME ZONE NOT NULL,
            effective_to TIMESTAMP WITH TIME ZONE,
            
            -- Notes and conditions
            notes TEXT,
            
            -- Soft delete
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMP WITH TIME ZONE,
            
            -- Audit trail
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            
            CONSTRAINT uq_supplier_price_agreements_tenant_supplier_material 
                UNIQUE (tenant_id, supplier_id, material_id)
        );
        
        -- Indexes
        CREATE INDEX ix_supplier_price_agreements_tenant_id 
            ON supplier_price_agreements(tenant_id);
        CREATE INDEX ix_supplier_price_agreements_is_deleted 
            ON supplier_price_agreements(is_deleted);
        CREATE INDEX ix_supplier_price_agreements_status 
            ON supplier_price_agreements(status);
        CREATE INDEX ix_supplier_price_agreements_supplier_id 
            ON supplier_price_agreements(supplier_id);
        CREATE INDEX ix_supplier_price_agreements_material_id 
            ON supplier_price_agreements(material_id);
        CREATE INDEX ix_supplier_price_agreements_effective_from 
            ON supplier_price_agreements(effective_from);
        
        RAISE NOTICE 'Table supplier_price_agreements created successfully';
    ELSE
        RAISE NOTICE 'Table supplier_price_agreements already exists - skipping creation';
    END IF;
END $$;

-- ============================================================================
-- TABLE 2: standard_cost_revisions
-- ============================================================================
-- Cost approval workflow tracking (PENDING → APPROVED/REJECTED)

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'standard_cost_revisions'
    ) THEN
        CREATE TABLE standard_cost_revisions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
            requested_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            
            -- Cost proposal
            requested_cost NUMERIC(18, 6) NOT NULL,
            current_cost NUMERIC(18, 6) NOT NULL,
            variance_percent NUMERIC(8, 2),
            
            -- Reason and context
            reason VARCHAR(50) NOT NULL 
                CHECK (reason IN ('GRN_VARIANCE', 'SUPPLIER_AGREEMENT', 'VARIANCE_THRESHOLD', 'MANUAL_ADJUSTMENT')),
            notes TEXT,
            
            -- Approval workflow
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
            approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
            approved_at TIMESTAMP WITH TIME ZONE,
            rejection_reason TEXT,
            
            -- Soft delete
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMP WITH TIME ZONE,
            
            -- Audit trail
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        
        -- Indexes
        CREATE INDEX ix_standard_cost_revisions_tenant_id 
            ON standard_cost_revisions(tenant_id);
        CREATE INDEX ix_standard_cost_revisions_material_id 
            ON standard_cost_revisions(material_id);
        CREATE INDEX ix_standard_cost_revisions_requested_by 
            ON standard_cost_revisions(requested_by);
        CREATE INDEX ix_standard_cost_revisions_approved_by 
            ON standard_cost_revisions(approved_by);
        CREATE INDEX ix_standard_cost_revisions_status 
            ON standard_cost_revisions(status);
        CREATE INDEX ix_standard_cost_revisions_created_at 
            ON standard_cost_revisions(created_at);
        
        RAISE NOTICE 'Table standard_cost_revisions created successfully';
    ELSE
        RAISE NOTICE 'Table standard_cost_revisions already exists - skipping creation';
    END IF;
END $$;

-- ============================================================================
-- TABLE 3: material_cost_history
-- ============================================================================
-- Immutable audit log of all material cost changes (insert-only, no updates)

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'material_cost_history'
    ) THEN
        CREATE TABLE material_cost_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
            
            -- Cost values
            old_cost NUMERIC(18, 6),  -- null if first initialization
            new_cost NUMERIC(18, 6) NOT NULL,
            
            -- Change metadata
            change_type VARCHAR(30) NOT NULL 
                CHECK (change_type IN ('GRN_RECEIPT', 'GRN_REVERSAL', 'COST_REVISION_APPROVED', 'COST_REVISION_REJECTED', 'MANUAL_OVERRIDE')),
            source_type VARCHAR(20) NOT NULL 
                CHECK (source_type IN ('GRN', 'PO_RECEIPT', 'SUPPLIER_AGREEMENT', 'MANUAL')),
            source_id VARCHAR(255),  -- grn_id, cost_revision_id, etc.
            
            -- Approval
            approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
            
            -- Context
            notes TEXT,
            
            -- Timestamp (insert-only, no updates)
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        
        -- Indexes
        CREATE INDEX ix_material_cost_history_tenant_id 
            ON material_cost_history(tenant_id);
        CREATE INDEX ix_material_cost_history_material_id 
            ON material_cost_history(material_id);
        CREATE INDEX ix_material_cost_history_change_type 
            ON material_cost_history(change_type);
        CREATE INDEX ix_material_cost_history_created_at 
            ON material_cost_history(created_at);
        
        RAISE NOTICE 'Table material_cost_history created successfully';
    ELSE
        RAISE NOTICE 'Table material_cost_history already exists - skipping creation';
    END IF;
END $$;

-- ============================================================================
-- TABLE 4: price_override_records
-- ============================================================================
-- Manual price override analytics and tracking

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'price_override_records'
    ) THEN
        CREATE TABLE price_override_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
            grn_id UUID REFERENCES goods_receipt_notes(id) ON DELETE RESTRICT,
            
            -- Price comparison
            suggested_price NUMERIC(18, 6) NOT NULL,
            override_price NUMERIC(18, 6) NOT NULL,
            variance_percent NUMERIC(8, 2),
            
            -- Override metadata
            override_reason VARCHAR(50) NOT NULL 
                CHECK (override_reason IN ('QUALITY_ISSUE', 'RUSH_ORDER', 'BULK_DISCOUNT', 'VENDOR_PREFERENCE', 'OTHER')),
            override_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            notes TEXT,
            
            -- Soft delete
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMP WITH TIME ZONE,
            
            -- Audit trail
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        
        -- Indexes
        CREATE INDEX ix_price_override_records_tenant_id 
            ON price_override_records(tenant_id);
        CREATE INDEX ix_price_override_records_material_id 
            ON price_override_records(material_id);
        CREATE INDEX ix_price_override_records_grn_id 
            ON price_override_records(grn_id);
        CREATE INDEX ix_price_override_records_override_by 
            ON price_override_records(override_by);
        CREATE INDEX ix_price_override_records_created_at 
            ON price_override_records(created_at);
        
        RAISE NOTICE 'Table price_override_records created successfully';
    ELSE
        RAISE NOTICE 'Table price_override_records already exists - skipping creation';
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check all tables exist
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = 'public' AND information_schema.tables.table_name = table_name) as column_count
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
SELECT 'Procurement Pricing Phase 2 tables setup complete!' as status;
