# Troubleshooting: Dropdowns Not Appearing

**Issue:** Storage Location and Base Unit dropdowns not showing in Excel template

---

## Step 1: Restart Backend Server (CRITICAL)

**The backend MUST be restarted to pick up code changes!**

```powershell
# 1. Stop current backend (press Ctrl+C in terminal where backend is running)

# 2. Restart backend
cd C:\Users\sayye\source\repos\MedTrack\backend
uvicorn app.main:app --reload
```

**Wait for:** "Application startup complete" message

---

## Step 2: Check Backend Logs

### Download Template While Watching Logs

1. **Start backend** and watch the console
2. **Login to MedTrack** in browser
3. **Download Excel template** from Material Onboarding page
4. **Check logs** for these messages:

### Expected Logs (Dropdowns Working):

```
🔍 Fetching master data for tenant: <uuid>
✅ Fetched 5 storage locations: ['MAIN-WH', 'STORE-1', ...]
✅ Fetched 7 UOMs: ['KG', 'MTR', 'PCS', 'LTR', ...]
✅ Fetched default storage location: MAIN-WH
📋 Adding Storage Location dropdown with 5 options
✅ Storage Location dropdown added to column I with 5 locations
📋 Adding Base Unit dropdown with 7 options
✅ Base Unit dropdown added to column D with 7 UOMs
✅ Excel template complete with 3 sheets
```

### Problem Logs (No Master Data):

```
🔍 Fetching master data for tenant: <uuid>
✅ Fetched 0 storage locations: []
✅ Fetched 0 UOMs: []
⚠️  No storage locations available - dropdown will not be added
⚠️  No UOMs configured - dropdown will not be added
```

**Solution:** Add master data (see Step 3)

### Problem Logs (Not Authenticated):

```
⚠️  No authentication - template will not include dropdowns
```

**Solution:** Login before downloading template

---

## Step 3: Check Database for Master Data

### Check if UOMs exist:

```sql
-- Check UOMs for your tenant
SELECT id, tenant_id, code, name, is_active, is_deleted
FROM units_of_measure
WHERE is_deleted = false AND is_active = true
ORDER BY code;
```

**Expected:** At least KG, MTR, PCS, LTR, etc.

**If empty, add UOMs:**

```sql
-- Get your tenant ID first
SELECT id, name FROM tenants WHERE is_deleted = false LIMIT 1;

-- Add basic UOMs (replace <tenant_id> with actual UUID)
INSERT INTO units_of_measure (id, tenant_id, code, name, precision, is_active, is_deleted, created_at, updated_at, created_by, updated_by)
SELECT 
    gen_random_uuid(),
    '<tenant_id>'::uuid,
    uom.code,
    uom.name,
    uom.precision,
    true,
    false,
    NOW(),
    NOW(),
    (SELECT id FROM users WHERE tenant_id = '<tenant_id>'::uuid LIMIT 1),
    (SELECT id FROM users WHERE tenant_id = '<tenant_id>'::uuid LIMIT 1)
FROM (VALUES
    ('KG', 'Kilogram', 3),
    ('MTR', 'Meter', 2),
    ('PCS', 'Pieces', 0),
    ('LTR', 'Liter', 2),
    ('TON', 'Tonne', 3),
    ('BOX', 'Box', 0),
    ('SET', 'Set', 0)
) AS uom(code, name, precision)
WHERE NOT EXISTS (
    SELECT 1 FROM units_of_measure u
    WHERE u.tenant_id = '<tenant_id>'::uuid AND u.code = uom.code AND u.is_deleted = false
);
```

### Check if Storage Locations exist:

```sql
-- Check locations for your tenant  
SELECT id, tenant_id, code, name, is_active, is_default, is_deleted
FROM locations
WHERE is_deleted = false AND is_active = true
ORDER BY name;
```

**If empty, add locations:**

```sql
-- Add basic locations (replace <tenant_id> with actual UUID)
INSERT INTO locations (id, tenant_id, code, name, location_type, is_active, is_default, is_deleted, created_at, updated_at, created_by, updated_by)
SELECT 
    gen_random_uuid(),
    '<tenant_id>'::uuid,
    loc.code,
    loc.name,
    'WAREHOUSE',
    true,
    loc.is_default,
    false,
    NOW(),
    NOW(),
    (SELECT id FROM users WHERE tenant_id = '<tenant_id>'::uuid LIMIT 1),
    (SELECT id FROM users WHERE tenant_id = '<tenant_id>'::uuid LIMIT 1)
FROM (VALUES
    ('MAIN-WH', 'Main Warehouse', true),
    ('STORE-1', 'Storage Room 1', false),
    ('STORE-2', 'Storage Room 2', false)
) AS loc(code, name, is_default)
WHERE NOT EXISTS (
    SELECT 1 FROM locations l
    WHERE l.tenant_id = '<tenant_id>'::uuid AND l.code = loc.code AND l.is_deleted = false
);
```

