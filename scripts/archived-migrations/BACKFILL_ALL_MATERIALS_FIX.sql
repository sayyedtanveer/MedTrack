BEGIN;

-- ═══════════════════════════════════════════════════════════════════
-- FIX ALL MATERIALS: Move stock from actual location to storage location
-- ═══════════════════════════════════════════════════════════════════

-- Step 1: Find all mismatches for the 14 materials
WITH mismatches AS (
  SELECT 
    m.id as material_id,
    m.tenant_id,
    m.code,
    m.name,
    m.current_stock,
    m.location_id as storage_location_id,
    l_storage.name as storage_location_name,
    -- Get the actual stock location
    (
      SELECT sl.location_id
      FROM stock_levels sl
      WHERE sl.material_id = m.id
        AND sl.tenant_id = m.tenant_id
        AND sl.is_deleted = FALSE
        AND sl.quantity > 0
      ORDER BY sl.created_at ASC
      LIMIT 1
    ) as actual_stock_location_id,
    l_actual.name as actual_stock_location_name
  FROM materials m
  LEFT JOIN locations l_storage ON l_storage.id = m.location_id
  LEFT JOIN locations l_actual ON l_actual.id = (
    SELECT sl.location_id
    FROM stock_levels sl
    WHERE sl.material_id = m.id
      AND sl.tenant_id = m.tenant_id
      AND sl.is_deleted = FALSE
      AND sl.quantity > 0
    ORDER BY sl.created_at ASC
    LIMIT 1
  )
  WHERE m.is_deleted = FALSE
    AND m.current_stock > 0
    AND m.location_id IS NOT NULL
    AND m.code IN (
      'SF-SRE-000001', 'RM-00X-000006', 'RM-MWA-000002', 'RM-MWA-000001', 
      'RM-TRA-000004', 'RM-TRA-000002', 'RM-040-000002', 'RM-040-000001',
      'RM-TRA-000001', 'RM-TRA-000003', 'RM-149-000005', 'RM-RPE-000004',
      'RM-GB1-000003', 'RM-GT1-000002'
    )
    AND (
      SELECT sl.location_id
      FROM stock_levels sl
      WHERE sl.material_id = m.id
        AND sl.tenant_id = m.tenant_id
        AND sl.is_deleted = FALSE
        AND sl.quantity > 0
      ORDER BY sl.created_at ASC
      LIMIT 1
    ) IS NOT NULL
    AND m.location_id != (
      SELECT sl.location_id
      FROM stock_levels sl
      WHERE sl.material_id = m.id
        AND sl.tenant_id = m.tenant_id
        AND sl.is_deleted = FALSE
        AND sl.quantity > 0
      ORDER BY sl.created_at ASC
      LIMIT 1
    )
),
stock_moves AS (
  SELECT 
    m.material_id,
    m.tenant_id,
    m.actual_stock_location_id as from_location_id,
    m.storage_location_id as to_location_id,
    m.code,
    m.name,
    m.current_stock as quantity_to_move,
    m.storage_location_name,
    m.actual_stock_location_name
  FROM mismatches m
)

-- Step 2: Log all transfers in audit trail
INSERT INTO inventory_transactions (
  id, tenant_id, material_id, transaction_type, quantity,
  reference_type, reference_id, from_location_id, to_location_id,
  remarks, created_by, created_at, updated_at
)
SELECT 
  gen_random_uuid(),
  sm.tenant_id,
  sm.material_id,
  'transfer',
  sm.quantity_to_move,
  'material_storage_location_backfill',
  sm.material_id,
  sm.from_location_id,
  sm.to_location_id,
  'Backfill: Storage Location sync from ' || sm.actual_stock_location_name || ' to ' || sm.storage_location_name,
  (SELECT id FROM users WHERE is_deleted = FALSE LIMIT 1),
  NOW(),
  NOW()
FROM stock_moves sm;

