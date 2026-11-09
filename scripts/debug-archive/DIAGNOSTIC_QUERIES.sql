-- ═════════════════════════════════════════════════════════════════════════════
-- DIAGNOSTIC_QUERIES.sql
-- 
-- Find where stock actually is for the 14 mismatched materials
-- ═════════════════════════════════════════════════════════════════════════════

-- Query 1: Where Each Material's Stock Actually Is
-- Shows: material code, total stock, where it SHOULD be, where it ACTUALLY is
SELECT 
  m.code,
  m.name,
  m.current_stock as total_in_system,
  l_storage.name as storage_location_set,
  STRING_AGG(DISTINCT l_actual.name, ' | ' ORDER BY l_actual.name) as actual_locations_with_stock,
  STRING_AGG(DISTINCT sl.stock_status, ' | ') as stock_statuses,
  SUM(sl.quantity) as total_at_actual_locations
FROM materials m
LEFT JOIN locations l_storage ON m.location_id = l_storage.id
LEFT JOIN stock_levels sl ON m.id = sl.material_id 
  AND sl.is_deleted = FALSE
  AND sl.quantity > 0
LEFT JOIN locations l_actual ON sl.location_id = l_actual.id
WHERE m.code IN (
  'SF-SRE-000001', 'RM-00X-000006', 'RM-MWA-000002', 'RM-MWA-000001', 
  'RM-TRA-000004', 'RM-TRA-000002', 'RM-040-000002', 'RM-040-000001',
  'RM-TRA-000001', 'RM-TRA-000003', 'RM-149-000005', 'RM-RPE-000004',
  'RM-GB1-000003', 'RM-GT1-000002'
)
  AND m.is_deleted = FALSE
GROUP BY m.id, m.code, m.name, m.current_stock, l_storage.name
ORDER BY m.code;

-- ═════════════════════════════════════════════════════════════════════════════

-- Query 2: All Locations With Stock
-- Shows: which locations have stock, how many materials, total quantity
SELECT 
  l.name as location_name,
  COUNT(DISTINCT sl.material_id) as num_materials,
  SUM(sl.quantity) as total_qty,
  STRING_AGG(DISTINCT m.code, ', ' ORDER BY m.code) as material_codes
FROM stock_levels sl
JOIN locations l ON sl.location_id = l.id
JOIN materials m ON sl.material_id = m.id
WHERE sl.is_deleted = FALSE
  AND sl.quantity > 0
GROUP BY l.id, l.name
ORDER BY total_qty DESC;
