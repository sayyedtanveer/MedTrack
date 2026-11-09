# Manufacturing Business Rules

**For:** AI agents and domain experts  
**Updated:** November 9, 2026  
**Version:** 1.0.0

## Non-Negotiable Rules

These rules are fundamental to MedTrack's functionality. Any violation is a critical bug requiring:
1. ✅ Unit test demonstrating the rule
2. ✅ E2E test with realistic scenario
3. ✅ Business stakeholder approval
4. ✅ Migration if schema changes

---

## 1. Bill of Materials (BOM) Rules

### Rule 1.1: Versioning
- Each BOM is versioned independently
- Only one version can be **active** at a time per product
- Changing an active BOM creates a new version (doesn't modify the existing one)
- Historical versions remain queryable for auditing

### Rule 1.2: Component Uniqueness
- No duplicate components within a single BOM
- Each material appears only once per BOM line
- Violates with `DuplicateComponentError`

**Example:**
```python
class BOM:
    lines: List[BOMLine]
    
    def add_line(self, line: BOMLine) -> None:
        if any(l.material_id == line.material_id for l in self.lines):
            raise DuplicateComponentError("Material already in BOM")
        self.lines.append(line)
```

### Rule 1.3: Active BOM Immutability
- Active BOMs cannot be modified
- To change an active BOM, create a new version
- Prevents work orders from using inconsistent BOMs mid-production

### Rule 1.4: Material Must Exist
- All materials in BOM lines must exist in the tenant's database
- Materials must be active (not soft-deleted)
- Enforced at both domain and database layers

### Rule 1.5: Product Template Validation
- BOM must reference a valid, active product template
- Cannot create BOM for non-existent or inactive template

---

## 2. Inventory & Stock Management Rules

### Rule 2.1: Stock Reservation System
When a work order is released, materials are **reserved** (not consumed yet).

**Stock Status Lifecycle:**
```
Available Stock
    ↓ (WO released)
Reserved Stock
    ↓ (WO completed → materials consumed)
Consumed Stock  

OR

Reserved Stock
    ↓ (WO cancelled → materials released)
Available Stock
```

**Key Points:**
- Reserved stock is blocked from other reservations
- Reservations are released if WO is cancelled
- Reservations are marked consumed when WO completes

### Rule 2.2: Low-Stock Alerts
- Alert triggered when `available_stock < reorder_point`
- Configurable per material
- Prevents stock-outs from going unnoticed

**Implementation:**
```python
async def consume_material(self, material_id: uuid.UUID, quantity: Decimal):
    material = await self.repo.get_material(material_id)
    material.available_stock -= quantity
    
    if material.available_stock < material.reorder_point:
        await self.event_dispatcher.publish(
            InventoryLowStockAlert(
                material_id=material_id,
                current_stock=material.available_stock,
                reorder_point=material.reorder_point
            )
        )
```

### Rule 2.3: Multi-Warehouse Support
- Each warehouse has separate stock levels
- Material location must be specified when issuing
- Default location is "DEFAULT"

### Rule 2.4: Batch & Serial Tracking
- Materials tracked by batch/serial number
- Enables traceability and recall management
- Supports first-in-first-out (FIFO) or last-in-first-out (LIFO) strategies

---

## 3. Work Order Status Rules

### Rule 3.1: Linear Status Workflow (Strict State Machine)

Work orders MUST follow this workflow:

```
┌────────────────────────────────────────────┐
│              DRAFT                         │
│  (Initial state, can add lines)            │
│        ↓                                    │
│    RELEASED                                │
│  (Materials reserved, ready for shop floor)│
│        ↓                                    │
│    STARTED                                 │
│  (Production in progress)                  │
│        ↓                                    │
│    COMPLETED                               │
│  (Materials consumed, invoice generated)   │
│        ↓                                    │
│    CLOSED                                  │
│  (Final state, immutable)                  │
│        ↓                                    │
│  (or from RELEASED or STARTED)             │
│    CANCELLED                               │
│  (Materials released back to inventory)    │
└────────────────────────────────────────────┘
```

**Rules:**
- Cannot skip steps (e.g., DRAFT→STARTED is invalid)
- Cannot go backward (e.g., COMPLETED→STARTED is invalid)
- Only RELEASED or STARTED can be CANCELLED
- CLOSED is final (immutable)

**Implementation:**
```python
class WorkOrder:
    status: str
    
    def release(self) -> None:
        if self.status != 'DRAFT':
            raise InvalidStateTransitionError(
                f"Cannot release from {self.status}"
            )
        self.status = 'RELEASED'
    
    def start(self) -> None:
        if self.status != 'RELEASED':
            raise InvalidStateTransitionError(
                f"Cannot start from {self.status}"
            )
        self.status = 'STARTED'
    
    def complete(self) -> None:
        if self.status != 'STARTED':
            raise InvalidStateTransitionError(
                f"Cannot complete from {self.status}"
            )
        self.status = 'COMPLETED'
    
    def close(self) -> None:
        if self.status != 'COMPLETED':
            raise InvalidStateTransitionError(
                f"Cannot close from {self.status}"
            )
        self.status = 'CLOSED'
    
    def cancel(self) -> None:
        if self.status not in ('RELEASED', 'STARTED'):
            raise InvalidStateTransitionError(
                f"Cannot cancel from {self.status}"
            )
        self.status = 'CANCELLED'
```

### Rule 3.2: Materials Reserved on Release
- Materials are reserved when WO status → RELEASED
- If any material is insufficient, WO cannot be released
- Raises `InsufficientStockError`

**Validation before release:**
```python
async def handle_release_work_order(self, cmd: ReleaseWOCommand):
    wo = await self.repo.get_work_order(cmd.wo_id)
    
    # Check stock availability
    for line in wo.lines:
        available = await self.inventory_service.get_available_stock(
            line.material_id
        )
        if available < line.quantity:
            raise InsufficientStockError(
                f"Need {line.quantity}, have {available}"
            )
    
    # Reserve stock
    for line in wo.lines:
        await self.inventory_service.reserve(
            line.material_id,
            line.quantity,
            work_order_id=wo.id
        )
    
    wo.release()
    await self.repo.save(wo)
```

### Rule 3.3: Materials Consumed on Completion
- Materials are marked as consumed when WO → COMPLETED
- Updates inventory levels and valuation
- Triggers production metrics update

**On completion:**
```python
async def handle_complete_work_order(self, cmd: CompleteWOCommand):
    wo = await self.repo.get_work_order(cmd.wo_id)
    
    if wo.status != 'STARTED':
        raise InvalidStateTransitionError("Only STARTED WOs can be completed")
    
    # Consume reserved materials
    for line in wo.lines:
        await self.inventory_service.consume(
            line.material_id,
            line.quantity,
            work_order_id=wo.id
        )
    
    # Update work order
    wo.status = 'COMPLETED'
    wo.completed_at = datetime.utcnow()
    await self.repo.save(wo)
    
    # Publish event
    await self.event_dispatcher.publish(
        WorkOrderCompletedEvent(wo_id=wo.id)
    )
```

### Rule 3.4: Work Order Cancellation
- Can only cancel from RELEASED or STARTED status
- Releases reserved materials back to available inventory
- Cannot cancel COMPLETED or CLOSED orders

---

## 4. Sales Order Rules

### Rule 4.1: Approval Workflow
- Sales orders require approval before manufacturing
- Can only approve with APPROVED or MANAGER role
- Cannot modify approved sales orders without creating new revision

**Status flow:**
```
DRAFT → APPROVED → MANUFACTURING → DELIVERED
```

### Rule 4.2: Priority Levels
- Sales orders can have priority: LOW, MEDIUM, HIGH, URGENT
- Higher priority work orders are scheduled first
- Default priority is MEDIUM

---

## 5. Procurement & GRN Rules

### Rule 5.1: GRN Against PO
- Goods Receipt Notes (GRN) must reference an existing PO
- GRN quantity cannot exceed PO quantity
- Raises `ExcessiveGRNError`

**Validation:**
```python
async def handle_create_grn(self, cmd: CreateGRNCommand):
    po = await self.repo.get_purchase_order(cmd.po_id)
    if not po:
        raise PONotFoundError(cmd.po_id)
    
    # Get already received quantity
    received = await self.repo.get_grn_total_quantity(cmd.po_id)
    
    if received + cmd.quantity > po.quantity:
        raise ExcessiveGRNError(
            f"Cannot receive {cmd.quantity}: "
            f"Already received {received}, PO total {po.quantity}"
        )
```

### Rule 5.2: Subcontracting Materials Tracked
- Subcontracting operations issue materials to supplier
- Must track outgoing quantity by batch
- Receiving back triggers valuation adjustment

---

## 6. Quality Control Rules

### Rule 6.1: QC Inspection Before Acceptance
- All incoming materials must pass QC before being accepted
- QC status: PENDING → IN_PROGRESS → PASSED/FAILED
- Failed batches are quarantined

**QC Status Workflow:**
```
PENDING
  ↓ (Inspection starts)
IN_PROGRESS
  ↓
PASSED (Materials accepted)
  OR
FAILED (Materials quarantined)
```

### Rule 6.2: Failed Batches Quarantined
- Failed QC batches cannot be used in production
- Flagged for rework or scrap
- Tracked for root cause analysis

---

## 7. Financial Rules

### Rule 7.1: Invoice Generation on WO Completion
- Invoices generated automatically when WO → COMPLETED
- Based on BOM costs and sales order pricing
- Sent to customer upon generation

### Rule 7.2: Standard Costing
- Material costs based on most recent received GRN
- Updates when new GRN received
- Historical costing available for closed work orders

---

## Business Events

These events signal state changes and trigger downstream actions:

| Event | Trigger | Subscribers |
|-------|---------|-------------|
| `work_order.released` | WO → RELEASED | Materials reserved |
| `work_order.started` | WO → STARTED | Production starts |
| `work_order.completed` | WO → COMPLETED | Materials consumed, invoice generated |
| `work_order.cancelled` | WO → CANCELLED | Materials released |
| `inventory.low_stock_alert` | Stock < reorder_point | Alert to planners |
| `bom.activated` | BOM → active | Linked to product, usable |
| `grn.received` | GRN created | Material costs updated |
| `qc.inspection_failed` | QC → FAILED | Batch quarantined |

---

**Summary:**
- ✅ BOMs are versioned, immutable when active
- ✅ Work order status is linear (no backtracking)
- ✅ Materials reserved on release, consumed on completion
- ✅ Stock reservations prevent double-booking
- ✅ Low-stock alerts prevent stockouts
- ✅ Multi-warehouse and batch tracking
- ✅ Sales orders require approval
- ✅ GRNs must not exceed PO quantity
- ✅ QC inspection before acceptance
- ✅ Invoices generated on WO completion
