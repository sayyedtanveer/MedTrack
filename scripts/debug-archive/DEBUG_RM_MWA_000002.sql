-- Debug RM-MWA-000002 - Check exact location IDs

-- Get the material info
SELECT 
  m.id as material_id,
  m.code,
  m.name,
  m.current_stock,
  m.location_id as materials_warehouse_location
FROM materials m
WHERE m.code = 'RM-MWA-000002';

-- Get all locations named WAREHOUSE (what the user selected)
SELECT 
  l.id as location_id,
  l.name,
  l.created_at
FROM locations l
WHERE l.name = 'WAREHOUSE'
  AND l.is_deleted = FALSE;

-- Get all stock_levels for this material
SELECT 
  sl.id as stock_level_id,
  sl.location_id as stock_location,
  sl.quantity,
  sl.stock_status,
  l.name as location_name,
  l.id as location_id
FROM stock_levels sl
LEFT JOIN locations l ON sl.location_id = l.id
WHERE sl.material_id = (SELECT id FROM materials WHERE code = 'RM-MWA-000002')
  AND sl.is_deleted = FALSE;

-- Check: do they match?
SELECT 
  'Material location_id' as type,
  m.location_id as value
FROM materials m
WHERE m.code = 'RM-MWA-000002'
UNION ALL
SELECT 
  'Stock_levels location_id' as type,
  DISTINCT sl.location_id as value
FROM stock_levels sl
WHERE sl.material_id = (SELECT id FROM materials WHERE code = 'RM-MWA-000002')
  AND sl.is_deleted = FALSE;
