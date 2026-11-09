-- ============================================================================
-- QUICK FIX: Add missing columns to subcontract_material_issues table
-- ============================================================================
-- Run this immediately on production to fix the subcontract error
-- ============================================================================

BEGIN;

-- Add missing columns to subcontract_material_issues
ALTER TABLE subcontract_material_issues ADD COLUMN IF NOT EXISTS batch_id UUID;
ALTER TABLE subcontract_material_issues ADD COLUMN IF NOT EXISTS batch_number VARCHAR(100);
ALTER TABLE subcontract_material_issues ADD COLUMN IF NOT EXISTS returned_quantity NUMERIC(15, 3) DEFAULT 0;
ALTER TABLE subcontract_material_issues ADD COLUMN IF NOT EXISTS from_location_id UUID;
ALTER TABLE subcontract_material_issues ADD COLUMN IF NOT EXISTS issued_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE subcontract_material_issues ADD COLUMN IF NOT EXISTS issued_by UUID;

-- Add foreign key constraints if they don't exist
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

-- Verify columns were added
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'subcontract_material_issues'
  AND column_name IN ('batch_id', 'batch_number', 'returned_quantity', 'from_location_id', 'issued_at', 'issued_by')
ORDER BY ordinal_position;

COMMIT;

-- ============================================================================
-- ✅ FIX COMPLETE!
-- ============================================================================
-- The subcontract material issues table now has all required columns:
--   ✅ batch_id (FK → batches)
--   ✅ batch_number (VARCHAR for display/backward compat)
--   ✅ returned_quantity (tracking for returned items)
--   ✅ from_location_id (FK → locations, where material was issued from)
--   ✅ issued_at (when material was issued)
--   ✅ issued_by (who issued the material)
-- ============================================================================