---

## Step 4: Verify Dropdown in Excel

### How to Check:

1. **Download template** (after backend restart + database check)
2. **Open Excel file**
3. **Go to "Raw Materials" sheet** (NOT "Field Guide")
4. **Click on cell D2** (Base Unit column, row 2)
5. **Look for dropdown arrow (▼)** on right side of cell
6. **Click dropdown** → Should show list: KG, MTR, PCS, LTR, etc.

7. **Click on cell I2** (Storage Location column, row 2)
8. **Look for dropdown arrow (▼)**
9. **Click dropdown** → Should show your storage locations

### Dropdown Not Visible?

**Check in Excel:**
1. Click cell
2. Go to Excel menu: **Data** → **Data Validation**
3. Should show:
   - Allow: List
   - Source: "KG","MTR","PCS"...

If this exists but arrow doesn't show:
- It's an Excel display issue
- Dropdown still works (start typing to see list)
- Try clicking the cell and pressing Alt+Down Arrow

---

## Common Issues & Solutions

###  Issue 1: Backend Not Restarted

**Symptom:** Old template still downloading, no new logs

**Solution:** 
- Stop backend (Ctrl+C)
- Start backend again
- Wait for "Application startup complete"

### Issue 2: Not Logged In

**Symptom:** Logs show "No authentication"

**Solution:**
- Login to MedTrack first
- Then download template

### Issue 3: No Master Data

**Symptom:** Logs show "Fetched 0 UOMs" or "Fetched 0 storage locations"

**Solution:**
- Run SQL scripts above to add UOMs and locations
- Download template again

### Issue 4: Wrong Tenant

**Symptom:** Logs show data fetched but dropdown empty

**Solution:**
- Check you're logged in as correct tenant
- Verify UOMs/locations exist for YOUR tenant (not different tenant)

### Issue 5: Excel Cache

**Symptom:** Old template keeps opening

**Solution:**
- Delete old template file
- Clear browser cache/download folder
- Download fresh template

---

## Quick Diagnostic Checklist

Run through this list:

- [ ] Backend restarted after code changes
- [ ] Logged in to MedTrack before downloading
- [ ] Backend logs show "Fetched X UOMs" and "Fetched Y storage locations"
- [ ] Backend logs show "dropdown added to column"
- [ ] Downloaded NEW template (not old cached file)
- [ ] Opened "Raw Materials" sheet (not "Field Guide")
- [ ] Clicked on row 2 cells (not row 1 headers)
- [ ] At least 1 UOM exists in database for tenant
- [ ] At least 1 location exists in database for tenant

---

## Still Not Working?

**Send these logs:**

1. **Backend startup logs** (first 20 lines)
2. **Template download logs** (when you click download)
3. **Database query results:**
   ```sql
   SELECT COUNT(*) FROM units_of_measure WHERE is_deleted = false AND is_active = true;
   SELECT COUNT(*) FROM locations WHERE is_deleted = false AND is_active = true;
   ```
4. **Screenshot of Excel** showing:
   - Which sheet you're on
   - Which cell you clicked
   - Data Validation settings (Data → Data Validation menu)

---

## Expected Final Result

**When working correctly:**

1. **Backend logs show:**
   ```
   ✅ Fetched 7 UOMs: ['KG', 'MTR', 'PCS', ...]
   ✅ Fetched 5 storage locations: ['MAIN-WH', ...]
   ✅ Base Unit dropdown added to column D with 7 UOMs
   ✅ Storage Location dropdown added to column I with 5 locations
   ```

2. **Excel shows:**
   - Cell D2: Dropdown with KG, MTR, PCS, LTR, TON, BOX, SET
   - Cell I2: Dropdown with MAIN-WH, STORE-1, STORE-2

3. **Upload works:**
   - Select from dropdown → uploads successfully
   - Type manually (case-insensitive) → uploads successfully
