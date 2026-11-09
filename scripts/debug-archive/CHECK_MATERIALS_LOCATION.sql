-- Check what materials.location_id points to

SELECT 
  m.code,
  m.current_stock,
  m.location_id,
  l.name as location_name
FROM materials m
LEFT JOIN locations l ON m.location_id = l.id
WHERE m.code IN (
  'RM-MWA-000001', 'RM-MWA-000002', 'RM-TRA-000001', 'RM-TRA-000002',
  'RM-TRA-000003', 'RM-TRA-000004'
)
ORDER BY m.code;
