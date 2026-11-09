-- RM-TRA-000004 Direct Diagnosis - Run this NOW

-- Step 1: Get material ID
WITH mat AS (
  SELECT id, code, current_stock, location_id 
  FROM materials 
  WHERE code = 'RM-TRA-000004'
)

-- Step 2: Show all stock_levels for this material
SELECT 
  (SELECT location_id FROM mat) as materials_warehouse_location,
  sl.location_id as stock_level_location,
  sl.quantity,
  sl.stock_status,
  sl.is_deleted,
  CASE 
    WHEN sl.location_id = (SELECT location_id FROM mat) 
      AND sl.is_deleted = FALSE 
      AND sl.stock_status = 'available' 
    THEN '✅ THIS WILL BE DEDUCTED'
    ELSE '❌ IGNORED'
  END as will_be_used
FROM stock_levels sl, mat
WHERE sl.material_id = mat.id
ORDER BY sl.created_at DESC;

-- Step 3: Show what the backend will find
SELECT 
  'WHAT BACKEND QUERIES' as check,
  COALESCE(sl.quantity, 0) as available_qty,
  (SELECT current_stock FROM materials WHERE code = 'RM-TRA-000004') as expected_qty
FROM stock_levels sl
WHERE sl.material_id = (SELECT id FROM materials WHERE code = 'RM-TRA-000004')
  AND sl.location_id = (SELECT location_id FROM materials WHERE code = 'RM-TRA-000004')
  AND sl.stock_status = 'available'
  AND sl.is_deleted = FALSE
LIMIT 1;

-- Step 4: For ALL 14 materials - show the issue
SELECT 
  m.code,
  m.current_stock as materials_qty,
  COUNT(sl.id) as stock_level_rows,
  SUM(CASE WHEN sl.is_deleted = FALSE THEN sl.quantity ELSE 0 END) as active_qty,
  CASE 
    WHEN m.current_stock != COALESCE(SUM(CASE WHEN sl.is_deleted = FALSE THEN sl.quantity ELSE 0 END), 0)
    THEN '❌ MISMATCH - ' || (m.current_stock - COALESCE(SUM(CASE WHEN sl.is_deleted = FALSE THEN sl.quantity ELSE 0 END), 0)) || ' SHORT'
    ELSE '✅ MATCH'
  END as status
FROM materials m
LEFT JOIN stock_levels sl ON m.id = sl.material_id
WHERE m.code IN (
  'SF-SRE-000001', 'RM-00X-000006', 'RM-MWA-000002', 'RM-MWA-000001', 
  'RM-TRA-000004', 'RM-TRA-000002', 'RM-040-000002', 'RM-040-000001',
  'RM-TRA-000001', 'RM-TRA-000003', 'RM-149-000005', 'RM-RPE-000004',
  'RM-GB1-000003', 'RM-GT1-000002'
)
GROUP BY m.id, m.code, m.current_stock
ORDER BY m.code;
