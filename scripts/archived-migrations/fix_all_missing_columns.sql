-- ═══════════════════════════════════════════════════════════════════════════════
-- EMERGENCY FIX: Add ALL missing columns to production database
-- 
-- This script adds missing columns from:
-- 1. Subcontracting feature (subcontract_orders table)
-- 2. Document management feature (document_associations table)
--
-- Safe to run multiple times (idempotent)
-- ═══════════════════════════════════════════════════════════════════════════════

-- ───────────────────────────────────────────────────────────────────────────────
-- PART 1: Fix subcontract_orders table
-- ───────────────────────────────────────────────────────────────────────────────
DO $$ 
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE 'FIXING: subcontract_orders table';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    
    -- Check if table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'subcontract_orders') THEN
        RAISE NOTICE '⚠️  Table subcontract_orders does not exist - skipping';
    ELSE
        -- Add bom_id
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'subcontract_orders' AND column_name = 'bom_id'
        ) THEN
            ALTER TABLE subcontract_orders ADD COLUMN bom_id UUID;
            RAISE NOTICE '✅ Added bom_id';
        ELSE
            RAISE NOTICE '⏭️  bom_id already exists';
        END IF;
        
        -- Add due_date
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'subcontract_orders' AND column_name = 'due_date'
        ) THEN
            ALTER TABLE subcontract_orders ADD COLUMN due_date DATE;
            RAISE NOTICE '✅ Added due_date';
        ELSE
            RAISE NOTICE '⏭️  due_date already exists';
        END IF;
        
        -- Add notes
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'subcontract_orders' AND column_name = 'notes'
        ) THEN
            ALTER TABLE subcontract_orders ADD COLUMN notes TEXT;
            RAISE NOTICE '✅ Added notes';
        ELSE
            RAISE NOTICE '⏭️  notes already exists';
        END IF;
        
        -- Add output_batch_id
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'subcontract_orders' AND column_name = 'output_batch_id'
        ) THEN
            ALTER TABLE subcontract_orders ADD COLUMN output_batch_id UUID;
            RAISE NOTICE '✅ Added output_batch_id';
        ELSE
            RAISE NOTICE '⏭️  output_batch_id already exists';
        END IF;
        
        -- Add received_quantity
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'subcontract_orders' AND column_name = 'received_quantity'
        ) THEN
            ALTER TABLE subcontract_orders ADD COLUMN received_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0;
            RAISE NOTICE '✅ Added received_quantity';
        ELSE
            RAISE NOTICE '⏭️  received_quantity already exists';
        END IF;
        
        -- Add approved_by
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'subcontract_orders' AND column_name = 'approved_by'
        ) THEN
            ALTER TABLE subcontract_orders ADD COLUMN approved_by UUID;
            RAISE NOTICE '✅ Added approved_by';
        ELSE
            RAISE NOTICE '⏭️  approved_by already exists';
        END IF;
        
        -- Add approved_at
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'subcontract_orders' AND column_name = 'approved_at'
        ) THEN
            ALTER TABLE subcontract_orders ADD COLUMN approved_at TIMESTAMP WITH TIME ZONE;
            RAISE NOTICE '✅ Added approved_at';
        ELSE
            RAISE NOTICE '⏭️  approved_at already exists';
        END IF;
        
        -- Add created_by
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'subcontract_orders' AND column_name = 'created_by'
        ) THEN
            ALTER TABLE subcontract_orders ADD COLUMN created_by UUID;
            RAISE NOTICE '✅ Added created_by';
        ELSE
            RAISE NOTICE '⏭️  created_by already exists';
        END IF;
        
        RAISE NOTICE '✅ subcontract_orders table updated';
    END IF;
END $$;

-- ───────────────────────────────────────────────────────────────────────────────
-- PART 2: Fix document_associations table
-- ───────────────────────────────────────────────────────────────────────────────
DO $$ 
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE 'FIXING: document_associations table';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    
    -- Check if table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'document_associations') THEN
        RAISE NOTICE '⚠️  Table document_associations does not exist - skipping';
    ELSE
        -- Add show_on_wo
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'document_associations' AND column_name = 'show_on_wo'
        ) THEN
            ALTER TABLE document_associations ADD COLUMN show_on_wo BOOLEAN NOT NULL DEFAULT TRUE;
            RAISE NOTICE '✅ Added show_on_wo (default TRUE)';
        ELSE
            RAISE NOTICE '⏭️  show_on_wo already exists';
        END IF;
        
        -- Add work_order_line_id
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'document_associations' AND column_name = 'work_order_line_id'
        ) THEN
            ALTER TABLE document_associations ADD COLUMN work_order_line_id UUID;
            RAISE NOTICE '✅ Added work_order_line_id';
        ELSE
            RAISE NOTICE '⏭️  work_order_line_id already exists';
        END IF;
        
        -- Add created_at if missing (should exist but checking for completeness)
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'document_associations' AND column_name = 'created_at'
        ) THEN
            ALTER TABLE document_associations ADD COLUMN created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
            RAISE NOTICE '✅ Added created_at';
        ELSE
            RAISE NOTICE '⏭️  created_at already exists';
        END IF;
        
        RAISE NOTICE '✅ document_associations table updated';
    END IF;
