# AUDIT: Semi-Finished Material → Variant Mapping

**Date:** September 26, 2026  
**Scope:** Verify existing Product/Variant/Material relationships before implementing Semi-Finished support  
**Status:** COMPLETE - Pre-Implementation Audit

---

## EXECUTIVE SUMMARY

### Findings

✅ **Database:** `item_variants.material_id` → `materials.id` relationship EXISTS and is NULLABLE  
✅ **Backend:** Optional material_id support EXISTS in CreateItemVariantCommand  
✅ **Auto-Provisioning:** Phase 5 logic EXISTS to auto-create FG material when material_id is None  
⚠️ **Frontend:** Create form does NOT expose material_id selector  
✅ **Frontend:** Edit form DOES expose material_id selector  
✅ **BOM Ownership:** BOMs link to template_id OR variant_id (both nullable)  
✅ **BOM Explosion:** Logic EXISTS but only recurses for template/variant, NOT materials  

### Conclusion

The database schema and backend logic **ALREADY SUPPORT** the Semi-Finished use case. Only minor frontend and BOM explosion changes needed.

**NO DATABASE MIGRATION REQUIRED.**

---

## 1. DATABASE AUDIT

### 1.1 item_variants Table

**Source:** `backend/app/infrastructure/persistence/models/item_variant_model.py`

```python
class ItemVariantModel(Base):
    __tablename__ = "item_variants"
    
    # Primary Key
    id: Mapped[uuid.UUID]
    
    # Tenant Isolation
    tenant_id: Mapped[uuid.UUID]  # NOT NULL
    
    # Product Template Relationship
    template_id: Mapped[uuid.UUID]  # FK → item_templates.id, CASCADE, NOT NULL
    
    # Auto-Generated Fields
    code: Mapped[str]  # NOT NULL, Unique per tenant
    code_locked: Mapped[bool]  # NOT NULL, default=True
    name: Mapped[str]  # NOT NULL
    variant_key: Mapped[str]  # NOT NULL, Unique per (tenant, template, variant_key)
    
    # Variant Attributes
    attribute_values: Mapped[Any]  # JSONB, NOT NULL, default={}
    
    # Unit and Pricing
    base_unit_id: Mapped[Optional[uuid.UUID]]  # NULLABLE
    standard_cost: Mapped[Decimal]  # NOT NULL, default=0
    selling_price: Mapped[Optional[Decimal]]  # NULLABLE
    
    # ⭐ MATERIAL RELATIONSHIP (KEY FINDING)
    material_id: Mapped[Optional[uuid.UUID]]  # NULLABLE
    # FK → materials.id, ondelete='SET NULL'
    
    # Status
    is_active: Mapped[bool]  # NOT NULL, default=True
    is_deleted: Mapped[bool]  # NOT NULL, default=False
    deleted_at: Mapped[Optional[datetime]]  # NULLABLE
    
    # Audit
    created_at: Mapped[datetime]  # NOT NULL
    updated_at: Mapped[datetime]  # NOT NULL
```

**Constraints:**
- `uq_item_variant_tenant_code`: UNIQUE(tenant_id, code)
- `uq_item_variant_key`: UNIQUE(tenant_id, template_id, variant_key)

**Indexes:**
- `ix_item_variants_tenant_id`: (tenant_id)
- `ix_item_variants_template_id`: (template_id)
- `ix_item_variants_variant_key`: (tenant_id, template_id, variant_key)

**Foreign Keys:**
- `template_id` → `item_templates.id` (ondelete=CASCADE)
- `material_id` → `materials.id` (ondelete=SET NULL) ⭐

### 1.2 materials Table

**Source:** `backend/app/infrastructure/persistence/models/material_model.py`

