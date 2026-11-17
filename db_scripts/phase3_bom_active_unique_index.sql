-- ============================================================================
-- Phase 3 — BOM Active Uniqueness Indexes
-- Design-only. Review before executing. Do NOT run on production without
-- completing the pre-flight checks in the SAFETY section below.
-- ============================================================================
--
-- PURPOSE
-- -------
-- Prevent concurrent BOM activation from creating multiple active BOMs for
-- the same product+tenant combination. Without this constraint, two requests
-- arriving simultaneously can both pass the application-level deactivation
-- check and both set is_active=TRUE, leaving the product in an invalid state.
--
-- STRATEGY
-- --------
-- PostgreSQL partial unique indexes enforce uniqueness only where the WHERE
-- clause is true. This means:
--   - Two active BOMs for the same (tenant, variant) → rejected by DB
--   - Two inactive BOMs for the same (tenant, variant) → allowed (version history)
--   - Soft-deleted BOMs (is_deleted=TRUE) are excluded → no interference with
--     historical records
--   - Template and variant indexes are independent → activating a variant BOM
--     does NOT conflict with an active template BOM for the same product family
--
-- EXISTING DATA COMPATIBILITY
-- ---------------------------
-- The CREATE INDEX statement will FAIL if any (tenant_id, variant_id) pair
-- already has more than one row with is_active=TRUE AND is_deleted=FALSE.
-- Run the pre-flight queries below FIRST and resolve violations before applying.
--
-- CONCURRENCY / LOCKING
-- ---------------------
-- CREATE UNIQUE INDEX CONCURRENTLY avoids a full table lock during index build.
-- Normal SELECT/INSERT/UPDATE/DELETE continue during the build.
-- A brief lock is taken at the end to validate uniqueness.
-- If a concurrent activation race wins during the build window, the final
-- validation step will reject the index creation (not the data). Re-run after
-- resolving.
--
-- ROLLBACK
-- --------
-- DROP INDEX CONCURRENTLY uq_bom_one_active_per_variant;
-- DROP INDEX CONCURRENTLY uq_bom_one_active_per_template;
-- (No data is modified; dropping the index is fully reversible.)
--
-- ============================================================================


-- ── STEP 0: PRE-FLIGHT SAFETY CHECKS ─────────────────────────────────────────
-- Run these READ-ONLY queries first. If they return any rows, resolve the
-- violations before proceeding to STEP 1.

-- Check 1: Variants with multiple active BOMs (must return 0 rows)
SELECT tenant_id, variant_id, COUNT(*) AS active_bom_count
FROM boms
WHERE is_active = TRUE
  AND is_deleted = FALSE
  AND variant_id IS NOT NULL
GROUP BY tenant_id, variant_id
HAVING COUNT(*) > 1;

-- Check 2: Templates with multiple active BOMs (must return 0 rows)
SELECT tenant_id, template_id, COUNT(*) AS active_bom_count
FROM boms
WHERE is_active = TRUE
  AND is_deleted = FALSE
  AND template_id IS NOT NULL
GROUP BY tenant_id, template_id
HAVING COUNT(*) > 1;

-- ── STEP 1: CREATE INDEXES ────────────────────────────────────────────────────
-- Only proceed if both pre-flight checks return 0 rows.

-- Index A: at most one active BOM per (tenant, variant)
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_bom_one_active_per_variant
    ON boms (tenant_id, variant_id)
    WHERE is_active = TRUE
      AND is_deleted = FALSE
      AND variant_id IS NOT NULL;

-- Index B: at most one active BOM per (tenant, template)
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_bom_one_active_per_template
    ON boms (tenant_id, template_id)
    WHERE is_active = TRUE
      AND is_deleted = FALSE
      AND template_id IS NOT NULL;

-- ── STEP 2: VERIFY ───────────────────────────────────────────────────────────
-- Confirm both indexes were created successfully.

SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'boms'
  AND indexname IN ('uq_bom_one_active_per_variant', 'uq_bom_one_active_per_template');

-- ── STEP 3 (IF VIOLATIONS FOUND): DATA REPAIR ────────────────────────────────
-- If the pre-flight checks found violations, review each case manually.
-- The following query identifies which BOM IDs are involved:

/*
SELECT b.id, b.tenant_id, b.variant_id, b.template_id, b.version, b.is_active,
       b.created_at, b.updated_at
FROM boms b
WHERE b.is_active = TRUE
  AND b.is_deleted = FALSE
ORDER BY b.tenant_id, COALESCE(b.variant_id::text, b.template_id::text), b.created_at DESC;

-- To repair: keep only the most recently activated BOM active per product.
-- The deactivation must be performed by the application (via the existing
-- handle_activate endpoint) rather than by direct SQL to preserve audit trails.
-- If direct SQL is unavoidable in an emergency, record the change in the
-- tenant's audit log manually.
*/


-- ── ROLLBACK ─────────────────────────────────────────────────────────────────
-- To undo this migration (if needed):
/*
DROP INDEX CONCURRENTLY IF EXISTS uq_bom_one_active_per_variant;
DROP INDEX CONCURRENTLY IF EXISTS uq_bom_one_active_per_template;
*/
