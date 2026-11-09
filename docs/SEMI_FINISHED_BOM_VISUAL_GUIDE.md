# Semi-Finished BOM Setup - Visual Guide

## The Complete Picture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WHAT YOU CREATE IN THE UI                            │
└─────────────────────────────────────────────────────────────────────────────┘

STEP 1: Raw Materials (Master Data → Materials)
┌──────────────────────────────────────────────────────────────────────────┐
│  RM-001  │  RM-002  │  RM-003  │  ...  │  RM-010                         │
│  $10     │  $20     │  $30     │       │  $100                            │
│  Type: raw_material                                                       │
└──────────────────────────────────────────────────────────────────────────┘

STEP 2: Semi-Finished Material (Master Data → Materials)
┌──────────────────────────────────────────────────────────────────────────┐
│  SF-MECH-ASSY                                                             │
│  $550                                                                     │
│  Type: semi_finished  ← CRITICAL! This enables explosion                 │
└──────────────────────────────────────────────────────────────────────────┘

STEP 3: Product Template (Products → Templates)
┌──────────────────────────────────────────────────────────────────────────┐
│  TPL-ROTAMETER                                                            │
│  Item Type: FG                                                            │
│  Attributes: color, size                                                  │
└──────────────────────────────────────────────────────────────────────────┘

STEP 4: Variant for Semi-Finished (Products → Variants)
┌──────────────────────────────────────────────────────────────────────────┐
│  VAR-SF-MECH                                                              │
│  Template: TPL-ROTAMETER                                                  │
│  Material ID: SF-MECH-ASSY  ← THE KEY LINK!                             │
│                                                                           │
│  This creates the bridge:                                                 │
│  Variant (VAR-SF-MECH) ──→ Material (SF-MECH-ASSY)                      │
└──────────────────────────────────────────────────────────────────────────┘

STEP 5: BOM for Semi-Finished (VAR-SF-MECH → BOM Tab)
┌──────────────────────────────────────────────────────────────────────────┐
│  BOM v1.0.0 for VAR-SF-MECH                                              │
│  ├─ RM-001  qty: 1                                                       │
│  ├─ RM-002  qty: 2                                                       │
│  ├─ RM-003  qty: 3                                                       │
│  ├─ RM-004  qty: 4                                                       │
│  ├─ RM-005  qty: 5                                                       │
│  ├─ RM-006  qty: 6                                                       │
│  ├─ RM-007  qty: 7                                                       │
│  ├─ RM-008  qty: 8                                                       │
│  ├─ RM-009  qty: 9                                                       │
│  └─ RM-010  qty: 10                                                      │
└──────────────────────────────────────────────────────────────────────────┘

STEP 6: Finished Good Variant (Products → Variants)
┌──────────────────────────────────────────────────────────────────────────┐
│  FG-ROTAMETER                                                             │
│  Template: TPL-ROTAMETER                                                  │
│  Attributes: color=Red, size=Small                                        │
│  Material ID: (empty) ← FG variants don't link to materials              │
└──────────────────────────────────────────────────────────────────────────┘

STEP 7: BOM for Finished Good (FG-ROTAMETER → BOM Tab)
┌──────────────────────────────────────────────────────────────────────────┐
│  BOM v1.0.0 for FG-ROTAMETER                                             │
│  └─ SF-MECH-ASSY  qty: 1  scrap: 5%                                     │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         WHAT THE SYSTEM DOES                                 │
└─────────────────────────────────────────────────────────────────────────────┘

When you click "View Tree" on FG-ROTAMETER:

1. Load FG BOM
   └─ Has 1 line: material_id = SF-MECH-ASSY

2. Check material type
   └─ Query: SELECT material_type FROM materials WHERE id = SF-MECH-ASSY
   └─ Result: "semi_finished"  ✓

3. Find linked variant
   └─ Query: SELECT * FROM item_variants WHERE material_id = SF-MECH-ASSY
   └─ Result: VAR-SF-MECH  ✓

4. Get variant's BOM
   └─ Query: SELECT * FROM boms WHERE variant_id = VAR-SF-MECH AND is_active = true
   └─ Result: BOM with 10 raw material lines  ✓

