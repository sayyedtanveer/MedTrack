# Subcontracting Material Issue UX/UI Enhancement — Audit Report

**Date:** September 26, 2026  
**Status:** Phase A — Comprehensive Audit Complete  
**Objective:** Improve material issue UX so users don't need to manually search for BOM-required components

---

## Executive Summary

The existing subcontracting module is **fully functional** with proper:
- BOM snapshot on approval
- Required component tracking
- Inventory transactions
- Batch traceability
- RBAC/tenant isolation
- Audit logging

**Primary UX Problem:**  
Users must manually search for and select materials that are already known to the system (from the BOM snapshot), creating confusion and unnecessary friction.

**Solution Scope:**  
Frontend-only UX enhancement — no backend business logic changes required.

---

## Part 1: Database Schema Audit

### Tables and Relationships

```
subcontract_orders
├── id (PK)
├── tenant_id (FK → tenants)
├── order_number (unique per tenant)
├── supplier_id (FK → suppliers)
├── product_id (output material ID)
├── product_type ('variant')
├── quantity (order quantity)
├── bom_id (FK → boms, nullable)
├── due_date
├── notes
├── status (draft | approved | materials_issued | partially_received | completed | cancelled)
├── output_batch_id (FK → batches, nullable)
├── received_quantity
├── is_deleted
├── created_by, approved_by, approved_at
├── created_at, updated_at
│
├── Relationship: lines → SubcontractOrderLineModel[]
└── Relationship: issues → SubcontractMaterialIssueModel[]
```

```
subcontract_order_lines (BOM Snapshot)
├── id (PK)
├── tenant_id
├── subcontract_order_id (FK → subcontract_orders)
├── material_id (FK → materials)
├── required_quantity (from BOM * order qty + scrap)
├── issued_quantity (running total)
├── returned_quantity (running total)
├── created_at
│
└── Property: line_status → 'pending' | 'partial' | 'issued' | 'returned'
```

```
subcontract_material_issues (Transaction History)
├── id (PK)
├── tenant_id (FK → tenants)
├── subcontract_order_id (FK → subcontract_orders)
├── material_id (FK → materials)
├── batch_id (FK → batches, nullable)
├── batch_number (string, for display)
├── quantity
├── returned_quantity
├── from_location_id (FK → locations, nullable)
├── issued_at
└── issued_by (user ID)
```

### Key Observations

✅ **BOM snapshot is created at approval time**  
   - Copies BOM components into `subcontract_order_lines`
   - Calculates `required_quantity` = BOM qty × order qty + scrap

✅ **Issued quantity is tracked per component**  
   - Each line has `issued_quantity` field
   - Updated when material is issued
   - Supports partial issues

✅ **Remaining calculation is implicit**  
   - Remaining = `required_quantity - issued_quantity + returned_quantity`
   - Not stored, computed on-the-fly

✅ **Multiple issue transactions allowed per material**  
   - `subcontract_material_issues` allows multiple rows per material
   - Supports partial issues across multiple transactions

✅ **Batch traceability supported**  
   - `batch_id` (UUID FK) for proper traceability
   - `batch_number` (string) for display

---

## Part 2: Backend API Audit

### Endpoints

**1. Create Subcontract Order**
```
POST /api/v1/supply-chain/subcontract/orders
Body: {
  supplier_id, product_id, product_type, quantity,
  bom_id?, due_date?, notes?
}
Status: Creates order in 'draft' status
```

**2. Approve Subcontract Order**
```
POST /api/v1/supply-chain/subcontract/orders/{id}/approve
- Validates BOM exists and is active
- Loads BOM lines with selectinload
- Creates SubcontractOrderLineModel for each BOM component with material_id
- Calculates required_quantity = BOM qty × order qty × (1 + scrap %)
- Sets status to 'approved'
- Sets approved_by and approved_at
```

