-- Quick fix for production subcontract issues
-- Run this if you're seeing errors after deployment

-- 1. Ensure subcontract_order_lines table exists with consumed_quantity
DO $$ 
BEGIN
    -- Check if table exists
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'subcontract_order_lines') THEN
        RAISE EXCEPTION 'subcontract_order_lines table does not exist! Run full migration first.';
    END IF;
    
    -- Ensure consumed_quantity column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_order_lines' 
        AND column_name = 'consumed_quantity'
    ) THEN
        ALTER TABLE subcontract_order_lines 
        ADD COLUMN consumed_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0;
        RAISE NOTICE '✓ Added consumed_quantity column';
    ELSE
        RAISE NOTICE '✓ consumed_quantity column already exists';
    END IF;
    
    -- Ensure all required columns exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_order_lines' 
        AND column_name = 'issued_quantity'
    ) THEN
        ALTER TABLE subcontract_order_lines 
        ADD COLUMN issued_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0;
        RAISE NOTICE '✓ Added issued_quantity column';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_order_lines' 
        AND column_name = 'returned_quantity'
    ) THEN
        ALTER TABLE subcontract_order_lines 
        ADD COLUMN returned_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0;
        RAISE NOTICE '✓ Added returned_quantity column';
    END IF;
END $$;

-- 2. Ensure indexes exist
CREATE INDEX IF NOT EXISTS ix_sco_line_order ON subcontract_order_lines(subcontract_order_id);
CREATE INDEX IF NOT EXISTS ix_sco_line_tenant ON subcontract_order_lines(tenant_id);

-- 3. Verify subcontract_orders has correct status constraint
DO $$ 
BEGIN
    -- Drop old constraint if exists
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'subcontract_orders_status_check'
    ) THEN
        ALTER TABLE subcontract_orders DROP CONSTRAINT subcontract_orders_status_check;
    END IF;
    
    -- Add correct constraint
    ALTER TABLE subcontract_orders 
    ADD CONSTRAINT subcontract_orders_status_check 
    CHECK (status IN ('draft', 'approved', 'materials_issued', 'partially_received', 'completed', 'cancelled'));
    
    RAISE NOTICE '✓ Status constraint updated';
EXCEPTION WHEN duplicate_object THEN
    RAISE NOTICE '✓ Status constraint already correct';
END $$;

-- 4. Verify table structure
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'subcontract_order_lines'
    AND column_name IN ('id', 'tenant_id', 'subcontract_order_id', 'material_id', 
                        'required_quantity', 'issued_quantity', 'consumed_quantity', 'returned_quantity');
    
    IF col_count < 8 THEN
        RAISE WARNING 'Missing columns in subcontract_order_lines. Expected 8, found %', col_count;
    ELSE
        RAISE NOTICE '✓ All required columns present (% columns)', col_count;
    END IF;
END $$;

SELECT '✅ Subcontract tables verified and fixed' as status;
