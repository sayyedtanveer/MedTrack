# MedTrack Scripts Directory

This directory contains utility scripts for database management, testing, and maintenance.

## Directory Structure

### `/database` — Active Database Utilities
Frequently used scripts for database operations, testing, and maintenance.

**Scripts:**
- `sync_db.py` — Synchronize database schema across environments
- `find_heads.py` — Check Alembic migration heads for conflicts
- `run_priority_migration.py` — Execute priority-based migrations
- `seed_client_portal_demo.py` — Seed demo data for client portal
- `make_system_tenant.py` — Create system-level tenant
- `create_test_users.py` — Generate test user accounts
- `reset_supplier_password.py` — Reset supplier account password
- `link_supplier_user.py` — Link supplier to user account
- `print_users.py` — List all users in database
- `generate_enhanced_template.py` — Generate enhanced data templates
- `generate_init.py` — Generate initialization scripts
- `apply_doc_columns.py` — Apply document column schema
- `apply_schema_sync.py` — Apply schema synchronization
- `apply_subcontract_schema.py` — Apply subcontracting schema

**Usage:**
```bash
python scripts/database/sync_db.py
python scripts/database/create_test_users.py
```

---

### `/archived-migrations` — Historical Database Changes
Migration scripts and fixes from previous development phases. Kept for reference and potential rollback scenarios.

**Contents:**
- `add_*.py/sql` — Schema additions
- `fix_*.py/sql` — Bug fixes applied to schema
- `BACKFILL_*.sql` — Data backfill operations
- `POPULATE_*.sql` — Data population scripts
- Migration documentation files

**When to Use:**
- Reviewing historical schema changes
- Understanding what was modified and when
- Potential rollback to specific states
- Root cause analysis of past issues

---

### `/debug-archive` — Debug & Diagnostic Scripts
One-off debugging scripts, diagnostic queries, and testing utilities from development cycles. Archived for reference only.

**Contents:**
- `tmp_*.py` — Temporary debugging scripts
- `check_*.py` — Ad-hoc database checks
- `debug_*.py` — Issue-specific debugging
- `CREATE_*.sql`, `CHECK_*.sql`, etc. — Diagnostic SQL queries
- Test data generation scripts

**When to Use:**
- Debugging specific issues that recur
- Understanding past problem scenarios
- Reference for similar debugging needs

---

## Quick Reference

| Task | Script |
|------|--------|
| Setup test data | `python scripts/database/create_test_users.py` |
| Check migration status | `python scripts/database/find_heads.py` |
| Sync database | `python scripts/database/sync_db.py` |
| Reset supplier password | `python scripts/database/reset_supplier_password.py` |
| Generate templates | `python scripts/database/generate_enhanced_template.py` |
| Seed demo data | `python scripts/database/seed_client_portal_demo.py` |

---

## Notes

- **Active scripts** are kept in `database/` for easy access
- **Historical scripts** are archived in `archived-migrations/` for reference
- **Debug scripts** are in `debug-archive/` for occasional troubleshooting
- All scripts follow the same error handling and logging standards as the main application
- Ensure proper environment variables are set before running database scripts

---

**Last Updated:** November 9, 2026
