# Material Grid Location Visibility - Phase B Design

**Date:** 2026-09-29  
**Objective:** Design the minimal changes needed to add warehouse/subcontractor columns to Material List

---

## 1. DESIGN OVERVIEW

### 1.1 Current Data Flow

```
Frontend Material List
    ↓
GET /inventory/materials
    ↓
InventoryQueryHandler.list_materials()
    ↓
MaterialRepository.search()
    ↓
MaterialModel (materials table)
    ↓ current_stock (total across all locations)
MaterialResponse
    ↓
Frontend displays: Code | Name | Category | Total Stock | Actions
```

### 1.2 New Data Flow

```
Frontend Material List
    ↓
GET /inventory/materials
    ↓
InventoryQueryHandler.list_materials()
    ↓
MaterialRepository.search() → List[Material]
    ↓
NEW: Bulk fetch stock_levels for all materials
    ↓
NEW: Aggregate by location type (warehouse vs subcontractor)
    ↓
MaterialResponse (enhanced with warehouse_stock, subcontractor_stock)
    ↓
Frontend displays: Code | Name | Category | Total | Warehouse | At Subcontractor | Actions
```

---

## 2. BACKEND DESIGN

### 2.1 Enhanced MaterialResponse Schema

**File:** `backend/app/interfaces/api/v1/schemas/inventory_schemas.py`

```python
class MaterialResponse(BaseModel):
    # ... existing fields ...
    current_stock: Decimal          # Total stock (unchanged)
    reserved_stock: Decimal         # Reserved stock (unchanged)
    available_stock: Decimal        # available (unchanged)
    
    # NEW FIELDS
    warehouse_stock: Decimal = Decimal("0")        # Warehouse + zones + racks + production
    subcontractor_stock: Decimal = Decimal("0")    # At subcontractor locations
```

**Why these fields:**
- Simple, flat structure (no nested objects)
- Easy to display in table columns
- Defaults to 0 (backward compatible)
- Total should equal: `current_stock ≈ warehouse_stock + subcontractor_stock`

**Note:** Small discrepancies may occur if there are other location types (e.g., 'transit', 'customer'). We'll document this.

---

### 2.2 Stock Aggregation Logic

**New Service Method:** `InventoryQueryHandler._compute_stock_by_location_bulk()`

```python
async def _compute_stock_by_location_bulk(
    self,
    material_ids: List[uuid.UUID],
    tenant_id: uuid.UUID
) -> Dict[uuid.UUID, Dict[str, Decimal]]:
    """
    Compute warehouse and subcontractor stock for multiple materials in one query.
    
    Returns:
        {
            material_id_1: {
                "warehouse_stock": Decimal("10.0"),
                "subcontractor_stock": Decimal("2.0")
            },
            material_id_2: { ... }
        }
    """
    # Query stock_levels + locations for all material_ids
    # Group by material_id and location.type
    # Aggregate quantities
```

**SQL Strategy:**

```sql
SELECT 
    sl.material_id,
    l.type as location_type,
    SUM(sl.quantity) as total_quantity
FROM stock_levels sl
JOIN locations l ON sl.location_id = l.id
WHERE 
    sl.tenant_id = :tenant_id
    AND sl.material_id IN (:material_ids)
    AND sl.is_deleted = FALSE
    AND l.is_deleted = FALSE
    AND sl.stock_status = 'available'  -- Only count available stock
GROUP BY sl.material_id, l.type
```

**Then aggregate by category:**
- `warehouse_stock` = SUM where type IN ('warehouse', 'zone', 'rack', 'bin', 'production')
- `subcontractor_stock` = SUM where type = 'subcontractor'

---

### 2.3 Integration into list_materials

**File:** `backend/app/application/inventory/handlers/inventory_query_handler.py`

**Current:**
```python
async def list_materials(self, query: ListMaterialsQuery) -> PaginatedResult:
    materials = await self.material_repo.search(...)
    total = await self.material_repo.count(...)
    
    return PaginatedResult(
        items=[MaterialProjection.from_entity(m) for m in materials],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )
```

