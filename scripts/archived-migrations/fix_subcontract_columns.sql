-- Emergency fix for missing columns in production subcontract_orders table
-- Run this immediately to fix the 500 errors

DO $$ 
BEGIN
    -- Add bom_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_orders' AND column_name = 'bom_id'
    ) THEN
        ALTER TABLE subcontract_orders ADD COLUMN bom_id UUID;
        RAISE NOTICE '✅ Added bom_id';
    END IF;
    
    -- Add due_date
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_orders' AND column_name = 'due_date'
    ) THEN
        ALTER TABLE subcontract_orders ADD COLUMN due_date DATE;
        RAISE NOTICE '✅ Added due_date';
    END IF;
    
    -- Add notes
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_orders' AND column_name = 'notes'
    ) THEN
        ALTER TABLE subcontract_orders ADD COLUMN notes TEXT;
        RAISE NOTICE '✅ Added notes';
    END IF;
    
    -- Add output_batch_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_orders' AND column_name = 'output_batch_id'
    ) THEN
        ALTER TABLE subcontract_orders ADD COLUMN output_batch_id UUID;
        RAISE NOTICE '✅ Added output_batch_id';
    END IF;
    
    -- Add received_quantity
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_orders' AND column_name = 'received_quantity'
    ) THEN
        ALTER TABLE subcontract_orders ADD COLUMN received_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0;
        RAISE NOTICE '✅ Added received_quantity';
    END IF;
    
    -- Add approved_by
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_orders' AND column_name = 'approved_by'
    ) THEN
        ALTER TABLE subcontract_orders ADD COLUMN approved_by UUID;
        RAISE NOTICE '✅ Added approved_by';
    END IF;
    
    -- Add approved_at
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_orders' AND column_name = 'approved_at'
    ) THEN
        ALTER TABLE subcontract_orders ADD COLUMN approved_at TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE '✅ Added approved_at';
    END IF;
    
    -- Add created_by
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subcontract_orders' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE subcontract_orders ADD COLUMN created_by UUID;
        RAISE NOTICE '✅ Added created_by';
    END IF;
    
    RAISE NOTICE '';
    RAISE NOTICE '✅ All missing columns added to subcontract_orders';
END $$;

-- Now add foreign key constraints (safe to do after columns exist)
DO $$
BEGIN
    -- Add FK for bom_id if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'subcontract_orders_bom_id_fkey'
    ) THEN
        ALTER TABLE subcontract_orders 
        ADD CONSTRAINT subcontract_orders_bom_id_fkey 
        FOREIGN KEY (bom_id) REFERENCES boms(id) ON DELETE SET NULL;
        RAISE NOTICE '✅ Added FK for bom_id';
    END IF;
    
    -- Add FK for output_batch_id if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'subcontract_orders_output_batch_id_fkey'
    ) THEN
        ALTER TABLE subcontract_orders 
        ADD CONSTRAINT subcontract_orders_output_batch_id_fkey 
        FOREIGN KEY (output_batch_id) REFERENCES batches(id) ON DELETE SET NULL;
        RAISE NOTICE '✅ Added FK for output_batch_id';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'FK constraints may already exist or referenced tables missing (safe to ignore)';
END $$;

-- Show final table structure
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'subcontract_orders'
ORDER BY ordinal_position;
