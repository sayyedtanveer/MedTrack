# Quick Start: Creating BOMs with Semi-Finished Materials

## Overview
This guide shows you how to create a multi-level BOM using semi-finished materials so all raw materials are automatically mapped through the hierarchy.

**Result:** FG-ROTAMETER → SF-MECH-ASSY → 10 Raw Materials (automatic explosion)

---

## Step-by-Step Setup (15 minutes)

### STEP 1: Create Raw Materials (2 min)

**Navigate:** Master Data → Materials → Create New

Create these 10 raw materials:

| Code    | Name              | Type           | Unit | Cost   |
|---------|-------------------|----------------|------|--------|
| RM-001  | Raw Material 001  | raw_material   | kg   | $10    |
| RM-002  | Raw Material 002  | raw_material   | kg   | $20    |
| RM-003  | Raw Material 003  | raw_material   | kg   | $30    |
| RM-004  | Raw Material 004  | raw_material   | kg   | $40    |
| RM-005  | Raw Material 005  | raw_material   | kg   | $50    |
| RM-006  | Raw Material 006  | raw_material   | kg   | $60    |
| RM-007  | Raw Material 007  | raw_material   | kg   | $70    |
| RM-008  | Raw Material 008  | raw_material   | kg   | $80    |
| RM-009  | Raw Material 009  | raw_material   | kg   | $90    |
| RM-010  | Raw Material 010  | raw_material   | kg   | $100   |

**Quick Form Fill:**
```
Code: RM-001
Name: Raw Material 001
Type: raw_material ← Select from dropdown
Base Unit: kg
Current Cost: 10.00
Reorder Level: 100
Reorder Quantity: 500
Status: Active ✓
```

**Repeat for all 10 materials** (change code, name, cost)

---

### STEP 2: Create Semi-Finished Material (1 min)

**Navigate:** Master Data → Materials → Create New

```
Code: SF-MECH-ASSY
Name: Mechanical Assembly - Semi Finished
Type: semi_finished ← IMPORTANT! This enables BOM explosion
Base Unit: pcs
Current Cost: 550.00
Reorder Level: 50
Reorder Quantity: 200
Status: Active ✓
```

**✓ Save Material**

---

### STEP 3: Create Product Template (1 min)

**Navigate:** Products → Templates → Create New

```
Code: TPL-ROTAMETER
Item Code: FG
Item Type: FG
Name: Rotameter Product Template
Description: Template for rotameter products

Attributes: (Optional)
  - color: [Red, Blue, Green]
  - size: [Small, Medium, Large]
```

**✓ Save Template**

---

### STEP 4: Create Variant for Semi-Finished Material (2 min)

**Navigate:** Products → Variants → Create New

This is the **KEY STEP** that links the semi-finished material to its BOM!

```
Template: TPL-ROTAMETER ← Select from dropdown
Code: VAR-SF-MECH
Name: SF Mechanical Assembly Variant
Variant Key: sf-mech

🔑 CRITICAL FIELD:
Material ID: SF-MECH-ASSY ← Select the semi-finished material you created

Base Unit: pcs
Standard Cost: 550.00
Selling Price: 750.00
Status: Active ✓
```

**Why this matters:** The `Material ID` field creates the link:
- Variant (VAR-SF-MECH) → Material (SF-MECH-ASSY)
- When system sees SF-MECH-ASSY in a BOM, it looks for variants with this material_id
- It finds VAR-SF-MECH and gets its BOM → automatic explosion!

**✓ Save Variant**

---

### STEP 5: Create BOM for Semi-Finished Material (3 min)

**Navigate:** Products → Variants → Find "VAR-SF-MECH" → BOM Tab → Create BOM

```
Version: 1.0.0
Status: Active ✓
Valid From: (leave empty)
Valid To: (leave empty)
```

**Add BOM Lines:** Click "Add Line" 10 times