```python
class MaterialModel(Base):
    __tablename__ = "materials"
    
    id: Mapped[uuid.UUID]  # PK
    tenant_id: Mapped[uuid.UUID]  # NOT NULL
    code: Mapped[str]  # NOT NULL, Unique per tenant
    name: Mapped[str]  # NOT NULL
    
    # ⭐ MATERIAL TYPE (KEY FINDING)
    material_type: Mapped[str]  # NOT NULL, default="raw"
    # Values: "raw_material", "semi_finished", "finished_good"
    
    category_id: Mapped[Optional[uuid.UUID]]  # FK → material_categories
    base_unit_id: Mapped[Optional[uuid.UUID]]  # FK → units_of_measure
    
    # Stock and Cost
    current_cost: Mapped[float]  # NOT NULL, default=0
    current_stock: Mapped[float]  # NOT NULL, default=0
    reserved_stock: Mapped[float]  # NOT NULL, default=0
    reorder_level: Mapped[Optional[float]]  # NULLABLE
    
    # Status
    is_active: Mapped[bool]  # NOT NULL, default=True
    is_deleted: Mapped[bool]  # NOT NULL, default=False
    
    # ... (many other fields)
```

**Constraints:**
- `uq_material_tenant_code`: UNIQUE(tenant_id, code)

**Indexes:**
- `ix_materials_tenant_id`: (tenant_id)
- `ix_materials_is_deleted`: (is_deleted)

### 1.3 boms Table

**Source:** `backend/app/infrastructure/persistence/models/bom_model.py`

```python
class BOMModel(Base):
    __tablename__ = "boms"
    
    id: Mapped[uuid.UUID]  # PK
    tenant_id: Mapped[uuid.UUID]  # NOT NULL
    
    # ⭐ PRODUCT OWNERSHIP (KEY FINDING)
    template_id: Mapped[uuid.UUID | None]  # FK → item_templates, NULLABLE
    variant_id: Mapped[uuid.UUID | None]  # FK → item_variants, NULLABLE
    
    version: Mapped[str]  # NOT NULL
    is_active: Mapped[bool]  # NOT NULL, default=False
    valid_from: Mapped[datetime]  # NOT NULL
    valid_to: Mapped[datetime | None]  # NULLABLE
    
    created_by: Mapped[uuid.UUID]  # NOT NULL
    approved_by: Mapped[uuid.UUID | None]  # NULLABLE
    
    # Status
    is_deleted: Mapped[bool]  # NOT NULL, default=False
    
    # Relationships
    lines: Mapped[List["BOMLineModel"]]  # 1:N
    operations: Mapped[List["BOMOperationModel"]]  # 1:N
```

**Constraints:**
- `uq_bom_tenant_variant_version`: UNIQUE(tenant_id, variant_id, version)

**Key Finding:** BOMs are owned by either `template_id` OR `variant_id` (both nullable)

### 1.4 Relationship Summary

```
┌─────────────────────────────────────────────────────────────┐
│                     EXISTING RELATIONSHIPS                   │
└─────────────────────────────────────────────────────────────┘

item_templates (1) ←──── (N) item_variants
                              ↓ (N:1, optional)
                          materials
                              
item_variants (1:1) ←──── boms
                          ↓ (1:N)
                      bom_lines
                          ↓ (N:1)
                      materials OR templates OR variants
```

**Critical Path for Semi-Finished BOM Explosion:**

```
FG BOM Line
    ↓ material_id
Material (type=semi_finished)
    ↓ ← item_variants.material_id
ItemVariant
    ↓ ← boms.variant_id
Semi-Finished BOM
    ↓
Raw Material Components
```

---

## 2. BACKEND AUDIT

### 2.1 CreateItemVariantCommand

**Source:** `backend/app/application/product/commands/product_commands.py`

```python
class CreateItemVariantCommand(BaseModel):
    tenant_id: UUID
    template_id: UUID
    attribute_values: Dict[str, Any]
    standard_cost: Decimal = Decimal("0")
    selling_price: Optional[Decimal] = None
    base_unit_id: Optional[UUID] = None
    material_id: Optional[UUID] = None  # ⭐ OPTIONAL!
    created_by: Optional[UUID] = None
```

**Finding:** `material_id` is OPTIONAL in the API contract.

### 2.2 CreateItemVariantHandler

**Source:** `backend/app/application/product/handlers/product_handlers.py`

