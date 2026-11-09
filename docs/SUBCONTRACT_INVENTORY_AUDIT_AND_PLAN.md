# Subcontract Inventory Flow - Complete Audit & Implementation Plan

## PHASE 1: ARCHITECTURE AUDIT - FINDINGS

### Database Schema Analysis

#### Core Models Identified

**1. SubcontractOrderModel** (`subcontract_orders`)
- Tracks one subcontract order
- Fields: `order_number`, `supplier_id`, `product_id` (output), `quantity`, `status`, `received_quantity`
- Status flow: draft → approved → materials_issued → partially_received → completed | cancelled
- Relationships: `lines` (components), `issues` (material issues)

**2. SubcontractOrderLineModel** (`subcontract_order_lines`)
- BOM snapshot - required components per order
- Fields: `material_id`, `required_quantity`, `issued_quantity`, `returned_quantity`
- ✅ **TRACKS ISSUED VS RETURNED SEPARATELY**
- ✅ **NO "CONSUMED" FIELD - THIS IS THE GAP**

**3. SubcontractMaterialIssueModel** (`subcontract_material_issues`)
- One row per material issue transaction
- Fields: `material_id`, `quantity`, `returned_quantity`, `batch_id`, `from_location_id`
- ✅ **TRACKS ISSUED VS RETURNED**
- ❌ **NO CONSUMED FIELD**

**4. StockLevelModel** (`stock_levels`)
- Location-based inventory buckets
- Unique key: `(tenant_id, material_id, location_id, stock_status)`
- Fields: `quantity`, `stock_status` (available/pending_inspection/quarantine)
- ✅ **SUPPORTS LOCATION-BASED STOCK**

**5. LocationModel** (`locations`)
- Fields: `name`, `code`, `type`, `parent_location_id`
- Types include: warehouse, rack, bin, quarantine, **subcontractor**
- ✅ **SUBCONTRACTOR IS A LOCATION TYPE**

**6. InventoryTransactionModel** (`inventory_transactions`)
- Transaction log: in/out/transfer/adjustment
- Fields: `transaction_type`, `quantity`, `from_location_id`, `to_location_id`, `reference_type`, `reference_id`
- ✅ **PROVIDES FULL AUDIT TRAIL**

**7. MaterialModel** (`materials`)
- Fields: `current_stock`, `reserved_stock`, `reorder_level`
- ✅ **current_stock** = Sum of all stock_levels (all locations)
- ❌ **NO FIELD FOR WAREHOUSE-ONLY STOCK**

---

## CRITICAL FINDINGS

### ✅ What EXISTS and WORKS:

1. **Location-based inventory** - `stock_levels` table supports stock by location
2. **Subcontractor locations** - Vendors have location_type = 'subcontractor'
3. **Issue tracking** - `SubcontractMaterialIssueModel` tracks issued quantities
4. **Return tracking** - `returned_quantity` field exists on issues and lines
5. **Transfer transactions** - Issue creates transfer from warehouse → subcontractor
6. **Audit trail** - `inventory_transactions` logs all movements

### ❌ What is MISSING:

1. **Consumption tracking** - NO field/table to distinguish issued vs consumed
2. **Consumption transactions** - Issue logs "transfer", but no "consumption" event
3. **UI for stock-by-location** - Material detail doesn't show location breakdown
4. **Vendor name in location display** - Stock shows "subcontractor" not vendor name
5. **Subcontractor stock indicator** - No clear "With Vendors: X" summary
6. **BOM-based consumption calculation** - Currently consumes ALL issued (wrong!)

---

## PHASE 2: EXISTING AUTO-CONSUMPTION AUDIT

### Current Implementation (Added in previous session)

**Location:** `backend/app/application/manufacturing/services/inventory_service.py`

```python
async def consume_subcontract_raw_materials(
    subcontract_order_id,
    subcontractor_location_id,
    consumption_ratio=None  # Optional yield calculation
):
    # Get all issued materials
    issues = get_all_issues_for_order()
    
    for issue in issues:
        qty_to_consume = issue.quantity  # PROBLEM: Uses issued qty!
        if consumption_ratio:
            qty_to_consume *= consumption_ratio
        
        # Deduct from subcontractor location
        _deduct_from_location(subcontractor_location_id, qty_to_consume)
        
        # Sync material totals
        _sync_material_total_from_buckets()
        
        # Log transaction
        _log_transaction(type="out", from_location=subcontractor)
```

**Integrated in:** `backend/app/interfaces/api/v1/routes/supply_chain.py` → `receive_subcontract()`

```python
if new_received >= order.quantity:
    status = "completed"
    # Auto-consume ALL issued materials
    await consume_subcontract_raw_materials(...)
```

### Problems with Current Implementation:

1. ❌ **Consumes 100% of issued quantity** regardless of actual consumption
2. ❌ **Ignores BOM quantity** - doesn't calculate based on output received
3. ❌ **Ignores returned materials** - consumes even if material was returned
4. ❌ **Triggers only on completion** - partial receipts don't consume proportionally
5. ❌ **No idempotency check** - could consume twice on retry
6. ❌ **No validation** - consumes even if stock doesn't exist at subcontractor
7. ❌ **consumption_ratio parameter is unused** (always None in current integration)

### What It Does Right:

1. ✅ Deducts from subcontractor location (not warehouse)
2. ✅ Updates material.current_stock via sync
3. ✅ Logs transaction with type="out"
4. ✅ Links to subcontract_order via reference_type/reference_id

---

## PHASE 3: CORRECT DOMAIN MODEL

### The Five Concepts (Must Be Distinguished):

```
1. REQUIRED (BOM)
   - From subcontract_order_lines.required_quantity
   - Based on BOM snapshot

2. ISSUED
   - From subcontract_material_issues.quantity
   - Warehouse → Subcontractor location transfer
   - Transaction: type="transfer"

3. CONSUMED
   - NOT TRACKED YET!
   - Should be calculated from: output_qty * bom_unit_qty
   - Transaction: type="out" from subcontractor
   
4. RETURNED
   - From subcontract_material_issues.returned_quantity
   - Subcontractor → Warehouse transfer
   - Transaction: type="transfer"

5. REMAINING
   - Calculated: issued - consumed - returned
   - Still at subcontractor location
```

### Example Flow:

```
BOM: SF-001 requires 10 KG RM-001 per unit

Order: 10 SF-001
Required: 100 KG RM-001

Issue: 100 KG → Subcontractor

Vendor produces: 9 SF-001 (90% yield)
Consumed: 90 KG (9 * 10)
Remaining at vendor: 10 KG

Return: 8 KG → Warehouse
Final vendor stock: 2 KG (waste/scrap)

Stock breakdown:
- Warehouse: +8 KG (returned)
- Subcontractor: 2 KG (remaining)
- Consumed: 90 KG (used in production)
- Total company stock: 10 KG (8 + 2)
```

---

## PHASE 4: IMPLEMENTATION PLAN

### Option A: Add Consumption Tracking (Recommended)

**Database Changes:**
```sql
-- NO NEW TABLES NEEDED!
-- Use existing subcontract_order_lines to add consumed_quantity

ALTER TABLE subcontract_order_lines
ADD COLUMN consumed_quantity NUMERIC(15,3) DEFAULT 0 NOT NULL;
```