**Enhanced:**
```python
async def list_materials(self, query: ListMaterialsQuery) -> PaginatedResult:
    # 1. Get materials
    materials = await self.material_repo.search(...)
    total = await self.material_repo.count(...)
    
    # 2. Bulk fetch stock breakdown
    material_ids = [m.id for m in materials]
    stock_breakdown = await self._compute_stock_by_location_bulk(
        material_ids, query.tenant_id
    )
    
    # 3. Merge into projections
    items = []
    for m in materials:
        proj = MaterialProjection.from_entity(m)
        breakdown = stock_breakdown.get(m.id, {})
        proj.warehouse_stock = breakdown.get("warehouse_stock", Decimal("0"))
        proj.subcontractor_stock = breakdown.get("subcontractor_stock", Decimal("0"))
        items.append(proj)
    
    return PaginatedResult(items=items, total=total, ...)
```

---

### 2.4 MaterialProjection Enhancement

**File:** `backend/app/application/inventory/handlers/inventory_query_handler.py`

```python
@dataclass
class MaterialProjection:
    # ... existing fields ...
    current_stock: Decimal
    reserved_stock: Decimal
    available_stock: Decimal
    
    # NEW
    warehouse_stock: Decimal = Decimal("0")
    subcontractor_stock: Decimal = Decimal("0")
```

---

## 3. FRONTEND DESIGN

### 3.1 TypeScript Type Enhancement

**File:** `frontend/src/types/material.types.ts`

```typescript
export interface Material {
  // ... existing fields ...
  current_stock: number;
  reserved_stock: number;
  available_stock: number;
  
  // NEW
  warehouse_stock?: number;        // Optional for backward compat
  subcontractor_stock?: number;    // Optional for backward compat
}
```

---

### 3.2 Desktop Grid - New Columns

**File:** `frontend/src/modules/inventory/pages/MaterialListPage.tsx`

**Current Columns:**
1. Code
2. Material Name
3. Category
4. Stock (current_stock)
5. Actions

**New Columns:**
1. Code
2. Material Name
3. Category
4. **Total Stock** (current_stock)
5. **Warehouse** (warehouse_stock) ← NEW
6. **At Subcontractor** (subcontractor_stock) ← NEW
7. Actions

**Column Implementation:**

```typescript
{
  id: "current_stock",
  header: "Total Stock",  // Renamed from "Stock"
  cell: ({ row }) => {
    const qty = Number(row.original.current_stock ?? 0);
    const isLow = row.original.is_low_stock;
    const unit = units?.find(u => u.id === row.original.base_unit_id);
    const unitLabel = unit?.code || "";
    
    return (
      <div className="flex flex-col">
        <span className={isLow ? "text-destructive font-medium" : ""}>
          {qty} {unitLabel}
        </span>
        {isLow && <StatusBadge status="low-stock" label="Low" />}
      </div>
    );
  },
},
{
  id: "warehouse_stock",
  header: "Warehouse",  // NEW
  cell: ({ row }) => {
    const qty = Number(row.original.warehouse_stock ?? 0);
    const unit = units?.find(u => u.id === row.original.base_unit_id);
    const unitLabel = unit?.code || "";
    
    return <span>{qty} {unitLabel}</span>;
  },
},
{
  id: "subcontractor_stock",
  header: "At Subcontractor",  // NEW
  cell: ({ row }) => {
    const qty = Number(row.original.subcontractor_stock ?? 0);
    const unit = units?.find(u => u.id === row.original.base_unit_id);
    const unitLabel = unit?.code || "";
    
    if (qty === 0) {
      return <span className="text-muted-foreground">—</span>;
    }
    
    return (
      <span className="text-orange-600 font-medium">
        {qty} {unitLabel}
      </span>
    );
  },
},
```