**3. Issue Material to Vendor** ⚠️ **KEY ENDPOINT**
```
POST /api/v1/supply-chain/subcontract/orders/{id}/issue
Body: {
  material_id: UUID,
  quantity: Decimal,
  from_location_id: UUID,
  batch_id?: UUID | null,
  batch_number?: string | null
}

Flow:
1. Validates order exists and tenant matches
2. Validates status in ('approved', 'materials_issued')
3. Resolves batch_number from batch_id if not provided
4. Calls InventoryService.issue_to_subcontractor()
   - Locks material
   - Deducts from 'available' internal bucket
   - Adds to subcontractor location bucket
   - Raises InsufficientStockError if not enough stock
   - Logs inventory transaction with batch_id
5. Creates SubcontractMaterialIssueModel record
6. Updates matching SubcontractOrderLineModel.issued_quantity (if exists)
7. Sets order status to 'materials_issued'
8. Returns { status: 'ok' }
```

**4. Receive Processed Output**
```
POST /api/v1/supply-chain/subcontract/orders/{id}/receive
Body: { material_id, quantity, warehouse_location_id, output_batch_number? }
```

**5. Return Material**
```
POST /api/v1/supply-chain/subcontract/orders/{id}/return-material
Body: { material_id, quantity, to_location_id, batch_id? }
```

**6. Cancel Order**
```
POST /api/v1/supply-chain/subcontract/orders/{id}/cancel
```

**7. Get Order Detail**
```
GET /api/v1/supply-chain/subcontract/orders/{id}
Returns: SubcontractOrderDetail with lines[], issues[]
```

**8. Get Traceability**
```
GET /api/v1/supply-chain/subcontract/orders/{id}/traceability
Returns: { input_batches[], output_batch, inventory_transactions[] }
```

### Request Schemas

**SubcontractIssueRequest**
```python
class SubcontractIssueRequest(BaseModel):
    material_id: uuid.UUID         # ⚠️ User must provide this
    quantity: Decimal
    from_location_id: uuid.UUID
    batch_id: Optional[uuid.UUID] = None
    batch_number: Optional[str] = None
```

### Inventory Validation

**InventoryService.issue_to_subcontractor()**
```python
async def issue_to_subcontractor(
    tenant_id, material_id, quantity, from_location_id,
    subcontractor_location_id, subcontract_order_id,
    unit_id, created_by, batch_id?, batch_number?
):
    # 1. Lock material
    # 2. Deduct from available internal stock
    # 3. Raises InsufficientStockError if not enough
    # 4. Add to subcontractor location bucket
    # 5. Sync material totals
    # 6. Log transaction with batch_id
```

✅ **Backend provides full stock validation**  
✅ **Batch traceability supported**  
✅ **Tenant isolation enforced**  
✅ **Audit logging included**

---

## Part 3: Frontend UI Audit

### Current Page Structure

**File:** `frontend/src/modules/procurement/pages/SubcontractOrderDetailPage.tsx`

### Sections

**1. Header**
- Order number, status badge
- Approve, Cancel, Traceability buttons
- Output qty, received qty, due date

**2. Pre-Approval Info Banners** (recently added)
- Blue banner when BOM linked: explains snapshot process
- Amber banner when no BOM: warns about manual selection

**3. Required Components Section** ✅ **ALREADY EXISTS**
```tsx
{order.lines.length > 0 && (
  <section>
    <h2>Required components (from BOM snapshot)</h2>
    
    // Desktop: Table view
    <Table>
      <TableHeader>Material | Required | Issued | Returned | Status</TableHeader>
      <TableBody>
        {order.lines.map(line => (
          <TableRow highlighted={issueMat === line.material_id}>
            <MaterialInfo materialId={line.material_id} />
            {line.required_quantity}
            {line.issued_quantity}
            {line.returned_quantity}
            <Badge>{line.status}</Badge>
          </TableRow>
        ))}
      </TableBody>
    </Table>
    
    // Mobile: Card view
    <div className="md:hidden">
      {order.lines.map(line => (
        <Card>
          <MaterialInfo /> <Badge>{line.status}</Badge>
          <Grid cols=3>
            Required | Issued | Returned
          </Grid>
        </Card>
      ))}
    </div>
  </section>
)}
```

