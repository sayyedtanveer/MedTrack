# Production Migration - Quick Reference Card

## 🚀 Quick Start (5 Steps)

### 1. Backup
```bash
pg_dump -h HOST -U USER -d DATABASE > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Connect & Start Transaction
```bash
psql -h HOST -U USER -d DATABASE
```
```sql
BEGIN;
```

### 3. Run Script
```sql
\i db_migration_prod_subcontract_documents.sql
```

### 4. Verify (Quick Check)
```sql
-- Should return 8 tables
SELECT COUNT(*) FROM pg_tables 
WHERE tablename IN (
    'subcontract_orders', 'subcontract_order_lines', 'subcontract_material_issues', 'subcontract_number_sequences',
    'file_attachments', 'technical_documents', 'document_revisions', 'document_associations'
);
```

### 5. Commit
```sql
COMMIT;  -- If count = 8 and no errors
-- OR
ROLLBACK;  -- If issues found
```

---

## 📋 Tables Created

### Subcontracting (4)
- `subcontract_orders` - Main orders
- `subcontract_order_lines` - Component requirements
- `subcontract_material_issues` - Issue transactions
- `subcontract_number_sequences` - Order numbering

### Documents (4)
- `file_attachments` - File metadata
- `technical_documents` - Document master
- `document_revisions` - Version control
- `document_associations` - Links to entities

### Modified (2)
- `subcontract_orders` - Status constraint updated
- `work_order_materials` - Added work_order_line_id column

---

## ✅ Success Indicators

```sql
-- 1. All tables exist (should return 8)
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_name IN (
    'subcontract_orders', 'subcontract_order_lines', 
    'subcontract_material_issues', 'subcontract_number_sequences',
    'file_attachments', 'technical_documents', 
    'document_revisions', 'document_associations'
);

-- 2. Status constraint correct (should return 1 row)
SELECT constraint_name 
FROM information_schema.check_constraints 
WHERE constraint_name = 'subcontract_orders_status_check'
AND check_clause LIKE '%draft%approved%materials_issued%';

-- 3. No orphaned records (should return 0)
SELECT COUNT(*) FROM subcontract_order_lines sol
LEFT JOIN subcontract_orders so ON sol.subcontract_order_id = so.id
WHERE so.id IS NULL;
```

---

## ⚠️ Rollback (Emergency Only)

### Within Transaction (BEFORE COMMIT)
```sql
ROLLBACK;
```

### After COMMIT
```sql
BEGIN;

DROP TABLE IF EXISTS document_associations CASCADE;
DROP TABLE IF EXISTS document_revisions CASCADE;
DROP TABLE IF EXISTS technical_documents CASCADE;
DROP TABLE IF EXISTS file_attachments CASCADE;
DROP TABLE IF EXISTS subcontract_material_issues CASCADE;
DROP TABLE IF EXISTS subcontract_order_lines CASCADE;
DROP TABLE IF EXISTS subcontract_orders CASCADE;
DROP TABLE IF EXISTS subcontract_number_sequences CASCADE;

ALTER TABLE work_order_materials DROP COLUMN IF EXISTS work_order_line_id;

COMMIT;
```

---

## 🔍 Troubleshooting

| Error | Solution |
|-------|----------|
| "relation already exists" | Safe - table exists, skip |
| "column already exists" | Safe - column exists, skip |
| "permission denied" | Run as DB owner/superuser |
| "foreign key violation" | Check prerequisite tables exist |

---

## 📊 Post-Migration Checks

```sql
-- Table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) AS size
FROM pg_tables
WHERE tablename LIKE 'subcontract%' OR tablename LIKE '%document%'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;

-- Index verification (should be ~15+)
SELECT COUNT(*) FROM pg_indexes 
WHERE tablename LIKE 'subcontract%' OR tablename LIKE '%document%';
```

---

## 📱 Contacts

**Issues During Migration:** DBA Team / DevOps  
**Post-Migration Issues:** Application Team  
**Rollback Decision:** Project Manager + DBA Lead  

---

## ⏱️ Timeline

- **Estimated Duration:** 5-15 minutes
- **Downtime Window:** Yes (stop app servers)
- **Best Time:** Off-peak hours
- **Backup Retention:** 30 days minimum

---

## 🎯 Final Checklist

- [ ] Database backup completed
- [ ] Tested on staging successfully
- [ ] Application servers stopped
- [ ] Users notified of maintenance
- [ ] Transaction started (BEGIN)
- [ ] Migration script executed
- [ ] Verification queries passed
- [ ] Committed (COMMIT)
- [ ] Application servers restarted
- [ ] Smoke tests passed
- [ ] Users notified completion
- [ ] Backup verified and stored

---

**File:** db_migration_prod_subcontract_documents.sql  
**Version:** 1.0  
**Date:** 2026-09-26  
**Risk:** Medium  
**Reversible:** Yes (within transaction)
