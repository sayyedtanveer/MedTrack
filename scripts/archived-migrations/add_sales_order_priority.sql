-- Add priority field to sales_orders table
-- This allows users to set work order priority when creating sales orders

DO $$
BEGIN
    -- Add priority column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'sales_orders' AND column_name = 'priority'
    ) THEN
        ALTER TABLE sales_orders 
        ADD COLUMN priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL';
        
        RAISE NOTICE '✅ Added priority column to sales_orders';
    ELSE
        RAISE NOTICE '⏭️  priority column already exists';
    END IF;
    
    -- Add check constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'ck_sales_order_priority'
    ) THEN
        ALTER TABLE sales_orders 
        ADD CONSTRAINT ck_sales_order_priority 
        CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT'));
        
        RAISE NOTICE '✅ Added priority check constraint';
    ELSE
        RAISE NOTICE '⏭️  priority check constraint already exists';
    END IF;
    
    -- Add index if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'ix_sales_orders_priority'
    ) THEN
        CREATE INDEX ix_sales_orders_priority 
        ON sales_orders(tenant_id, priority);
        
        RAISE NOTICE '✅ Added priority index';
    ELSE
        RAISE NOTICE '⏭️  priority index already exists';
    END IF;
    
    RAISE NOTICE '';
    RAISE NOTICE '✅ Sales Order Priority Enhancement Complete!';
    RAISE NOTICE '';
    RAISE NOTICE 'Users can now set priority when creating sales orders:';
    RAISE NOTICE '  - URGENT: Rush orders, critical deadlines';
    RAISE NOTICE '  - HIGH: Important customers, time-sensitive';
    RAISE NOTICE '  - NORMAL: Standard orders (default)';
    RAISE NOTICE '  - LOW: Flexible deadlines, buffer stock';
    RAISE NOTICE '';
    RAISE NOTICE 'Auto-created work orders will inherit this priority!';
END $$;