5. Build tree recursively
   └─ FG-ROTAMETER
       └─ SF-MECH-ASSY (qty: 1.05)  ← 1.0 × (1 + 5%/100)
           ├─ RM-001 (qty: 1.05)    ← 1 × 1.05
           ├─ RM-002 (qty: 2.10)    ← 2 × 1.05
           ├─ RM-003 (qty: 3.15)    ← 3 × 1.05
           ├─ RM-004 (qty: 4.20)    ← 4 × 1.05
           ├─ RM-005 (qty: 5.25)    ← 5 × 1.05
           ├─ RM-006 (qty: 6.30)    ← 6 × 1.05
           ├─ RM-007 (qty: 7.35)    ← 7 × 1.05
           ├─ RM-008 (qty: 8.40)    ← 8 × 1.05
           ├─ RM-009 (qty: 9.45)    ← 9 × 1.05
           └─ RM-010 (qty: 10.50)   ← 10 × 1.05
```

---

## The Key Relationship

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     THE MAGIC TRIANGLE                                       │
└─────────────────────────────────────────────────────────────────────────────┘

                        ItemVariant (VAR-SF-MECH)
                                    │
                                    │ variant_id
                                    │
                                    ▼
         material_id ──────────► Material (SF-MECH-ASSY)
                                type: semi_finished
                                    │
                                    │ Used in
                                    │ BOM Line
                                    ▼
                        BOM (FG-ROTAMETER BOM)
                        Contains: SF-MECH-ASSY

When system sees SF-MECH-ASSY in a BOM:
  1. Check type → "semi_finished"  ✓
  2. Find variant with material_id = SF-MECH-ASSY  ✓
  3. Get that variant's BOM  ✓
  4. Show its components (10 raw materials)  ✓
```

---

## Database Schema (Simplified)

```sql
-- Materials Table
materials
├─ id (PK)
├─ code: "SF-MECH-ASSY"
├─ material_type: "semi_finished"  ← Triggers explosion
└─ ...

-- Item Variants Table
item_variants
├─ id (PK)
├─ code: "VAR-SF-MECH"
├─ template_id (FK → item_templates)
├─ material_id (FK → materials)  ← THE KEY LINK!
│   └─ Value: {id of SF-MECH-ASSY}
└─ ...

-- BOMs Table
boms
├─ id (PK)
├─ variant_id (FK → item_variants)  ← Links to VAR-SF-MECH
│   └─ This BOM defines what SF-MECH-ASSY contains
├─ is_active: true
└─ ...

-- BOM Lines Table (for SF BOM)
bom_lines
├─ bom_id (FK → boms)  ← SF BOM id
├─ material_id: RM-001, RM-002, ..., RM-010
├─ quantity: 1, 2, 3, ..., 10
└─ ...

-- BOM Lines Table (for FG BOM)
bom_lines
├─ bom_id (FK → boms)  ← FG BOM id
├─ material_id: SF-MECH-ASSY  ← Uses semi-finished
├─ quantity: 1.0
├─ scrap_percentage: 5.0
└─ ...
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     USER VIEWS FG BOM TREE                                   │
└─────────────────────────────────────────────────────────────────────────────┘

User clicks "View Tree" on FG-ROTAMETER
              ↓
┌───────────────────────────────────────┐
│  BOMBrowserService.build_tree()       │
│  - Load FG BOM                        │
│  - Start recursive build              │
└───────────────────────────────────────┘
              ↓
┌───────────────────────────────────────┐
│  _build_recursive(FG BOM, depth=1)    │
│  - For each line in FG BOM:           │
│    └─ Line 1: material_id = SF-MECH   │
└───────────────────────────────────────┘
              ↓
┌───────────────────────────────────────┐
│  ComponentDetailProvider              │
│  - Get material details               │
│  - Returns: material_type = "semi_f"  │
└───────────────────────────────────────┘
              ↓
       Is semi_finished? YES!
              ↓
┌───────────────────────────────────────┐
│  BOMProvider.get_bom_for_material()   │
│  - Find variant with material_id      │
│  - Get variant's BOM                  │
└───────────────────────────────────────┘
              ↓
┌───────────────────────────────────────┐
│  BOMRepository.get_bom_for_material() │
│  - JOIN item_variants ON material_id  │
│  - JOIN boms ON variant_id            │
│  - Returns SF BOM with 10 lines       │
└───────────────────────────────────────┘
              ↓
       Found SF BOM? YES!
              ↓
┌───────────────────────────────────────┐
│  _build_recursive(SF BOM, depth=2)    │
│  - For each line in SF BOM:           │
│    ├─ Line 1: RM-001 (leaf)          │
│    ├─ Line 2: RM-002 (leaf)          │
│    └─ ... (8 more)                    │
└───────────────────────────────────────┘
              ↓
┌───────────────────────────────────────┐
│  Return complete tree                 │
│  - FG → SF → 10 RMs                   │
│  - With calculated quantities         │
└───────────────────────────────────────┘
              ↓
┌───────────────────────────────────────┐
│  Frontend renders tree                │
│  - Purple badge on SF-MECH-ASSY       │
│  - Expandable/collapsible nodes       │
│  - Quantity display with units        │
└───────────────────────────────────────┘
```

