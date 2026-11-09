# Subcontract Issue - Stock Visibility Issue

## The Problem You're Experiencing

**What You See:** After issuing 50 units of raw material to subcontractor, the material's stock still shows 100 units (unchanged).

**Why This Happens:** The system is showing **total company stock** (warehouse + subcontractor), not **warehouse stock only**.

---

## Technical Explanation

### What Actually Happens During Issue

#### Backend Flow (`issue_to_subcontractor`)

```python
# Step 1: Deduct from warehouse stock_level
await self._deduct_available_internal(tenant_id, material_id, 50)
# Result: warehouse stock_level = 100 → 50

# Step 2: Add to subcontractor stock_level  
await self._add_bucket_quantity(
    location_id=subcontractor_location_id,
    quantity=50
)
# Result: subcontractor stock_level = 0 → 50

# Step 3: Sync material total
await self._sync_material_total_from_buckets(material)
# Sums ALL stock_levels (warehouse + subcontractor)
# material.current_stock = 50 + 50 = 100 (unchanged!)
```

### The Database State

**Before Issue:**
```sql
-- materials table
material_id | current_stock
------------|---------------
material-1  | 100

-- stock_levels table
location         | quantity
-----------------|----------
Warehouse        | 100
Subcontractor    | 0
```

**After Issue (50 units):**
```sql
-- materials table  
material_id | current_stock
------------|---------------
material-1  | 100  ← UNCHANGED (total still 100)

-- stock_levels table
location         | quantity
-----------------|----------
Warehouse        | 50   ← DECREASED
Subcontractor    | 50   ← INCREASED
```

---

## Why Was It Designed This Way?

### Accounting Principle: Transfer vs Consumption

From an **accounting/inventory valuation** perspective:
- ✅ Material is still owned by your company
- ✅ Just moved from one location to another
- ✅ Total inventory value unchanged
- ✅ Not consumed yet (vendor may return unused)

This is the **correct** behavior for:
- Financial reporting
- Inventory valuation
- Balance sheets

---

## Why Users Get Confused

### What Users Expect

**Warehouse Manager's Perspective:**
- "I issued 50 units out of my warehouse"
- "My warehouse stock should show 50, not 100"
- "The material list should show my warehouse stock"

### What System Shows

**Material List Page:**
- Shows `material.current_stock` = **100** (total)
- Doesn't show location breakdown
- Users see "100" and think nothing changed

---

## The Real Issue: Missing Stock-by-Location View