**Design Notes:**
- Orange color for subcontractor stock (visual distinction)
- Show "—" when subcontractor_stock = 0 (cleaner UI)
- Removed "Suggest PO" link from Total column (keep UI cleaner)
- Reserved stock info removed from Total column (still shown in Stock drawer)

---

### 3.3 Mobile Card Layout

**File:** `frontend/src/modules/inventory/pages/MaterialListPage.tsx`

**Current Mobile Card:**
```
┌─────────────────────────────────┐
│ Raw Material 4          [Stock] │
│ RM-0004                         │
│                                 │
│ Metal              10 KG [Low]  │
│                    Suggest PO   │
└─────────────────────────────────┘
```

**New Mobile Card:**
```
┌─────────────────────────────────┐
│ Raw Material 4          [Stock] │
│ RM-0004                         │
│                                 │
│ Metal                           │
│                                 │
│ Total: 10 KG [Low]              │
│ Warehouse: 9 KG                 │
│ At Vendor: ABC Eng — 1 KG       │
│                                 │
│ Suggest PO                      │
└─────────────────────────────────┘
```

**Implementation:**

```typescript
<Card key={product.id} className="..." onClick={...}>
  <CardContent className="p-4">
    <div className="flex justify-between items-start mb-2">
      <div>
        <h3 className="font-medium text-base">{product.name}</h3>
        <p className="text-xs text-muted-foreground font-mono">{product.code}</p>
      </div>
      <Button variant="ghost" size="sm" onClick={...}>
        <Replace className="h-4 w-4 mr-1"/> Stock
      </Button>
    </div>
    
    <div className="text-sm text-muted-foreground mb-2">
      {category?.name || "Uncategorized"}
    </div>
    
    {/* Stock breakdown */}
    <div className="space-y-1">
      {/* Total */}
      <div className="flex justify-between items-center">
        <span className="text-xs text-muted-foreground">Total:</span>
        <div className="flex items-center gap-2">
          <span className={isLow ? "text-destructive font-medium text-sm" : "text-sm font-medium"}>
            {qty} {unitLabel}
          </span>
          {isLow && <StatusBadge status="low-stock" label="Low" />}
        </div>
      </div>
      
      {/* Warehouse */}
      <div className="flex justify-between items-center">
        <span className="text-xs text-muted-foreground">Warehouse:</span>
        <span className="text-sm">{warehouseStock} {unitLabel}</span>
      </div>
      
      {/* Subcontractor */}
      {subcontractorStock > 0 && (
        <div className="flex justify-between items-center">
          <span className="text-xs text-muted-foreground">At Vendor:</span>
          <span className="text-sm text-orange-600 font-medium">
            {subcontractorStock} {unitLabel}
          </span>
        </div>
      )}
    </div>
    
    {isLow && (
      <Link to="/procurement/purchase-orders" ... className="text-xs text-blue-600 hover:underline mt-2 inline-block">
        Suggest PO
      </Link>
    )}
  </CardContent>
</Card>
```

---

## 4. RESPONSIVE BEHAVIOR

### 4.1 Desktop (≥ 768px)

**Table with 7 columns:**
```
| Code       | Material Name    | Category | Total Stock | Warehouse | At Subcontractor | Actions      |
|------------|------------------|----------|-------------|-----------|------------------|--------------|
| RM-MT-0004 | raw-003          | Metal    | 10 KG       | 9 KG      | ABC: 1 KG        | Stock | Edit |
| RM-MT-0002 | raw001           | Metal    | 20 KG       | 20 KG     | —                | Stock | Edit |
| SF-MT-0001 | main-sub-part    | Metal    | 1 KG        | 1 KG      | —                | Stock | Edit |
```

**Column widths:**
- Code: 120px
- Material Name: flex-1 (flexible)
- Category: 120px
- Total Stock: 120px
- Warehouse: 120px
- At Subcontractor: 150px
- Actions: 180px

---