```python
class CreateItemVariantHandler:
    async def handle(self, cmd: CreateItemVariantCommand) -> ItemVariantResult:
        # ... validation ...
        
        # Create variant with optional material_id
        variant = ItemVariant(
            ...
            material_id=cmd.material_id,  # ⭐ Can be None
            ...
        )
        
        # ⭐ PHASE 5: ATOMIC FG PROVISIONING
        if variant.material_id is None and self._material_repo is not None:
            # Auto-create Finished Good Material
            material = Material(
                code=fg_code,
                name=variant.name,
                material_type=MaterialType.FINISHED,  # ⭐ Always FG
                ...
            )
            await self._material_repo.save(material)
            variant.set_material_link(material.id)
        
        await self._variant_repo.save(variant)
        return result
```

**Key Behaviors:**

1. **If `material_id` provided:** Use it (link to existing material)
2. **If `material_id` is None:** Auto-create new FG material and link

**Finding:** Backend ALREADY supports linking to existing materials (including semi-finished).

### 2.3 UpdateItemVariantCommand

**Source:** Same file

```python
class UpdateItemVariantCommand(BaseModel):
    variant_id: UUID
    tenant_id: UUID
    standard_cost: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    material_id: Optional[UUID] = None  # ⭐ Can update material link
    is_active: Optional[bool] = None
```

**Finding:** Material link CAN be changed after creation.

### 2.4 Material Validation

**No special validation found** that prevents linking variants to semi-finished materials.

**Finding:** System does NOT enforce material type constraints on variant → material mapping.

### 2.5 BOM Creation

**Source:** `backend/app/application/bom/handlers/bom_handlers.py`

BOMs can be created for variants with `material_id` pointing to semi-finished materials.

**Finding:** No blocker for creating BOMs for semi-finished variants.

### 2.6 BOM Explosion Logic

**Source:** `backend/app/domain/bom/services/bom_browser_service.py`

```python
async def _build_recursive(
    self, tenant_id: UUID, bom: BillOfMaterial, depth: int, max_depth: int, qty_multiplier: float
) -> Dict[str, Any]:
    children: List[Dict[str, Any]] = []
    
    if depth <= max_depth:
        for line in bom.lines:
            is_material = line.material_id is not None
            component_id = line.material_id or line.variant_id or line.template_id
            
            details = await self._details.get_component_details(...)
            
            # ⚠️ CURRENT BEHAVIOR: Only recurse for templates/variants
            if not is_material:
                child_bom = await self._bom_provider.get_active_bom(
                    tenant_id=tenant_id, 
                    template_id=line.template_id, 
                    variant_id=line.variant_id
                )
                if child_bom:
                    # Recurse
                    child_tree = await self._build_recursive(...)
                    child_node["children"] = child_tree.get("children", [])
            
            children.append(child_node)
    
    return {"id": str(bom.id), "version": bom.version, "children": children}
```

**Finding:** BOM explosion does NOT currently check materials for associated BOMs.

**Required Change:** Add logic to check if `is_material` AND `material_type == "semi_finished"`, then lookup variant via `material_id` and get its BOM.

---

## 3. FRONTEND AUDIT

### 3.1 Variant Creation Form

**Source:** `frontend/src/modules/products/components/VariantManager.tsx`

**Current Behavior (Create Form):**

```tsx
// Create New Variant
<div className="grid grid-cols-2 gap-3 pt-2">
  <Input label="Standard Cost" />
  <Input label="Selling Price" />
  
  {/* NO MATERIAL SELECTOR! */}
  <div className="message">
    ✓ Finished Good inventory item will be created automatically.
  </div>
</div>
```

**Finding:** Create form does NOT expose `material_id` field. Users cannot link to existing materials during creation.

### 3.2 Variant Edit Form

**Source:** Same file (`EditRow` component)

**Current Behavior:**

```tsx
// Edit Variant
<Select value={materialId} onValueChange={setMaterialId}>
  <SelectTrigger />
  <SelectContent>
    <SelectItem value={NO_MATERIAL}>— No material linked —</SelectItem>
    
    {/* Finished Goods Section */}
    {fgMaterials.filter(m => t.includes("finish") || t === "fg").map(...)}
    
    {/* Other Materials Section */}
    {fgMaterials.filter(m => !t.includes("finish") && t !== "fg").map(...)}
  </SelectContent>
</Select>
```

