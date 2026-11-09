-- ============================================================================
-- MANUAL MIGRATION: Add missing columns to work_order_lines table
-- ============================================================================
-- Run this script manually in your PostgreSQL client (pgAdmin, DBeaver, etc.)
-- This fixes the "column work_order_lines.product_id does not exist" error
-- ============================================================================

BEGIN;

-- Check if work_order_lines table exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'work_order_lines'
    ) THEN
        RAISE EXCEPTION 'Table work_order_lines does not exist. This table should have been created earlier.';
    END IF;
END $$;

-- Add product_id column if missing
ALTER TABLE work_order_lines 
ADD COLUMN IF NOT EXISTS product_id UUID;

-- Add bom_id column if missing
ALTER TABLE work_order_lines 
ADD COLUMN IF NOT EXISTS bom_id UUID;

-- Add planned_quantity column if missing
ALTER TABLE work_order_lines 
ADD COLUMN IF NOT EXISTS planned_quantity NUMERIC(15, 3);

-- Add produced_quantity column if missing
ALTER TABLE work_order_lines 
ADD COLUMN IF NOT EXISTS produced_quantity NUMERIC(15, 3) DEFAULT 0;

-- Add scrap_quantity column if missing
ALTER TABLE work_order_lines 
ADD COLUMN IF NOT EXISTS scrap_quantity NUMERIC(15, 3) DEFAULT 0;

-- Add status column if missing
ALTER TABLE work_order_lines 
ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'PLANNED';

-- Add is_deleted column if missing
ALTER TABLE work_order_lines 
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;

-- Add deleted_at column if missing
ALTER TABLE work_order_lines 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Add created_at column if missing
ALTER TABLE work_order_lines 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- Add updated_at column if missing
ALTER TABLE work_order_lines 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Now set NOT NULL constraints and foreign keys for existing columns
-- (Skip if data exists to avoid errors)

-- Set product_id to NOT NULL (after ensuring data exists)
DO $$ 
BEGIN
    -- Only set NOT NULL if there's no data or all rows have product_id
    IF (SELECT COUNT(*) FROM work_order_lines WHERE product_id IS NULL) = 0 THEN
        ALTER TABLE work_order_lines 
        ALTER COLUMN product_id SET NOT NULL;
    ELSE
        RAISE WARNING 'Cannot set product_id to NOT NULL - some rows have NULL values. Please populate data first.';
    END IF;
END $$;

-- Set bom_id to NOT NULL (after ensuring data exists)
DO $$ 
BEGIN
    IF (SELECT COUNT(*) FROM work_order_lines WHERE bom_id IS NULL) = 0 THEN
        ALTER TABLE work_order_lines 
        ALTER COLUMN bom_id SET NOT NULL;
    ELSE
        RAISE WARNING 'Cannot set bom_id to NOT NULL - some rows have NULL values. Please populate data first.';
    END IF;
END $$;

-- Set planned_quantity to NOT NULL
DO $$ 
BEGIN
    IF (SELECT COUNT(*) FROM work_order_lines WHERE planned_quantity IS NULL) = 0 THEN
        ALTER TABLE work_order_lines 
        ALTER COLUMN planned_quantity SET NOT NULL;
    ELSE
        RAISE WARNING 'Cannot set planned_quantity to NOT NULL - some rows have NULL values. Please populate data first.';
    END IF;
END $$;

-- Set status to NOT NULL
ALTER TABLE work_order_lines 
ALTER COLUMN status SET NOT NULL;

-- Set is_deleted to NOT NULL
ALTER TABLE work_order_lines 
ALTER COLUMN is_deleted SET NOT NULL;

-- Set created_at to NOT NULL
ALTER TABLE work_order_lines 
ALTER COLUMN created_at SET NOT NULL;

-- Set updated_at to NOT NULL
ALTER TABLE work_order_lines 
ALTER COLUMN updated_at SET NOT NULL;

-- Add foreign key constraints (if they don't exist)
DO $$ 
BEGIN
    -- FK to item_variants (product_id)
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
    
    -- FK to boms (bom_id)
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

-- Verify the columns were added
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'work_order_lines'
ORDER BY ordinal_position;

COMMIT;

-- ============================================================================
-- SUCCESS! work_order_lines table updated
-- ============================================================================
-- Added columns:
--   - product_id (UUID, NOT NULL, FK to item_variants)
--   - bom_id (UUID, NOT NULL, FK to boms)
--   - planned_quantity (NUMERIC)
--   - produced_quantity (NUMERIC)
--   - scrap_quantity (NUMERIC)
--   - status (VARCHAR)
--   - is_deleted (BOOLEAN)
--   - deleted_at (TIMESTAMPTZ)
--   - created_at (TIMESTAMPTZ)
--   - updated_at (TIMESTAMPTZ)
--
-- The Work Order + BOM PDF generation should now work!
-- ============================================================================