**4. Issue Material Section** ⚠️ **CURRENT UX PROBLEM**
```tsx
{canIssue && (
  <section>
    <h2>Issue material to vendor</h2>
    
    // User must search for material even though it's in lines[] above
    <SubcontractMaterialSelector
      value={issueMat}
      onChange={handleIssueMaterialChange}
      typeFilter="raw"
      label="Component material"
      placeholder="Search raw or semi-finished components…"
    />
    
    {/* Shows pending qty IF material matches a line */}
    {issuePendingQty !== null && issuePendingQty > 0 && (
      <p>Pending from BOM: {issuePendingQty} units</p>
    )}
    
    <Input label="Quantity" value={issueQty} />
    <Select label="From warehouse" value={issueFrom} />
    <Input label="Batch ID (optional)" value={issueBatchId} />
    
    <Button onClick={issue}>Issue to vendor</Button>
  </section>
)}
```

**Logic:**
```tsx
const handleIssueMaterialChange = (id: string) => {
  setIssueMat(id)
  if (order) {
    const line = order.lines.find((l) => l.material_id === id)
    if (line) {
      const pending = Math.max(0, line.required_quantity - line.issued_quantity)
      setIssuePendingQty(pending)
      setIssueQty(String(pending > 0 ? pending : 1))
    } else {
      setIssuePendingQty(null)  // Not a BOM component
    }
  }
}
```

**5. Receive Output Section**
- Uses SubcontractMaterialSelector for output material
- Pre-filled with order's product_id
- Quantity, warehouse, batch number

**6. Return Material Section**
- Uses SubcontractMaterialSelector
- Quantity, return warehouse

**7. Issue History Table**
- Shows all past issues
- Material ID (first 8 chars), qty, returned, batch, date

### Components Used

**MaterialInfo**
```tsx
function MaterialInfo({ materialId }: { materialId: string }) {
  // Fetches material by ID
  // Displays: code + name
  // Fallback: UUID prefix
}
```

**SubcontractMaterialSelector**
```tsx
// Location: frontend/src/modules/procurement/components/SubcontractMaterialSelector
// Searchable dropdown for materials
// Filters by type: 'raw' or 'semi_finished'
```

---

## Part 4: UX Problem Analysis

### Current Flow (Problematic)

```
1. User views Required Components
   - RM-0002 Required 10, Issued 0
   - RM-0003 Required 5, Issued 0

2. User scrolls down to "Issue Material to Vendor"

3. User must SEARCH for "RM-0002" again
   ❌ System already knows RM-0002 is required!
   
4. After selecting RM-0002:
   ✓ System shows "Pending from BOM: 10 units"
   ✓ Pre-fills quantity = 10
   
5. User selects warehouse, batch, clicks Issue

6. Required Components updates:
   - RM-0002 Required 10, Issued 10 ✓
```

### Why It's Confusing

1. **Redundant search:** User must find the same material twice
2. **No direct action:** Required Components table is passive, no buttons
3. **Disconnected UI:** Issue form is separate from components table
4. **Additional material unclear:** Current form mixes BOM and non-BOM materials
5. **No remaining qty visible:** Must calculate Required - Issued mentally

---

## Part 5: Existing Business Rules

### Status Lifecycle

```
draft → approved → materials_issued → partially_received → completed
                 ↘                                          ↗
                  cancelled
```

### Material Issue Rules

✅ **Can issue when:** status = 'approved' OR 'materials_issued'  
✅ **Multiple partial issues allowed:** issue 4, then 3, then 3 = 10 total  
✅ **Backend validates stock:** raises InsufficientStockError  
✅ **Batch optional:** only required if material is batch-tracked  
✅ **Non-BOM materials can be issued:** current form allows any material  
✅ **Line issued_quantity updates:** if material_id matches a line  

