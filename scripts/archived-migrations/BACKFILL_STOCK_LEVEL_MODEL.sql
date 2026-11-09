-- ═════════════════════════════════════════════════════════════════════════════
-- BACKFILL_STOCK_LEVEL_MODEL.sql
-- 
-- Purpose: For existing materials created via bulk upload that have opening_stock
--          but no corresponding StockLevelModel entries, create those entries now.
-- 
-- Context: Prior to the bulk upload fix (Sept 2026), when materials were uploaded
--          with opening_stock > 0, only InventoryTransactionModel was created.
--          StockLevelModel entries were never created, causing stock-by-location
--          queries to return empty even though current_stock was set.
-- 
-- Impact:
--  - ✅ Stock-by-location queries will return warehouse breakdown
--  - ✅ Issue Material drawer will show warehouse availability
--  - ✅ Subcontract issue will check correct warehouse stock
--
-- Safety:
--  - Only creates MISSING StockLevelModel entries
--  - Skips materials that already have stock-by-location data
--  - No data is deleted or modified
--  - Idempotent: safe to run multiple times
-- ═════════════════════════════════════════════════════════════════════════════

BEGIN;

-- Find each tenant's default warehouse (for stock allocation)
-- Then backfill StockLevelModel for materials with current_stock > 0
-- but no existing StockLevelModel entries

WITH tenant_warehouses AS (
  -- Get the first active warehouse for each tenant
  SELECT DISTINCT ON (tenant_id)
    tenant_id,
    id as warehouse_location_id
  FROM locations
  WHERE type = 'warehouse'
    AND is_deleted = FALSE
    AND is_active = TRUE
  ORDER BY tenant_id, created_at ASC
),

materials_needing_stock_allocation AS (
  -- Find materials that:
  -- 1. Have current_stock > 0 (from onboarding)
  -- 2. Have no StockLevelModel entries (backfill needed)
  SELECT
    m.id as material_id,
    m.tenant_id,
    m.current_stock,
    tw.warehouse_location_id
  FROM materials m
  JOIN tenant_warehouses tw ON tw.tenant_id = m.tenant_id
  WHERE m.current_stock > 0
    AND m.is_deleted = FALSE
    AND NOT EXISTS (
      -- Skip if StockLevelModel already exists for this material
      SELECT 1 FROM stock_levels sl
      WHERE sl.material_id = m.id
        AND sl.tenant_id = m.tenant_id
        AND sl.is_deleted = FALSE
    )
)

-- Insert StockLevelModel entries
INSERT INTO stock_levels (
  id,
  tenant_id,
  material_id,
  location_id,
  stock_status,
  quantity,
  is_deleted,
  created_at,
  updated_at
)
SELECT
  gen_random_uuid(),  -- unique ID
  tenant_id,
  material_id,
  warehouse_location_id,
  'available'::text,  -- stock_status
  current_stock,      -- quantity matches MaterialModel.current_stock
  FALSE,              -- is_deleted
  NOW(),              -- created_at
  NOW()               -- updated_at
FROM materials_needing_stock_allocation
ON CONFLICT (tenant_id, material_id, location_id, stock_status) 
  DO NOTHING;  -- Skip if somehow already exists

-- Verify results
WITH backfilled_summary AS (
  SELECT
    COUNT(DISTINCT material_id) as materials_processed,
    SUM(quantity) as total_stock_allocated
  FROM stock_levels
  WHERE created_at >= NOW() - INTERVAL '1 minute'
    AND stock_status = 'available'
    AND is_deleted = FALSE
)
SELECT 
  'Backfill complete:' as status,
  materials_processed,
  total_stock_allocated,
  'Check Issue Material drawer and stock-by-location queries' as next_step
FROM backfilled_summary;

COMMIT;

-- ═════════════════════════════════════════════════════════════════════════════
-- VERIFICATION QUERIES (run after migration)
-- ═════════════════════════════════════════════════════════════════════════════

-- 1. Check materials that now have stock-by-location data
-- SELECT 
--   m.code,
--   m.name,
--   m.current_stock,
--   COUNT(sl.id) as warehouse_entries,
--   SUM(sl.quantity) as allocated_by_location
-- FROM materials m
-- LEFT JOIN stock_levels sl ON sl.material_id = m.id AND sl.is_deleted = FALSE
-- WHERE m.current_stock > 0
--   AND m.is_deleted = FALSE
-- GROUP BY m.id, m.code, m.name, m.current_stock
-- HAVING COUNT(sl.id) > 0;

-- 2. Check for any materials still missing stock allocation (should be empty)
-- SELECT m.code, m.name, m.current_stock
-- FROM materials m
-- WHERE m.current_stock > 0
--   AND m.is_deleted = FALSE
--   AND NOT EXISTS (
--     SELECT 1 FROM stock_levels sl
--     WHERE sl.material_id = m.id
--       AND sl.is_deleted = FALSE
--   );

-- 3. Check stock ledger entries exist for backfilled materials
-- SELECT sl.id, l.name, m.code, m.name, sl.quantity
-- FROM stock_levels sl
-- JOIN materials m ON m.id = sl.material_id
-- JOIN locations l ON l.id = sl.location_id
-- WHERE sl.created_at >= NOW() - INTERVAL '1 minute'
-- LIMIT 20;
