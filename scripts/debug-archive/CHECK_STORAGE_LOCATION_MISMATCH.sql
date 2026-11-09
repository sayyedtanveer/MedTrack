-- ═════════════════════════════════════════════════════════════════════════════
-- CHECK_STORAGE_LOCATION_MISMATCH.sql
-- 
-- Purpose: Verify if Storage Location (Material.location_id) and Stock Location
--          (StockLevelModel.location_id) are misaligned, causing the "7 then 0"
--          stock display issue during subcontracting
-- ═════════════════════════════════════════════════════════════════════════════

-- Query 1: Find materials with stock but unknown storage location
SELECT 
  m.id,
  m.code,
  m.name,
  m.location_id as "StorageLocation",
  COUNT(sl.id) as "StockBuckets",
  SUM(sl.quantity) as "TotalStock",
  STRING_AGG(DISTINCT l.name, ', ') as "ActualLocationsWithStock"
FROM materials m
LEFT JOIN stock_levels sl ON sl.material_id = m.id 
  AND sl.is_deleted = FALSE
  AND sl.quantity > 0
LEFT JOIN locations l ON l.id = sl.location_id
WHERE m.is_deleted = FALSE
  AND m.current_stock > 0
GROUP BY m.id, m.code, m.name, m.location_id
HAVING COUNT(sl.id) > 0
ORDER BY m.current_stock DESC;

-- Query 2: Mismatches - materials where Storage Location ≠ actual stock location
WITH material_stock AS (
  SELECT 
    m.id,
    m.code,
    m.name,
    m.current_stock,
    m.location_id as storage_location_id,
    sl.location_id as stock_location_id,
    l.name as storage_location_name,
    l2.name as stock_location_name
  FROM materials m
  LEFT JOIN stock_levels sl ON sl.material_id = m.id 
    AND sl.is_deleted = FALSE 
    AND sl.quantity > 0
  LEFT JOIN locations l ON l.id = m.location_id
  LEFT JOIN locations l2 ON l2.id = sl.location_id
  WHERE m.is_deleted = FALSE
    AND m.current_stock > 0
)
SELECT 
  *,
  CASE 
    WHEN storage_location_id IS NULL THEN 'No Storage Location set'
    WHEN stock_location_id IS NULL THEN 'No Stock Found'
    WHEN storage_location_id != stock_location_id THEN 'MISMATCH!'
    ELSE 'OK'
  END as status
FROM material_stock
WHERE storage_location_id IS NULL 
  OR stock_location_id IS NULL 
  OR storage_location_id != stock_location_id
ORDER BY code;

-- Query 3: Count summary
SELECT 
  CASE 
    WHEN COUNT(*) = 0 THEN 'No issues found'
    ELSE 'MISMATCHES DETECTED: ' || COUNT(*)::TEXT || ' materials'
  END as summary
FROM (
  WITH material_stock AS (
    SELECT 
      m.id,
      m.location_id as storage_location_id,
      sl.location_id as stock_location_id
    FROM materials m
    LEFT JOIN stock_levels sl ON sl.material_id = m.id 
      AND sl.is_deleted = FALSE 
      AND sl.quantity > 0
    WHERE m.is_deleted = FALSE
      AND m.current_stock > 0
  )
  SELECT * FROM material_stock
  WHERE storage_location_id IS NULL 
    OR stock_location_id IS NULL 
    OR storage_location_id != stock_location_id
) mismatches;

-- Query 4: After subcontract assignment - showing the "7 then 0" effect
SELECT 
  m.code,
  m.name,
  m.current_stock as "TotalStock",
  m.location_id,
  l.name as "StorageLocationName",
  wh.warehouse_qty,
  sub.subcontractor_qty,
  CASE 
    WHEN wh.warehouse_qty IS NULL OR wh.warehouse_qty = 0 THEN '⚠️ WAREHOUSE EMPTY'
    ELSE '✓ Stock in warehouse'
  END as status
FROM materials m
LEFT JOIN locations l ON l.id = m.location_id
LEFT JOIN (
  SELECT 
    material_id,
    SUM(quantity) as warehouse_qty
  FROM stock_levels sl
  JOIN locations loc ON loc.id = sl.location_id
  WHERE sl.is_deleted = FALSE
    AND loc.type IN ('warehouse', 'zone', 'rack', 'bin')
  GROUP BY material_id
) wh ON wh.material_id = m.id
LEFT JOIN (
  SELECT 
    material_id,
    SUM(quantity) as subcontractor_qty
  FROM stock_levels sl
  JOIN locations loc ON loc.id = sl.location_id
  WHERE sl.is_deleted = FALSE
    AND loc.type = 'subcontractor'
  GROUP BY material_id
) sub ON sub.material_id = m.id
WHERE m.is_deleted = FALSE
  AND m.current_stock > 0
  AND (wh.warehouse_qty IS NULL OR wh.warehouse_qty = 0)
  AND (sub.subcontractor_qty > 0 OR m.current_stock > 0)
ORDER BY m.code;

-- Query 5: Detailed stock history - which warehouse was this in originally?
SELECT 
  m.code,
  m.name,
  m.current_stock as "TotalStock",
  sl.location_id,
  l.name as location_name,
  l.type as location_type,
  sl.quantity as "StockAtLocation",
  sl.stock_status,
  sl.created_at as "CreatedAt",
  sl.updated_at as "LastUpdated",
  it.transaction_type,
  it.created_at as "TransactionDate"
FROM materials m
JOIN stock_levels sl ON sl.material_id = m.id AND sl.is_deleted = FALSE
LEFT JOIN locations l ON l.id = sl.location_id
LEFT JOIN inventory_transactions it ON it.material_id = m.id 
  AND it.reference_type = 'onboarding_opening_balance'
WHERE m.is_deleted = FALSE
  AND m.current_stock > 0
ORDER BY m.code, l.type DESC, sl.created_at;
