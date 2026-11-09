# Fix: Semi-Finished Materials in Variant Form

## Issue
When creating or editing variants, the "Material ID" dropdown was only showing Finished Goods materials. Semi-finished materials were not visible in the dropdown.

## Root Cause
The `VariantManager.tsx` component was filtering materials to only show those with `material_type` containing "finish" or "fg". Semi-finished materials with `material_type = "semi_finished"` were excluded.

## Solution
Updated the material selector in `VariantManager.tsx` to include three sections:

### Before (2 sections)
```
— No material linked —
─── Finished Goods ───
  FG-001 — Finished Good 1
  FG-002 — Finished Good 2
─── Other Materials ───
  RM-001 — Raw Material 1 (raw_material)
  SF-MECH-ASSY — Semi-Finished Assembly (semi_finished)  ← Hidden in "Other"
```

### After (3 sections)
```
— No material linked —
─── Finished Goods ───
  FG-001 — Finished Good 1
  FG-002 — Finished Good 2
─── Semi-Finished ───  ← NEW SECTION
  SF-MECH-ASSY — Semi-Finished Assembly 🟣 SF
  SF-ELEC-001 — Electronics Sub-Assembly 🟣 SF
─── Other Materials ───
  RM-001 — Raw Material 1 (raw_material)
```

## File Changed
- `frontend/src/modules/products/components/VariantManager.tsx`

## How to Use

### Step 1: Create Semi-Finished Material
```
Master Data → Materials → Create New
Code: SF-MECH-ASSY
Name: Mechanical Assembly - Semi Finished
Type: semi_finished  ← Important!
```

### Step 2: Create Variant and Link Material
```
Products → Variants → Create New
Template: TPL-ROTAMETER
Code: VAR-SF-MECH

Material ID: [Click dropdown]
  ✓ Now shows "Semi-Finished" section
  ✓ Select: SF-MECH-ASSY 🟣 SF
```

### Step 3: Create BOM for Variant
```
Variants → VAR-SF-MECH → BOM Tab → Create BOM
Add 10 raw material lines
```

### Step 4: Use in Finished Good BOM
```
Variants → FG-ROTAMETER → BOM Tab → Create BOM
Add component: SF-MECH-ASSY
Result: Automatic explosion in BOM tree!
```

## Visual Indicator
Semi-finished materials in the dropdown show:
- **🟣 SF** badge
- Listed in dedicated "Semi-Finished" section
- Clear separation from FG and raw materials

## Testing

### Test Case 1: Dropdown Shows Semi-Finished
1. Create a semi-finished material
2. Go to Products → Variants → Create or Edit
3. Click "Material ID" dropdown
4. ✓ Verify "Semi-Finished" section appears
5. ✓ Verify your SF material is listed with 🟣 SF badge

### Test Case 2: Link and Save
1. Select a semi-finished material from dropdown
2. Save variant
3. ✓ Verify material is linked (shows in variant list)
4. ✓ Create BOM for this variant
5. ✓ Use variant's material in another BOM
6. ✓ View BOM tree - should explode

## Benefits
✅ Semi-finished materials now visible in variant form  
✅ Clear visual organization (3 sections)  
✅ Purple badge identifies semi-finished materials  
✅ Enables complete BOM explosion workflow  
✅ Consistent with BOM line form (which already supported SF)  

## Related Changes
- Phase 1: BOM line form allows semi-finished materials ✅
- Phase 2: BOM explosion logic for semi-finished ✅
- Phase 3: Variant form shows semi-finished materials ✅ (This fix)

---

**Status:** ✅ Fixed  
**Date:** September 26, 2026  
**File:** frontend/src/modules/products/components/VariantManager.tsx
