# Material Standard Cost Workflow: Comprehensive Audit Report

**Report Date:** November 9, 2026  
**Audit Type:** Code Inspection & Gap Analysis  
**Scope:** Material Costing, BOM Cost Calculation, Material Selection Workflow  
**Status:** Read-Only Inspection Complete — Ready for Implementation  
**Prepared By:** Kiro Code Analysis Agent

---

## Executive Summary

MedTrack's material standard cost management system has **complete backend infrastructure** but **critical UI/UX gaps** that prevent users from effectively configuring costs and understanding BOM cost completeness.

### Key Findings

| Area | Status | Notes |
|------|--------|-------|
| **Backend Workflow** | ✅ Complete | StandardCostRevision entity, approval handlers, audit trail all implemented |
| **Database Schema** | ✅ Complete | Material.current_cost, StandardCostRevision tables ready |
| **API Endpoints** | ⚠️ Partial | Cost calculation works; response schema missing `is_complete` and `missing_costs` |
| **RBAC Permissions** | ⚠️ Partial | `inventory:write` exists; missing `procurement:propose_cost`, `procurement:approve_cost` |
| **Material Buy Tab UI** | ❌ Missing | No "Not Configured" indicator; no cost proposal/supplier agreement actions |
| **BOM Material Selection** | ❌ Missing | No cost status indicators; no warnings for uncosted materials |
| **BOM Cost Display** | ⚠️ Partial | Backend calculates is_complete/missing_costs; frontend never receives them |

### Critical Finding

**Users cannot distinguish between:**
- Material with cost explicitly set to 0.00 (intentional)
- Material with no approved cost (uncosted, should show "Not Configured")

**Impact:** BOM costs appear complete when they're actually incomplete; users don't know which materials are missing costs.

---

## Detailed Audit Findings

### 1. Material.current_cost Field

**Location:** `backend/app/infrastructure/persistence/models/material_model.py:40`

**Definition:**
```python
current_cost: Mapped[float] = mapped_column(
    Numeric(18, 4), 
    nullable=False,          # ← NOT NULL
    default=0                # ← Defaults to 0
)
```

**Status:** ❌ **Not Suitable for "Not Configured" State**

**Analysis:**
- Column is NOT NULL, always has a value
- Defaults to 0, cannot be NULL
- No way to distinguish "0 cost" from "no approved cost"
- To detect uncosted materials, must query StandardCostRevision status

**Recommendation:**
- Keep database as-is (backward compatible)
- In UI, show "Not Configured" only if:
  - No APPROVED StandardCostRevision exists for material
  - (Even if `current_cost = 0`)

**Files to Modify:** Frontend only (no schema change needed)

---

### 2. StandardCostRevision: Complete Workflow Implemented

**Location:** 
- Domain: `backend/app/domain/procurement/pricing/entities.py:372-492`
- Handler: `backend/app/application/procurement/pricing/handlers.py:541-606`
- Repository: `backend/app/infrastructure/persistence/repositories/procurement_pricing_repository.py:394-620`

**Status:** ✅ **Fully Implemented & Production Ready**

**State Machine:**
```
CREATE
  ↓
PENDING → APPROVED → (updates Material.current_cost)
       ↘ REJECTED
```

**Features Implemented:**
- ✅ Create revision with reason (GRN_VARIANCE, SUPPLIER_AGREEMENT, MANUAL_ADJUSTMENT)
- ✅ Approval with segregation of duties (requester ≠ approver)
- ✅ Rejection with reason
- ✅ Audit trail to MaterialCostHistory
- ✅ Stale revision detection (prevents race conditions)
- ✅ Updates Material.current_cost on approval

**Code Quality:**
- ✅ Full type hints
- ✅ Comprehensive error handling
- ✅ Multi-tenant isolation
- ✅ Structured logging with context

**What's Missing:**
- ❌ No UI to create revisions (frontend modal)
- ❌ No UI to view/approve pending revisions
- ❌ No permission enforcement (handlers exist but not checked)

**Gap Analysis:** **UI-only gap** — backend is production-ready, just needs frontend