| Line | Component Type | Component    | Quantity | Scrap % | Unit |
|------|----------------|--------------|----------|---------|------|
| 1    | Material       | RM-001       | 1        | 0       | kg   |
| 2    | Material       | RM-002       | 2        | 0       | kg   |
| 3    | Material       | RM-003       | 3        | 0       | kg   |
| 4    | Material       | RM-004       | 4        | 0       | kg   |
| 5    | Material       | RM-005       | 5        | 0       | kg   |
| 6    | Material       | RM-006       | 6        | 0       | kg   |
| 7    | Material       | RM-007       | 7        | 0       | kg   |
| 8    | Material       | RM-008       | 8        | 0       | kg   |
| 9    | Material       | RM-009       | 9        | 0       | kg   |
| 10   | Material       | RM-010       | 10       | 0       | kg   |

**Quick Entry Pattern:**
```
1. Click "Add Line"
2. Component Type: Material
3. Component: Start typing "RM-001" → Select from dropdown
4. Quantity: 1
5. Scrap %: 0
6. Unit: kg (auto-filled from material)
7. Click "Add Line" for next row
```

**✓ Save BOM**

**Result:** Semi-finished material (SF-MECH-ASSY) now has a complete BOM showing what raw materials it needs!

---

### STEP 6: Create Finished Good Variant (1 min)

**Navigate:** Products → Variants → Create New

```
Template: TPL-ROTAMETER
Code: FG-ROTAMETER
Name: Rotameter - Red/Small
Variant Key: red-small

Attribute Values:
  - color: Red
  - size: Small

Material ID: (leave empty) ← FG variants typically don't link to materials

Base Unit: pcs
Standard Cost: 600.00
Selling Price: 1000.00
Status: Active ✓
```

**✓ Save Variant**

---

### STEP 7: Create BOM for Finished Good (2 min)

**Navigate:** Products → Variants → Find "FG-ROTAMETER" → BOM Tab → Create BOM

```
Version: 1.0.0
Status: Active ✓
```

**Add BOM Line:** (just 1 line!)

| Component Type | Component      | Quantity | Scrap % | Unit |
|----------------|----------------|----------|---------|------|
| Material       | SF-MECH-ASSY   | 1        | 5       | pcs  |

**Form Details:**
```
1. Click "Add Line"
2. Component Type: Material
3. Component: Start typing "SF-MECH-ASSY" → Select
   ✓ You should now see it in the dropdown (Phase 1 implementation)
4. Quantity: 1
5. Scrap %: 5 ← This tests the quantity rollup!
6. Unit: pcs (auto-filled)
```

**✓ Save BOM**

---

### STEP 8: View Multi-Level BOM Explosion! (1 min)

**Navigate:** Products → Variants → Find "FG-ROTAMETER" → BOM Tab

**Click "View Tree" button** 🎉

**You should see:**

```
📦 FG-ROTAMETER (v1.0.0)
  └─ 🔧 SF-MECH-ASSY [qty: 1.05] 🟣 Semi-Finished
      ├─ 📦 RM-001 [qty: 1.05 kg]
      ├─ 📦 RM-002 [qty: 2.10 kg]
      ├─ 📦 RM-003 [qty: 3.15 kg]
      ├─ 📦 RM-004 [qty: 4.20 kg]
      ├─ 📦 RM-005 [qty: 5.25 kg]
      ├─ 📦 RM-006 [qty: 6.30 kg]
      ├─ 📦 RM-007 [qty: 7.35 kg]
      ├─ 📦 RM-008 [qty: 8.40 kg]
      ├─ 📦 RM-009 [qty: 9.45 kg]
      └─ 📦 RM-010 [qty: 10.50 kg]
```

**What to verify:**

✅ **Purple Badge:** SF-MECH-ASSY shows purple "Semi-Finished" badge  
✅ **Expandable:** SF-MECH-ASSY node has arrow icon (expandable)  
✅ **10 Children:** Clicking arrow shows all 10 raw materials  
✅ **Quantities:** Each RM quantity = base qty × 1.05 (5% scrap rollup)  
✅ **Amber Badges:** Raw materials show amber "Material" badges  
✅ **Leaf Nodes:** Raw materials are NOT expandable (no arrows)  

---

## Understanding the Magic 🪄

### How It Works

