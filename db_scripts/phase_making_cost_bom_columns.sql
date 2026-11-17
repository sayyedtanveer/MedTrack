-- ============================================================================
-- Semi-Finished Making Cost — BOM Table Columns
-- Approved design: Option A (two nullable columns on boms)
--
-- DO NOT execute on shared/production databases without separate approval.
-- Run the pre-flight checks in STEP 0 first.
-- ============================================================================
--
-- PURPOSE
-- -------
-- Add outside making charge support to the boms table.
-- NULL for both fields = no making charge (all existing BOMs unaffected).
-- Zero making charge is valid (explicitly configured zero).
-- PER_PIECE is the only supported basis initially.
--
-- BACKWARD COMPATIBILITY
-- ----------------------
-- Both columns are nullable with no server-side default.
-- SQLAlchemy treats NULL as "not configured" in the application layer.
-- All existing BOMs continue to work with zero making_cost in rollup.
--
-- ============================================================================


-- ── STEP 0: PRE-FLIGHT CHECKS ─────────────────────────────────────────────────
-- Run these before the ALTER. Both must return 0 rows.

-- Check 1: Confirm columns do not already exist
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'boms'
  AND column_name IN ('making_charge', 'making_charge_basis');
-- Expected: 0 rows

-- Check 2: Confirm boms table exists
SELECT COUNT(*) AS bom_count FROM boms;
-- Expected: any non-error result


-- ── STEP 1: ADD COLUMNS ──────────────────────────────────────────────────────

ALTER TABLE boms
  ADD COLUMN IF NOT EXISTS making_charge       NUMERIC(18, 4)  NULL,
  ADD COLUMN IF NOT EXISTS making_charge_basis VARCHAR(20)     NULL;


-- ── STEP 2: ADD CHECK CONSTRAINTS ────────────────────────────────────────────

-- Constraint A: making_charge must not be negative when set
ALTER TABLE boms
  ADD CONSTRAINT chk_bom_making_charge_nonneg
  CHECK (making_charge IS NULL OR making_charge >= 0);

-- Constraint B: making_charge_basis must be a supported value when set
ALTER TABLE boms
  ADD CONSTRAINT chk_bom_making_charge_basis_valid
  CHECK (making_charge_basis IS NULL OR making_charge_basis IN ('PER_PIECE'));

-- Constraint C: both fields must be NULL together or both set together
ALTER TABLE boms
  ADD CONSTRAINT chk_bom_making_charge_paired
  CHECK (
    (making_charge IS NULL AND making_charge_basis IS NULL)
    OR
    (making_charge IS NOT NULL AND making_charge_basis IS NOT NULL)
  );


-- ── STEP 3: VERIFY ───────────────────────────────────────────────────────────

-- Confirm columns exist
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_name = 'boms'
  AND column_name IN ('making_charge', 'making_charge_basis')
ORDER BY column_name;

-- Confirm constraints exist
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'boms'::regclass
  AND conname IN (
    'chk_bom_making_charge_nonneg',
    'chk_bom_making_charge_basis_valid',
    'chk_bom_making_charge_paired'
  );


-- ── DEPLOYMENT ORDER ─────────────────────────────────────────────────────────
-- 1. Run pre-flight checks (STEP 0).
-- 2. Run STEP 1 (ADD COLUMN) — no lock contention, adds NULL columns instantly.
-- 3. Run STEP 2 (ADD CHECK CONSTRAINTS) — PostgreSQL validates existing rows;
--    all current rows have NULL values which satisfy all three constraints.
-- 4. Run STEP 3 to verify.
-- 5. Deploy application code (backend + frontend).
-- 6. Test a sample BOM update with making_charge in lower environments first.


-- ── LOCKING IMPLICATIONS ─────────────────────────────────────────────────────
-- ALTER TABLE ... ADD COLUMN NULL takes a brief ACCESS EXCLUSIVE lock on boms.
-- For large tables, run during a maintenance window or use:
--   BEGIN; SET lock_timeout = '5s'; ALTER TABLE boms ADD COLUMN ...; COMMIT;
-- ADD CONSTRAINT CHECK is validated immediately but does not rewrite rows for
-- PostgreSQL 12+ (uses a NOT VALID scan then VALIDATE CONSTRAINT).
-- For zero-downtime on large tables, consider:
--   ALTER TABLE boms ADD CONSTRAINT ... CHECK ... NOT VALID;
--   ALTER TABLE boms VALIDATE CONSTRAINT ...;  (runs without AccessExclusiveLock)


-- ── ROLLBACK ─────────────────────────────────────────────────────────────────
/*
ALTER TABLE boms
  DROP CONSTRAINT IF EXISTS chk_bom_making_charge_nonneg,
  DROP CONSTRAINT IF EXISTS chk_bom_making_charge_basis_valid,
  DROP CONSTRAINT IF EXISTS chk_bom_making_charge_paired,
  DROP COLUMN IF EXISTS making_charge,
  DROP COLUMN IF EXISTS making_charge_basis;
*/
