-- ============================================================================
-- MANUAL MIGRATION: Add priority column to sales_orders table
-- ============================================================================
-- Run this script manually in your PostgreSQL client (pgAdmin, DBeaver, etc.)
-- Works on both LOCAL and PRODUCTION databases
-- ============================================================================

BEGIN;

-- Step 1: Add priority column with default value
ALTER TABLE sales_orders 
ADD COLUMN IF NOT EXISTS priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL';

-- Step 2: Add check constraint to ensure valid values
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

-- Step 3: Add index for efficient filtering
CREATE INDEX IF NOT EXISTS ix_sales_orders_priority 
ON sales_orders(tenant_id, priority);

-- Verify the column was added
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'sales_orders' 
  AND column_name = 'priority';

COMMIT;

-- ============================================================================
-- SUCCESS! Priority column added to sales_orders table
-- ============================================================================
-- Users can now set priority when creating sales orders:
--   🔴 URGENT  - Rush orders, critical deadlines
--   🟠 HIGH    - Important customers, time-sensitive  
--   🟢 NORMAL  - Standard orders (default)
--   ⚪ LOW     - Flexible deadlines, buffer stock
--
-- Auto-created work orders will inherit this priority!
-- ============================================================================
