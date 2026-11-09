-- Add consumed_quantity column to subcontract_order_lines
-- Migration: 20260926_add_consumed_quantity_subcontract
-- Business Context: Track actual raw material consumption separately from issued quantity

-- Check if column exists first
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='subcontract_order_lines' 
        AND column_name='consumed_quantity'
    ) THEN
        ALTER TABLE subcontract_order_lines
        ADD COLUMN consumed_quantity NUMERIC(15,3) NOT NULL DEFAULT 0;
        
        RAISE NOTICE 'Successfully added consumed_quantity column';
    ELSE
        RAISE NOTICE 'Column consumed_quantity already exists';
    END IF;
END $$;

-- Verify the column was added
SELECT 
    column_name, 
    data_type, 
    numeric_precision, 
    numeric_scale,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'subcontract_order_lines'
AND column_name = 'consumed_quantity';