### Stock Validation

**Backend (InventoryService):**
```python
remaining = await self._deduct_available_internal(tenant_id, material_id, quantity)
if remaining > 0:
    raise InsufficientStockError(...)
```

**Frontend error handling:**
```tsx
catch (e) {
  const detail = e?.response?.data?.detail
  toast({ title: detail || "Operation failed", variant: "destructive" })
}
```

---

## Part 6: What Can Be Reused

### ✅ Backend — NO CHANGES NEEDED

- **Approval endpoint:** Creates BOM snapshot correctly
- **Issue endpoint:** Validates stock, updates line quantities
- **Inventory service:** Full transaction support
- **Schemas:** SubcontractIssueRequest works perfectly
- **RBAC:** Permissions already enforced
- **Audit:** Transaction logging included

### ✅ Frontend Components

- **MaterialInfo:** Shows code + name, works great
- **SubcontractMaterialSelector:** Needed for "Additional Material" flow
- **Badge, Button, Input, Select:** UI components
- **Responsive layout:** Desktop table / mobile cards pattern

### ⚠️ Frontend Logic — NEEDS ENHANCEMENT

**Current state management:**
```tsx
const [issueMat, setIssueMat] = useState("")
const [issueQty, setIssueQty] = useState("1")
const [issueFrom, setIssueFrom] = useState("")
const [issueBatchId, setIssueBatchId] = useState("")
```

**What's missing:**
- No "Issue" button on each line in Required Components
- No drawer/modal for focused issue workflow
- No warehouse stock availability display
- No batch selector with availability info
- No clear separation between BOM-required vs additional materials

---

## Part 7: Proposed UX Flow (No Backend Changes)

### Flow A: BOM-Required Material Issue

```
1. User views Required Components table/cards
   
2. Each line with remaining > 0 shows:
   [ Issue Material ] button
   
3. User clicks [ Issue Material ] on RM-0002 line
   
4. Drawer/Modal opens with:
   Title: "Issue Material to Vendor"
   
   Context:
   - Subcontract Order: SCO-20260926-0001
   - Vendor: ABC Engineering
   - Material: RM-0002 — Raw Material 2
   - Required: 10, Issued: 0, Remaining: 10
   
   Form:
   - Quantity to Issue: [10] (pre-filled with remaining)
   - From Warehouse: [Raw Materials Warehouse ▼]
     → Show available stock per warehouse if possible
   - Batch/Lot: [Select batch ▼] (if batch-tracked)
     → Show batch availability, expiry
   - [ Cancel ] [ Confirm Issue ]
   
5. User confirms → calls existing API:
   POST /api/v1/.../orders/{id}/issue
   Body: { material_id: RM-0002, quantity: 10, ... }
   
6. Success:
   - Drawer closes
   - Required Components refreshes
   - RM-0002 shows: Issued 10, ✓ Fully Issued
   - Toast: "Material issued successfully"
```

### Flow B: Additional Material Issue

```
1. User scrolls past Required Components

2. Sees section:
   "Additional Material Issue"
   ℹ️ Use this only when issuing materials not part of the BOM

3. User clicks [ + Issue Additional Material ]

4. Same drawer opens, but:
   - Material: [Search materials…] (SubcontractMaterialSelector)
   - All fields editable
   - No "Required/Remaining" context
```

---

## Part 8: Implementation Plan

### Phase B: UX Design Mapping ✅ COMPLETE (this audit)

**Current flow:** Search → Select → Issue  
**Problem:** Redundant search for known BOM materials  
**New flow:** Click line → Pre-filled drawer → Confirm  
**Existing API reused:** POST .../orders/{id}/issue  
**Database:** No changes  
**New UI state:** Modal open/close, selected line context  