---

### 3. SupplierPriceAgreement: Complete Workflow Implemented

**Location:** `backend/app/domain/procurement/pricing/entities.py:94-360`

**Status:** ✅ **Fully Implemented & Integrated**

**Features:**
- ✅ Versioning with effective date ranges (effective_from / effective_to)
- ✅ Status workflow: DRAFT → PENDING → APPROVED → ACTIVE
- ✅ Quantity tiers with discount percentages
- ✅ Integrated into PO pricing engine (Level 1 priority in price calculation)
- ✅ Multi-supplier support per material

**Integration Points:**
- Highest priority in PO pricing (overrides latest purchase price)
- Used in PO pricing engine: `backend/app/application/procurement/pricing/po_pricing_engine.py:136-143`

**What's Missing:**
- ❌ No UI to create/manage supplier agreements in Material detail
- ❌ No UI to view agreements by material
- ❌ No approval workflow UI

**Gap Analysis:** **UI-only gap** — backend is complete

---

### 4. BOM Cost Calculation: Backend Complete, Response Incomplete

**Location:** 
- Service: `backend/app/domain/bom/services/cost_rollup_service.py`
- Provider: `backend/app/infrastructure/services/bom_providers.py:45-66`
- Route: `backend/app/interfaces/api/v1/routes/boms.py:436-455`

**Status:** ⚠️ **Partially Exposed**

**What Works:**
- ✅ Calculates `total_cost` = material_cost + operation_cost
- ✅ Identifies `missing_costs` (materials without approved StandardCostRevision)
- ✅ Sets `is_complete = true/false` based on missing costs
- ✅ Returns 0 total cost when any material is missing (correct behavior)
- ✅ Only uses APPROVED StandardCostRevision costs

**Backend Calculation (Hidden):**
```python
# cost_rollup_service.py:86-102
if missing_costs:
    return {
        "total_cost": Decimal('0'),
        "is_complete": False,
        "missing_costs": missing_costs,  # ← Never reaches frontend
    }
```

**API Response Schema (Current):**
```python
# bom_schemas.py:105-110
class BOMCostResponse(BaseModel):
    bom_id: uuid.UUID
    material_cost: Decimal
    operation_cost: Decimal
    total_cost: Decimal
    currency_code: Optional[str] = None
    currency_symbol: Optional[str] = None
    # ← Missing: is_complete, missing_costs
```

**Impact:** 
- ❌ Frontend never knows if BOM cost is complete
- ❌ Cannot display warnings for missing materials
- ❌ Cannot show which specific materials need costs

**Gap Analysis:** **Schema + Response gap** — need to expose is_complete and missing_costs

---

### 5. Material Buy Tab: Current State vs. Required

**Location:** `frontend/src/modules/inventory/components/MaterialFormDrawer.tsx`

**Current Rendering (lines 117-143):**
```typescript
const standardCost = Number(material?.current_cost ?? 0)

// Shows 0.00 for both uncosted and cost-intentionally-zero
<span className="text-sm font-semibold tabular-nums">
    {currencyCode} {fmt(standardCost)}
</span>
```

**What's Displayed:**
- ✅ Standard Cost field (editable)
- ✅ Latest Purchase Price (read-only)
- ✅ Variance % (if cost > 0)
- ✅ Last Supplier, Purchase Count, Last Date
- ✅ Purchase history table

**What's Missing:**
- ❌ "Not Configured" label for uncosted materials
- ❌ Cost status indicator (APPROVED/PENDING/REJECTED)
- ❌ "Propose Standard Cost" button (requires form + handler)
- ❌ "Add Supplier Price" button (requires form + handler)
- ❌ List of active supplier agreements
- ❌ List of cost revisions (history)

**Current Behavior Issues:**
```typescript
// Line 127: Only shows variance if cost > 0
if (latestPrice !== null && standardCost > 0) {
    // Cannot distinguish:
    // - standardCost = 0 (intentional) → should show variance vs latest
    // - standardCost = 0 (uncosted) → should show "Not Configured"
}
```

**Gap Analysis:** **UI visibility gap** — need cost status detection + new action buttons

