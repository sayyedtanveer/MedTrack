-- ============================================================================
-- COMPLETE PRODUCTION DATABASE MIGRATION
-- ============================================================================
-- This script contains ALL missing migrations for production
-- Run this ONCE on your production database to fix all errors
-- ============================================================================
-- Fixes:
--   1. sales_orders.priority column missing
--   2. work_order_lines.product_id and related columns missing
--   3. subcontract_orders missing columns (from earlier)
--   4. document_associations missing columns (from earlier)
-- ============================================================================

BEGIN;

-- ============================================================================
-- PART 1: Add priority to sales_orders
-- ============================================================================

ALTER TABLE sales_orders 
ADD COLUMN IF NOT EXISTS priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL';

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'ck_sales_order_priority' 
        AND table_name = 'sales_orders'
    ) THEN
        ALTER TABLE sales_orders 
        ADD CONSTRAINT ck_sales_order_priority 
        CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_sales_orders_priority 
ON sales_orders(tenant_id, priority);

-- ============================================================================
-- PART 2: Add missing columns to work_order_lines
-- ============================================================================

-- Check if work_order_lines table exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'work_order_lines'
    ) THEN
        -- Create the table if it doesn't exist
        CREATE TABLE work_order_lines (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            work_order_id UUID NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL,
            product_id UUID NOT NULL REFERENCES item_variants(id) ON DELETE RESTRICT,
            bom_id UUID NOT NULL REFERENCES boms(id) ON DELETE RESTRICT,
            planned_quantity NUMERIC(15, 3) NOT NULL,
            produced_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
            scrap_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
            status VARCHAR(50) NOT NULL DEFAULT 'PLANNED',
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            deleted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        
        CREATE INDEX ix_work_order_lines_work_order_id ON work_order_lines(work_order_id);
        CREATE INDEX ix_work_order_lines_tenant_id ON work_order_lines(tenant_id);
        
        RAISE NOTICE '✅ Created work_order_lines table';
    ELSE
        -- Table exists, add missing columns
        ALTER TABLE work_order_lines ADD COLUMN IF NOT EXISTS product_id UUID;
        ALTER TABLE work_order_lines ADD COLUMN IF NOT EXISTS bom_id UUID;
        ALTER TABLE work_order_lines ADD COLUMN IF NOT EXISTS planned_quantity NUMERIC(15, 3);
        ALTER TABLE work_order_lines ADD COLUMN IF NOT EXISTS produced_quantity NUMERIC(15, 3) DEFAULT 0;
        ALTER TABLE work_order_lines ADD COLUMN IF NOT EXISTS scrap_quantity NUMERIC(15, 3) DEFAULT 0;
        ALTER TABLE work_order_lines ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'PLANNED';
        ALTER TABLE work_order_lines ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
        ALTER TABLE work_order_lines ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
        ALTER TABLE work_order_lines ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
        ALTER TABLE work_order_lines ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
        
        RAISE NOTICE '✅ Added missing columns to work_order_lines';
    END IF;
END $$;

-- Add foreign key constraints if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'work_order_lines_product_id_fkey'
    ) THEN
        ALTER TABLE work_order_lines 
        ADD CONSTRAINT work_order_lines_product_id_fkey 
        FOREIGN KEY (product_id) 
        REFERENCES item_variants(id) 
        ON DELETE RESTRICT;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'work_order_lines_bom_id_fkey'
    ) THEN
        ALTER TABLE work_order_lines 
        ADD CONSTRAINT work_order_lines_bom_id_fkey 
        FOREIGN KEY (bom_id) 
        REFERENCES boms(id) 
        ON DELETE RESTRICT;
    END IF;
END $$;

-- ============================================================================
-- PART 3: Add missing columns to subcontract_orders (from earlier fix)
-- ============================================================================

