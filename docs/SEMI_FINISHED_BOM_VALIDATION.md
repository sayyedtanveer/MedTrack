# Semi-Finished Material BOM Explosion - Validation Guide

## Overview

This guide provides step-by-step instructions for validating the multi-level BOM explosion feature for semi-finished materials in MedTrack ERP.

## Feature Description

**What was implemented:**
- Semi-finished materials in BOMs now automatically explode to show their underlying raw material components
- Multi-level BOM tree displays the complete hierarchy: Finished Good → Semi-Finished → Raw Materials
- Frontend displays a purple "Semi-Finished" badge to identify expandable materials
- Quantities are correctly rolled up through multiple levels with scrap percentage calculations

## Test Scenario

### Expected Hierarchy

```
FG-ROTAMETER (Finished Good Variant)
  └─ SF-MECH-ASSY (Semi-Finished Material, qty: 1.05 with 5% scrap)
      ├─ RM-001 (Raw Material, qty: 1.05)
      ├─ RM-002 (Raw Material, qty: 2.10)
      ├─ RM-003 (Raw Material, qty: 3.15)
      ├─ RM-004 (Raw Material, qty: 4.20)
      ├─ RM-005 (Raw Material, qty: 5.25)
      ├─ RM-006 (Raw Material, qty: 6.30)
      ├─ RM-007 (Raw Material, qty: 7.35)
      ├─ RM-008 (Raw Material, qty: 8.40)
      ├─ RM-009 (Raw Material, qty: 9.45)
      └─ RM-010 (Raw Material, qty: 10.50)
```

## Automated Validation

### Option 1: Run Validation Script

```bash
# From project root
python scripts/validate_semi_finished_bom_explosion.py
```

**What the script does:**
1. Creates 10 raw materials (RM-001 to RM-010)
2. Creates 1 semi-finished material (SF-MECH-ASSY)
3. Creates 1 finished good template (TPL-ROTAMETER)
4. Creates variants linking materials to BOMs
5. Creates hierarchical BOMs
6. Validates explosion logic programmatically

### Option 2: Run Unit Tests

```bash
# Run all BOM explosion tests
pytest backend/tests/api/bom/test_bom_semi_finished_explosion.py -v

# Run specific test
pytest backend/tests/api/bom/test_bom_semi_finished_explosion.py::TestSemiFinishedBOMExplosion::test_semi_finished_material_explodes_to_raw_materials -v
```

## Manual UI Validation

### Prerequisites

1. Backend server running on http://localhost:8000
2. Frontend running on http://localhost:3000
3. Valid tenant and authentication

### Step 1: Create Raw Materials

**Navigate to:** Master Data → Materials

Create 10 raw materials:

| Code    | Name              | Type         | Current Cost |
|---------|-------------------|--------------|--------------|
| RM-001  | Raw Material 001  | raw_material | $10.00       |
| RM-002  | Raw Material 002  | raw_material | $20.00       |
| RM-003  | Raw Material 003  | raw_material | $30.00       |
| RM-004  | Raw Material 004  | raw_material | $40.00       |
| RM-005  | Raw Material 005  | raw_material | $50.00       |
| RM-006  | Raw Material 006  | raw_material | $60.00       |
| RM-007  | Raw Material 007  | raw_material | $70.00       |
| RM-008  | Raw Material 008  | raw_material | $80.00       |
| RM-009  | Raw Material 009  | raw_material | $90.00       |
| RM-010  | Raw Material 010  | raw_material | $100.00      |

### Step 2: Create Semi-Finished Material

**Navigate to:** Master Data → Materials

Create semi-finished material:

| Field         | Value                                  |
|---------------|----------------------------------------|
| Code          | SF-MECH-ASSY                          |
| Name          | Mechanical Assembly - Semi Finished    |
| Type          | **semi_finished** ⚠️ Important         |
| Current Cost  | $550.00                               |
| Base Unit     | pcs                                    |

### Step 3: Create Product Template

**Navigate to:** Products → Templates → Create New

| Field      | Value           |
|------------|-----------------|
| Code       | TPL-ROTAMETER   |
| Item Code  | FG              |
| Item Type  | FG              |
| Name       | Rotameter       |
| Attributes | color, size     |

### Step 4: Create Semi-Finished Variant

**Navigate to:** Products → Variants → Create New