### 4.2 Mobile (< 768px)

**Card layout with vertical stock breakdown**

Advantages:
- More readable on small screens
- Clear label-value pairs
- Stock breakdown doesn't force horizontal scrolling

---

## 5. VENDOR NAME RESOLUTION (OPTIONAL ENHANCEMENT)

### 5.1 Problem

Current design shows:
```
At Subcontractor: 1.0 KG
```

User doesn't know WHICH subcontractor.

### 5.2 Solution Options

#### Option A: Show quantity only (current design)
```
At Subcontractor: 1.0 KG
```

**Pros:** Simple, no extra queries  
**Cons:** User must click "Stock" button to see vendor

#### Option B: Show first vendor name
```
At Subcontractor: ABC Engineering — 1.0 KG
```

**Pros:** Immediate visibility  
**Cons:** What if multiple vendors?

#### Option C: Show vendor count if multiple
```
At Subcontractor: 3 vendors — 10 KG
```

**Pros:** Handles multiple vendors  
**Cons:** Still need to click for details

### 5.3 Recommendation: Option A for MVP

**Rationale:**
- Keeps grid query simple and fast
- Vendor names already available via "Stock" button
- Can enhance later if user feedback demands it

**Future Enhancement (Phase 2):**
- Add `subcontractor_details` array to response
- Show vendor names with tooltips/popovers
- Add filter "Show only materials at vendors"

---

## 6. DATA CONSISTENCY

### 6.1 Invariant

```
current_stock ≈ warehouse_stock + subcontractor_stock + other_stock
```

**"Other stock" includes:**
- Transit locations
- Customer locations
- Any custom location types

**For most cases:**
```
current_stock = warehouse_stock + subcontractor_stock
```

### 6.2 Validation

Add logging/monitoring to detect discrepancies:

```python
if abs(current_stock - (warehouse_stock + subcontractor_stock)) > 0.01:
    logger.warning(
        f"Stock mismatch for material {material_id}: "
        f"current={current_stock}, warehouse={warehouse_stock}, subcontractor={subcontractor_stock}"
    )
```

---

## 7. PERFORMANCE CONSIDERATIONS

### 7.1 Query Complexity

**Current:** 1 query (materials table)

**New:** 2 queries
1. Materials table (unchanged)
2. Stock_levels + locations bulk fetch (new)

**Expected Performance:**
- Materials: ~10-20ms (indexed, paginated)
- Stock breakdown: ~20-40ms (indexed on material_id, location_id)
- **Total: ~30-60ms** (acceptable)

### 7.2 Pagination Impact

**Current page_size:** default 20, max 500

**Worst case:** 500 materials × stock aggregation = still only 2 queries

**Mitigation:**
- Keep page_size default at 20
- Add note in UI if user selects large page_size

---

## 8. TESTING STRATEGY

### 8.1 Backend Unit Tests

Test `_compute_stock_by_location_bulk()`:
1. Material with only warehouse stock
2. Material with only subcontractor stock
3. Material with both warehouse and subcontractor stock
4. Material with multiple warehouse locations (should aggregate)
5. Material with multiple subcontractor locations (should aggregate)
6. Material with no stock
7. Material with consumed stock (should not count)
8. Bulk query with 100+ materials (performance test)

### 8.2 API Integration Tests

Test `GET /inventory/materials`:
1. Response includes warehouse_stock, subcontractor_stock
2. Values sum to ≈ current_stock
3. Pagination works with new fields
4. Filtering works with new fields

### 8.3 Frontend Component Tests

Test MaterialListPage:
1. Displays Total, Warehouse, Subcontractor columns
2. Shows "—" when subcontractor_stock = 0
3. Shows orange text when subcontractor_stock > 0
4. Mobile cards show stock breakdown
5. Clicking "Stock" button still works
6. Clicking "Edit" button still works

### 8.4 E2E Business Flow Tests

