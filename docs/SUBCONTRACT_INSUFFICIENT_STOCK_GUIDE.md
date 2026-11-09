# Subcontract Order - Insufficient Stock Error Guide

## Error Message

When trying to issue material to a subcontractor, you see:

```
Insufficient stock. Short by X units. 
Please check stock availability in the selected warehouse 
or choose a different warehouse.
```

---

## What This Means

The inventory system checks for **available stock in internal locations** (warehouses) before allowing material to be issued to a subcontractor.

The error means:
- ❌ The selected warehouse does not have enough stock with "available" status
- ❌ The material might exist but is in a different location type (subcontractor, customer, transit, etc.)
- ❌ The material might have a different status (reserved, quarantine, damaged, etc.)

---

## Stock Requirements

For a material to be issuable to a subcontractor, it must:

1. ✅ Exist in an **internal location** type:
   - `warehouse`
   - `zone`
   - `rack`
   - `bin`
   - `production`

2. ✅ Have stock status = **"available"**

3. ✅ Not be deleted or inactive

---

## Troubleshooting Steps

### Step 1: Check What Stock Exists

Run the debug script to see actual stock levels:

```bash
python debug_subcontract_stock.py <order_id>
```

Example:
```bash
python debug_subcontract_stock.py 4412fe8e-b123-4b2f-a766-b2d15db2c89e
```

This will show you:
- All materials required by the subcontract order
- Where stock exists (all locations)
- Which stock is **usable** (✓) and which is **not usable** (✗)
- Total available stock per material

---

### Step 2: Understand the Output

```
Component 1: Material 55c87cf5-af2f-4204-a575-2a1e8523e075
  Required: 1.000
  Issued: 0.000
  Remaining: 1.0

  Stock Levels (2 locations):
    ✓ Raw Materials Warehouse (warehouse)
       Status: available, Qty: 5.0
    
    ✗ Vendor Location (subcontractor)
       Status: available, Qty: 10.0

  📊 Total Available (Internal Locations): 5.0
  📊 Remaining to Issue: 1.0
  ✅ SUFFICIENT STOCK
```

**Explanation:**
- ✓ = Can be issued (warehouse location + available status)
- ✗ = Cannot be issued (subcontractor location, even if available)
- Only the 5.0 units in "Raw Materials Warehouse" count
- The 10.0 units at "Vendor Location" don't count (wrong location type)

---

### Step 3: Common Scenarios

#### Scenario A: No Stock Exists

```
❌ NO STOCK FOUND for this material!
```

**Solution:**
1. Create a purchase order for this material
2. Receive the material into a warehouse
3. Then try issuing to subcontractor

---

#### Scenario B: Stock Exists in Wrong Location

```
Stock Levels:
  ✗ Customer Site (customer)
     Status: available, Qty: 10.0
  
  ✗ Transit Location (transit)
     Status: available, Qty: 5.0

📊 Total Available (Internal Locations): 0
```

**Solution:**
1. Transfer material from customer/transit to a warehouse
2. Use inventory transfer transactions
3. Then try issuing to subcontractor

---

#### Scenario C: Stock Has Wrong Status

```
Stock Levels:
  ✗ Raw Materials Warehouse (warehouse)
     Status: reserved, Qty: 10.0
  
  ✗ Raw Materials Warehouse (warehouse)
     Status: quarantine, Qty: 5.0

📊 Total Available (Internal Locations): 0
```

**Solution:**
- **Reserved stock:** Release the reservation or use different stock
- **Quarantine stock:** Complete QC inspection to make it available
- **Damaged stock:** Cannot be used, need to receive new stock

---

#### Scenario D: Stock in Multiple Warehouses

```
Stock Levels:
  ✓ Warehouse A (warehouse)
     Status: available, Qty: 3.0
  
  ✓ Warehouse B (warehouse)
     Status: available, Qty: 7.0

📊 Total Available (Internal Locations): 10.0
📊 Remaining to Issue: 5.0
✅ SUFFICIENT STOCK
```

