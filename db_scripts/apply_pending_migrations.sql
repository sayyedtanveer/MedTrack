-- Apply Pending Migrations: Add is_default to locations and procurement pricing columns
-- This script manually applies the schema changes from the 2 pending Alembic migrations
-- PostgreSQL doesn't support "IF NOT EXISTS" for constraints, so we use DO blocks

-- ============================================================================
-- MIGRATION 1: Add is_default column to locations table
-- ============================================================================

-- Step 1: Add is_default column to locations
ALTER TABLE locations 
ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT false;

-- Step 2: Create index for default location lookups
CREATE INDEX IF NOT EXISTS ix_location_tenant_default 
ON locations(tenant_id, is_default) 
WHERE is_default = true AND is_deleted = false AND is_active = true;

-- Verify: Check that is_default column was added
SELECT 'is_default column added to locations' as status;

-- ============================================================================
-- MIGRATION 2: Add procurement pricing columns (Phase 2)
-- ============================================================================

-- Step 3: Add currency_code to purchase_orders
ALTER TABLE purchase_orders 
ADD COLUMN IF NOT EXISTS currency_code VARCHAR(3) NULL;

-- Step 4: Add unit_id to purchase_order_lines
ALTER TABLE purchase_order_lines 
ADD COLUMN IF NOT EXISTS unit_id UUID NULL;

-- Create FK for purchase_order_lines.unit_id (safe: use DO block)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'purchase_order_lines' 
        AND constraint_name = 'fk_purchase_order_lines_unit_id'
    ) THEN
        ALTER TABLE purchase_order_lines 
        ADD CONSTRAINT fk_purchase_order_lines_unit_id 
        FOREIGN KEY (unit_id) REFERENCES units_of_measure(id) ON DELETE RESTRICT;
    END IF;
END $$;

-- Step 5: Add columns to supplier_quotations
ALTER TABLE supplier_quotations 
ADD COLUMN IF NOT EXISTS currency_code VARCHAR(3) NULL;

ALTER TABLE supplier_quotations 
ADD COLUMN IF NOT EXISTS unit_id UUID NULL;

-- Create FK for supplier_quotations.unit_id
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'supplier_quotations' 
        AND constraint_name = 'fk_supplier_quotations_unit_id'
    ) THEN
        ALTER TABLE supplier_quotations 
        ADD CONSTRAINT fk_supplier_quotations_unit_id 
        FOREIGN KEY (unit_id) REFERENCES units_of_measure(id) ON DELETE RESTRICT;
    END IF;
END $$;

-- Step 6: Add columns to supplier_price_history
ALTER TABLE supplier_price_history 
ADD COLUMN IF NOT EXISTS grn_line_id UUID NULL;

ALTER TABLE supplier_price_history 
ADD COLUMN IF NOT EXISTS currency_code VARCHAR(3) NULL;

ALTER TABLE supplier_price_history 
ADD COLUMN IF NOT EXISTS unit_id UUID NULL;

-- Create FK for supplier_price_history.grn_line_id
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'supplier_price_history' 
        AND constraint_name = 'fk_supplier_price_history_grn_line_id'
    ) THEN
        ALTER TABLE supplier_price_history 
        ADD CONSTRAINT fk_supplier_price_history_grn_line_id 
        FOREIGN KEY (grn_line_id) REFERENCES grn_lines(id) ON DELETE RESTRICT;
    END IF;
END $$;

-- Create FK for supplier_price_history.unit_id
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'supplier_price_history' 
        AND constraint_name = 'fk_supplier_price_history_unit_id'
    ) THEN
        ALTER TABLE supplier_price_history 
        ADD CONSTRAINT fk_supplier_price_history_unit_id 
        FOREIGN KEY (unit_id) REFERENCES units_of_measure(id) ON DELETE RESTRICT;
    END IF;
END $$;

-- Create unique constraint on supplier_price_history
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'supplier_price_history' 
        AND constraint_name = 'uq_supplier_price_history_grn_line'
    ) THEN
        ALTER TABLE supplier_price_history 
        ADD CONSTRAINT uq_supplier_price_history_grn_line 
        UNIQUE (tenant_id, grn_line_id);
    END IF;
END $$;

-- Step 7: Create supplier_price_agreements table
CREATE TABLE IF NOT EXISTS supplier_price_agreements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE', 'EXPIRED')),
    base_price NUMERIC(18, 6) NOT NULL,
    currency_code VARCHAR(3) NOT NULL,
    purchase_uom_id UUID REFERENCES units_of_measure(id) ON DELETE RESTRICT,
    minimum_order_quantity NUMERIC(18, 6),
    quantity_tier TEXT,
    effective_from TIMESTAMP WITH TIME ZONE NOT NULL,
    effective_to TIMESTAMP WITH TIME ZONE,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes on supplier_price_agreements
CREATE INDEX IF NOT EXISTS ix_supplier_price_agreements_tenant 
ON supplier_price_agreements(tenant_id);

CREATE INDEX IF NOT EXISTS ix_supplier_price_agreements_supplier 
ON supplier_price_agreements(supplier_id);

CREATE INDEX IF NOT EXISTS ix_supplier_price_agreements_material 
ON supplier_price_agreements(material_id);

CREATE INDEX IF NOT EXISTS ix_supplier_price_agreements_status 
ON supplier_price_agreements(status) WHERE is_deleted = false;

-- Create partial unique index (equivalent to WHERE clause in constraint)
CREATE UNIQUE INDEX IF NOT EXISTS ix_supplier_price_agreements_tenant_supplier_material_unique
ON supplier_price_agreements(tenant_id, supplier_id, material_id) 
WHERE is_deleted = false;

-- ============================================================================
-- FINAL VERIFICATION
-- ============================================================================

SELECT 'Schema migration complete!' as result;

-- Verify all new columns exist
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE (
    (table_name = 'locations' AND column_name = 'is_default')
    OR (table_name = 'purchase_orders' AND column_name = 'currency_code')
    OR (table_name = 'purchase_order_lines' AND column_name = 'unit_id')
    OR (table_name = 'supplier_quotations' AND column_name IN ('currency_code', 'unit_id'))
    OR (table_name = 'supplier_price_history' AND column_name IN ('grn_line_id', 'currency_code', 'unit_id'))
)
ORDER BY table_name, column_name;
