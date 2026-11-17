# UOM (Unit of Measure) Dropdown Analysis & Recommendation

**Date:** November 16, 2026  
**Issue:** Base Unit field validation and Excel dropdown binding  
**Status:** Analysis Complete - Recommendation Provided  

---

## Current Implementation

### 1. UOM Validation (Backend)

**Location:** `backend/app/interfaces/api/v1/routes/material_onboarding.py`

**Current Behavior:**
```python
# Line 283: UOM extracted from data
uom = str(data.get("uom", "")).strip()

# Line 297-300: Validation
if not uom:
    issues.append({"field": "uom", "severity": "error", "message": "Base Unit is required"})
elif len(uom) > 20:
    issues.append({"field": "uom", "severity": "error", "message": "Base Unit cannot exceed 20 characters"})
```

**Current Auto-Creation:**
```python
# Line 1495-1509: Auto-creates missing UOMs (case-insensitive)
uom_code = str(data.get("uom", "")).strip().upper()
if uom_code and uom_code not in uom_map:
    new_uom = UnitOfMeasureModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=uom_code,  # UPPERCASE
        name=uom_code,
        precision=2,
        is_active=True,
        ...
    )
    db.add(new_uom)
    uom_map[uom_code] = new_uom.id
```

**Issues:**
- ❌ No validation against master UOM list
- ❌ Auto-creates UOMs on-the-fly (can lead to duplicates: "KG" vs "kg" vs "Kg")
- ❌ No Excel dropdown to guide users
- ✅ Case-insensitive matching (converts to uppercase)
- ⚠️ Can create invalid UOMs (typos: "KGS", "KILOGRAM", etc.)

### 2. Storage Location Dropdown (Already Implemented)

**Location:** Same file, lines 626-1088

**Current Behavior:**
```python
# Fetches storage locations from master
async def _get_storage_locations(db_session: AsyncSession, tenant_id: uuid.UUID) -> List[str]:
    stmt = (
        select(LocationModel)
        .where(
            LocationModel.tenant_id == tenant_id,
            LocationModel.is_deleted == False,
            LocationModel.is_active == True
        )
        .order_by(LocationModel.name.asc())
    )
    result = await db_session.execute(stmt)
    locations = result.scalars().all()
    return [loc.code if loc.code else loc.name for loc in locations]

# Adds Excel dropdown
storage_dv = DataValidation(type="list", formula1=f'"{storage_list}"', allow_blank=True)
storage_dv.error = 'Please select a storage location from the dropdown'
ws.add_data_validation(storage_dv)
```

**Benefits:**
- ✅ Guides users to select from valid values
- ✅ Prevents typos
- ✅ Still allows free text if needed (allow_blank=True)
- ✅ Clear error message when invalid value entered

---

## Problem Analysis

### Scenario 1: Current Behavior (No Dropdown)

**Master UOMs in Database:**
```
- KG (Kilogram)
- MTR (Meter)
- PCS (Pieces)
```

**User Uploads Excel:**
```
Row 1: Base Unit = "kg"      → Auto-creates "KG" (duplicate!)
Row 2: Base Unit = "Kg"      → Maps to existing "KG" ✓
Row 3: Base Unit = "KGS"     → Auto-creates "KGS" (typo!)
Row 4: Base Unit = "KILOGRAM" → Auto-creates "KILOGRAM" (invalid!)
Row 5: Base Unit = "meter"   → Auto-creates "METER" (should be MTR)
```

**Problems:**
1. **Duplicate UOMs created:** Multiple entries for same unit
2. **Typos create invalid UOMs:** "KGS", "KILOGRAM", "KILO"
3. **No standardization:** Different users use different codes
4. **Inventory chaos:** Cannot aggregate stock across different UOM codes
5. **Reporting broken:** "KG" vs "kg" vs "KILOGRAM" treated as separate

### Scenario 2: With Dropdown (Recommended)

**Master UOMs in Database:**
```
- KG (Kilogram)
- MTR (Meter)
- PCS (Pieces)
```

**User Sees Excel Dropdown:**
```
Base Unit column → Dropdown shows:
  - KG
  - MTR
  - PCS
```

**User Uploads Excel:**
```
Row 1: Base Unit = "KG"   (selected from dropdown) → ✓ Valid
Row 2: Base Unit = "MTR"  (selected from dropdown) → ✓ Valid
Row 3: Base Unit = "PCS"  (selected from dropdown) → ✓ Valid
Row 4: Base Unit = "kg"   (typed manually) → ✓ Case-insensitive match to "KG"
Row 5: Base Unit = "LITER" (typed manually) → ✗ Error: "LITER not found in master. Contact admin to add."
```

