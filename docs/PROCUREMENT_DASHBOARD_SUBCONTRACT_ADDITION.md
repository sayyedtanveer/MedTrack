# Procurement Dashboard - Subcontract Orders Display

**Date:** 2026-10-01  
**Objective:** Add subcontract order tracking to procurement dashboard

---

## CURRENT STATE

### Procurement Dashboard Shows:
1. ✅ **Purchase Requisitions** - Pending approval
2. ✅ **Pending PO Approvals** - Purchase orders waiting for approval
3. ✅ **Supplier Deliveries** - Expected in next 7 days
4. ✅ **GRN Pending** - Goods received but not inspected
5. ✅ **Material Shortages** - Blocking work orders
6. ✅ **Overdue Deliveries** - Supplier deliveries past due date

### What's MISSING:
- ❌ **Subcontract Orders** - No visibility at all
- ❌ **Materials at Subcontractors** - Not tracked on dashboard
- ❌ **Overdue Subcontract Returns** - No alerts

---

## QUESTION: SHOULD SUBCONTRACTS APPEAR ON PROCUREMENT DASHBOARD?

### Arguments FOR (Yes, add them):

**Reason 1: They Are Part of Supply Chain**
- Procurement manages external suppliers
- Subcontractors ARE external parties
- Both involve sending materials OUT and receiving IN
- Procurement team likely coordinates both

**Reason 2: Similar Workflows**
- Issue materials → Track progress → Receive back
- Same as: Order materials → Track delivery → Receive
- Both have due dates and can be overdue

**Reason 3: Single View**
- Procurement team wants ONE dashboard for all external dependencies
- Don't want to check multiple places
- Holistic view of everything outside the company

**Reason 4: Material Shortage Impact**
- If subcontractor is late, it blocks production
- Same impact as supplier being late
- Should be visible on same dashboard

### Arguments AGAINST (No, keep separate):

**Reason 1: Different Nature**
- Procurement = BUY materials (spend money)
- Subcontracting = PROCESS materials (conversion)
- Different business processes

**Reason 2: Different Teams**
- Procurement team handles suppliers
- Production/Manufacturing team handles subcontractors
- May confuse responsibilities

**Reason 3: Already Have Manufacturing Dashboard**
- Subcontract orders could appear on Manufacturing Dashboard
- Where work orders, production schedules are tracked
- Keeps procurement focused on purchasing

**Reason 4: Dashboard Clutter**
- Adding too many metrics makes dashboard less useful
- Procurement dashboard already has 6 cards
- Better to have focused, role-specific dashboards

---

## RECOMMENDATION

### Option 1: Add to Procurement Dashboard (Simpler)
**Recommended IF:**
- Same team manages suppliers AND subcontractors
- You consider subcontracting as "outsourced production"
- Want single view of all external dependencies

**Add these cards:**
```
┌────────────────────────────────┐
│ Active Subcontract Orders      │
│ 5                              │
│ Processing at vendors          │
└────────────────────────────────┘

┌────────────────────────────────┐
│ Materials at Subcontractors    │
│ 150 KG                         │
│ Across 3 vendors               │
└────────────────────────────────┘

┌────────────────────────────────┐
│ Overdue Subcontract Returns    │
│ 2                              │
│ Past expected date             │
└────────────────────────────────┘
```

### Option 2: Add to Manufacturing Dashboard (Better Separation)
**Recommended IF:**
- Different teams manage suppliers vs subcontractors
- Want to keep procurement focused on purchasing
- Subcontracting is part of production planning

**Create Manufacturing Dashboard with:**
- Work orders in progress
- Materials reserved for production
- **Active subcontract orders** ← NEW
- **Materials at subcontractors** ← NEW
- Equipment utilization
- Production bottlenecks

### Option 3: Create Supply Chain Dashboard (Most Comprehensive)
**Recommended IF:**
- You want holistic view across procurement + manufacturing
- Larger organization with dedicated supply chain role
- Want to track everything external

**New Dashboard:**
- Procurement metrics (POs, GRNs, shortages)
- Subcontract metrics (active orders, materials out)
- Supplier performance
- Subcontractor performance
- Overall material flow

---

## MY RECOMMENDATION: Option 1 (Add to Procurement Dashboard)

