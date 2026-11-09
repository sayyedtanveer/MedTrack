# Subcontract Inventory - Quick Start Guide

## For Users

### How to View Stock by Location

1. **Navigate to Inventory → Materials**
2. **Click on any material** to open details
3. **Click "Stock Locations" tab**
4. **View breakdown:**
   - Total stock
   - Warehouse stock (green)
   - Subcontractor stock (amber)
   - Detailed location list

### What the Numbers Mean

**Total Stock:** All material owned by your company (all locations combined)

**Warehouse Stock:** Material available in your warehouses (ready to use)

**Subcontractor Stock:** Material currently with vendors for processing

**Available:** Total minus reserved (can be issued/sold)

### Warning: Stock with Subcontractors

If you see an amber warning "X units with subcontractors":
- ⚠️ These materials are NOT in your warehouse
- ⚠️ They have been sent to vendors for processing
- ⚠️ They will be consumed to create the output product
- ✅ You can see which vendor has them
- ✅ You can click the order number to see details

---

## For Developers

### Backend API

**Get stock by location:**
```bash
GET /api/v1/inventory/materials/{material_id}/stock-by-location
```

**Response includes:**
- Total, warehouse, subcontractor stock summary
- Location array with vendor names
- Subcontract order links

### Database

**New field:**
```sql
subcontract_order_lines.consumed_quantity
```

**Tracks:** Cumulative consumption across all receipts

**Formula:** `output_received × (bom_requirement / order_quantity)`

### Consumption Flow

```python
# Called on each receipt (partial or complete)
await inventory_service.consume_subcontract_raw_materials(
    receipt_quantity=incremental_amount
)

# Calculates per BOM line:
consumption = receipt_qty × (required_qty / order_qty)

# Updates:
line.consumed_quantity += consumption
stock_levels (deducts from subcontractor location)
inventory_transactions (logs "out" transaction)
material.current_stock (reduces total)
```

### Key Concepts

```
ISSUED = Warehouse → Vendor (transfer)
CONSUMED = Vendor → Manufacturing (out)
RETURNED = Vendor → Warehouse (transfer)
REMAINING = Issued - Consumed - Returned
```

### Frontend Component

```tsx
import { MaterialStockByLocation } from "@/modules/inventory/components/MaterialStockByLocation"

<MaterialStockByLocation materialId={materialId} />
```

---

## Troubleshooting

### Stock shows wrong total

**Check:** Is consumption being called on receipt?  
**Fix:** Verify `consume_subcontract_raw_materials()` is called in receive endpoint

### Vendor stock not showing

**Check:** Is location type = 'subcontractor'?  
**Fix:** Verify location type in database

### Consumed quantity is 0

**Check:** Have you received output yet?  
**Note:** Consumption happens on receipt, not on issue

### Historical orders show consumed_quantity = 0

**Expected behavior** - Field was added recently, not backfilled

---

## Testing

### Manual Test Flow

1. Create subcontract order for 10 units (BOM: 10 KG per unit)
2. Issue 100 KG raw material → Check: warehouse=0, vendor=100
3. Receive 5 units → Check: consumed_quantity=50, vendor=50
4. View stock locations → Check: shows vendor name and order
5. Receive 5 units → Check: consumed_quantity=100, vendor=0

### API Test

```bash
# Get material stock by location
curl http://localhost:5000/api/v1/inventory/materials/{id}/stock-by-location

# Should return warehouse_stock + subcontractor_stock = total_stock
```

---

## Common Questions

**Q: Why does total stock stay 100 after issuing 100 to vendor?**  
A: It's a transfer, not consumption. Material is still company-owned, just at a different location.

**Q: When does stock decrease?**  
A: When output is received and consumption is calculated from BOM.

**Q: Can I see which vendor has my material?**  
A: Yes! Stock Locations tab shows vendor name and order number.

**Q: What happens to returned material?**  
A: It goes back to warehouse, increases warehouse stock.

**Q: What's the remaining stock formula?**  
A: `issued - consumed - returned`

---

## Need Help?

- **Architecture questions** → See `docs/SUBCONTRACT_INVENTORY_AUDIT_AND_PLAN.md`
- **Implementation details** → See `docs/SUBCONTRACT_INVENTORY_IMPLEMENTATION_STATUS.md`
- **Full report** → See Final Implementation Report artifact
- **Code** → Check inline comments in backend/frontend files