**Benefits:**
1. **Prevents duplicates:** Users select from valid list
2. **Standardized codes:** Everyone uses "KG", not "kg"/"KILOGRAM"
3. **Catches typos:** Invalid UOMs rejected before import
4. **Better UX:** Users see available options
5. **Data integrity:** Stock aggregation works correctly

---

## Recommendation: Add UOM Dropdown ✅

### Implementation Strategy

**Option A: Strict Validation (Recommended)**

**Pros:**
- ✅ Highest data quality
- ✅ Forces standardization
- ✅ Prevents invalid UOMs
- ✅ Clear error messages guide users

**Cons:**
- ⚠️ Requires admin to add UOMs first
- ⚠️ Less flexible for new UOMs

**Use Case:** Production systems, multi-user environments, inventory-heavy businesses

**Option B: Soft Validation (Fallback)**

**Pros:**
- ✅ Flexible for new UOMs
- ✅ Warning instead of error
- ✅ Auto-creates if needed

**Cons:**
- ❌ Can still create duplicates
- ❌ Less data quality enforcement

**Use Case:** Small businesses, single-user, rapid prototyping

### Recommended Implementation: **Option A (Strict Validation)**

**Reasoning:**
1. **MedTrack is production ERP** — Data quality is critical
2. **Multi-tenant SaaS** — Standardization required
3. **Inventory management** — Stock aggregation depends on consistent UOMs
4. **Compliance** — Audit trails need standardized units
5. **Already precedent** — Storage Location uses dropdown successfully

---

## Implementation Plan

### Phase 1: Add UOM Dropdown to Template (High Priority)

**1. Create Helper Function (Similar to Storage Locations):**

```python
async def _get_unit_of_measures(db_session: AsyncSession, tenant_id: uuid.UUID) -> List[str]:
    """
    Fetch all active UOMs for a tenant.
    Used for Excel data validation dropdown.
    Returns: List of UOM codes sorted alphabetically.
    """
    try:
        stmt = (
            select(UnitOfMeasureModel.code)
            .where(
                UnitOfMeasureModel.tenant_id == tenant_id,
                UnitOfMeasureModel.is_deleted == False,
                UnitOfMeasureModel.is_active == True
            )
            .order_by(UnitOfMeasureModel.code.asc())
        )
        result = await db_session.execute(stmt)
        uoms = [row.code for row in result.scalars().all() if row]
        return uoms
    except Exception as e:
        logging.warning(f"Could not fetch UOMs: {e}")
        return []
```

**2. Fetch UOMs in Template Endpoint:**

```python
@router.get("/template")
async def get_template(...):
    # Fetch storage locations (existing)
    storage_locations = await _get_storage_locations(db, tenant_id)
    
    # Fetch UOMs (NEW)
    unit_of_measures = await _get_unit_of_measures(db, tenant_id)
    logging.info(f"✅ Fetched {len(unit_of_measures)} UOMs for template")
```

**3. Add Excel Dropdown (Similar to Storage Location):**

```python
# Add data validation for Base Unit dropdown
if unit_of_measures:
    uom_list = '","'.join(unit_of_measures)
    uom_dv = DataValidation(
        type="list", 
        formula1=f'"{uom_list}"', 
        allow_blank=False  # Required field
    )
    uom_dv.error = 'Please select a Unit of Measure from the dropdown or contact admin to add new UOM'
    uom_dv.errorTitle = 'Invalid Unit'
    uom_dv.showErrorMessage = True
    ws.add_data_validation(uom_dv)
    
    # Apply to Base Unit column (find index)
    try:
        uom_col_idx = FRIENDLY_COLUMNS.index("Base Unit") + 1
        uom_col_letter = get_column_letter(uom_col_idx)
        uom_dv.add(f"{uom_col_letter}2:{uom_col_letter}1048576")
        logging.info(f"✅ UOM dropdown added with {len(unit_of_measures)} units")
    except ValueError:
        logging.warning("Base Unit column not found in FRIENDLY_COLUMNS")
else:
    logging.warning("⚠️ No UOMs available - user must contact admin to configure UOMs first")
```

### Phase 2: Add Strict Validation (High Priority)