**Rationale:**
1. You're asking about "procurement dashboard" specifically
2. Likely same person/team coordinates both
3. Simpler than creating new dashboard
4. Both involve external parties and due dates
5. Small addition (3 new cards) won't clutter

**Implementation:** Add 3 cards to existing procurement dashboard

---

## IMPLEMENTATION PLAN

### Step 1: Backend - Add Metrics to KPIQueryService

**File:** `backend/app/services/kpi_query_service.py`

**Add to `get_procurement_summary()` method:**

```python
# Active subcontract orders (not yet completed)
result = await self._session.execute(
    text("""
        SELECT COUNT(*) FROM subcontract_orders
        WHERE tenant_id = :tid
          AND status IN ('approved', 'materials_issued', 'partially_received')
          AND is_deleted = false
    """),
    {"tid": tenant_id},
)
active_subcontracts = result.scalar() or 0

# Materials at subcontractors (total quantity)
result = await self._session.execute(
    text("""
        SELECT COALESCE(SUM(sl.quantity), 0)
        FROM stock_levels sl
        JOIN locations l ON l.id = sl.location_id
        WHERE sl.tenant_id = :tid
          AND l.type = 'subcontractor'
          AND sl.is_deleted = false
          AND l.is_deleted = false
    """),
    {"tid": tenant_id},
)
materials_at_subcontractors = float(result.scalar() or 0)

# Overdue subcontract returns (past due date, not completed)
result = await self._session.execute(
    text("""
        SELECT COUNT(*) FROM subcontract_orders
        WHERE tenant_id = :tid
          AND due_date IS NOT NULL
          AND due_date < :today
          AND status NOT IN ('completed', 'cancelled')
          AND is_deleted = false
    """),
    {"tid": tenant_id, "today": today},
)
overdue_subcontracts = result.scalar() or 0

return ProcurementSummary(
    # ... existing fields ...
    active_subcontracts=active_subcontracts,
    materials_at_subcontractors=materials_at_subcontractors,
    overdue_subcontracts=overdue_subcontracts,
)
```

---

### Step 2: Update Response Schema

**File:** `backend/app/interfaces/api/v1/routes/inventory_transactions.py`

**Update `ProcurementDashboardResponse`:**

```python
class ProcurementDashboardResponse(BaseModel):
    # Existing fields
    pending_requisitions: int
    approved_requisitions: int
    pending_purchase_orders: int = Field(alias="pending_po_approvals")
    supplier_deliveries_next_7_days: int = Field(alias="upcoming_supplier_deliveries")
    overdue_deliveries: int
    grn_pending: int
    material_shortages: int
    
    # NEW fields
    active_subcontracts: int = 0
    materials_at_subcontractors: float = 0.0
    overdue_subcontracts: int = 0

    class Config:
        populate_by_name = True
```

---

### Step 3: Frontend - Add Cards to Dashboard

**File:** `frontend/src/modules/procurement/pages/ProcurementDashboardPage.tsx`

**Add interface fields:**

```typescript
interface ProcurementDashboardData {
  pending_requisitions: number
  pending_po_approvals: number
  upcoming_supplier_deliveries: number
  overdue_deliveries: number
  grn_pending: number
  material_shortages: number
  // NEW
  active_subcontracts: number
  materials_at_subcontractors: number
  overdue_subcontracts: number
}
```

**Add new cards to grid:**