---

### 6. BOM Material Selection: No Cost Indicators

**Location:** `frontend/src/modules/bom/components/BOMLineForm.tsx`

**Current Behavior:**
```typescript
// Lines 96-99: Material search returns no cost info
const { data: results } = useQuery({
    queryKey: ["component-search", compType, debouncedSearch],
    queryFn: async () => {
        return filtered.map(m => ({ 
            id: m.id, 
            label: m.name, 
            sub: m.code,        // ← No cost_status
            type: "material" 
        }))
    },
})
```

**What's Missing:**
- ❌ Cost status badge (✅ Configured / ⚠️ Not Configured) in search results
- ❌ Warning when adding material without cost: "⚠️ BOM cost incomplete"
- ❌ "Configure Cost" quick action button
- ❌ Cannot jump to material detail without losing BOM edits

**Current Workflow Gap:**
1. User searches for material → No cost indicator shown
2. User adds material → No warning about missing cost
3. User wants to fix → Must navigate away, losing unsaved BOM

**Gap Analysis:** **UI indicators + UX workflow gap** — need badges, warnings, and modal overlay

---

### 7. BOM Cost Display: Missing Uncosted Materials List

**Location:** `frontend/src/modules/bom/components/BOMCostBreakdown.tsx`

**Current Display:**
```typescript
// Lines 58-62
<div className="text-2xl sm:text-3xl font-bold text-green-800 truncate">
    {formatCurrency(data.total_cost, data.currency_symbol || "₹")}
</div>
```

**Shows:**
- ✅ Total cost
- ✅ Material cost breakdown table
- ✅ Operation cost breakdown
- ✅ Cost percentages

**Missing:**
- ❌ Warning if cost is incomplete (is_complete = false)
- ❌ List of materials causing incomplete cost
- ❌ "Configure Cost" links for each missing material

**Backend Data (Available but Hidden):**
```python
{
    "is_complete": False,
    "missing_costs": [
        {"component_type": "material", "component_id": "uuid-1", "name": "Brass Rod"},
        {"component_type": "material", "component_id": "uuid-2", "name": "Steel Plate"}
    ]
}
```

**Gap Analysis:** **Response schema + UI display gap** — need to expose and render missing materials

---

### 8. RBAC Permissions: Partially Defined

**Location:** `backend/app/domain/shared/permissions.py`

**Current Permissions:**
```python
INVENTORY_READ = "inventory:read"
INVENTORY_WRITE = "inventory:write"      # ← Covers material edit + cost update
INVENTORY_DELETE = "inventory:delete"
# ← Missing procurement permissions
```

**Material Edit:** Uses `inventory:write` permission (general-purpose)

**Cost Proposal/Approval:** No specific permissions defined

**What's Missing:**
- ❌ `procurement:propose_cost` — Create StandardCostRevision
- ❌ `procurement:approve_cost` — Approve StandardCostRevision (segregation of duties)
- ❌ `procurement:manage_supplier_agreements` — Create/manage supplier price agreements
- ❌ No permission checks on cost endpoints (handlers exist but not secured)

**Current Risk:**
- Any user with `inventory:write` can directly edit Material.current_cost (bypasses approval)
- No way to enforce "Accounting Manager" approval requirement

**Gap Analysis:** **Permission definition + enforcement gap** — need to add and apply permissions

---

### 9. Direct Cost Update Path: Works but Unrestricted

**Location:** `backend/app/interfaces/api/v1/routes/inventory.py:195-247`

**Current Behavior:**
```python
@router.put("/materials/{material_id}")
async def update_material(
    material_id: uuid.UUID,
    body: UpdateMaterialRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    # ← Only requires inventory:write, no approval workflow
):
    # Direct update to Material.current_cost
    await handler.handle(UpdateMaterialCommand(
        ...,
        current_cost=body.current_cost,  # ← Bypasses approval
    ))
```

**Current State:**
- ✅ Direct cost edit works (for quick adjustments)
- ✅ Uses `inventory:write` permission (existing)
- ❌ Bypasses audit trail (no StandardCostRevision created)
- ❌ No segregation of duties

