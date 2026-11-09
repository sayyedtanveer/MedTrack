-- ═════════════════════════════════════════════════════════════════════════════
-- VERIFY_STOCK_LEVELS_FIX.sql
-- 
-- Check if the FIX_CREATE_MISSING_STOCK_LEVELS.sql script executed successfully
-- ═════════════════════════════════════════════════════════════════════════════

-- Query 1: Current state of all 14 materials
SELECT 
  m.id,
  m.code,
  m.name,
  m.current_stock as total_stock_in_materials,
  m.location_id,
  l.name as storage_location_name,
  COUNT(sl.id) as stock_level_records,
  SUM(CASE WHEN sl.is_deleted = FALSE THEN sl.quantity ELSE 0 END) as total_qty_in_stock_levels,
  CASE 
    WHEN m.current_stock = COALESCE(SUM(CASE WHEN sl.is_deleted = FALSE THEN sl.quantity ELSE 0 END), 0) 
    THEN '✅ MATCH' 
    ELSE '❌ MISMATCH' 
  END as status
FROM materials m
LEFT JOIN locations l ON m.location_id = l.id
LEFT JOIN stock_levels sl ON m.id = sl.material_id
WHERE m.code IN (
  'SF-SRE-000001', 'RM-00X-000006', 'RM-MWA-000002', 'RM-MWA-000001', 
  'RM-TRA-000004', 'RM-TRA-000002', 'RM-040-000002', 'RM-040-000001',
  'RM-TRA-000001', 'RM-TRA-000003', 'RM-149-000005', 'RM-RPE-000004',
  'RM-GB1-000003', 'RM-GT1-000002'
)
  AND m.is_deleted = FALSE
GROUP BY m.id, m.code, m.name, m.current_stock, m.location_id, l.name
ORDER BY m.code;

-- ═════════════════════════════════════════════════════════════════════════════

-- Query 2: Detailed stock_levels for each material (shows location and quantity)
SELECT 
  m.code,
  m.name,
  l.name as location_name,
  sl.quantity,
  sl.stock_status,
  sl.is_deleted,
  sl.created_at
FROM materials m
JOIN stock_levels sl ON m.id = sl.material_id
LEFT JOIN locations l ON sl.location_id = l.id
WHERE m.code IN (
  'SF-SRE-000001', 'RM-00X-000006', 'RM-MWA-000002', 'RM-MWA-000001', 
  'RM-TRA-000004', 'RM-TRA-000002', 'RM-040-000002', 'RM-040-000001',
  'RM-TRA-000001', 'RM-TRA-000003', 'RM-149-000005', 'RM-RPE-000004',
  'RM-GB1-000003', 'RM-GT1-000002'
)
  AND m.is_deleted = FALSE
ORDER BY m.code, l.name;

-- ═════════════════════════════════════════════════════════════════════════════

-- Query 3: Check for specific material RM-TRA-000004 (the one you tested)
SELECT 
  m.id,
  m.code,
  m.name,
  m.current_stock,
  m.location_id,
  l.name as warehouse_name,
  sl.id as stock_level_id,
  sl.location_id as stock_location_id,
  sl.quantity as stock_qty,
  sl.stock_status,
  sl.created_at
FROM materials m
LEFT JOIN locations l ON m.location_id = l.id
LEFT JOIN stock_levels sl ON m.id = sl.material_id
WHERE m.code = 'RM-TRA-000004'
  AND m.is_deleted = FALSE
ORDER BY sl.created_at;

</content>
