-- Find all WAREHOUSE location UUIDs in your system

SELECT 
  'UNIQUE WAREHOUSE LOCATIONS' as check,
  l.id,
  l.name,
  COUNT(DISTINCT m.id) as num_materials,
  COUNT(DISTINCT sl.id) as num_stock_levels
FROM locations l
LEFT JOIN materials m ON m.location_id = l.id AND m.is_deleted = FALSE
LEFT JOIN stock_levels sl ON sl.location_id = l.id AND sl.is_deleted = FALSE
WHERE l.name = 'WAREHOUSE'
GROUP BY l.id, l.name
ORDER BY COUNT(DISTINCT m.id) DESC;

-- Show which materials point to which warehouse
SELECT 
  'MATERIALS' as type,
  m.code,
  l.name,
  l.id as location_id
FROM materials m
LEFT JOIN locations l ON m.location_id = l.id
WHERE m.code IN (
  'RM-MWA-000001', 'RM-MWA-000002', 'RM-TRA-000001', 'RM-TRA-000002',
  'RM-TRA-000003', 'RM-TRA-000004'
)
ORDER BY m.code;

-- Show which stock_levels point to which warehouse
SELECT 
  'STOCK_LEVELS' as type,
  m.code,
  l.name,
  l.id as location_id,
  sl.quantity
FROM stock_levels sl
JOIN materials m ON m.id = sl.material_id
LEFT JOIN locations l ON sl.location_id = l.id
WHERE m.code IN (
  'RM-MWA-000001', 'RM-MWA-000002', 'RM-TRA-000001', 'RM-TRA-000002',
  'RM-TRA-000003', 'RM-TRA-000004'
)
  AND sl.is_deleted = FALSE
ORDER BY m.code;