**Two Paths Exist:**
1. **Direct Edit** (Current) → Material.current_cost updated immediately → No audit
2. **Revision Workflow** (Not exposed in UI) → StandardCostRevision → PENDING → APPROVED → Audit trail

**Recommendation:** Keep both paths:
- **Direct edit** (0.00 adjustments): Uses `inventory:write`
- **Formal revision** (audit trail): Uses new `procurement:propose_cost` permission

**Gap Analysis:** **Permission scoping gap** — need distinct permissions for each path

---

## 6 Identified Gaps

### Gap 1: Material Cost Status Visibility

**Problem:** Users cannot tell if a material has an approved cost or just defaults to 0.00

**Root Cause:**
- `Material.current_cost` is NOT NULL, always has value (defaults to 0)
- No UI query of StandardCostRevision status
- Material Buy tab shows all costs as 0.00 or decimal value

**Current Behavior:**
```
Material with approved cost (5.50)          → Displays: ₹ 5.50 ✓
Material with no cost (0 default)           → Displays: ₹ 0.00 ✗ (indistinguishable)
Material cost explicitly set to 0 (intentional) → Displays: ₹ 0.00 ✗ (indistinguishable)
```

**Required Behavior:**
```
Material with approved cost (5.50)          → Displays: ₹ 5.50 ✓
Material with no approved cost (0 default)  → Displays: Not Configured ✓
Material cost intentionally 0 (with revision) → Displays: ₹ 0.00 ✓
```

**Solution:** Query StandardCostRevision status for material
- If APPROVED revision exists → show `current_cost` value
- If no APPROVED revision → show "Not Configured"

**Affected Files:** 3 backend, 1 frontend
**Effort:** 2-3 hours
**Risk:** Low (UI-only, no data modification)

---

### Gap 2: BOM Cost Response Missing is_complete & missing_costs

**Problem:** Frontend cannot determine if BOM cost is complete or which materials are uncosted

**Root Cause:**
- Backend calculates `is_complete` and `missing_costs` but doesn't return them
- Response schema omits these fields
- Frontend receives only total_cost (appears complete even when incomplete)

**Current Response:**
```json
{
  "bom_id": "uuid",
  "material_cost": 100.00,
  "operation_cost": 50.00,
  "total_cost": 150.00,
  "currency_code": "INR"
}
```

**Required Response:**
```json
{
  "bom_id": "uuid",
  "material_cost": 100.00,
  "operation_cost": 50.00,
  "total_cost": 0.00,
  "is_complete": false,
  "missing_costs": [
    {
      "component_type": "material",
      "component_id": "uuid-1",
      "name": "Brass Rod",
      "code": "BR-001"
    }
  ],
  "currency_code": "INR"
}
```

**Solution:** 
1. Add `is_complete: bool` to BOMCostResponse schema
2. Add `missing_costs: List[MissingCostDetail]` to schema
3. Update BOM cost endpoint to return these fields
4. Update frontend to display warning + missing materials list

**Affected Files:** 3 backend, 2 frontend
**Effort:** 2-3 hours
**Risk:** Low (backward compatible, new fields optional for existing clients)

---

### Gap 3: BOM Material Selection Has No Cost Indicators

**Problem:** Users don't know if a material has approved cost before adding to BOM; no warning if adding uncosted material

**Root Cause:**
- Material search doesn't include cost status
- No warning in BOM when adding uncosted material
- No way to jump to material detail without losing BOM edits

**Current Workflow:**
```
User searches → Selects material → Adds to BOM → Silent (no warning)
                (no cost info)       (no check)
```

**Required Workflow:**
```
User searches → Sees cost badge → Adds material → Sees warning "⚠️ Incomplete"
 (cost shown)                         (if uncosted)
                                      ↓
                            "Configure Cost" action
                                      ↓
                         Modal opens Material detail
                      (preserves BOM in background)
```