```
┌──────────────────────────────────────────────────────────────┐
│ USER CREATES                                                  │
├──────────────────────────────────────────────────────────────┤
│ 1. Material: SF-MECH-ASSY (type: semi_finished)             │
│ 2. Variant: VAR-SF-MECH (material_id → SF-MECH-ASSY)        │
│ 3. BOM for VAR-SF-MECH (lists 10 raw materials)             │
│ 4. FG Variant: FG-ROTAMETER                                  │
│ 5. BOM for FG-ROTAMETER (uses SF-MECH-ASSY as component)    │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ SYSTEM EXPLOSION LOGIC                                        │
├──────────────────────────────────────────────────────────────┤
│ 1. Load FG-ROTAMETER BOM                                     │
│ 2. See component: SF-MECH-ASSY (material)                   │
│ 3. Check material_type → "semi_finished" ✓                   │
│ 4. Look for variant with material_id = SF-MECH-ASSY         │
│ 5. Found: VAR-SF-MECH                                        │
│ 6. Get BOM for VAR-SF-MECH                                   │
│ 7. Recurse: Show all 10 raw materials                        │
│ 8. Calculate quantities with scrap rollup                    │
└──────────────────────────────────────────────────────────────┘
```

### The Key Relationship

```sql
-- When user views FG BOM
SELECT * FROM bom_lines WHERE bom_id = 'FG-ROTAMETER-BOM'
→ Returns: material_id = 'SF-MECH-ASSY'

-- System checks material type
SELECT material_type FROM materials WHERE id = 'SF-MECH-ASSY'
→ Returns: 'semi_finished'

-- System finds linked variant
SELECT * FROM item_variants WHERE material_id = 'SF-MECH-ASSY'
→ Returns: variant_id = 'VAR-SF-MECH'

-- System gets variant's BOM
SELECT * FROM boms WHERE variant_id = 'VAR-SF-MECH' AND is_active = true
→ Returns: BOM with 10 raw material lines

-- System recursively builds tree
```

---

## Common Use Cases

### Use Case 1: Multiple Semi-Finished in One FG

**Scenario:** Rotameter needs both mechanical assembly AND electronic assembly

**Setup:**
1. Create: SF-MECH-ASSY (5 raw materials)
2. Create: SF-ELEC-ASSY (5 different raw materials)
3. Create variants for both (link material_id)
4. Create BOMs for both variants
5. FG BOM uses BOTH semi-finished materials

**Result:**
```
FG-ROTAMETER
  ├─ SF-MECH-ASSY → 5 raw materials
  └─ SF-ELEC-ASSY → 5 raw materials
Total: 10 raw materials automatically shown!
```

### Use Case 2: Three-Level Hierarchy

**Scenario:** Sub-assembly → Semi-finished → Raw materials

**Setup:**
1. 10 raw materials
2. SF-SUB-ASSY (uses 5 raw materials)
3. SF-MAIN-ASSY (uses SF-SUB-ASSY + 3 more raw materials)
4. FG-PRODUCT (uses SF-MAIN-ASSY + 2 finishing materials)

**Result:**
```
FG-PRODUCT
  └─ SF-MAIN-ASSY
      ├─ SF-SUB-ASSY
      │   ├─ RM-001
      │   ├─ RM-002
      │   ├─ RM-003
      │   ├─ RM-004
      │   └─ RM-005
      ├─ RM-006
      ├─ RM-007
      └─ RM-008
```

### Use Case 3: Mixing Materials and Variants

**Scenario:** BOM contains both direct materials AND semi-finished

