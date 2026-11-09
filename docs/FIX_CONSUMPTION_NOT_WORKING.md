# Fix: Raw Material Not Being Consumed After Receipt

## The Problem

**Symptom:** 
- You received semi-finished product (GRN done)
- Stock Locations tab still shows raw material at subcontractor
- Raw material quantity NOT deducted from total

**Example:**
```
Before Receipt:
- Raw Material: 100 at subcontractor

After Receipt (expected):
- Raw Material: Should be 0 (consumed)
- Semi-Finished: Received quantity

After Receipt (actual - WRONG):
- Raw Material: Still 100 at subcontractor ❌
- Semi-Finished: Received quantity ✓
```

---

## Root Cause

**The backend server is not using the updated code!**

The consumption logic was added/fixed in the code, but the backend server needs to be restarted to load the changes.

---

## Solution: Restart Backend

### Step 1: Stop Backend
```bash
# Press Ctrl+C in the terminal running the backend
# Or kill the process
```

### Step 2: Verify Column Exists
```bash
# Connect to database
psql -U postgres -d medtrack

# Check column
SELECT column_name 
FROM information_schema.columns 
WHERE table_name='subcontract_order_lines' 
AND column_name='consumed_quantity';

# Should return:
#  column_name
# ------------------
#  consumed_quantity
```

If column doesn't exist:
```sql
ALTER TABLE subcontract_order_lines
ADD COLUMN consumed_quantity NUMERIC(15,3) NOT NULL DEFAULT 0;
```

### Step 3: Start Backend
```bash
cd backend
python -m app.main

# Or however you normally start it:
# uvicorn app.main:app --reload
```

### Step 4: Test with New Receipt

**IMPORTANT:** The fix only works for NEW receipts after restart!

1. Create a new subcontract order
2. Issue materials
3. **Restart backend** ✓
4. Receive output
5. Check Stock Locations → Raw material should decrease

---

## Verify Backend is Using New Code

### Method 1: Check Logs
When you receive output, look for in backend logs:
```
INFO: Consuming raw materials for subcontract order...
```

### Method 2: Check Database
After receiving, check:
```sql
SELECT 
    order_number,
    status,
    received_quantity,
    consumed_quantity
FROM subcontract_order_lines l
JOIN subcontract_orders o ON o.id = l.subcontract_order_id
WHERE o.order_number = 'YOUR_ORDER_NUMBER';
```

`consumed_quantity` should be > 0 after receipt.

### Method 3: Check API Response
Add console.log in frontend receive function to see response.

---

## For Existing Orders (Already Received)

**Bad News:** Consumption won't happen retroactively for orders received before the backend was restarted.

**Options:**

### Option A: Manual Fix (SQL)
```sql
-- Calculate and set consumed_quantity manually
UPDATE subcontract_order_lines l
SET consumed_quantity = (
    SELECT o.received_quantity * (l.required_quantity / o.quantity)
    FROM subcontract_orders o
    WHERE o.id = l.subcontract_order_id
)
WHERE l.subcontract_order_id = 'YOUR_ORDER_ID';

-- Then manually deduct from subcontractor location
-- (Complex - not recommended)
```

### Option B: Return & Re-receive
1. Return the semi-finished material (if possible)
2. "Undo" the receipt
3. Re-issue materials if needed
4. **Restart backend**
5. Receive again (consumption will happen)

### Option C: Accept Historical Data
- Leave old orders as-is
- Only NEW receipts (after restart) will consume correctly
- Add note that stock locations are inaccurate for old orders

**Recommendation:** Option C (accept historical data, fix going forward)

---

## How to Test It's Working

### Test Flow:
```
1. Restart Backend ✓

2. Create new subcontract order
   - Output: 10 units
   - BOM: 10 KG per unit
   
3. Issue materials
   - Issue: 100 KG
   - Check Stock Locations: "100 with vendor" ✓
   
4. Receive output (5 units)
   - Expected consumption: 5 × 10 = 50 KG
   
5. Check Stock Locations
   - Vendor should show: 50 KG (not 100!) ✓
   - Total should be: 50 KG (decreased!) ✓
   
6. Receive remaining (5 units)
   - Expected consumption: 5 × 10 = 50 KG
   
7. Check Stock Locations
   - Vendor should show: 0 KG ✓
   - Total should be: 0 KG ✓
```

### If Still Not Working:

Check backend code is actually updated:
```bash
# In backend/app/interfaces/api/v1/routes/supply_chain.py
# Should see around line 2580:

await inv.consume_subcontract_raw_materials(
    receipt_quantity=Decimal(str(body.quantity)),
)

# Should NOT be commented out!
```

---

## Common Mistakes

### ❌ Forgot to restart backend
Solution: Always restart after code changes

### ❌ Database column missing
Solution: Run the ALTER TABLE command

### ❌ Expecting old receipts to work
Solution: Only NEW receipts after restart will work

### ❌ Backend code not saved
Solution: Check git status, ensure files saved

### ❌ Wrong environment
Solution: Make sure development DB matches where you added column

---

## Quick Diagnostic Commands

### Check consumed_quantity
```sql
SELECT 
    o.order_number,
    l.issued_quantity,
    l.consumed_quantity,
    l.returned_quantity,
    (l.issued_quantity - l.consumed_quantity - l.returned_quantity) as remaining
FROM subcontract_order_lines l
JOIN subcontract_orders o ON o.id = l.subcontract_order_id
WHERE o.status IN ('partially_received', 'completed')
ORDER BY o.created_at DESC
LIMIT 5;
```

### Check subcontractor stock
```sql
SELECT 
    m.code,
    l.name as vendor_location,
    sl.quantity as vendor_stock
FROM stock_levels sl
JOIN materials m ON m.id = sl.material_id
JOIN locations l ON l.id = sl.location_id
WHERE l.type = 'subcontractor'
AND sl.quantity > 0;
```

### Check inventory transactions
```sql
SELECT 
    created_at,
    transaction_type,
    quantity,
    remarks
FROM inventory_transactions
WHERE reference_type = 'subcontract_order'
AND transaction_type = 'out'
ORDER BY created_at DESC
LIMIT 10;
```

If you see transactions with `type='out'` and `remarks` containing "Consumed in subcontract processing", then it's working!

---

## Summary

**Problem:** Backend not restarted, so new consumption logic not active

**Solution:**
1. ✅ Restart backend
2. ✅ Verify column exists
3. ✅ Test with NEW receipt
4. ✅ Check Stock Locations shows decreased quantity

**For old orders:** Accept historical inaccuracy or manually fix (complex)

**For new orders:** Will work correctly after restart! 🎯

---

## Still Not Working?

If after restart it STILL doesn't work:

1. Check backend logs for errors
2. Verify `consume_subcontract_raw_materials` is NOT commented out
3. Run SQL query: `check_consumption.sql`
4. Check `consumed_quantity` field is actually being updated
5. Report the specific error message