### Phase C: Frontend Enhancement (Next)

**Files to modify:**
1. `frontend/src/modules/procurement/pages/SubcontractOrderDetailPage.tsx`
   - Add issue button to each line
   - Create issue drawer/modal component
   - Move SubcontractMaterialSelector to "Additional Material" section

**New components to create:**
2. `frontend/src/modules/procurement/components/IssueMaterialDrawer.tsx`
   - Drawer/Dialog with Material info header
   - Quantity input (default = remaining)
   - Warehouse selector (with stock info if available)
   - Batch selector (if batch-tracked, show availability)
   - Confirmation button

3. Optional: `frontend/src/modules/procurement/components/WarehouseStockInfo.tsx`
   - Query and display available stock per warehouse

4. Optional: `frontend/src/modules/procurement/components/BatchSelector.tsx`
   - Dropdown with batch number, available qty, expiry

**API calls:**
- Reuse existing `supplyChainApi.issueSubcontract()`
- No new endpoints needed

**State management:**
```tsx
const [issueDrawerOpen, setIssueDrawerOpen] = useState(false)
const [selectedLine, setSelectedLine] = useState<SubcontractOrderLine | null>(null)
```

### Phase D: Additional Material Flow

- Keep SubcontractMaterialSelector
- Move to separate section below Required Components
- Add clear labeling and guidance

### Phase E: Regression Testing

**Test scenarios:**
1. Existing subcontract orders (created before UX change) still work
2. Approval creates lines correctly
3. Issue updates line.issued_quantity
4. Partial issues work (issue 4, then 6)
5. Insufficient stock error displays correctly
6. Batch issue with traceability works
7. Mobile responsive layout works
8. Non-BOM material issue still supported (if needed)
9. RBAC permissions respected
10. Tenant isolation maintained

---

## Part 9: Risks and Constraints

### ✅ Low Risk

- **Frontend-only changes:** No backend business logic modified
- **Existing API stable:** POST .../issue endpoint works correctly
- **No database migration:** Schema unchanged
- **No RBAC changes:** Permissions already enforced
- **No breaking changes:** Old flow can coexist during transition

### ⚠️ Medium Risk

- **Batch selector complexity:** Need to query batches per material+warehouse
  - **Mitigation:** Start with simple text input, enhance later
  
- **Warehouse stock display:** Requires stock query API
  - **Mitigation:** Display only if API available, not required for MVP

### ❌ Must Preserve

- **Inventory transaction integrity:** Must always call InventoryService
- **Stock validation:** Backend remains authoritative
- **Batch traceability:** batch_id must be passed to API
- **Tenant isolation:** Never bypass tenant_id checks
- **Audit logging:** All transactions logged
- **Line quantity updates:** issued_quantity must increment correctly
- **Status transitions:** Order status rules unchanged

---

## Part 10: Files Inventory

### Backend (No Changes Required)

```
backend/app/infrastructure/persistence/models/subcontract_model.py
  - SubcontractOrderModel
  - SubcontractOrderLineModel
  - SubcontractMaterialIssueModel

backend/app/interfaces/api/v1/routes/supply_chain.py
  - issue_subcontract_material() endpoint (line ~2464)

backend/app/interfaces/api/v1/schemas/supply_chain_schemas.py
  - SubcontractIssueRequest

backend/app/application/manufacturing/services/inventory_service.py
  - InventoryService.issue_to_subcontractor()
```

### Frontend (To Be Modified)

```
frontend/src/modules/procurement/pages/SubcontractOrderDetailPage.tsx
  ⚠️ Main file to enhance

frontend/src/modules/procurement/components/SubcontractMaterialSelector.tsx
  ✅ Reuse for "Additional Material" flow

frontend/src/services/supply-chain.service.ts
  ✅ issueSubcontract() works correctly
```

### Frontend (To Be Created)