**Logic Changes:**
1. Calculate consumption: `output_received * bom_unit_requirement`
2. Store in `consumed_quantity` field
3. Update on each receipt (proportional for partial)
4. Prevent over-consumption (can't exceed issued - returned)

**Remaining Calculation:**
```python
remaining = issued_quantity - consumed_quantity - returned_quantity
```

### Option B: Calculate Consumption On-The-Fly (Current Approach - Needs Fix)

**No DB changes, but fix the calculation:**

```python
async def consume_subcontract_raw_materials(...):
    # Get order to find BOM relationship
    order = get_subcontract_order()
    
    # For each order line (component)
    for line in order.lines:
        # Calculate consumption based on output received
        bom_unit_qty = line.required_quantity / order.quantity
        consumed = order.received_quantity * bom_unit_qty
        
        # Deduct only consumed amount (not full issued!)
        # But check: already_consumed = previous consumptions
        # Only consume: consumed - already_consumed
        
        # This requires tracking previous consumptions somehow...
```

**Problem:** Without a consumed_quantity field, we can't track what was already consumed on previous partial receipts!

---

## RECOMMENDATION: Option A (Add consumed_quantity field)

### Why:

1. **Explicit is better than calculated** - prevents errors
2. **Supports partial receipts** - track consumption incrementally
3. **Supports manual adjustments** - if needed for scrap/corrections
4. **Audit trail** - clear history of what was consumed when
5. **Performance** - no need to recalculate from transactions
6. **Matches existing pattern** - issued_quantity and returned_quantity already exist

---

## PHASE 5: UI REQUIREMENTS

### Material Detail Page Enhancement

**Add "Stock by Location" Section:**

```
RM-001 — Raw Steel Sheet

┌─────────────────────────────────────────────────┐
│ Stock Summary                                   │
├─────────────────────────────────────────────────┤
│ Total Company Stock:        100 KG              │
│ Available in Warehouse:      20 KG              │
│ With Subcontractors:         80 KG              │
│ Reserved:                     0 KG              │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Stock by Location                               │
├─────────────────────────────────────────────────┤
│ 📦 Main Warehouse                               │
│    20 KG (Available)                            │
│                                                 │
│ 🏭 ABC Engineering Pvt Ltd                      │
│    50 KG (Subcontractor Stock)                  │
│    📋 SCO-001 | Issued: 29 Sep                  │
│                                                 │
│ 🏭 XYZ Fabrication Pvt Ltd                      │
│    30 KG (Subcontractor Stock)                  │
│    📋 SCO-002 | Issued: 28 Sep                  │
└─────────────────────────────────────────────────┘
```

### Material Catalog Enhancement

**Add vendor stock indicator:**

```
Material List:
RM-001  | 100 KG | ⚠️ 80 KG with vendors
RM-002  | 50 KG  | ✓ All in warehouse
```

---

## PHASE 6: IMPLEMENTATION SEQUENCE

### Step 1: Database Migration (1 column)

```python
# alembic/versions/add_consumed_quantity_to_subcontract_lines.py

def upgrade():
    op.add_column(
        'subcontract_order_lines',
        sa.Column('consumed_quantity', sa.Numeric(15, 3), nullable=False, server_default='0')
    )

def downgrade():
    op.drop_column('subcontract_order_lines', 'consumed_quantity')
```

### Step 2: Refactor consume_subcontract_raw_materials()

**Key changes:**
1. Calculate consumption per BOM line (output * unit_requirement)
2. Check already_consumed to prevent double consumption
3. Only consume incremental amount
4. Update consumed_quantity field
5. Handle partial receipts correctly

### Step 3: Add Backend API for Stock-by-Location

```python
# GET /api/v1/inventory/materials/{material_id}/stock-by-location
{
  "material_id": "...",
  "total_stock": 100,
  "locations": [
    {
      "location_id": "...",
      "location_name": "Main Warehouse",
      "location_type": "warehouse",
      "quantity": 20,
      "stock_status": "available"
    },
    {
      "location_id": "...",
      "location_name": "ABC Engineering Pvt Ltd",
      "location_type": "subcontractor",
      "quantity": 50,
      "stock_status": "available",
      "supplier_id": "...",
      "subcontract_orders": [
        {
          "order_id": "...",
          "order_number": "SCO-001",
          "issued_date": "2026-09-29"
        }
      ]
    }
  ]
}
```

### Step 4: Create Material Detail UI Component

**Component:** `MaterialStockLocationView.tsx`

Shows:
- Stock summary (total, warehouse, subcontractor)
- Location breakdown with vendor names
- Subcontract order links for traceability

### Step 5: Integrate into Material Pages

- Material List: Add vendor stock indicator
- Material Detail: Add stock-by-location section

### Step 6: Testing

Test all scenarios from Phase 17 of requirements.

---

## PHASE 7: ACCEPTANCE CRITERIA CHECKLIST

Based on requirements section 18:

- [ ] Material stock viewable by location ← UI enhancement
- [ ] Vendor/subcontractor name visible ← Join supplier table
- [ ] Vendor stock distinguished from warehouse ← Stock summary
- [ ] Issue transfers stock to vendor ← ALREADY WORKS
- [ ] Issue doesn't consume material ← ALREADY CORRECT
- [ ] Consumption removes from vendor stock ← FIX CALCULATION
- [ ] Receipt creates semi-finished stock ← ALREADY WORKS
- [ ] Returned material goes to warehouse ← ALREADY WORKS
- [ ] Remaining vendor stock visible ← UI + CALCULATION
- [ ] Total stock not double counted ← ALREADY CORRECT
- [ ] Transactions auditable ← ALREADY WORKS
- [ ] Subcontract traceability preserved ← ADD TO UI
- [ ] BOM snapshot unchanged ← NO CHANGES TO BOM
- [ ] Semi-finished BOM flow unchanged ← NO CHANGES
- [ ] Existing APIs reused ← REUSE stock_levels, transactions
- [ ] No unnecessary migration ← ONLY 1 COLUMN
- [ ] Regression testing passes ← RUN TESTS
- [ ] Mobile UX works ← RESPONSIVE DESIGN
- [ ] UI explains vendor stock ← CLEAR INDICATORS

---

## SUMMARY

### Existing Architecture is 90% Correct!

**What Works:**
- ✅ Location-based inventory (stock_levels)
- ✅ Subcontractor locations exist
- ✅ Issue/return tracking
- ✅ Transaction audit trail
- ✅ Transfer semantics (issue ≠ consumption)

**What Needs Fixing:**
- ❌ Consumption calculation (currently consumes ALL, should be BOM-based)
- ❌ Consumption tracking (add consumed_quantity field)
- ❌ UI doesn't show stock by location
- ❌ UI doesn't show vendor names

**Implementation Effort:**
- **Backend:** 1 migration + refactor 1 method + 1 new API endpoint
- **Frontend:** 2 new components + enhance 2 existing pages
- **Risk:** LOW (additive changes, existing flow preserved)

**Next Action:** Proceed with Step 1 (database migration) after approval.