```tsx
{/* Active Subcontract Orders */}
<Card
  className="cursor-pointer hover:shadow-md transition-shadow"
  onClick={() => navigate("/manufacturing/subcontract-orders")}
>
  <CardHeader className="pb-2">
    <CardDescription className="flex items-center gap-2">
      <Boxes className="h-4 w-4 text-purple-500" />
      Active Subcontract Orders
    </CardDescription>
  </CardHeader>
  <CardContent>
    <div className="flex items-center gap-2">
      <p className="text-3xl font-bold text-slate-900">
        {isLoading ? "—" : (data?.active_subcontracts ?? 0)}
      </p>
      {!isLoading && (data?.overdue_subcontracts ?? 0) > 0 && (
        <Badge variant="destructive" className="text-xs">
          {data?.overdue_subcontracts} overdue
        </Badge>
      )}
    </div>
    <p className="mt-1 text-xs text-slate-500">Processing at vendors</p>
  </CardContent>
</Card>

{/* Materials at Subcontractors */}
<Card
  className="cursor-pointer hover:shadow-md transition-shadow"
  onClick={() => navigate("/inventory/materials")}
>
  <CardHeader className="pb-2">
    <CardDescription className="flex items-center gap-2">
      <PackageCheck className="h-4 w-4 text-violet-500" />
      Materials at Subcontractors
    </CardDescription>
  </CardHeader>
  <CardContent>
    <p className="text-3xl font-bold text-slate-900">
      {isLoading ? "—" : `${(data?.materials_at_subcontractors ?? 0).toFixed(0)} KG`}
    </p>
    <p className="mt-1 text-xs text-slate-500">Issued for processing</p>
  </CardContent>
</Card>
```

---

### Step 4: Update Grid Layout

**Current:** 2 columns on mobile, 3 columns on desktop
```
sm:grid-cols-2 lg:grid-cols-3
```

**New:** Extend to 3x3 grid
```
sm:grid-cols-2 lg:grid-cols-3
```

**Card Order (9 total):**
1. Purchase Requisitions
2. Pending PO Approvals
3. Supplier Deliveries
4. GRN Pending
5. Material Shortages
6. Overdue Deliveries
7. **Active Subcontract Orders** ← NEW
8. **Materials at Subcontractors** ← NEW
9. *(Optional: Overdue Subcontracts - or merge with #7)*

---

## VISUAL MOCKUP

### Before (6 cards):
```
┌──────────────────┬──────────────────┬──────────────────┐
│ Requisitions: 3  │ PO Approvals: 5  │ Deliveries: 8    │
├──────────────────┼──────────────────┼──────────────────┤
│ GRN Pending: 2   │ Shortages: 1     │ Overdue: 0       │
└──────────────────┴──────────────────┴──────────────────┘
```

### After (8-9 cards):
```
┌──────────────────┬──────────────────┬──────────────────┐
│ Requisitions: 3  │ PO Approvals: 5  │ Deliveries: 8    │
├──────────────────┼──────────────────┼──────────────────┤
│ GRN Pending: 2   │ Shortages: 1     │ Overdue: 0       │
├──────────────────┼──────────────────┼──────────────────┤
│ Subcontracts: 4  │ Materials Out:   │ (Empty/Future)   │
│ (2 overdue)      │ 150 KG           │                  │
└──────────────────┴──────────────────┴──────────────────┘
```

---

## ALTERNATIVE: SIMPLER VERSION

If you don't want too many cards, **merge into existing cards:**

### Option: Add to "Material Shortages" card
```
┌────────────────────────────────┐
│ Material Shortages             │
│ 1 blocking WOs                 │
│ 150 KG at subcontractors       │ ← ADD THIS LINE
└────────────────────────────────┘
```

**OR** show as tooltip/hover on existing cards.

---

## ESTIMATED EFFORT

**Backend:** 30-60 minutes
- Add 3 SQL queries to KPIQueryService
- Update response schema
- Test endpoint

**Frontend:** 30-60 minutes
- Add interface fields
- Add 2 new cards
- Test responsive layout

**Total:** 1-2 hours

---

## TESTING CHECKLIST

- [ ] Backend endpoint returns subcontract metrics
- [ ] Active subcontracts count is accurate
- [ ] Materials at subcontractors sum is correct
- [ ] Overdue subcontracts count works
- [ ] Frontend displays new cards
- [ ] Cards are clickable and navigate correctly
- [ ] Responsive layout works on mobile
- [ ] Dashboard refreshes correctly
- [ ] Numbers update after subcontract actions

---

## CONCLUSION

**Yes, subcontract orders SHOULD appear on the procurement dashboard** because:
1. They involve external parties (like suppliers)
2. They have due dates and can be overdue
3. They impact material availability
4. Same team likely coordinates both
5. Single view is more useful than scattered information

**Recommendation:** Add 2 new cards to existing procurement dashboard showing active subcontract orders and materials at subcontractors.

**Effort:** ~2 hours total

---

**Want me to implement this?**
