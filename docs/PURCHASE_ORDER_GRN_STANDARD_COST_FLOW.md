# Purchase Order → GRN → Standard Cost Update Flow

## Complete Flow Explanation

### Step 1: Material Creation (Initial Setup)
When you create a material, you can optionally set a `current_cost` (Standard Cost):
- If you **don't provide** a cost → `current_cost = 0.00`
- If you **provide** a cost → `current_cost = [your value]`
- This field is stored in the `materials` table as `current_cost`

**Location in UI**: Inventory → Materials → Add Material → "Current Cost" field

---

### Step 2: Purchase Order Creation
When you create a Purchase Order:
1. Select supplier
2. Add material lines with:
   - Material
   - Quantity
   - **Unit Price** (the price you're purchasing at from this supplier)

**Note**: The PO's unit_price is stored in `purchase_order_lines.unit_price`

**Location in UI**: Procurement → Purchase Orders → New PO

---

### Step 3: PO Acknowledgment/Approval
- PO goes through approval flow: draft → sent → acknowledged
- Status changes are tracked
- **No cost comparison happens here**

---

### Step 4: Goods Receipt (GRN)
When you receive goods against a PO:

#### 4.1 Post Receipt
1. Navigate to: **Procurement → Goods Receipt (GRN)**
2. Select the PO (status: sent, acknowledged, or partial)
3. Select warehouse location
4. Enter quantities to receive for each line
5. Click **"Post receipt"**

#### 4.2 Backend Processing
Backend (via `InventoryService.add_stock`):
- Adds stock to warehouse
- Updates `materials.current_stock`
- Updates `materials.reserved_stock`
- Creates inventory transaction records
- Updates PO status (partial or received)
- **Does NOT automatically update `current_cost`**

#### 4.3 Frontend Cost Comparison (Task 7.2)
After successful GRN, frontend **automatically**:
1. Compares PO line `unit_price` vs Material `current_cost`
2. Identifies differences
3. If differences exist → shows **"Update Standard Cost?"** dialog

**Code Location**: `frontend/src/modules/procurement/pages/GrnPage.tsx` (lines 189-209)

---

### Step 5: Standard Cost Update Dialog

The dialog shows:

```
Update Standard Cost?

The purchase prices on this GRN differ from the current Standard Costs.
Do you want to update the Standard Cost for these materials?

Material | Current Std Cost | New Purchase Price | Difference | Change
---------|------------------|-------------------|------------|-------
raw001   | 0.00            | 100.00            | + 100.00   | —
```

#### Why This Appears:
- **Current Std Cost**: Material's `current_cost` field (0.00 if not set during creation)
- **New Purchase Price**: PO line's `unit_price` (100.00 in your example)
- **Difference**: 100.00 - 0.00 = +100.00

#### Your Options:

##### Option 1: **Ignore**
- Closes the dialog
- GRN is already posted (stock is added)
- Material's `current_cost` remains unchanged (0.00)
- You can manually update cost later via Material master data

##### Option 2: **Update Standard Cost**
- Updates material's `current_cost` to match the purchase price
- Calls: `PUT /inventory/materials/{id}` with `{ current_cost: 100.00 }`
- Future GRNs will compare against this new cost
- Used for calculating:
  - Material valuation
  - Cost of goods sold (COGS)
  - Production costing (BOM cost rollup)

---

## Why Does This Dialog Appear?

### Scenario 1: Material Created Without Cost (Your Case)
```
Step 1: Create material "raw001" → current_cost = 0.00
Step 2: Create PO with unit_price = 100.00
Step 3: Receive goods
Result: Dialog shows → 0.00 vs 100.00 = difference
```

### Scenario 2: Material Has Existing Cost
```
Step 1: Material "raw002" → current_cost = 50.00
Step 2: Create PO with unit_price = 55.00 (price increased)
Step 3: Receive goods
Result: Dialog shows → 50.00 vs 55.00 = +5.00 difference (+10%)
```

### Scenario 3: No Difference
```
Step 1: Material "raw003" → current_cost = 200.00
Step 2: Create PO with unit_price = 200.00
Step 3: Receive goods
Result: No dialog (prices match)
```

---

## Where Does the Price Come From?

| Field | Source | When Set | Purpose |
|-------|--------|----------|---------|
| **Material `current_cost`** | Material master data | Material creation or manual update | Standard/average cost for valuation |
| **PO Line `unit_price`** | Purchase Order creation | When adding PO lines | Negotiated price from supplier |

The system compares these two values to detect:
- ✅ Price increases (supplier raised price)
- ✅ Price decreases (better negotiation)
- ✅ First-time costing (current_cost was 0)

---

## Best Practices

### Option A: Always Update Standard Cost (Simplest)
**Use when**: You want material cost to reflect latest purchase price
- ✅ Click "Update Standard Cost" every time
- ✅ Material valuation stays current
- ✅ Production costing uses real prices

### Option B: Weighted Average Costing
**Use when**: You want to average multiple purchase prices
- Click "Ignore" on the dialog
- Manually calculate weighted average
- Update material cost periodically

### Option C: Manual Cost Control
**Use when**: You have a dedicated costing team
- Click "Ignore" on the dialog
- Finance team reviews and updates costs separately
- Allows for cost approval workflow

---

## After You Choose Ignore or Update

Both options result in the same outcome for the GRN:
- ✅ Stock is added to warehouse
- ✅ PO status is updated
- ✅ Inventory transactions are recorded
- ✅ Material `current_stock` is increased

The **only difference** is whether `current_cost` gets updated.

---

## How to View/Update Material Cost Later

If you clicked "Ignore" and want to update cost later:

1. Navigate to: **Inventory → Materials**
2. Find your material (raw001)
3. Click "Edit"
4. Update **"Current Cost"** field
5. Save

---

## Technical Implementation

### Frontend Code Flow
```typescript
// GrnPage.tsx - After successful GRN

// 1. Build cost diff list
const diffs: CostDiff[] = po.lines
  .filter(l => Number(qtyByLine[l.id] || 0) > 0) // Only received lines
  .filter(l => {
    const mat = materialMap[l.material_id]
    return mat && Number(l.unit_price) !== mat.current_cost // Price differs
  })
  .map(l => ({
    materialId: l.material_id,
    materialName: materialMap[l.material_id]?.name,
    currentCost: materialMap[l.material_id]?.current_cost,
    newPrice: Number(l.unit_price),
    uom: materialMap[l.material_id]?.uom
  }))

// 2. Show prompt only if differences exist
if (diffs.length > 0) {
  setCostDiffs(diffs)
  setShowCostPrompt(true)
}

// 3. Update cost if user confirms
const handleUpdateCost = async () => {
  for (const diff of costDiffs) {
    await materialService.updateMaterial(diff.materialId, { 
      current_cost: diff.newPrice 
    })
  }
}
```

### Backend API
```python
# PUT /inventory/materials/{material_id}
# Updates material.current_cost

# No automatic cost update in InventoryService.add_stock
# Frontend handles the comparison and update
```

---

## Summary

**Your Question**: "When I raise PO, at time of acknowledge it says price differ, but from where? At time of material upload I didn't give price, then where does that differ come from?"

**Answer**: 
1. **Price differ** message appears **during GRN (Goods Receipt)**, not PO acknowledgment
2. The comparison is: **PO unit_price (100.00)** vs **Material current_cost (0.00)**
3. Since you didn't set a cost during material creation → current_cost = 0.00
4. Your PO has unit_price = 100.00
5. Difference = 100.00 - 0.00 = **+100.00 difference**

**What to do**:
- If this is the first purchase → Click **"Update Standard Cost"** to set cost to 100.00
- If you want to control costs manually → Click **"Ignore"** and update later
- Either way, your stock is already received and added to inventory

**Location**: This happens on the **Procurement → Goods Receipt (GRN)** page, right after clicking "Post receipt" button.