---

## Quantity Calculation Flow

```
FG BOM Line: SF-MECH-ASSY
├─ Base Quantity: 1.0
├─ Scrap %: 5.0
└─ Effective Qty: 1.0 × (1 + 5/100) = 1.05

SF BOM Line 1: RM-001
├─ Base Quantity: 1
├─ Parent Multiplier: 1.05
└─ Final Qty: 1 × 1.05 = 1.05

SF BOM Line 2: RM-002
├─ Base Quantity: 2
├─ Parent Multiplier: 1.05
└─ Final Qty: 2 × 1.05 = 2.10

SF BOM Line 3: RM-003
├─ Base Quantity: 3
├─ Parent Multiplier: 1.05
└─ Final Qty: 3 × 1.05 = 3.15

...and so on for all 10 raw materials
```

---

## UI Indicators

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  BOM TREE VIEW                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

📦 FG-ROTAMETER (v1.0.0)
  │
  ├─ 🔧 SF-MECH-ASSY  [qty: 1.05 pcs]  🟣 Semi-Finished  [Material]  [1 ▼]
  │   │
  │   ├─ 📦 RM-001  [qty: 1.05 kg]  [Material]
  │   ├─ 📦 RM-002  [qty: 2.10 kg]  [Material]
  │   ├─ 📦 RM-003  [qty: 3.15 kg]  [Material]
  │   ├─ 📦 RM-004  [qty: 4.20 kg]  [Material]
  │   ├─ 📦 RM-005  [qty: 5.25 kg]  [Material]
  │   ├─ 📦 RM-006  [qty: 6.30 kg]  [Material]
  │   ├─ 📦 RM-007  [qty: 7.35 kg]  [Material]
  │   ├─ 📦 RM-008  [qty: 8.40 kg]  [Material]
  │   ├─ 📦 RM-009  [qty: 9.45 kg]  [Material]
  │   └─ 📦 RM-010  [qty: 10.50 kg]  [Material]

Legend:
  🟣 Purple Badge = Semi-Finished (expandable)
  🟡 Amber Badge = Material (standard)
  ▼ Arrow = Click to expand/collapse
  [1] = Number of children
```

---

## Common Mistakes to Avoid

```
❌ WRONG: Creating semi-finished without linking to variant
┌──────────────────────────────────────┐
│ Material: SF-MECH-ASSY               │
│ Type: semi_finished                  │
└──────────────────────────────────────┘
         ❌ No variant with material_id
         ❌ System can't find BOM
         ❌ Won't explode

✅ CORRECT: Linking variant to material
┌──────────────────────────────────────┐
│ Material: SF-MECH-ASSY               │
│ Type: semi_finished                  │
└──────────────────────────────────────┘
         ↓ material_id link
┌──────────────────────────────────────┐
│ Variant: VAR-SF-MECH                 │
│ material_id: {SF-MECH-ASSY id}       │
└──────────────────────────────────────┘
         ↓ variant_id link