**Finding:** Edit form DOES have material selector, but it does NOT show semi-finished materials in a dedicated section.

**Issue:** Semi-finished materials appear in "Other Materials" section, not prominently displayed.

### 3.3 Material Selector

**Current Filter Logic:**

```tsx
// Finished Goods
fgMaterials.filter(m => {
  const t = String(m.material_type || "").toLowerCase()
  return t.includes("finish") || t === "fg"
})

// Other Materials  
fgMaterials.filter(m => {
  const t = String(m.material_type || "").toLowerCase()
  return !t.includes("finish") && t !== "fg"
})
```

**Finding:** No dedicated section for `semi_finished` materials.

### 3.4 BOM Tree View

**Source:** `frontend/src/modules/bom/components/BOMTreeView.tsx`

Currently shows material nodes but does NOT indicate if they are semi-finished or expandable.

**Finding:** Frontend will need visual indicator (purple badge) to show semi-finished materials.

---

## 4. CURRENT SYSTEM BEHAVIOR

### 4.1 Normal Finished Good Flow (TODAY)

```
User Action                     System Behavior
───────────────────────────────────────────────────────────────
1. Create Template              → item_templates record
   TPL-ROTAMETER               
                                
2. Create Variant               → item_variants record
   (no material_id provided)      material_id = NULL initially
                                
3. Backend Handler              → Auto-creates material
   CreateItemVariantHandler       material_type = "finished_good"
                                  
4. System Links                 → item_variants.material_id = new material
                                
5. Result                       → Variant ←→ FG Material linked
```

**Status:** ✅ WORKING - This must remain unchanged.

### 4.2 Current Semi-Finished Limitation

```
User Action                     Current System
───────────────────────────────────────────────────────────────
1. Create SF Material           → materials record
   SF-MECH-ASSY                   material_type = "semi_finished"
   type = semi_finished         
                                
2. Create Template/Variant      → item_variants record
   (no way to link SF material)   material_id = NULL
                                  ❌ No UI to select SF-MECH-ASSY
                                
3. Backend auto-creates FG      → Creates unwanted FG material
                                  
4. Edit Variant                 → Can change material_id
   (manually select SF)           ✅ Works but requires 2 steps
                                
5. Create BOM for Variant       → boms record
                                  ✅ Works
                                
6. Use SF in FG BOM             → FG BOM → SF-MECH-ASSY
                                  ✅ Works
                                
7. View BOM Tree                → ❌ SF material shows as leaf
   (explosion)                    ❌ Does not recurse into SF BOM
```

**Status:** ⚠️ PARTIALLY WORKING - Requires workarounds.

---

## 5. REQUIRED CHANGES

### 5.1 Database

**Required:** ❌ NONE

**Reason:** `item_variants.material_id` → `materials.id` relationship already exists and is nullable.

### 5.2 Backend

**Required:** ✅ YES (Minor - BOM Explosion Only)

**Files:**
1. `backend/app/infrastructure/persistence/repositories/bom_repository.py`
   - Add `get_bom_for_material(material_id)` method
   
2. `backend/app/infrastructure/services/bom_providers.py`
   - Add `get_bom_for_material()` to provider
   - Enhance `get_component_details()` to return `material_type`
   
3. `backend/app/domain/bom/services/bom_browser_service.py`
   - Update `_build_recursive()` to check semi-finished materials
   - Add recursion path for materials

**No changes needed:**
- ✅ CreateItemVariantCommand (already supports optional material_id)
- ✅ CreateItemVariantHandler (already supports linking to existing materials)
- ✅ UpdateItemVariantCommand (already supports changing material_id)
- ✅ BOM creation (already works for variants with any material_id)

### 5.3 Frontend

**Required:** ✅ YES (UX Enhancement)

**Option A: Expose in Create Form (Minimal)**

Add collapsible "Advanced" section in create form:

```tsx
<Collapsible defaultOpen={false}>
  <CollapsibleTrigger>
    <Button variant="ghost" size="sm">
      Advanced: Link to Existing Material
    </Button>
  </CollapsibleTrigger>
  <CollapsibleContent>
    <MaterialSelector />
    <HelpText>Only needed for semi-finished materials</HelpText>
  </CollapsibleContent>
</Collapsible>
```