The problem is **NOT with the backend logic** (it's correct).

The problem is **the UI doesn't show stock by location**:

1. ❌ Material list shows total `current_stock` (all locations)
2. ❌ No material detail page showing stock breakdown by location
3. ❌ No way to see "Warehouse: 50 | Subcontractor: 50"

---

## Solutions

### Solution 1: Add Stock-by-Location Column (Quick Fix)

Modify Material List Page to show:
```
Material    | Warehouse Stock | Subcontractor | Total
------------|-----------------|---------------|-------
RM-001      | 50             | 50            | 100
```

### Solution 2: Material Detail Page with Location Breakdown (Better)

Create a material detail view showing:
```
Material: RM-STEEL-001
Total Stock: 100 units

Stock by Location:
┌────────────────────┬──────────┬────────────┐
│ Location           │ Quantity │ Status     │
├────────────────────┼──────────┼────────────┤
│ Main Warehouse     │ 50       │ Available  │
│ ABC Subcontractor  │ 50       │ Available  │
└────────────────────┴──────────┴────────────┘
```

### Solution 3: Add "Warehouse Stock" to Material Model (Alternative)

Add a computed field:
```python
class MaterialModel:
    current_stock: float  # All locations
    
    @property
    async def warehouse_stock(self) -> float:
        """Stock in internal warehouses only"""
        return sum(stock_levels 
                  where location.type in ['warehouse', 'zone', 'rack', 'bin']
                  and status = 'available')
```

Then show both in UI:
```
Material    | Warehouse | Total
------------|-----------|-------
RM-001      | 50        | 100
```

---

## How to Verify Stock Was Actually Deducted

### Method 1: Check Inventory Transactions

Navigate to: **Inventory → Transactions**

Filter by:
- Material: Your issued material
- Type: Transfer
- Reference: Subcontract Order

You should see:
```
Type: Transfer
From: Main Warehouse → ABC Subcontractor  
Quantity: 50
```

### Method 2: Query Database Directly

```python
# Run debug_subcontract_issue.py
python debug_subcontract_issue.py <order_id>

# Shows:
# Stock Levels by Location:
# Location                  Type         Status      Quantity
# ----------------------------------------------------------------
# Main Warehouse           warehouse    available      50.000
# ABC Subcontractor        subcontractor available     50.000
```

### Method 3: Check Realtime Stock API

```bash
curl http://localhost:5000/api/v1/inventory/realtime
```

Look for stock breakdown - it will show total across all locations.

---

## Current Workaround for Users

Until UI is enhanced:

### To See Actual Warehouse Stock:

1. **Navigate to Inventory Dashboard**
   - Shows stock by location (if implemented)

2. **Check Transaction History**
   - Inventory → Transactions
   - Filter by material
   - See transfer records

3. **Use Realtime Stock View**
   - Shows per-location breakdown

4. **Query via API**
   ```bash
   # Get stock levels for a material
   GET /api/v1/inventory/materials/{material_id}/stock-levels
   ```

---

## Recommendation

### Immediate Fix (High Priority)

Add a **"Stock by Location"** tab or section to Material List or a new Material Detail page:

**Material Detail Page:**
```
┌─────────────────────────────────────────────────────────┐
│ Material: RM-STEEL-001                                  │
│ Total Stock: 100 units                                  │
├─────────────────────────────────────────────────────────┤
│ Stock Breakdown:                                        │
│                                                         │
│ Main Warehouse                         50 units        │
│ ABC Subcontractor                      50 units        │
│ XYZ Subcontractor                       0 units        │
├─────────────────────────────────────────────────────────┤
│ Reserved Stock: 0                                       │
│ Available: 100                                          │
└─────────────────────────────────────────────────────────┘
```

This makes it **crystal clear** that:
- ✅ Total stock is 100 (accounting)
- ✅ Warehouse stock is 50 (warehouse manager view)
- ✅ Subcontractor has 50 (in transit)

---

## Summary

### Your Observation: ✅ CORRECT
**"Stock is not deducting from inventory"** - You're correct from a warehouse manager's perspective!

### System Behavior: ✅ ALSO CORRECT  
**Material.current_stock stays at 100** - Correct from an accounting perspective!

### The Gap: UI DOESN'T SHOW LOCATION BREAKDOWN
- Backend is working correctly (stock moved from warehouse to subcontractor)
- UI only shows total stock (all locations combined)
- Users can't see the warehouse vs subcontractor breakdown

### Solution:
Add a Material Detail page or enhance Material List to show stock by location.

---

## Test Query to Verify

Run this to see the actual stock breakdown:

```sql
SELECT 
    m.code AS material_code,
    m.name AS material_name,
    m.current_stock AS total_stock,
    l.name AS location_name,
    l.type AS location_type,
    sl.quantity AS location_stock,
    sl.stock_status
FROM materials m
LEFT JOIN stock_levels sl ON sl.material_id = m.id
LEFT JOIN locations l ON l.id = sl.location_id  
WHERE m.code = 'RM-YOUR-MATERIAL'
  AND sl.is_deleted = false
  AND sl.quantity > 0
ORDER BY l.name;
```

You'll see:
```
material_code | total_stock | location_name     | location_stock
--------------|-------------|-------------------|----------------
RM-001        | 100         | Main Warehouse    | 50
RM-001        | 100         | ABC Subcontractor | 50
```

This proves the stock WAS deducted from warehouse and added to subcontractor! 🎯
