-- Fix the ONE broken material: RM-00X-000006

BEGIN;

-- Create missing stock_levels for RM-00X-000006
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
  m.id,
  m.location_id,
  'available',
  m.current_stock,
  FALSE,
  NOW(),
  NOW()
FROM materials m
WHERE m.code = 'RM-00X-000006'
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

-- Verify
SELECT 
  m.code,
  m.current_stock,
  COALESCE(SUM(sl.quantity), 0) as stock_level_qty,
  CASE 
    WHEN m.current_stock = COALESCE(SUM(sl.quantity), 0) THEN '✅ FIXED'
    ELSE '❌ STILL BROKEN'
  END as status
FROM materials m
LEFT JOIN stock_levels sl ON m.id = sl.material_id AND sl.is_deleted = FALSE
WHERE m.code = 'RM-00X-000006'
GROUP BY m.id, m.code, m.current_stock;
