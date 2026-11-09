-- Quick diagnostic for RM-TRA-000004 (the one you tested)

-- What's in materials table?
SELECT 
  m.id, m.code, m.current_stock, m.location_id,
  l.name as warehouse_location
FROM materials m
LEFT JOIN locations l ON m.location_id = l.id
WHERE m.code = 'RM-TRA-000004';

-- What's in stock_levels table for this material? (ALL records, including deleted)
SELECT 
  sl.id, sl.material_id, sl.location_id, sl.quantity, sl.stock_status, sl.is_deleted,
  l.name as location_name, sl.created_at
FROM stock_levels sl
LEFT JOIN locations l ON sl.location_id = l.id
WHERE sl.material_id = (SELECT id FROM materials WHERE code = 'RM-TRA-000004')
ORDER BY sl.created_at DESC;

-- Count total qty in stock_levels (only active, not deleted)
SELECT 
  COUNT(*) as num_records,
  SUM(CASE WHEN is_deleted = FALSE THEN quantity ELSE 0 END) as total_active_qty,
  SUM(CASE WHEN is_deleted = TRUE THEN quantity ELSE 0 END) as total_deleted_qty
FROM stock_levels
WHERE material_id = (SELECT id FROM materials WHERE code = 'RM-TRA-000004');