| Field           | Value                            |
|-----------------|----------------------------------|
| Template        | TPL-ROTAMETER                    |
| Code            | VAR-SF-MECH                      |
| Name            | SF Mechanical Assembly Variant   |
| **Material ID** | **SF-MECH-ASSY** ⚠️ Key Link     |
| Standard Cost   | $550.00                          |

**Critical:** The `material_id` field links the variant to the semi-finished material. This is how the BOM explosion finds the material's BOM.

### Step 5: Create BOM for Semi-Finished Material

**Navigate to:** Products → Variants → VAR-SF-MECH → BOM Tab → Create BOM

| Field    | Value  |
|----------|--------|
| Version  | 1.0.0  |
| Active   | ✓ Yes  |

**Add BOM Lines:** (10 lines)

| Component    | Type     | Quantity | Scrap % |
|--------------|----------|----------|---------|
| RM-001       | Material | 1        | 0%      |
| RM-002       | Material | 2        | 0%      |
| RM-003       | Material | 3        | 0%      |
| RM-004       | Material | 4        | 0%      |
| RM-005       | Material | 5        | 0%      |
| RM-006       | Material | 6        | 0%      |
| RM-007       | Material | 7        | 0%      |
| RM-008       | Material | 8        | 0%      |
| RM-009       | Material | 9        | 0%      |
| RM-010       | Material | 10       | 0%      |

### Step 6: Create Finished Good Variant

**Navigate to:** Products → Variants → Create New

| Field           | Value                     |
|-----------------|---------------------------|
| Template        | TPL-ROTAMETER             |
| Code            | FG-ROTAMETER              |
| Name            | Rotameter - Red/Small     |
| Attribute Value | color: Red, size: Small   |
| Material ID     | (leave empty)             |
| Standard Cost   | $600.00                   |
| Selling Price   | $1000.00                  |

### Step 7: Create BOM for Finished Good

**Navigate to:** Products → Variants → FG-ROTAMETER → BOM Tab → Create BOM

| Field    | Value  |
|----------|--------|
| Version  | 1.0.0  |
| Active   | ✓ Yes  |

**Add BOM Line:** (1 line)

| Component      | Type     | Quantity | Scrap % |
|----------------|----------|----------|---------|
| SF-MECH-ASSY   | Material | 1        | 5%      |

**Important:** Set scrap percentage to 5% to test quantity rollup calculation.

### Step 8: View BOM Tree and Validate

**Navigate to:** Products → Variants → FG-ROTAMETER → BOM Tab

1. **Click "View Tree"** button
2. **Verify the following:**

#### Root Level
- ✓ Shows "FG-ROTAMETER" as root
- ✓ Shows version "1.0.0"

#### Level 1 - Semi-Finished Material
- ✓ Shows "SF-MECH-ASSY" as child
- ✓ Displays **purple "Semi-Finished" badge** 🟣
- ✓ Shows quantity: **1.05** (1.0 * 1.05 scrap factor)
- ✓ Component type badge shows "Material"
- ✓ Node is **expandable** (has arrow icon)

#### Level 2 - Raw Materials (After Expanding SF-MECH-ASSY)
- ✓ Shows 10 raw material children
- ✓ Each shows "Material" type badge (amber color)
- ✓ Quantities are correctly calculated:
  - RM-001: **1.05** (1 × 1.05)
  - RM-002: **2.10** (2 × 1.05)
  - RM-003: **3.15** (3 × 1.05)
  - RM-004: **4.20** (4 × 1.05)
  - RM-005: **5.25** (5 × 1.05)
  - RM-006: **6.30** (6 × 1.05)
  - RM-007: **7.35** (7 × 1.05)
  - RM-008: **8.40** (8 × 1.05)
  - RM-009: **9.45** (9 × 1.05)
  - RM-010: **10.50** (10 × 1.05)
- ✓ Raw materials are **not expandable** (no arrow icon)

### Step 9: Test Depth Controls

1. **Click "Collapse"** - Tree should collapse to show only root
2. **Click "+ Level"** - Should expand one level (show SF only)
3. **Click "+ Level" again** - Should expand to show raw materials
4. **Click "Expand All"** - Should fully expand (same as above since only 2 levels)

## Validation Checklist

- [ ] Semi-finished material can be selected in BOM line form
- [ ] Semi-finished material appears in BOM tree
- [ ] Purple "Semi-Finished" badge is displayed for SF material
- [ ] SF material node is expandable
- [ ] Expanding SF shows all 10 raw materials
- [ ] Quantities are correctly calculated with scrap rollup
- [ ] Raw materials show amber "Material" badge
- [ ] Raw materials are not expandable (leaf nodes)
- [ ] Depth controls work correctly
- [ ] Tree loads without errors
- [ ] Console shows no JavaScript errors