**1. Remove Auto-Create Logic:**

```python
# DELETE THIS (Lines 1495-1509):
# if uom_code and uom_code not in uom_map:
#     new_uom = UnitOfMeasureModel(...)  # ❌ Remove auto-creation
```

**2. Add Validation in _validate_row:**

```python
def _validate_row(data, row_num, existing_codes, available_uoms: Set[str]):
    """
    Args:
        available_uoms: Set of valid UOM codes (UPPERCASE)
    """
    uom = str(data.get("uom", "")).strip()
    
    if not uom:
        issues.append({
            "field": "uom",
            "severity": "error",
            "message": "Base Unit is required"
        })
    elif len(uom) > 20:
        issues.append({
            "field": "uom",
            "severity": "error",
            "message": "Base Unit cannot exceed 20 characters"
        })
    elif uom.upper() not in available_uoms:
        issues.append({
            "field": "uom",
            "severity": "error",
            "message": f"Base Unit '{uom}' not found in master. Available: {', '.join(sorted(available_uoms)[:5])}... Contact admin to add new UOM."
        })
```

**3. Pass Available UOMs to Validation:**

```python
# In validate endpoint (line ~1360)
async def validate_session(...):
    # Fetch available UOMs
    uom_result = await db.execute(
        select(UnitOfMeasureModel.code).where(
            UnitOfMeasureModel.tenant_id == tenant_id,
            UnitOfMeasureModel.is_deleted == False,
            UnitOfMeasureModel.is_active == True
        )
    )
    available_uoms = {row.code.upper() for row in uom_result.scalars().all()}
    
    # Pass to validation
    for row in rows:
        classification, status, issues, changes = _validate_row(
            row["data"], 
            row["row_number"], 
            existing_codes,
            available_uoms  # NEW parameter
        )
```

### Phase 3: Update Execution Logic (High Priority)

**Remove Auto-Create in Execute:**

```python
# In execute endpoint (line ~1492-1509)
# Phase 2: AUTO-CREATE MISSING UOMS → REMOVE THIS ENTIRE BLOCK

# OLD (DELETE):
# for row in actionable:
#     data = row["data"]
#     uom_code = str(data.get("uom", "")).strip().upper()
#     if uom_code and uom_code not in uom_map:
#         new_uom = UnitOfMeasureModel(...)  # ❌ Remove
#         db.add(new_uom)

# NEW: Assume UOMs already validated and exist
# If UOM not in uom_map, it's a bug (validation should have caught it)
```

### Phase 4: Same for Supplier UOM (Medium Priority)

**Apply same logic to Supplier UOM field:**

```python
# Add validation for supplier_uom
if has_supplier_pricing:
    supplier_uom = str(data.get("supplier_uom", "")).strip()
    if supplier_uom and supplier_uom.upper() not in available_uoms:
        issues.append({
            "field": "supplier_uom",
            "severity": "error",
            "message": f"Supplier UOM '{supplier_uom}' not found in master. Available: {', '.join(sorted(available_uoms)[:5])}..."
        })
```

---

## Case Sensitivity Strategy

### Recommended: Case-Insensitive Matching with Uppercase Storage

**Why:**
- ✅ User-friendly (users can type "kg" or "KG")
- ✅ Database standardized (all stored as "KG")
- ✅ Matching reliable (no duplicates from case differences)
- ✅ Industry standard (UOMs typically uppercase: KG, MTR, PCS)

**Implementation:**
```python
# When matching UOM from Excel:
uom_input = str(data.get("uom", "")).strip()
uom_normalized = uom_input.upper()  # Convert to uppercase

# Check against master (already uppercase in DB)
if uom_normalized not in uom_map:
    # Error: UOM not found
```

**Database Storage:**
- Always store UOMs in **UPPERCASE** (KG, not kg)
- Display to users in **UPPERCASE**
- Accept user input in any case, normalize to uppercase
- Excel dropdown shows **UPPERCASE** options

---

## Migration Plan

### Step 1: Seed Default UOMs (If Not Already Present)

**Ensure every tenant has basic UOMs:**

```sql
-- Script: seed_default_uoms.sql
INSERT INTO units_of_measure (id, tenant_id, code, name, precision, is_active, is_deleted, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    t.id AS tenant_id,
    uom.code,
    uom.name,
    uom.precision,
    true AS is_active,
    false AS is_deleted,
    NOW(),
    NOW()
FROM tenants t
CROSS JOIN (VALUES
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
    WHERE u.tenant_id = t.id AND u.code = uom.code AND u.is_deleted = false
);
```