**Option B: Keep Create Simple (Two-Step)**

No changes to create form. Document the workflow:
1. Create variant (auto-creates FG)
2. Edit variant → Change material_id to SF
3. Proceed with BOM

**Recommendation:** Option A (collapsible) - one-step process, hidden by default.

**Edit Form:**
- Enhance material selector to show semi-finished section
- Add visual indicators (purple badge for SF materials)

**BOM Tree View:**
- Add `material_type` field to node interface
- Display purple "Semi-Finished" badge for SF materials
- Show expandable indicator for SF materials

---

## 6. VALIDATION RULES

### 6.1 Existing Validations (KEEP)

✅ **Tenant Isolation:** Material must belong to same tenant as variant
✅ **Material Existence:** Selected material must exist and not be deleted
✅ **Variant Uniqueness:** variant_key must be unique per (tenant, template)

### 6.2 New Validations (ADD)

**None Required** - System should allow any material type to be linked.

**Rationale:**
- Finished goods can be linked (already working)
- Semi-finished should be allowed (new use case)
- Raw materials could be linked (edge case, but no technical reason to block)

### 6.3 Duplicate Material Mapping

**Question:** Can multiple variants link to the same material?

**Current System:** No constraint prevents this.

**Finding:** Multiple variants CAN link to the same material (e.g., different color variants sharing same inventory pool).

**Decision:** Keep existing behavior (allow duplicates).

---

## 7. BOM EXPLOSION DEPENDENCY

### 7.1 Current Lookup Path

```
BOM Line (material_id = SF-MECH-ASSY)
    ↓
❌ System stops (is_material = True, no recursion)
```

### 7.2 Required Lookup Path

```
BOM Line (material_id = SF-MECH-ASSY)
    ↓
Check: material_type == "semi_finished" ?
    ↓ YES
Find: item_variants WHERE material_id = SF-MECH-ASSY
    ↓
Found: VAR-SF-MECH
    ↓
Find: boms WHERE variant_id = VAR-SF-MECH AND is_active = TRUE
    ↓
Found: SF BOM
    ↓
✅ Recurse into SF BOM components
```

### 7.3 Implementation

**Repository Method:**

```python
# bom_repository.py
async def get_bom_for_material(
    self, tenant_id: UUID, material_id: UUID
) -> Optional[BillOfMaterial]:
    stmt = (
        select(BOMModel)
        .join(ItemVariantModel, BOMModel.variant_id == ItemVariantModel.id)
        .where(
            ItemVariantModel.material_id == material_id,
            ItemVariantModel.tenant_id == tenant_id,
            BOMModel.tenant_id == tenant_id,
            BOMModel.is_active == True,
            BOMModel.is_deleted == False
        )
        .options(selectinload(BOMModel.lines))
    )
    result = await self._session.execute(stmt)
    return result.scalar_one_or_none()
```

**Service Method:**

```python
# bom_browser_service.py
async def _build_recursive(...):
    for line in bom.lines:
        is_material = line.material_id is not None
        
        # Get component details (enhanced to include material_type)
        details = await self._details.get_component_details(...)
        
        # Check for child BOM
        child_bom = None
        
        if not is_material:
            # Existing path: templates/variants
            child_bom = await self._bom_provider.get_active_bom(...)
        elif is_material and details.get("material_type") == "semi_finished":
            # NEW path: semi-finished materials
            child_bom = await self._bom_provider.get_bom_for_material(
                tenant_id, line.material_id
            )
        
        if child_bom:
            # Recurse
            child_tree = await self._build_recursive(...)
```

---

## 8. REGRESSION RISKS

### 8.1 High Risk (Must Test)

❗ **Normal FG Variant Creation**
- **Risk:** Breaking the default auto-create flow
- **Test:** Create variant without selecting material → Must auto-create FG
- **Mitigation:** Keep create form simple by default

❗ **Existing BOM Explosion**
- **Risk:** Breaking template/variant BOM explosion
- **Test:** Multi-level template → variant → material BOMs
- **Mitigation:** Only ADD new path for semi-finished, don't modify existing paths