## API Validation

### Get BOM Tree Endpoint

```bash
# Get BOM tree for FG-ROTAMETER
curl -X GET "http://localhost:8000/api/v1/boms/{bom_id}/tree?max_depth=20" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json"
```

**Expected Response Structure:**

```json
{
  "id": "bom-id-uuid",
  "version": "1.0.0",
  "children": [
    {
      "id": "sf-material-id",
      "name": "Mechanical Assembly - Semi Finished",
      "code": "SF-MECH-ASSY",
      "type": "material",
      "material_type": "semi_finished",
      "quantity": 1.05,
      "unit": "pcs",
      "children": [
        {
          "id": "rm-001-id",
          "name": "Raw Material 001",
          "code": "RM-001",
          "type": "material",
          "material_type": "raw_material",
          "quantity": 1.05,
          "unit": "kg",
          "children": []
        },
        ... (9 more raw materials)
      ]
    }
  ]
}
```

## Troubleshooting

### Issue: Semi-Finished Material Not Expanding

**Possible causes:**
1. Material type is not set to "semi_finished"
2. Variant's `material_id` is not set to the SF material
3. No active BOM exists for the SF variant
4. Database relationship is broken

**Solution:**
- Verify material type in Materials table
- Check ItemVariant.material_id links to correct material
- Ensure BOM for SF variant exists and is_active=true

### Issue: Incorrect Quantities

**Possible causes:**
1. Scrap percentage not applied correctly
2. Quantity rollup calculation error

**Solution:**
- Check scrap_percentage in BOM lines
- Verify formula: `qty = base_qty * (1 + scrap%/100) * parent_qty`

### Issue: Purple Badge Not Showing

**Possible causes:**
1. Frontend not receiving `material_type` field
2. Badge CSS not loaded

**Solution:**
- Check browser console for errors
- Verify API response includes `material_type` in tree nodes
- Check if BOMTreeView.tsx is properly updated

### Issue: Raw Materials Showing As Expandable

**Possible causes:**
1. Backend incorrectly identifying raw materials as semi-finished
2. Logic bug in recursion check

**Solution:**
- Verify material_type in database
- Check `_build_recursive()` logic in bom_browser_service.py

## Technical Implementation Summary

### Backend Changes

1. **BOMRepository.get_bom_for_material()** - Joins ItemVariant → BOM via material_id
2. **BOMProvider.get_bom_for_material()** - Protocol method for retrieving material BOMs
3. **ComponentDetailProvider** - Enhanced to include material_type in details
4. **BOMBrowserService._build_recursive()** - Added logic to check `material_type='semi_finished'` and recurse

### Frontend Changes

1. **BOMTreeNode interface** - Added `material_type` field
2. **BOMTreeView component** - Added purple badge for semi-finished materials

### Key Relationships

```
ItemVariantModel.material_id → MaterialModel.id
BOMModel.variant_id → ItemVariantModel.id
BOMLineModel.material_id → MaterialModel.id
```

### Explosion Logic Flow

```
1. FG BOM loaded
2. For each BOM line:
   a. If material_id exists and material_type='semi_finished':
      - Call get_bom_for_material(material_id)
      - If BOM found, recurse with child BOM
   b. If template_id or variant_id exists:
      - Call get_active_bom(template_id, variant_id)
      - If BOM found, recurse with child BOM
   c. Otherwise: leaf node (no recursion)
3. Return tree with all children
```

## Success Criteria

✅ **Feature is working correctly if:**

1. Semi-finished materials can be added to BOMs
2. BOM tree automatically expands SF materials to show components
3. Quantities are correctly calculated through all levels
4. Visual indicators (badges) clearly identify SF materials
5. No performance degradation with multi-level BOMs
6. Existing template/variant BOM logic unaffected
7. All automated tests pass
8. Manual UI validation passes all checks

## Questions or Issues?

If validation fails or you encounter issues:

1. Check console logs (frontend & backend)
2. Review database relationships (variant → material → BOM)
3. Verify test data was created correctly
4. Run automated tests to isolate the issue
5. Check browser network tab for API errors

---

**Last Updated:** 2026-09-26
**Feature:** Multi-Level BOM Explosion for Semi-Finished Materials
**Status:** Implementation Complete, Ready for Validation