**Test Case 1: Issue to Subcontractor**
```
Initial:     Total: 100, Warehouse: 100, Subcontractor: 0
Issue 10:    Total: 100, Warehouse: 90,  Subcontractor: 10
```

**Test Case 2: Consume at Subcontractor**
```
Before:      Total: 100, Warehouse: 90,  Subcontractor: 10
Consume 10:  Total: 90,  Warehouse: 90,  Subcontractor: 0
```

**Test Case 3: Return from Subcontractor**
```
Before:      Total: 100, Warehouse: 90,  Subcontractor: 10
Return 10:   Total: 100, Warehouse: 100, Subcontractor: 0
```

**Test Case 4: Receive Semi-Finished**
```
Raw Before:  Total: 100, Warehouse: 0,   Subcontractor: 100
Consume 100: Total: 0,   Warehouse: 0,   Subcontractor: 0
SF After:    Total: 10,  Warehouse: 10,  Subcontractor: 0
```

---

## 9. FILES TO MODIFY

### Backend

1. **`backend/app/interfaces/api/v1/schemas/inventory_schemas.py`**
   - Add `warehouse_stock`, `subcontractor_stock` to MaterialResponse

2. **`backend/app/application/inventory/handlers/inventory_query_handler.py`**
   - Add `_compute_stock_by_location_bulk()` method
   - Enhance `list_materials()` to call it
   - Update MaterialProjection dataclass

3. **`backend/app/application/inventory/handlers/inventory_query_handler.py`** (same file)
   - Add MaterialProjection fields

### Frontend

4. **`frontend/src/types/material.types.ts`**
   - Add `warehouse_stock?`, `subcontractor_stock?` to Material interface

5. **`frontend/src/modules/inventory/pages/MaterialListPage.tsx`**
   - Add warehouse_stock column
   - Add subcontractor_stock column
   - Rename "Stock" column header to "Total Stock"
   - Enhance mobile card layout

### Database

**NO CHANGES NEEDED** - stock_levels table already exists

---

## 10. ROLLOUT PLAN

### Phase C: Backend (Estimated: 2 hours)
1. Update MaterialResponse schema (15 min)
2. Implement _compute_stock_by_location_bulk() (45 min)
3. Integrate into list_materials() (30 min)
4. Write unit tests (30 min)

### Phase D: Frontend (Estimated: 1.5 hours)
1. Update Material type (5 min)
2. Add desktop columns (30 min)
3. Enhance mobile cards (30 min)
4. Test responsive behavior (25 min)

### Phase E: Testing (Estimated: 2 hours)
1. Manual testing of all scenarios
2. E2E flow tests
3. Performance testing with 500+ materials

### Phase F: Documentation (Estimated: 30 min)
1. Update API documentation
2. Update user guide
3. Create summary report

**Total Estimated Time: 6 hours**

---

## 11. ACCEPTANCE CRITERIA

### Backend
- ✅ MaterialResponse includes warehouse_stock, subcontractor_stock
- ✅ list_materials uses only 2 queries (not N+1)
- ✅ Stock breakdown accurate within 0.01 tolerance
- ✅ No performance regression (< 100ms response time)

### Frontend
- ✅ Desktop grid shows 7 columns
- ✅ Mobile cards show stock breakdown
- ✅ Subcontractor stock = 0 shows "—"
- ✅ Subcontractor stock > 0 shows in orange
- ✅ Total = Warehouse + Subcontractor (visually obvious)

### Business Logic
- ✅ Issue: Warehouse ↓, Subcontractor ↑, Total unchanged
- ✅ Consume: Subcontractor ↓, Total ↓
- ✅ Return: Subcontractor ↓, Warehouse ↑, Total unchanged
- ✅ Multi-vendor: Aggregates correctly

---

## 12. NEXT STEPS

1. ✅ Phase A: Audit complete
2. ✅ Phase B: Design complete
3. ⏭️ **Phase C: Backend Implementation**

Ready to proceed with implementation!