### Step 2: Communicate Change to Users

**Email/Notification:**
```
🔔 Material Onboarding Update

We've improved the material upload process!

What's New:
✅ Base Unit now has a dropdown with valid options
✅ No more typos or invalid units
✅ Better data quality and inventory accuracy

Action Required:
If you need a new Unit of Measure (e.g., "GALLON"), contact your admin to add it to the master list before uploading materials.

Available Units: KG, MTR, PCS, LTR, TON, BOX, SET
```

### Step 3: Deploy Changes

1. Deploy backend code with dropdown
2. Test template download (verify dropdown appears)
3. Test upload with valid UOM (should work)
4. Test upload with invalid UOM (should show clear error)

### Step 4: Monitor & Support

**First Week:**
- Monitor error logs for UOM validation failures
- Track requests for new UOMs
- Provide admin training on adding UOMs

---

## Comparison: Current vs Recommended

| Aspect | Current (Auto-Create) | Recommended (Dropdown + Validation) |
|--------|----------------------|-------------------------------------|
| **Data Quality** | ❌ Low (duplicates, typos) | ✅ High (standardized, validated) |
| **User Experience** | ⚠️ Flexible but error-prone | ✅ Guided with dropdown |
| **Maintenance** | ❌ Cleanup required regularly | ✅ Clean from start |
| **Scalability** | ❌ Grows uncontrolled | ✅ Controlled growth |
| **Multi-user** | ❌ Inconsistent across users | ✅ Consistent for all users |
| **Reporting** | ❌ Aggregation broken | ✅ Reliable aggregation |
| **Admin Control** | ❌ No control over UOMs | ✅ Admin manages master list |
| **Error Messages** | ⚠️ Silent creation | ✅ Clear validation errors |

---

## Testing Checklist

### Test Case 1: Valid UOM from Dropdown
- ✅ User selects "KG" from dropdown
- ✅ Upload succeeds
- ✅ Material created with uom_id pointing to existing "KG"

### Test Case 2: Valid UOM Typed (Case-Insensitive)
- ✅ User types "kg" (lowercase)
- ✅ System normalizes to "KG"
- ✅ Upload succeeds
- ✅ Material created with correct UOM

### Test Case 3: Invalid UOM
- ✅ User types "KILOGRAM" (not in master)
- ✅ Validation fails with clear error
- ✅ Error message: "Base Unit 'KILOGRAM' not found. Available: KG, MTR, PCS... Contact admin to add."

### Test Case 4: Empty UOM
- ✅ User leaves Base Unit blank
- ✅ Validation fails
- ✅ Error: "Base Unit is required"

### Test Case 5: Dropdown Not Loaded (No Auth)
- ✅ User downloads template without authentication
- ✅ Base Unit column allows free text (no dropdown)
- ✅ Upload still validates against master

### Test Case 6: Admin Adds New UOM
- ✅ Admin adds "GALLON" to master
- ✅ Template downloaded after shows "GALLON" in dropdown
- ✅ Users can now upload materials with "GALLON"

---

## Recommendation Summary

### ✅ Implement UOM Dropdown with Strict Validation

**Rationale:**
1. **Data Quality First:** MedTrack is production ERP, not prototype
2. **Already Proven:** Storage Location dropdown works well
3. **Industry Standard:** ERPs enforce master data consistency
4. **User Benefit:** Dropdown guides users, reduces errors
5. **Admin Control:** Maintains data governance

**Implementation:**
- **Priority:** High (Phase 1 of next sprint)
- **Effort:** 4-6 hours (similar to storage location)
- **Risk:** Low (proven pattern already exists)
- **Breaking Change:** Yes (auto-create removed), but better UX

**Rollout:**
1. Seed default UOMs for all tenants
2. Deploy backend with dropdown + validation
3. Communicate change to users
4. Monitor and support first week

### Case Sensitivity: Case-Insensitive with Uppercase Storage
- Accept any case from user (kg, KG, Kg)
- Normalize to uppercase (KG)
- Store in database as uppercase
- Display in UI as uppercase

---

**Status:** ✅ Analysis Complete - Ready for Implementation  
**Next Step:** Review recommendation → Approve → Implement Phase 1  
**Estimated Timeline:** 1 sprint (4-6 hours development + testing)
