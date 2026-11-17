# Database Migration Scripts

## Procurement Pricing Phase 2 Setup

### Overview
These scripts safely create the procurement pricing tables if they don't already exist. Safe to run multiple times - will skip existing tables.

### Quick Start

**Option 1: Python Script (Recommended)**
```bash
python scripts/database/run_procurement_pricing_migration.py
```

**Option 2: Direct SQL (Manual)**
```bash
# Using psql
psql -U postgres -h localhost -d medtrack -f db_scripts/create_procurement_pricing_tables_safe.sql

# Using pgAdmin or another SQL client
# Copy and paste content of: db_scripts/create_procurement_pricing_tables_safe.sql
```

### What Gets Created

Four new tables for procurement pricing:

1. **supplier_price_agreements** — Supplier pricing contracts
   - Status: DRAFT → PENDING → APPROVED → ACTIVE → EXPIRED/CANCELLED
   - Fields: supplier_id, material_id, base_price, currency_code, effective_from/to
   - 7 indexes for performance

2. **standard_cost_revisions** — Cost approval workflow
   - Status: PENDING → APPROVED/REJECTED
   - Fields: material_id, requested_cost, reason, approval tracking
   - 6 indexes

3. **material_cost_history** — Immutable audit log
   - Insert-only, no updates (complete historical record)
   - Change types: GRN_RECEIPT, GRN_REVERSAL, COST_REVISION_APPROVED, etc.
   - 4 indexes

4. **price_override_records** — Manual price override analytics
   - Tracks when prices were manually overridden
   - Reasons: QUALITY_ISSUE, RUSH_ORDER, BULK_DISCOUNT, VENDOR_PREFERENCE
   - 5 indexes

### Pre-requisites Fixed

The script automatically:
- ✅ Fixes null `operation_code` values in operations table
- ✅ Creates all tables with proper constraints
- ✅ Creates all indexes for performance
- ✅ Verifies tables exist at the end

### Features

**Safe Execution:**
- Each table creation wrapped in `DO $$` block
- Checks `IF NOT EXISTS` before creating
- Prints notices about what was created/skipped
- Idempotent - can run multiple times safely

**Multi-tenancy:**
- All tables have `tenant_id` column
- Soft deletes supported (`is_deleted`, `deleted_at`)
- Audit trail (`created_by`, `updated_by`, `created_at`, `updated_at`)

**Indexes:**
- Tenant filtering indexes
- Status/state indexes
- FK relationship indexes
- Timestamp indexes for sorting

### Verification

After running, verify with:

```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('supplier_price_agreements', 'standard_cost_revisions', 
                   'material_cost_history', 'price_override_records')
ORDER BY table_name;

-- Check no null operation_codes
SELECT COUNT(*) FROM operations WHERE operation_code IS NULL;

-- Check indexes
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('supplier_price_agreements', 'standard_cost_revisions',
                    'material_cost_history', 'price_override_records');
```

### Troubleshooting

**Connection Error:**
```
ERROR: could not connect to server: Connection refused
```
Solution: Ensure PostgreSQL is running on localhost:5432

**Database not found:**
```
ERROR: database "medtrack" does not exist
```
Solution: Check .env DATABASE_URL or create database:
```sql
CREATE DATABASE medtrack;
```

**Permission denied:**
```
ERROR: permission denied for schema public
```
Solution: Check user permissions or use superuser

**Table already exists:**
```
NOTICE: Table supplier_price_agreements already exists - skipping creation
```
This is normal - script is idempotent

### Testing

After migration, test the full workflow:

```bash
# Run the complete onboarding test
python tests/debug_full_onboarding_flow.py
```

Expected output:
```
======================================================================
✅ WORKFLOW COMPLETED SUCCESSFULLY
======================================================================
```

This will:
1. Upload CSV with supplier pricing
2. Validate data
3. Preview (shows 3 materials + 3 supplier agreements)
4. Execute import (creates records in database)

### Rollback (if needed)

To remove tables (use with caution):

```sql
DROP TABLE IF EXISTS price_override_records CASCADE;
DROP TABLE IF EXISTS material_cost_history CASCADE;
DROP TABLE IF EXISTS standard_cost_revisions CASCADE;
DROP TABLE IF EXISTS supplier_price_agreements CASCADE;
```

### Files

- `create_procurement_pricing_tables_safe.sql` — Main SQL script
- `fix_procurement_pricing_migration.sql` — Alternative (simpler) script
- `run_procurement_pricing_migration.py` — Python runner script
- `README.md` — This file

### Questions?

Check logs:
- Backend: http://127.0.0.1:8001/health
- Alembic: `python -m alembic current`
- Database: `psql -U postgres -d medtrack`

---

**Status:** Production Ready  
**Last Updated:** November 13, 2026  
**Tested:** ✅ Safe to run multiple times