**Setup:**
FG BOM with:
- 1× SF-MECH-ASSY (explodes to 10 raw materials)
- 2× RM-PAINT (direct raw material, doesn't explode)
- 1× RM-PACKAGING (direct raw material, doesn't explode)

**Result:**
```
FG-PRODUCT
  ├─ SF-MECH-ASSY [expandable]
  │   └─ ... 10 raw materials
  ├─ RM-PAINT [leaf]
  └─ RM-PACKAGING [leaf]
```

---

## Troubleshooting

### Problem: Semi-Finished Not Showing Purple Badge

**Cause:** Material type not set correctly

**Fix:**
1. Go to Materials → Find SF-MECH-ASSY
2. Edit material
3. Verify Type = "semi_finished" (not "raw_material")
4. Save
5. Refresh BOM tree

---

### Problem: Semi-Finished Not Expandable

**Cause 1:** No variant linked to material

**Fix:**
1. Go to Variants → Find variant
2. Check "Material ID" field
3. Should be set to SF-MECH-ASSY
4. If empty, select it and save

**Cause 2:** No BOM exists for the variant

**Fix:**
1. Go to Variants → Find variant with material_id
2. Check BOM tab
3. Create BOM if missing
4. Set BOM to Active

**Cause 3:** BOM is not active

**Fix:**
1. Go to variant's BOM
2. Edit BOM
3. Check "Active" checkbox
4. Save

---

### Problem: Wrong Quantities

**Cause:** Scrap percentage calculation

**Fix:**
- Verify formula: `child_qty = base_qty × (1 + scrap%/100) × parent_qty`
- Example: RM-003 base qty = 3, SF scrap = 5%
  - Expected: 3 × 1.05 = 3.15
- Check BOM line scrap percentages

---

### Problem: "Cannot add semi-finished to BOM"

**Cause:** Old code still running (Phase 1 not deployed)

**Fix:**
1. Clear browser cache
2. Hard refresh (Ctrl+F5)
3. Verify backend running latest code
4. Check bom_handlers.py has semi_finished in allowed types

---

## API Testing

### Create Material via API

```bash
curl -X POST "http://localhost:8000/api/v1/materials" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "SF-MECH-ASSY",
    "name": "Mechanical Assembly - Semi Finished",
    "material_type": "semi_finished",
    "base_unit_id": "unit-uuid",
    "current_cost": 550.00,
    "reorder_level": 50,
    "reorder_quantity": 200
  }'
```

### Create Variant with Material Link

```bash
curl -X POST "http://localhost:8000/api/v1/products/templates/{template_id}/variants" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "VAR-SF-MECH",
    "name": "SF Mechanical Assembly Variant",
    "variant_key": "sf-mech",
    "material_id": "material-uuid-for-SF-MECH-ASSY",
    "standard_cost": 550.00,
    "selling_price": 750.00
  }'
```

### Get BOM Tree (See Explosion)

```bash
curl -X GET "http://localhost:8000/api/v1/boms/{bom_id}/tree?max_depth=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Quick Reference

### Critical Fields Checklist

When creating semi-finished BOM setup:

- [ ] Material: `material_type = "semi_finished"`
- [ ] Variant: `material_id = {semi_finished_material_id}`
- [ ] Variant BOM: `is_active = true`
- [ ] Variant BOM: Has lines with raw materials
- [ ] FG BOM: Uses semi-finished material as component
- [ ] FG BOM: `is_active = true`

### Field Mapping

| UI Field             | Database Field                | Table          |
|----------------------|-------------------------------|----------------|
| Material Type        | material_type                 | materials      |
| Material ID (Variant)| material_id                   | item_variants  |
| Component (BOM Line) | material_id/template_id/variant_id | bom_lines |
| Active (BOM)         | is_active                     | boms           |

---

## Next Steps

1. ✅ **Try the setup above** - Create your first multi-level BOM
2. 📊 **Test with real data** - Use your actual products
3. 🔄 **Create variations** - Try 3-level hierarchies
4. 💰 **Add costs** - Verify cost rollup works
5. 🏭 **Create work orders** - Test manufacturing flow

---

## Video Tutorial (Coming Soon)

Screen recording showing:
1. Creating materials (30 sec)
2. Creating variants (30 sec)
3. Creating BOMs (2 min)
4. Viewing explosion (30 sec)

**Total time:** 3.5 minutes to complete BOM setup!

---

## Summary

**What You Learned:**
- ✅ How to create semi-finished materials
- ✅ How to link variants to materials (KEY!)
- ✅ How to create multi-level BOMs
- ✅ How BOM explosion works automatically
- ✅ How quantities roll up with scrap

**Key Insight:**  
The `material_id` field in the variant is what makes everything work! It creates the bridge between:
- BOM line (uses material)
- Material (type: semi_finished)
- Variant (has material_id)
- Variant's BOM (defines what the material contains)

**Result:**  
Click "View Tree" → See complete multi-level hierarchy automatically! 🎉

---

**Questions?** Refer to `SEMI_FINISHED_BOM_VALIDATION.md` for detailed troubleshooting.

**Document Version:** 1.0  
**Created:** September 26, 2026  
**Feature:** Multi-Level BOM with Semi-Finished Materials
