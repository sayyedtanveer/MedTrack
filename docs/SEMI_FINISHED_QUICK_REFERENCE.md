# Semi-Finished BOM - Quick Reference

**Status:** ✅ IMPLEMENTED  
**Migration Required:** ❌ NO  
**Breaking Changes:** ❌ NONE

---

## What Changed

### Backend (1 file)
- `backend/app/domain/bom/services/bom_browser_service.py`
  - Added circular reference protection to prevent BOM loops
  - Semi-finished materials now explode to show their components

### Frontend (1 file)
- `frontend/src/modules/products/components/VariantManager.tsx`
  - Material selector moved to collapsible "Advanced" section (default collapsed)
  - Preserves simple default UX, enables advanced mapping when needed

---

## How It Works

```
Product Variant → (optional) material_id → Material → (if SF) → BOM → Components
```

**Example:**
1. Create variant "TPL-MECH-ASSY-001" 
2. Link to semi-finished material "SF-MECH-ASSY"
3. SF-MECH-ASSY has its own BOM with 10 raw materials
4. When viewing FG BOM that uses this variant, tree automatically shows nested components

---

## User Guide

### Creating Variant with Material Link (Advanced)

1. Go to **Products** → Select template → **Add Variant**
2. Fill attributes + costs (as before)
3. **Click "Advanced: Material Mapping"** to expand section
4. Select existing FG or SF material (or leave default for auto-create)
5. Click **Create**

**Default behavior (Advanced collapsed):** Auto-creates FG material - unchanged!

### Viewing Multi-Level BOM

1. Go to **BOM** → View any BOM with semi-finished components
2. Semi-finished materials show **purple "Semi-Finished" badge**
3. Click to expand - components automatically display
4. Quantities roll up through levels: `parent_qty × (1 + scrap%) × child_qty`

---

## Visual Indicators

| Badge | Color | Meaning |
|-------|-------|---------|
| Material | Amber | Raw material component |
| Template | Blue | Product template reference |
| Variant | Violet | Product variant reference |
| **Semi-Finished** | **Purple** | **SF material with nested BOM** |

---

## Test Checklist

- [ ] Create variant WITHOUT expanding Advanced → FG auto-created ✓
- [ ] Create variant WITH Advanced section → Links to selected material ✓
- [ ] View BOM with SF component → Purple badge shows ✓
- [ ] Expand SF component → Nested materials display ✓
- [ ] Multi-level explosion → Quantities calculate correctly ✓
- [ ] Circular BOM → No infinite loop ✓

---

## Troubleshooting

**Q: I don't see the purple badge?**  
A: The material must have `material_type = "semi_finished"` and a linked BOM

**Q: Variant creation not working?**  
A: You don't need to expand Advanced section! Default flow unchanged.

**Q: BOM not exploding to components?**  
A: Check:
1. Material type is "semi_finished"
2. Variant has `material_id` set
3. Linked material has an active BOM

**Q: Circular BOM error?**  
A: System now prevents infinite loops - tree stops at repeated BOMs

---

## Files Reference

### Backend
- `backend/app/domain/bom/services/bom_browser_service.py` - BOM explosion logic
- `backend/app/infrastructure/persistence/repositories/bom_repository.py` - `get_bom_for_material()`
- `backend/app/infrastructure/services/bom_providers.py` - BOMProvider protocol

### Frontend
- `frontend/src/modules/products/components/VariantManager.tsx` - Variant form with Advanced section
- `frontend/src/modules/bom/components/BOMTreeView.tsx` - BOM tree with purple badges
- `frontend/src/types/bom.types.ts` - BOMTreeNode with material_type

### Documentation
- `docs/SEMI_FINISHED_BOM_IMPLEMENTATION_REPORT.md` - Full implementation report
- `docs/AUDIT_SEMI_FINISHED_VARIANT_MAPPING.md` - Pre-implementation audit
- `docs/QUICK_START_SEMI_FINISHED_BOM.md` - Original user guide

---

## Support

For issues or questions, reference:
- Implementation report for technical details
- Audit document for design decisions
- Quick start guide for step-by-step instructions

**Implementation Date:** 2026-09-26  
**Version:** 1.0.0