┌──────────────────────────────────────┐
│ BOM for VAR-SF-MECH                  │
│ Contains: 10 raw materials           │
└──────────────────────────────────────┘
         ✅ System finds complete chain
         ✅ BOM explodes correctly
```

```
❌ WRONG: Setting wrong material type
┌──────────────────────────────────────┐
│ Material: SF-MECH-ASSY               │
│ Type: raw_material  ← WRONG!         │
└──────────────────────────────────────┘
         ❌ System won't try to explode
         ❌ Shows as leaf node

✅ CORRECT: Setting correct material type
┌──────────────────────────────────────┐
│ Material: SF-MECH-ASSY               │
│ Type: semi_finished  ← CORRECT!      │
└──────────────────────────────────────┘
         ✅ System checks for BOM
         ✅ Explodes if BOM exists
```

---

## Troubleshooting Checklist

**Problem:** Semi-finished not expanding in tree

**Check these 4 things in order:**

```
1. Material Type
   ┌────────────────────────────────────┐
   │ Go to: Materials → SF-MECH-ASSY    │
   │ Check: Type = "semi_finished"      │
   │ If not: Edit and change to SF      │
   └────────────────────────────────────┘

2. Variant Link
   ┌────────────────────────────────────┐
   │ Go to: Variants → VAR-SF-MECH      │
   │ Check: Material ID = SF-MECH-ASSY  │
   │ If empty: Edit and select material │
   └────────────────────────────────────┘

3. BOM Exists
   ┌────────────────────────────────────┐
   │ Go to: Variants → VAR-SF-MECH      │
   │ Check: BOM tab has BOM v1.0.0      │
   │ If not: Create BOM with RM lines   │
   └────────────────────────────────────┘

4. BOM Active
   ┌────────────────────────────────────┐
   │ Go to: Variants → VAR-SF-MECH      │
   │ BOM tab → Check "Active" ✓         │
   │ If not: Edit BOM, check Active     │
   └────────────────────────────────────┘
```

---

## Quick Reference Commands

**Check setup via SQL:**

```sql
-- 1. Verify material type
SELECT code, material_type FROM materials WHERE code = 'SF-MECH-ASSY';
-- Expected: material_type = 'semi_finished'

-- 2. Verify variant link
SELECT v.code, v.material_id, m.code as material_code
FROM item_variants v
JOIN materials m ON v.material_id = m.id
WHERE v.code = 'VAR-SF-MECH';
-- Expected: material_code = 'SF-MECH-ASSY'

-- 3. Verify BOM exists
SELECT b.version, b.is_active, COUNT(bl.id) as line_count
FROM boms b
JOIN bom_lines bl ON b.id = bl.bom_id
JOIN item_variants v ON b.variant_id = v.id
WHERE v.code = 'VAR-SF-MECH'
GROUP BY b.id;
-- Expected: is_active = true, line_count = 10

-- 4. Verify FG BOM uses SF material
SELECT bl.*, m.code as material_code
FROM bom_lines bl
JOIN materials m ON bl.material_id = m.id
JOIN boms b ON bl.bom_id = b.id
JOIN item_variants v ON b.variant_id = v.id
WHERE v.code = 'FG-ROTAMETER';
-- Expected: material_code = 'SF-MECH-ASSY'
```

---

## Summary: The 7 Steps

```
1. Create Raw Materials (10)     →  RM-001 to RM-010
2. Create Semi-Finished (1)      →  SF-MECH-ASSY (type: semi_finished)
3. Create Template (1)           →  TPL-ROTAMETER
4. Create SF Variant (1)         →  VAR-SF-MECH (material_id → SF-MECH-ASSY)
5. Create SF BOM (1)             →  For VAR-SF-MECH, with 10 RM lines
6. Create FG Variant (1)         →  FG-ROTAMETER
7. Create FG BOM (1)             →  For FG-ROTAMETER, with 1 SF line

Result: Click "View Tree" → See complete hierarchy! 🎉
```

---

**Document Version:** 1.0  
**Created:** September 26, 2026  
**Feature:** Multi-Level BOM with Semi-Finished Materials