### 8.2 Medium Risk (Should Test)

⚠️ **Tenant Isolation**
- **Risk:** Leaking materials across tenants
- **Test:** Verify material selector only shows same-tenant materials
- **Mitigation:** Use existing tenant_id filters

⚠️ **Existing Variants with Material Links**
- **Risk:** Breaking existing FG variants that already have material_id set
- **Test:** Load and display existing variant with material link
- **Mitigation:** No changes to existing data

### 8.3 Low Risk

✓ **Subcontracting**
- **Risk:** Minor - SF materials now discoverable
- **Impact:** Positive - enables subcontracting of SF materials
- **Test:** Existing subcontract flows continue working

✓ **Work Orders**
- **Risk:** Minimal - WO references variants, not materials directly
- **Test:** Create WO for variant with SF material link
- **Mitigation:** No WO code changes needed

---

## 9. IMPLEMENTATION PLAN

### Phase 1: Backend (BOM Explosion)

**Priority:** HIGH
**Risk:** LOW
**Estimate:** 2 hours

**Tasks:**
1. Add `get_bom_for_material()` to BOMRepository
2. Update BOMProvider protocol and implementation
3. Enhance `get_component_details()` to return material_type
4. Modify `_build_recursive()` to check semi-finished materials
5. Write unit tests for new recursion path

**Files:**
- `backend/app/infrastructure/persistence/repositories/bom_repository.py`
- `backend/app/infrastructure/services/bom_providers.py`
- `backend/app/domain/bom/services/bom_browser_service.py`
- `backend/tests/api/bom/test_bom_semi_finished_explosion.py` (new)

### Phase 2: Frontend (BOM Tree Display)

**Priority:** MEDIUM
**Risk:** LOW
**Estimate:** 1 hour

**Tasks:**
1. Add `material_type` to BOMTreeNode interface
2. Display purple "Semi-Finished" badge in tree view
3. Show expandable indicator for SF materials

**Files:**
- `frontend/src/types/bom.types.ts`
- `frontend/src/modules/bom/components/BOMTreeView.tsx`

### Phase 3: Frontend (Variant Form UX)

**Priority:** MEDIUM
**Risk:** MEDIUM (UX change)
**Estimate:** 2 hours

**Tasks:**
1. Add collapsible "Advanced" section to create form
2. Add material selector inside advanced section
3. Enhance edit form material selector (add SF section)
4. Add contextual help text

**Files:**
- `frontend/src/modules/products/components/VariantManager.tsx`

### Phase 4: Testing & Validation

**Priority:** HIGH
**Risk:** N/A
**Estimate:** 2 hours

**Tasks:**
1. Test normal FG variant creation (regression)
2. Test SF material → variant linking
3. Test SF BOM creation
4. Test multi-level BOM explosion (FG → SF → RM)
5. Test tenant isolation
6. Test edit variant (existing behavior)

---

## 10. RECOMMENDATION

### Proceed with Implementation: ✅ YES

**Rationale:**

1. **Database:** No migration needed ✅
2. **Backend:** Minimal changes, low risk ✅
3. **Frontend:** Optional UX enhancement ✅
4. **Backward Compatibility:** Existing flows unchanged ✅
5. **Business Value:** Enables multi-level BOM and subcontracting ✅

### Approach

**Phase 1 First:** Implement BOM explosion backend changes
- Enables semi-finished BOM discovery
- Zero UI changes
- Can test via API

**Phase 2 Second:** Add frontend indicators
- Users see which materials are semi-finished
- Visual feedback in BOM tree

**Phase 3 Last:** Enhance variant form
- Improves UX for SF variant creation
- Optional - can ship without this

### Approval Required Before Proceeding

**Confirm:**
1. ✅ Reuse existing `item_variants.material_id` relationship
2. ✅ No database migration
3. ✅ Keep normal variant creation flow unchanged
4. ✅ Add optional "Advanced" section in create form
5. ✅ Implement BOM explosion for semi-finished materials

---

**END OF AUDIT**

**Next Step:** Await approval to proceed with implementation based on this plan.