ALTER TABLE subcontract_orders ADD COLUMN IF NOT EXISTS bom_id UUID;
ALTER TABLE subcontract_orders ADD COLUMN IF NOT EXISTS work_order_id UUID;
ALTER TABLE subcontract_orders ADD COLUMN IF NOT EXISTS order_date DATE DEFAULT CURRENT_DATE;
ALTER TABLE subcontract_orders ADD COLUMN IF NOT EXISTS expected_delivery_date DATE;
ALTER TABLE subcontract_orders ADD COLUMN IF NOT EXISTS delivery_date DATE;
ALTER TABLE subcontract_orders ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE subcontract_orders ADD COLUMN IF NOT EXISTS created_by UUID;
ALTER TABLE subcontract_orders ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- Add missing columns to subcontract_material_issues
ALTER TABLE subcontract_material_issues ADD COLUMN IF NOT EXISTS batch_id UUID;
ALTER TABLE subcontract_material_issues ADD COLUMN IF NOT EXISTS batch_number VARCHAR(100);
ALTER TABLE subcontract_material_issues ADD COLUMN IF NOT EXISTS returned_quantity NUMERIC(15, 3) DEFAULT 0;
ALTER TABLE subcontract_material_issues ADD COLUMN IF NOT EXISTS from_location_id UUID;
ALTER TABLE subcontract_material_issues ADD COLUMN IF NOT EXISTS issued_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE subcontract_material_issues ADD COLUMN IF NOT EXISTS issued_by UUID;

-- Add foreign key constraints for subcontract_material_issues
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'subcontract_material_issues_batch_id_fkey'
    ) THEN
        ALTER TABLE subcontract_material_issues 
        ADD CONSTRAINT subcontract_material_issues_batch_id_fkey 
        FOREIGN KEY (batch_id) 
        REFERENCES batches(id) 
        ON DELETE SET NULL;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'subcontract_material_issues_from_location_id_fkey'
    ) THEN
        ALTER TABLE subcontract_material_issues 
        ADD CONSTRAINT subcontract_material_issues_from_location_id_fkey 
        FOREIGN KEY (from_location_id) 
        REFERENCES locations(id) 
        ON DELETE SET NULL;
    END IF;
END $$;

-- ============================================================================
-- PART 4: Add missing columns to document_associations (from earlier fix)
-- ============================================================================

ALTER TABLE document_associations ADD COLUMN IF NOT EXISTS show_on_wo BOOLEAN DEFAULT FALSE;
ALTER TABLE document_associations ADD COLUMN IF NOT EXISTS work_order_line_id UUID;

-- Add foreign key for work_order_line_id if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'document_associations_work_order_line_id_fkey'
    ) THEN
        ALTER TABLE document_associations 
        ADD CONSTRAINT document_associations_work_order_line_id_fkey 
        FOREIGN KEY (work_order_line_id) 
        REFERENCES work_order_lines(id) 
        ON DELETE CASCADE;
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION: Show what was added
-- ============================================================================

-- Check sales_orders
SELECT 'sales_orders' as table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'sales_orders' AND column_name = 'priority'

UNION ALL

-- Check work_order_lines
SELECT 'work_order_lines' as table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'work_order_lines' AND column_name IN ('product_id', 'bom_id')

UNION ALL

-- Check subcontract_orders
SELECT 'subcontract_orders' as table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'subcontract_orders' AND column_name = 'bom_id'

UNION ALL

-- Check document_associations
SELECT 'document_associations' as table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'document_associations' AND column_name = 'show_on_wo'

ORDER BY table_name, column_name;

COMMIT;

-- ============================================================================
-- ✅ MIGRATION COMPLETE!
-- ============================================================================
-- All missing columns have been added:
--   ✅ sales_orders.priority
--   ✅ work_order_lines.product_id, bom_id, and related columns
--   ✅ subcontract_orders.bom_id and related columns
--   ✅ document_associations.show_on_wo and work_order_line_id
--
-- Your application should now work without database errors!
-- ============================================================================
