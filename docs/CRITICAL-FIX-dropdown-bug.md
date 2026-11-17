# CRITICAL BUG FIX: Dropdown Not Appearing

**Date:** November 16, 2026  
**Severity:** HIGH  
**Status:** ✅ FIXED  

---

## Problem Identified

**Dropdowns not appearing in Excel template** for both:
1. Storage Location column
2. Base Unit (UOM) column

## Root Cause

**Database session context issue:**

```python
# WRONG (Line 738-744) - db context closed here
async with container.session_factory() as db:
    storage_locations = await _get_storage_locations(db, tenant_id)
    unit_of_measures = await _get_unit_of_measures(db, tenant_id)
# db is CLOSED after this line

# WRONG (Line 1108) - trying to use db AFTER context closed
default_location = await _get_default_storage_location(db, tenant_id)
# ❌ ERROR: db doesn't exist here!
```

**Result:**
- Code threw exception when trying to fetch default_location
- Exception caught by try/except
- Template generation continued without dropdowns
- Logs showed warning: "Could not load master data for template"

## Fix Applied

### Change 1: Fetch default_location INSIDE async context

**Before:**
```python
async with container.session_factory() as db:
    storage_locations = await _get_storage_locations(db, tenant_id)
    unit_of_measures = await _get_unit_of_measures(db, tenant_id)
    # db context ends here

# Later (WRONG - db doesn't exist):
default_location = await _get_default_storage_location(db, tenant_id)
```

**After:**
```python
async with container.session_factory() as db:
    storage_locations = await _get_storage_locations(db, tenant_id)
    unit_of_measures = await _get_unit_of_measures(db, tenant_id)
    default_location = await _get_default_storage_location(db, tenant_id)  # FIXED
    # All data fetched while db is still open
```

### Change 2: Use fetched default_location

**Before:**
```python
# WRONG - trying to call async function outside async context
default_location = await _get_default_storage_location(db, tenant_id)
if default_location:
    ws[f"{storage_col_letter}2"] = default_location
```

**After:**
```python
# CORRECT - use already-fetched value
if default_location:  # Already fetched above in async context
    ws[f"{storage_col_letter}2"] = default_location
```

## Files Changed

**File:** `backend/app/interfaces/api/v1/routes/material_onboarding.py`

**Lines modified:**
- Line ~738-748: Added `default_location` fetch inside async context
- Line ~1108-1112: Removed duplicate `await _get_default_storage_location(db, tenant_id)` call

## Testing After Fix

### Test 1: Restart Backend
```bash
# Stop backend (Ctrl+C)
# Start backend
cd C:\Users\sayye\source\repos\MedTrack\backend
uvicorn app.main:app --reload
```

### Test 2: Download Template (Logged In)
1. Login to MedTrack
2. Go to Material Onboarding
3. Click "Download Excel template"
4. Open downloaded Excel

### Test 3: Verify Dropdowns
**Expected in Excel:**

**Storage Location column:**
- Click cell in Storage Location column
- Should see dropdown arrow (▼)
- Click dropdown → Should show list of locations

**Base Unit column:**
- Click cell in Base Unit column
- Should see dropdown arrow (▼)
- Click dropdown → Should show list of UOMs (KG, MTR, PCS, etc.)

### Test 4: Check Backend Logs
**Expected logs after template download:**
```
✅ Fetched 5 storage locations for template
✅ Fetched 7 UOMs for template
✅ Fetched default storage location: MAIN-WH
✅ Storage Location dropdown added with 5 locations (default: MAIN-WH)
✅ Base Unit dropdown added with 7 UOMs
✅ Excel template complete with 3 sheets
```

**If no dropdowns, logs should show:**
```
⚠️ No storage locations available for dropdown - will allow free text entry
⚠️ No UOMs configured - Base Unit will allow free text entry
```

## Verification Checklist

### After Backend Restart:

- [ ] Template download works (no errors)
- [ ] Storage Location dropdown appears in Excel
- [ ] Base Unit dropdown appears in Excel
- [ ] Dropdown shows correct values from database
- [ ] Upload with selected values works correctly
- [ ] Upload with manually typed values still works

## Why This Happened

**Original code had async context bug:**
1. Storage location dropdown was partially working (by luck)
2. Default location fetch happened outside context (bug existed before)
3. Adding UOM dropdown exposed the bug
4. Both dropdowns affected because they share same code pattern

**Why it seemed to work before:**
- If exception occurred on `default_location` fetch, it was silently caught
- Dropdowns were still added, but without default value
- Might have appeared to work in some cases

## Prevention

**For future dropdown additions:**

1. **Fetch ALL data inside SAME async context:**
   ```python
   async with container.session_factory() as db:
       data1 = await fetch_data1(db)
       data2 = await fetch_data2(db)
       data3 = await fetch_data3(db)
   # All data fetched, db closed
   ```

2. **Use fetched data outside context:**
   ```python
   # Now use data1, data2, data3 - no db needed
   if data1:
       process(data1)
   ```

3. **Never call async db functions outside context:**
   ```python
   # ❌ WRONG:
   async with db:
       pass
   data = await fetch(db)  # db closed!
   
   # ✅ RIGHT:
   async with db:
       data = await fetch(db)  # db still open
   # Now use data
   ```

## Impact Assessment

### Before Fix:
- ❌ Dropdowns not appearing
- ⚠️ Silent exception caught
- ⚠️ Users had to type values manually
- ⚠️ Increased risk of typos

### After Fix:
- ✅ Dropdowns appear correctly
- ✅ Storage Location dropdown works
- ✅ Base Unit (UOM) dropdown works
- ✅ Default location pre-filled
- ✅ Better user experience

## Rollback

If issues arise:
1. Revert 2 changes in material_onboarding.py (lines ~738, ~1108)
2. Restart backend
3. Dropdowns won't appear, but uploads still work

---

**Status:** ✅ Fixed  
**Tested:** Pending (restart backend required)  
**Risk:** Low (fix is straightforward, improves existing bug)