**Solution:**
1. Extend material search API to include cost status
2. Show cost badge in BOMLineForm results (✅ Configured / ⚠️ Not Configured)
3. Display non-blocking warning when uncosted material added
4. "Configure Cost" action opens MaterialFormDrawer as modal overlay

**Affected Files:** 3 backend, 4 frontend
**Effort:** 4-5 hours
**Risk:** Medium (requires state management for overlay mode)

---

### Gap 4: Material Buy Tab Missing "Propose Standard Cost" Action

**Problem:** No UI to initiate cost approval workflow

**Root Cause:**
- StandardCostRevision handlers exist but not exposed
- No frontend form for cost proposal
- No permission checks

**Current State:**
- Backend: CreateStandardCostRevisionCommand, handlers, repositories all exist
- Frontend: No button, no form, no modal

**Required State:**
- ✅ "Propose Standard Cost" button in Material Buy tab
- ✅ Modal form with:
  - New cost (Decimal input)
  - Reason (dropdown: GRN_VARIANCE, SUPPLIER_AGREEMENT, MANUAL_ADJUSTMENT)
  - Notes (optional text)
- ✅ Submit creates PENDING StandardCostRevision
- ✅ Show "Pending Approval" status if revision exists
- ✅ Permission check: `procurement:propose_cost`

**Solution:**
1. Add permission definition: `COST_PROPOSE = "procurement:propose_cost"`
2. Add permission check to cost creation endpoint
3. Create ProposeCostModal component
4. Wire button to modal in MaterialFormDrawer

**Affected Files:** 2 backend, 2-3 frontend (1 new file)
**Effort:** 3-4 hours
**Risk:** Low (new UI, existing handlers, permission check at endpoint)

---

### Gap 5: Material Buy Tab Missing "Add Supplier Price" Action

**Problem:** No UI to manage supplier price agreements

**Root Cause:**
- SupplierPriceAgreement workflow exists but not exposed in Material detail
- No form for creating agreements
- No list display

**Current State:**
- Backend: Entity, handlers, repositories all exist
- Frontend: No button, no form, no list

**Required State:**
- ✅ "Add Supplier Price" button in Material Buy tab
- ✅ Modal form with:
  - Supplier (dropdown search)
  - Base Price (Decimal)
  - Currency (select)
  - Effective From/To (date pickers)
  - Minimum Order Quantity
  - Quantity Tiers (optional)
- ✅ List of active supplier agreements for material
- ✅ Permission check: `procurement:manage_supplier_agreements`

**Solution:**
1. Add permission definition: `SUPPLIER_AGREEMENT_MANAGE = "procurement:manage_supplier_agreements"`
2. Add permission checks to supplier agreement endpoints
3. Create SupplierPriceAgreementModal component
4. Create SupplierPriceList component
5. Wire button to modal in MaterialFormDrawer

**Affected Files:** 2 backend, 3-4 frontend (2-3 new files)
**Effort:** 4-5 hours
**Risk:** Low (new UI, existing handlers, permission check)

---

### Gap 6: Cannot Preserve BOM Work When Opening Material Detail

**Problem:** Clicking "Configure Cost" loses unsaved BOM edits

**Root Cause:**
- MaterialFormDrawer opens full-page (clears state)
- No modal overlay mode
- BOM session not preserved

**Current Workflow:**
```
Editing BOM
    ↓ [Click "Configure Cost"]
Material detail opens (full page) → BOM state lost
    ↓ [Close material]
Back to BOM → Edits lost
```

**Required Workflow:**
```
Editing BOM (in background)
    ↓ [Click "Configure Cost"]
Material detail opens (modal overlay)
    ↓
BOM visible in background, preserved
    ↓ [Material cost updated]
Close material modal → BOM refreshes cost calculation
```

**Solution:**
1. Add overlay mode to MaterialFormDrawer:
   - `isOverlay` prop
   - Render as modal (z-50, centered, backdrop)
   - Close button instead of page navigation
2. BOM page manages overlay state in Context
3. On close, if cost changed, refresh BOM cost calculation

**Affected Files:** 2 frontend
**Effort:** 2-3 hours
**Risk:** Medium (state management complexity)

---

## Summary Table: All Gaps