END $$;

-- ───────────────────────────────────────────────────────────────────────────────
-- PART 3: Add Foreign Key Constraints (if tables exist)
-- ───────────────────────────────────────────────────────────────────────────────
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE 'ADDING: Foreign Key Constraints';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    
    -- FK for subcontract_orders.bom_id
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'subcontract_orders') 
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'boms') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'subcontract_orders_bom_id_fkey'
        ) THEN
            BEGIN
                ALTER TABLE subcontract_orders 
                ADD CONSTRAINT subcontract_orders_bom_id_fkey 
                FOREIGN KEY (bom_id) REFERENCES boms(id) ON DELETE SET NULL;
                RAISE NOTICE '✅ Added FK for subcontract_orders.bom_id → boms.id';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE '⚠️  Could not add FK for bom_id: %', SQLERRM;
            END;
        ELSE
            RAISE NOTICE '⏭️  FK for bom_id already exists';
        END IF;
    END IF;
    
    -- FK for subcontract_orders.output_batch_id
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'subcontract_orders') 
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'batches') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'subcontract_orders_output_batch_id_fkey'
        ) THEN
            BEGIN
                ALTER TABLE subcontract_orders 
                ADD CONSTRAINT subcontract_orders_output_batch_id_fkey 
                FOREIGN KEY (output_batch_id) REFERENCES batches(id) ON DELETE SET NULL;
                RAISE NOTICE '✅ Added FK for subcontract_orders.output_batch_id → batches.id';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE '⚠️  Could not add FK for output_batch_id: %', SQLERRM;
            END;
        ELSE
            RAISE NOTICE '⏭️  FK for output_batch_id already exists';
        END IF;
    END IF;
    
    -- FK for document_associations.work_order_line_id
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'document_associations') 
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'work_order_lines') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'document_associations_work_order_line_id_fkey'
        ) THEN
            BEGIN
                ALTER TABLE document_associations 
                ADD CONSTRAINT document_associations_work_order_line_id_fkey 
                FOREIGN KEY (work_order_line_id) REFERENCES work_order_lines(id) ON DELETE CASCADE;
                RAISE NOTICE '✅ Added FK for document_associations.work_order_line_id → work_order_lines.id';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE '⚠️  Could not add FK for work_order_line_id: %', SQLERRM;
            END;
        ELSE
            RAISE NOTICE '⏭️  FK for work_order_line_id already exists';
        END IF;
    END IF;
    
    RAISE NOTICE '✅ Foreign key constraints processed';
END $$;

-- ───────────────────────────────────────────────────────────────────────────────
-- PART 4: Verification Summary
-- ───────────────────────────────────────────────────────────────────────────────
DO $$
DECLARE
    subcontract_count INTEGER := 0;
    document_count INTEGER := 0;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE 'VERIFICATION SUMMARY';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    
    -- Count subcontract_orders columns
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'subcontract_orders') THEN
        SELECT COUNT(*) INTO subcontract_count
        FROM information_schema.columns
        WHERE table_name = 'subcontract_orders'
        AND column_name IN ('bom_id', 'due_date', 'notes', 'output_batch_id', 
                           'received_quantity', 'approved_by', 'approved_at', 'created_by');
        RAISE NOTICE 'subcontract_orders: % of 8 expected columns present', subcontract_count;
    ELSE
        RAISE NOTICE 'subcontract_orders: Table does not exist';
    END IF;
    
    -- Count document_associations columns
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'document_associations') THEN
        SELECT COUNT(*) INTO document_count
        FROM information_schema.columns
        WHERE table_name = 'document_associations'
        AND column_name IN ('show_on_wo', 'work_order_line_id', 'created_at');
        RAISE NOTICE 'document_associations: % of 3 expected columns present', document_count;
    ELSE
        RAISE NOTICE 'document_associations: Table does not exist';
    END IF;
    
    RAISE NOTICE '';
    IF (subcontract_count = 8 OR NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'subcontract_orders'))
       AND (document_count = 3 OR NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'document_associations')) THEN
        RAISE NOTICE '🎉 ALL FIXES APPLIED SUCCESSFULLY!';
        RAISE NOTICE '';
        RAISE NOTICE 'Next steps:';
        RAISE NOTICE '1. Restart your backend service';
        RAISE NOTICE '2. Test the APIs:';
        RAISE NOTICE '   - /api/v1/inventory/materials';
        RAISE NOTICE '   - /api/v1/documents/work_order/{id}/generate';
        RAISE NOTICE '3. Verify no more column errors in logs';
    ELSE
        RAISE NOTICE '⚠️  Some columns may be missing. Check details above.';
    END IF;
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
END $$;
