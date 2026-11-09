-- ═════════════════════════════════════════════════════════════════════════════
-- FIX_CREATE_MISSING_STOCK_LEVELS.sql
-- 
-- Purpose: Create missing stock_levels records for materials that have
--          current_stock but no stock_levels entries
--
-- Problem: 14 materials show stock in materials.current_stock but have NO rows
--          in stock_levels table, causing "Warehouse: 0" display
--
-- Solution: Create stock_levels entries at the material's location_id with
--           quantity = current_stock and status = 'available'
-- ═════════════════════════════════════════════════════════════════════════════

BEGIN;

-- Step 2: Create stock_levels records
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
  gen_random_uuid(),
  m.tenant_id,
  m.id as material_id,
  m.location_id,
  'available',
  m.current_stock,
  FALSE,
  NOW(),
  NOW()
FROM materials m
WHERE m.code IN (
  'SF-SRE-000001', 'RM-00X-000006', 'RM-MWA-000002', 'RM-MWA-000001', 
  'RM-TRA-000004', 'RM-TRA-000002', 'RM-040-000002', 'RM-040-000001',
  'RM-TRA-000001', 'RM-TRA-000003', 'RM-149-000005', 'RM-RPE-000004',
  'RM-GB1-000003', 'RM-GT1-000002'
)
  AND m.is_deleted = FALSE
  AND m.current_stock > 0
  AND m.location_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM stock_levels sl
    WHERE sl.material_id = m.id
      AND sl.is_deleted = FALSE
      AND sl.quantity > 0
  );

-- Step 3: Log the creation in audit trail
INSERT INTO inventory_transactions (
  id,
  tenant_id,
  material_id,
  transaction_type,
  quantity,
  reference_type,
  reference_id,
  to_location_id,
  remarks,
  created_by,
  created_at,
  updated_at
)
SELECT 
  gen_random_uuid(),
  m.tenant_id,
  m.id,
  'in',
  m.current_stock,
  'stock_levels_creation_backfill',
  m.id,
  m.location_id,
  'Backfill: Created missing stock_levels record from materials.current_stock',
  (SELECT id FROM users WHERE is_deleted = FALSE LIMIT 1),
  NOW(),
  NOW()
FROM materials m
WHERE m.code IN (
  'SF-SRE-000001', 'RM-00X-000006', 'RM-MWA-000002', 'RM-MWA-000001', 
  'RM-TRA-000004', 'RM-TRA-000002', 'RM-040-000002', 'RM-040-000001',
  'RM-TRA-000001', 'RM-TRA-000003', 'RM-149-000005', 'RM-RPE-000004',
  'RM-GB1-000003', 'RM-GT1-000002'
)
  AND m.is_deleted = FALSE
  AND m.current_stock > 0
  AND m.location_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM stock_levels sl
    WHERE sl.material_id = m.id
      AND sl.is_deleted = FALSE
      AND sl.quantity > 0
  );

COMMIT;

-- ═════════════════════════════════════════════════════════════════════════════
-- VERIFICATION (run after to confirm)
-- ═════════════════════════════════════════════════════════════════════════════

SELECT 
  m.code,
  m.name,
  m.current_stock as total_stock,
  l.name as warehouse,
  COALESCE(SUM(sl.quantity), 0) as stock_at_warehouse,
  CASE 
    WHEN m.current_stock = COALESCE(SUM(sl.quantity), 0) THEN '✅ FIXED'
    ELSE '❌ STILL MISMATCH'
  END as status
FROM materials m
LEFT JOIN locations l ON m.location_id = l.id
LEFT JOIN stock_levels sl ON m.id = sl.material_id 
  AND sl.location_id = m.location_id
  AND sl.is_deleted = FALSE
WHERE m.code IN (
  'SF-SRE-000001', 'RM-00X-000006', 'RM-MWA-000002', 'RM-MWA-000001', 
  'RM-TRA-000004', 'RM-TRA-000002', 'RM-040-000002', 'RM-040-000001',
  'RM-TRA-000001', 'RM-TRA-000003', 'RM-149-000005', 'RM-RPE-000004',
  'RM-GB1-000003', 'RM-GT1-000002'
)
  AND m.is_deleted = FALSE
GROUP BY m.id, m.code, m.name, m.current_stock, l.name
ORDER BY m.code;