| # | Gap | Severity | Backend | Frontend | Effort | Risk |
|---|-----|----------|---------|----------|--------|------|
| 1 | Cost status visibility | High | 1 file | 2 files | 2-3h | Low |
| 2 | BOM response missing fields | High | 2 files | 2 files | 2-3h | Low |
| 3 | BOM material selection warnings | High | 1 file | 4 files | 4-5h | Med |
| 4 | "Propose Cost" action | Medium | 1 file | 2-3 files | 3-4h | Low |
| 5 | "Add Supplier Price" action | Medium | 1 file | 3-4 files | 4-5h | Low |
| 6 | Modal overlay for edits | Medium | 0 files | 2 files | 2-3h | Med |
| **TOTAL** | | | **6 files** | **15 files** | **17-23h** | **Low-Med** |

---

## Implementation Roadmap

### Phase 1: Foundation (2-3 hours) — Enable All Other Phases
**Must-do first:**
1. ✅ Add `is_complete`, `missing_costs` to BOMCostResponse
2. ✅ Update BOM cost endpoint to return new fields
3. ✅ Add permission definitions (3 new)
4. ✅ Add material cost-status query endpoint

**Deliverable:** Backend API ready for frontend

### Phase 2: Material Buy Tab (3-4 hours) — Cost Visibility
1. ✅ Material cost status detection (query approved revision)
2. ✅ "Not Configured" label instead of 0.00
3. ✅ "Propose Standard Cost" button + modal
4. ✅ Permission checks

**Deliverable:** Users can see cost status and propose new costs

### Phase 3: BOM Material Selection (4-5 hours) — Warnings & Quick Actions
1. ✅ Extend material search with cost status
2. ✅ Cost badges in BOM picker
3. ✅ Warning when adding uncosted material
4. ✅ "Configure Cost" quick action

**Deliverable:** Users warned about uncosted materials with easy fix path

### Phase 4: Polish (4-6 hours) — Complete Workflows
1. ✅ BOM Cost Breakdown displays warning + missing materials
2. ✅ "Add Supplier Price" button + form + list
3. ✅ Modal overlay for material edit
4. ✅ Refresh BOM cost after edit

**Deliverable:** Complete end-to-end workflows

---

## Database Schema Assessment

**Recommendation:** ✅ **No changes needed**

**Why:**
- Material.current_cost works fine (NOT NULL, defaults 0 is correct)
- StandardCostRevision table ready
- SupplierPriceAgreement table ready
- MaterialCostHistory exists for audit trail

**Strategy:**
- Detect "Not Configured" state via StandardCostRevision query (not database field)
- Keep existing schema for backward compatibility
- No migrations required

---

## Risk Assessment

### Low Risk ✅
- Adding response fields (backward compatible)
- New permission definitions (no behavior change)
- UI visibility improvements (no data modification)
- Query endpoints (read-only)

### Medium Risk ⚠️
- MaterialFormDrawer overlay mode (state management)
- Material search query with cost join (performance)

### Mitigation
- Thorough testing of overlay state with large BOMs
- Profile search query; add index if needed
- Keep existing direct edit path working

---

## Success Criteria

### End-to-End Workflow
1. ✅ User edits material → Sees "Not Configured" if no approved cost
2. ✅ User clicks "Propose Standard Cost" → Form opens → Submits → Creates PENDING revision
3. ✅ User adds uncosted material to BOM → Sees warning "⚠️ Cost incomplete"
4. ✅ User clicks "Configure Cost" → Material modal opens (preserves BOM)
5. ✅ Material cost updates → BOM cost recalculates → is_complete changes
6. ✅ Finance user approves revision → Material.current_cost updates → BOM reflects new cost

### Testing Coverage
- [ ] Material without approved cost shows "Not Configured"
- [ ] Proposing cost creates PENDING StandardCostRevision
- [ ] BOM cost endpoint returns is_complete: false when uncosted
- [ ] Adding uncosted material shows non-blocking warning
- [ ] "Configure Cost" preserves BOM edits
- [ ] Approval updates Material + refreshes BOM
- [ ] Supplier price agreement creates and links correctly
- [ ] Permissions enforced on all actions

