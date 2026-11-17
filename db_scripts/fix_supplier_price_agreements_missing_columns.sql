-- ============================================================================
-- Fix: supplier_price_agreements missing columns
--
-- The table was created via fix_procurement_pricing_migration.sql which
-- omitted purchase_uom_id and minimum_order_quantity.
-- The ORM model (SupplierPriceAgreementModel) includes both columns.
-- This script adds them safely.
--
-- Run once against your database. Safe to re-run (IF NOT EXISTS / IF NOT EXISTS
-- logic via column check).
-- ============================================================================

-- ── Step 0: Verify the columns are actually missing ───────────────────────
-- Should return 0 rows if the fix is needed.
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'supplier_price_agreements'
  AND column_name IN ('purchase_uom_id', 'minimum_order_quantity');


-- ── Step 1: Add missing columns ───────────────────────────────────────────
ALTER TABLE supplier_price_agreements
  ADD COLUMN IF NOT EXISTS purchase_uom_id      UUID         NULL,
  ADD COLUMN IF NOT EXISTS minimum_order_quantity NUMERIC(18, 6) NULL;


-- ── Step 2: Add FK constraint for purchase_uom_id ────────────────────────
-- Only run this if units_of_measure table exists and you want referential integrity.
-- Skip if you prefer a loose reference (matching the ORM which uses no ondelete).
ALTER TABLE supplier_price_agreements
  ADD CONSTRAINT IF NOT EXISTS fk_spa_purchase_uom_id
  FOREIGN KEY (purchase_uom_id)
  REFERENCES units_of_measure(id)
  ON DELETE RESTRICT;


-- ── Step 3: Verify ────────────────────────────────────────────────────────
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'supplier_price_agreements'
  AND column_name IN ('purchase_uom_id', 'minimum_order_quantity')
ORDER BY column_name;
-- Expected: 2 rows


-- ── Rollback (if needed) ─────────────────────────────────────────────────
/*
ALTER TABLE supplier_price_agreements
  DROP CONSTRAINT IF EXISTS fk_spa_purchase_uom_id,
  DROP COLUMN IF EXISTS purchase_uom_id,
  DROP COLUMN IF EXISTS minimum_order_quantity;
*/