**Solution:**
- Select either Warehouse A or Warehouse B in the issue dialog
- System will deduct from the selected warehouse
- If selecting Warehouse A, you can only issue up to 3 units
- For 5 units, select Warehouse B (has 7 available)

---

## Next Steps After Checking Stock

### If Stock is Sufficient

1. Make sure you're selecting the correct warehouse in the issue dialog
2. Try issuing again

### If Stock is Missing

**Option 1: Purchase Material**
1. Go to Procurement → Purchase Orders
2. Create PO for the missing material
3. Receive the material into a warehouse
4. Then issue to subcontractor

**Option 2: Transfer from Another Location**
1. Go to Inventory → Stock Transfers
2. Transfer material from customer/transit/production to warehouse
3. Then issue to subcontractor

**Option 3: Change Subcontract Order**
1. If material is permanently unavailable
2. Cancel this subcontract order
3. Create a new order with available materials

---

## Technical Notes

### Why This Check Exists

The inventory system enforces strict stock tracking:
- **Prevents over-issuing:** Can't send what you don't have
- **Maintains accuracy:** Stock levels always match physical reality
- **Audit trail:** Every transfer is logged
- **Prevents errors:** Catches problems before they reach the vendor

### What "Available" Means

```
Stock Status Values:
- available   ← ✅ Can be issued
- reserved    ← ❌ Allocated to sales/work orders
- quarantine  ← ❌ Awaiting QC approval
- damaged     ← ❌ Not usable
- in_transit  ← ❌ Moving between locations
```

### What "Internal Location" Means

```
Location Types:
✅ warehouse    ← Your storage
✅ zone         ← Warehouse zone
✅ rack         ← Storage rack
✅ bin          ← Storage bin
✅ production   ← Production floor

❌ subcontractor  ← Already at vendor
❌ customer       ← At customer site
❌ transit        ← In transit
❌ supplier       ← At supplier
```

---

## Prevention

### To Avoid This Error in Future

1. **Check stock before creating subcontract order:**
   - Review BOM components
   - Verify available stock for each component
   - Create POs for missing materials first

2. **Maintain minimum stock levels:**
   - Set reorder levels for common raw materials
   - Create POs automatically when stock is low

3. **Regular stock audits:**
   - Reconcile physical stock with system
   - Fix discrepancies immediately

4. **Proper stock status management:**
   - Complete QC inspections promptly
   - Release reservations when not needed
   - Mark damaged stock correctly

---

## Quick Reference

| Error | Cause | Solution |
|-------|-------|----------|
| "1 short" | Need 1, have 0 | Purchase or transfer material |
| "5 short" | Need 10, have 5 | Purchase 5 more or issue partial (5) |
| "✗ subcontractor location" | Stock at vendor, not warehouse | Can't use (already issued) |
| "✗ reserved status" | Stock allocated elsewhere | Release reservation or use other stock |
| "❌ NO STOCK FOUND" | No stock anywhere | Purchase material |

---

## Example Workflow

### Good Workflow ✅

```
1. Create subcontract order
2. Run: python debug_subcontract_stock.py <order_id>
3. See: "✅ SUFFICIENT STOCK" for all components
4. Approve order
5. Issue materials (works!)
6. Materials sent to vendor
```

### Bad Workflow ❌

```
1. Create subcontract order
2. Approve order immediately
3. Try to issue materials
4. Error: "Insufficient stock"
5. Now must create PO and wait for delivery
6. Vendor is waiting, production delayed
```

---

## Database Query (For Advanced Users)

Check stock directly:

```sql
SELECT 
    m.code as material_code,
    m.name as material_name,
    l.name as location,
    l.type as location_type,
    sl.stock_status,
    sl.quantity
FROM stock_levels sl
JOIN materials m ON m.id = sl.material_id
JOIN locations l ON l.id = sl.location_id
WHERE sl.material_id = '<material_id>'
  AND sl.is_deleted = false
  AND l.is_deleted = false
  AND sl.quantity > 0
ORDER BY l.type, l.name;
```

---

**Created:** September 26, 2026  
**For:** MedTrack ERP Subcontracting Module  
**Debug Script:** `debug_subcontract_stock.py`

