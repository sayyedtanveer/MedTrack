# Archived Migrations

Historical database migrations and schema fixes. Kept for reference and potential rollback.

## Purpose

These scripts document all schema changes made during development. They provide:
- Historical context for data structure evolution
- Reference for understanding how the schema was built
- Potential rollback points if needed
- Root cause analysis for past issues

## Organization

### Schema Additions
- `add_consumed_column.py` — Add consumed_quantity to tables
- `add_consumed_quantity.sql` — SQL version
- `add_sales_order_priority.sql` — Add priority to sales orders
- `add_test_po.py`, `add_test_po_simple.py` — Test data additions

### Bug Fixes
- `fix_db.py` — General database fixes
- `fix_production_subcontract.sql` — Fix subcontracting production
- `fix_reservation.py` — Fix inventory reservation logic
- `fix_so.py` — Fix sales order schema
- `fix_subcontract_*.py/sql` — Subcontracting fixes
- `fix_wo_status.py` — Fix work order status constraints

### Data Operations
- `BACKFILL_*.sql` — Backfill operations for data population
- `POPULATE_*.sql` — Initial data population
- Production migration scripts

### Documentation
- `SCHEMA_FIX_LOG.md` — Log of all schema changes
- `RUN_MIGRATION.md` — Migration execution guide

## Usage

**Do not run these scripts directly** unless specifically requested for:
1. **Rolling back** to a previous schema state
2. **Debugging** historical schema issues
3. **Understanding** how the schema evolved
4. **Reference** when making similar changes

## Important Notes

- These migrations are **archived only** — use Alembic for new migrations
- Always consult `SCHEMA_FIX_LOG.md` before attempting any rollback
- Test any rollback in development environment first
- Current schema is defined in Alembic migrations in `alembic/versions/`

---

**Last Updated:** November 9, 2026
