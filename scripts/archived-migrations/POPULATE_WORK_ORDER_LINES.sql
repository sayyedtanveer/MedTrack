-- ============================================================================
-- POPULATE work_order_lines FOR EXISTING WORK ORDERS
-- ============================================================================
-- This script creates work_order_lines entries for existing work orders
-- that don't have them yet (single-product legacy work orders)
-- ============================================================================

BEGIN;

-- Count work orders without lines
DO $$
DECLARE
    wo_without_lines_count INT;
BEGIN
    SELECT COUNT(DISTINCT wo.id)
    INTO wo_without_lines_count
    FROM work_orders wo
    WHERE wo.is_deleted = FALSE
      AND NOT EXISTS (
          SELECT 1 FROM work_order_lines wol 
          WHERE wol.work_order_id = wo.id
      );
    
    RAISE NOTICE '🔍 Found % work orders without lines', wo_without_lines_count;
END $$;

-- Create work_order_lines entries for work orders that don't have them
-- This handles single-product legacy work orders
INSERT INTO work_order_lines (
    id,
    work_order_id,
    tenant_id,
    product_id,
    bom_id,
    planned_quantity,
    produced_quantity,
    scrap_quantity,
    status,
    is_deleted,
    deleted_at,
    created_at,
    updated_at
)
SELECT 
    gen_random_uuid() as id,
    wo.id as work_order_id,
    wo.tenant_id,
    wo.product_id,
    wo.bom_id,
    wo.planned_quantity,
    wo.produced_quantity,
    wo.scrap_quantity,
    CASE 
        WHEN wo.status = 'PLANNED' THEN 'PLANNED'
        WHEN wo.status = 'MATERIAL_RESERVED' THEN 'MATERIAL_RESERVED'
        WHEN wo.status = 'MATERIAL_ISSUED' THEN 'MATERIAL_ISSUED'
        WHEN wo.status = 'IN_PRODUCTION' THEN 'IN_PRODUCTION'
        WHEN wo.status = 'PAUSED' THEN 'PAUSED'
        WHEN wo.status = 'QC_PENDING' THEN 'QC_PENDING'
        WHEN wo.status = 'QC_APPROVED' THEN 'QC_APPROVED'
        WHEN wo.status = 'QC_REJECTED' THEN 'QC_REJECTED'
        WHEN wo.status = 'REWORK' THEN 'REWORK'
        WHEN wo.status = 'COMPLETED' THEN 'COMPLETED'
        WHEN wo.status = 'CANCELLED' THEN 'CANCELLED'
        ELSE 'PLANNED'
    END as status,
    wo.is_deleted,
    wo.deleted_at,
    wo.created_at,
    wo.updated_at
FROM work_orders wo
WHERE wo.is_deleted = FALSE
  AND NOT EXISTS (
      SELECT 1 FROM work_order_lines wol 
      WHERE wol.work_order_id = wo.id
  );

-- Show how many were created
DO $$
DECLARE
    lines_created_count INT;
BEGIN
    SELECT COUNT(*)
    INTO lines_created_count
    FROM work_order_lines;
    
    RAISE NOTICE '✅ Created work_order_lines entries';
    RAISE NOTICE '📊 Total work_order_lines rows: %', lines_created_count;
END $$;

-- Verify the data
SELECT 
    wo.wo_number,
    wo.status as wo_status,
    wol.status as line_status,
    wol.planned_quantity,
    wol.product_id,
    wol.bom_id
FROM work_orders wo
JOIN work_order_lines wol ON wol.work_order_id = wo.id
WHERE wo.is_deleted = FALSE
ORDER BY wo.created_at DESC
LIMIT 10;

COMMIT;

-- ============================================================================
-- ✅ MIGRATION COMPLETE!
-- ============================================================================
-- Existing work orders now have work_order_lines entries
-- The Work Order + BOM PDF should now show materials correctly!
-- ============================================================================