---

## Files to Modify

### Backend (6 files)
1. `backend/app/interfaces/api/v1/schemas/bom_schemas.py` — BOMCostResponse: add is_complete, missing_costs
2. `backend/app/interfaces/api/v1/routes/boms.py` — Return new fields in cost endpoint
3. `backend/app/domain/shared/permissions.py` — Add 3 new permissions
4. `backend/app/interfaces/api/v1/routes/procurement_pricing.py` — Add cost-status endpoint, permission checks
5. `backend/app/interfaces/api/v1/routes/inventory.py` — Extend material search with cost status
6. `backend/app/application/procurement/pricing/commands.py` — Minor schema additions (if needed)

### Frontend (8-10 files)
1. `frontend/src/modules/inventory/components/MaterialFormDrawer.tsx` — Cost visibility, overlay mode, buttons
2. `frontend/src/modules/inventory/services/materialApi.ts` — Query cost status
3. `frontend/src/types/bom.types.ts` — BOMCostResponse interface
4. `frontend/src/modules/bom/components/BOMLineForm.tsx` — Cost badges
5. `frontend/src/modules/bom/components/BOMLineList.tsx` — Warnings
6. `frontend/src/modules/bom/components/BOMCostBreakdown.tsx` — Missing materials display
7. New: `frontend/src/modules/inventory/components/ProposeCostModal.tsx`
8. New: `frontend/src/modules/inventory/components/SupplierPriceAgreementModal.tsx`
9. New: `frontend/src/modules/inventory/components/SupplierPriceList.tsx`
10. `frontend/src/modules/bom/pages/BOMEditPage.tsx` — Overlay state management

---

## Approval Gate

**Ready to proceed after user confirms:**
1. ✅ All 6 gaps accurately identified?
2. ✅ Root causes correct?
3. ✅ Solutions appropriate?
4. ✅ No additional gaps missed?
5. ✅ Acceptable to proceed with Phase 1 implementation?

---

## Appendix: Code Examples

### Example 1: Detecting "Not Configured" State

**Frontend:**
```typescript
// After querying cost status from backend
const hasCost = costStatus.has_approved_revision;

if (hasCost) {
  return <span>{formatCurrency(material.current_cost)}</span>;
} else {
  return <span className="text-amber-600">Not Configured</span>;
}
```

**Backend Query (new):**
```python
@router.get("/materials/{material_id}/cost-status")
async def get_material_cost_status(material_id: UUID, tenant_id: UUID = ...):
    revision = await repo.get_latest_approved_revision(tenant_id, material_id)
    return {
        "has_approved_revision": revision is not None,
        "status": revision.status if revision else None,
        "current_cost": float(revision.requested_cost) if revision else None,
    }
```

### Example 2: Extended BOM Cost Response

**Before:**
```json
{
  "material_cost": 100.00,
  "total_cost": 100.00
}
```

**After:**
```json
{
  "material_cost": 0.00,
  "total_cost": 0.00,
  "is_complete": false,
  "missing_costs": [
    {
      "component_type": "material",
      "component_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Brass Rod",
      "code": "BR-001",
      "quantity": 10,
      "unit": "kg"
    }
  ]
}
```

### Example 3: Permission-Gated Cost Proposal

**Endpoint:**
```python
@router.post(
    "/cost-revisions",
    dependencies=[Depends(require_permission("procurement:propose_cost"))]
)
async def create_cost_revision(
    body: CreateCostRevisionRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    # Only users with procurement:propose_cost can reach here
    cmd = CreateStandardCostRevisionCommand(
        material_id=body.material_id,
        requested_cost=body.requested_cost,
        reason=body.reason,
        requested_by=user_id,
    )
    result = await handlers.handle_create_standard_cost_revision(cmd)
    return StandardCostRevisionResult.from_entity(result)
```

---

**Report Generated:** November 9, 2026  
**Status:** Complete & Ready for Approval  
**Next Step:** Confirm findings, then proceed to Phase 1 implementation
