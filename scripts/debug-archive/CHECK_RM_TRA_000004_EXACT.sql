-- RM-TRA-000004 - EXACT DIAGNOSIS

-- Get the material ID first
SELECT id, code, current_stock, location_id INTO TEMP mat_data
FROM materials 
WHERE code = 'RM-TRA-000004';

-- Show what materials table has
SELECT 'MATERIALS TABLE' as source, 
       code, current_stock, location_id,
       (SELECT name FROM locations WHERE id = location_id) as warehouse_name
FROM materials 
WHERE code = 'RM-TRA-000004';

-- Show EVERY stock_levels row for this material
SELECT 'STOCK_LEVELS TABLE' as source,
       sl.id, sl.location_id, sl.quantity, sl.stock_status, sl.is_deleted,
       (SELECT name FROM locations WHERE id = sl.location_id) as loc_name,
       sl.created_at
FROM stock_levels sl
WHERE sl.material_id = (SELECT id FROM mat_data)
ORDER BY sl.created_at;

-- Show what backend query will find (exact query from inventory_service.py line 1851)
SELECT 'BACKEND QUERY RESULT' as source,
       sl.quantity, sl.stock_status
FROM stock_levels sl
WHERE sl.material_id = (SELECT id FROM mat_data)
  AND sl.location_id = (SELECT location_id FROM mat_data)
  AND sl.stock_status = 'available'
  AND sl.is_deleted = FALSE;

-- Summary
SELECT 'SUMMARY' as check,
       m.current_stock as expected_qty,
       COALESCE((
         SELECT sl.quantity
         FROM stock_levels sl
         WHERE sl.material_id = m.id
           AND sl.location_id = m.location_id
           AND sl.stock_status = 'available'
           AND sl.is_deleted = FALSE
       ), 0) as found_qty,
       m.current_stock - COALESCE((
         SELECT sl.quantity
         FROM stock_levels sl
         WHERE sl.material_id = m.id
           AND sl.location_id = m.location_id
           AND sl.stock_status = 'available'
           AND sl.is_deleted = FALSE
       ), 0) as SHORT_BY
FROM materials m
WHERE m.code = 'RM-TRA-000004';