-- Step 3: Update stock_levels - reduce quantity at actual location
WITH stock_moves AS (
  SELECT 
    m.material_id,
    m.tenant_id,
    m.actual_stock_location_id,
    m.storage_location_id,
    m.quantity_to_move
  FROM (
    SELECT 
      m.id as material_id,
      m.tenant_id,
      m.location_id as storage_location_id,
      (
        SELECT sl.location_id
        FROM stock_levels sl
        WHERE sl.material_id = m.id
          AND sl.tenant_id = m.tenant_id
          AND sl.is_deleted = FALSE
          AND sl.quantity > 0
        ORDER BY sl.created_at ASC
        LIMIT 1
      ) as actual_stock_location_id,
      m.current_stock as quantity_to_move
    FROM materials m
    WHERE m.is_deleted = FALSE
      AND m.current_stock > 0
      AND m.location_id IS NOT NULL
      AND m.code IN (
        'SF-SRE-000001', 'RM-00X-000006', 'RM-MWA-000002', 'RM-MWA-000001', 
        'RM-TRA-000004', 'RM-TRA-000002', 'RM-040-000002', 'RM-040-000001',
        'RM-TRA-000001', 'RM-TRA-000003', 'RM-149-000005', 'RM-RPE-000004',
        'RM-GB1-000003', 'RM-GT1-000002'
      )
      AND m.location_id != (
        SELECT sl.location_id
        FROM stock_levels sl
        WHERE sl.material_id = m.id
          AND sl.tenant_id = m.tenant_id
          AND sl.is_deleted = FALSE
          AND sl.quantity > 0
        ORDER BY sl.created_at ASC
        LIMIT 1
      )
  ) m
)
UPDATE stock_levels sl
SET 
  quantity = 0,
  updated_at = NOW()
FROM stock_moves sm
WHERE sl.material_id = sm.material_id
  AND sl.tenant_id = sm.tenant_id
  AND sl.location_id = sm.actual_stock_location_id
  AND sl.quantity > 0;

-- Step 4: Update stock_levels - increase quantity at storage location
WITH stock_moves AS (
  SELECT 
    m.material_id,
    m.tenant_id,
    m.actual_stock_location_id,
    m.storage_location_id,
    m.quantity_to_move
  FROM (
    SELECT 
      m.id as material_id,
      m.tenant_id,
      m.location_id as storage_location_id,
      (
        SELECT sl.location_id
        FROM stock_levels sl
        WHERE sl.material_id = m.id
          AND sl.tenant_id = m.tenant_id
          AND sl.is_deleted = FALSE
          AND sl.quantity > 0
        ORDER BY sl.created_at ASC
        LIMIT 1
      ) as actual_stock_location_id,
      m.current_stock as quantity_to_move
    FROM materials m
    WHERE m.is_deleted = FALSE
      AND m.current_stock > 0
      AND m.location_id IS NOT NULL
      AND m.code IN (
        'SF-SRE-000001', 'RM-00X-000006', 'RM-MWA-000002', 'RM-MWA-000001', 
        'RM-TRA-000004', 'RM-TRA-000002', 'RM-040-000002', 'RM-040-000001',
        'RM-TRA-000001', 'RM-TRA-000003', 'RM-149-000005', 'RM-RPE-000004',
        'RM-GB1-000003', 'RM-GT1-000002'
      )
      AND m.location_id != (
        SELECT sl.location_id
        FROM stock_levels sl
        WHERE sl.material_id = m.id
          AND sl.tenant_id = m.tenant_id
          AND sl.is_deleted = FALSE
          AND sl.quantity > 0
        ORDER BY sl.created_at ASC
        LIMIT 1
      )
  ) m
)
UPDATE stock_levels sl
SET 
  quantity = sl.quantity + sm.quantity_to_move,
  updated_at = NOW()
FROM stock_moves sm
WHERE sl.material_id = sm.material_id
  AND sl.tenant_id = sm.tenant_id
  AND sl.location_id = sm.storage_location_id
  AND sl.stock_status = 'available'
  AND sl.is_deleted = FALSE;

COMMIT;

-- ═══════════════════════════════════════════════════════════════════
-- VERIFICATION QUERY (run after to confirm)
-- ═══════════════════════════════════════════════════════════════════

SELECT 
  m.code,
  m.name,
  m.current_stock as total_stock,
  l.name as warehouse,
  COALESCE(SUM(sl.quantity), 0) as stock_at_warehouse,
  CASE 
    WHEN m.current_stock = COALESCE(SUM(sl.quantity), 0) THEN '✅ SYNCED'
    ELSE '❌ MISMATCH'
  END as status
FROM materials m
LEFT JOIN locations l ON m.location_id = l.id
LEFT JOIN stock_levels sl ON m.id = sl.material_id 
  AND sl.location_id = m.location_id
  AND sl.is_deleted = FALSE
WHERE m.code IN (
  'SF-SRE-000001', 'RM-00X-000006', 'RM-MWA-000002', 'RM-MWA-000001', 
  'RM-TRA-000004', 'RM-TRA-000002', 'RM-040-000002', 'RM-040-000001',
  'RM-TRA-000001', 'RM-TRA-000003', 'RM-149-000005', 'RM-RPE-000004',
  'RM-GB1-000003', 'RM-GT1-000002'
)
  AND m.is_deleted = FALSE
GROUP BY m.id, m.code, m.name, m.current_stock, l.name
ORDER BY m.code;
