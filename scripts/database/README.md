# Database Utility Scripts

Active, frequently-used scripts for database operations and testing.

## Scripts

### `sync_db.py`
Synchronizes database schema across environments.
```bash
python sync_db.py
```

### `find_heads.py`
Checks Alembic migration heads for conflicts in multi-developer setups.
```bash
python find_heads.py
```

### `run_priority_migration.py`
Executes priority-based migrations for production deployments.
```bash
python run_priority_migration.py
```

### `seed_client_portal_demo.py`
Seeds demonstration data for the client portal.
```bash
python seed_client_portal_demo.py
```

### `make_system_tenant.py`
Creates a system-level tenant for administrative purposes.
```bash
python make_system_tenant.py
```

### `create_test_users.py`
Generates test user accounts with various roles for development/testing.
```bash
python create_test_users.py
```

### `reset_supplier_password.py`
Resets a supplier account password (requires supplier ID).
```bash
python reset_supplier_password.py --supplier-id <ID>
```

### `link_supplier_user.py`
Links a supplier account to a user account.
```bash
python link_supplier_user.py --supplier-id <ID> --user-id <ID>
```

### `print_users.py`
Lists all users in the database with their roles and tenant.
```bash
python print_users.py
```

### `generate_*.py`
Generate data templates and initialization scripts.
```bash
python generate_enhanced_template.py
python generate_init.py
```

### `apply_*.py`
Apply schema changes and synchronizations.
```bash
python apply_schema_sync.py
python apply_subcontract_schema.py
python apply_doc_columns.py
```

---

## Environment Setup

Before running scripts, ensure:
1. `.env` file is configured with database credentials
2. Python virtual environment is activated
3. Dependencies from `requirements.txt` are installed

```bash
source .venv/bin/activate  # Linux/Mac
# or
.\.venv\Scripts\Activate.ps1  # Windows PowerShell

pip install -r requirements.txt
```

---

## Error Handling

All scripts include:
- Try/catch error handling
- Detailed error messages
- Transaction rollback on failure
- Logging of all operations

---

**Last Updated:** November 9, 2026