```
frontend/src/modules/procurement/components/IssueMaterialDrawer.tsx
  NEW: Issue workflow drawer/modal

frontend/src/modules/procurement/components/WarehouseStockInfo.tsx (optional)
  NEW: Display available stock per warehouse

frontend/src/modules/procurement/components/BatchSelector.tsx (optional)
  NEW: Batch dropdown with availability
```

---

## Part 11: Acceptance Criteria Verification

### Can the existing system support the new UX?

✅ **Scenario 1: Full Issue**
- Line: Required 10, Issued 0
- Action: Issue 10
- Result: Backend updates line.issued_quantity = 10
- Status: line_status property returns 'issued'

✅ **Scenario 2: Partial Issue**
- Line: Required 10, Issued 0
- Action: Issue 4
- Result: Backend updates line.issued_quantity = 4
- Remaining: Frontend calculates 10 - 4 = 6

✅ **Scenario 3: Second Issue**
- Line: Required 10, Issued 4
- Action: Issue 6
- Result: Backend updates line.issued_quantity = 4 + 6 = 10

✅ **Scenario 4: Insufficient Stock**
- Warehouse has: 5 units
- User tries: 10 units
- Result: InventoryService raises InsufficientStockError
- Frontend: Displays error.detail from API response

✅ **Scenario 5: Batch Tracked**
- User selects batch_id
- Backend: Passes batch_id to issue_to_subcontractor()
- Result: Transaction logged with batch_id for traceability

✅ **Scenario 6: Semi-Finished BOM**
- Subcontract order for SF-MECH-ASSY
- Approval: Loads BOM, creates lines for RM-001...RM-010
- Issue flow: Same as above, works for all component types

✅ **Scenario 7: Existing Orders**
- Orders created before UX change
- Structure: Same SubcontractOrderModel, same lines[]
- Compatibility: 100% compatible, no migration needed

---

## Part 12: Next Steps

### Immediate Actions

1. ✅ **Audit complete** — this document
2. **Get stakeholder approval** for proposed UX flow
3. **Create issue drawer component** (IssueMaterialDrawer.tsx)
4. **Modify detail page** to add issue buttons per line
5. **Move material search** to "Additional Material" section
6. **Test** all scenarios from Part 11
7. **Document** changes in implementation report

### Out of Scope (Future Enhancements)

- **Batch selector with expiry display:** Nice to have, not MVP
- **Real-time stock availability:** Requires stock query API
- **Multi-warehouse stock comparison:** Complex query, defer
- **Warehouse auto-suggestion:** Based on highest stock
- **Issue all remaining:** Button to issue all pending components at once
- **Undo last issue:** Would require return transaction immediately

---

## Summary

**What exists:**
- ✅ Full subcontracting module with BOM snapshot
- ✅ Required component tracking (SubcontractOrderLineModel)
- ✅ Material issue API with stock validation
- ✅ Batch traceability support
- ✅ RBAC and tenant isolation
- ✅ Audit logging

**What's missing (UX only):**
- ❌ Direct "Issue" button on each required component line
- ❌ Pre-filled issue form when clicking a BOM component
- ❌ Clear separation between BOM-required vs additional materials
- ❌ Warehouse/batch selection with availability info

**What's safe to change:**
- ✅ Frontend UI layout and user flow
- ✅ Add buttons to required components table/cards
- ✅ Create issue drawer/modal
- ✅ Pre-fill form from line data

**What must NOT change:**
- ❌ Backend API contracts
- ❌ Inventory transaction logic
- ❌ Database schema
- ❌ RBAC rules
- ❌ Existing business rules

**Implementation risk:** **LOW**  
**Backend changes required:** **NONE**  
**Breaking changes:** **NONE**  
**Estimated effort:** **Frontend-only, 1-2 days**

---

**Audit Status:** ✅ COMPLETE  
**Ready for Phase C:** ✅ YES  
**Stakeholder approval required:** ⚠️ RECOMMENDED before proceeding

