---
trigger: model_decision
description: "Manufacturing ERP business rules: BOMs, work orders, inventory, procurement, quality control"
---

# Manufacturing Business Rules

**Canonical Source:** AGENTS.md §15 and docs/ai-guidelines/MANUFACTURING_BUSINESS_RULES.md

## 7 Non-Negotiable Business Rules

### Rule 1: BOMs Are Versioned

**When:** Changing active BOM  
**Action:** Create new version, deactivate old  
**Why:** Historical accuracy, audit trail

```
Active BOM v1 (with components A, B, C)
  ↓ (change to A, B, D)
Active BOM v2 (new version with A, B, D)
v1 remains in history (archived, not deleted)
```

**Implementation:**
- Only ONE active version per product/variant
- No duplicate components in BOM
- Immutable when active (must create new version to modify)

### Rule 2: Work Order Status Is Linear (State Machine)

**Valid Path:**
```
DRAFT → RELEASED → STARTED → COMPLETED → CLOSED
```

**Cancellation allowed from:** DRAFT, RELEASED, STARTED

**Invalid transitions:**
- ❌ Cannot skip steps (DRAFT → COMPLETED)
- ❌ Cannot go backward (STARTED → RELEASED)
- ❌ Cannot transition from CLOSED

**Implementation:** Validate before any status change

### Rule 3: Materials Reserved on WO Release

**Timing:** When `WO.status` transitions to RELEASED

**Rules:**
- Cannot release WO without sufficient stock (raises `InsufficientStockError`)
- Reservation BLOCKS other reservations on same material
- Reservation state: PENDING → RESERVED → CONSUMED (or RELEASED on cancel)

**Formula:**
```
Available Stock = Total Stock - Reserved - Quarantined
```

### Rule 4: Materials Consumed on WO Completion

**Timing:** When `WO.status` transitions to COMPLETED

**Rules:**
- Inventory decreased by consumed qty
- Scrap tracked separately
- Reserved qty released
- Inventory updated atomically

**NOT on release:** Materials are reserved, not consumed at release time

### Rule 5: Multi-Tenancy Enforced

**Implementation:**
- Tenant extracted from JWT `tid` claim only (never from user input)
- Every query: `WHERE tenant_id = ...`
- Database enforces via FK constraints
- Middleware sets tenant context

**Every query must include tenant scope.**

### Rule 6: Soft Deletes Only

**Pattern:**
```python
entity.is_deleted = True
entity.deleted_at = datetime.utcnow()
```

**Query Pattern:**
```python
WHERE is_deleted = False  # MANDATORY
```

### Rule 7: All Mutations Audited

**Logged:**
- `user_id` (who)
- `timestamp` (when)
- `tenant_id` (which customer)
- `correlation_id` (request trace)
- `operation` (create/update/delete)
- `before/after` values

## 8 Core Manufacturing Workflows

### Workflow 1: Sales Order Lifecycle

```
DRAFT → APPROVED → MANUFACTURING → DELIVERED
```

**Rules:**
- Orders must be approved before manufacturing starts
- Priority level: LOW, MEDIUM, HIGH, URGENT
- Driven by customer demand or planning

### Workflow 2: Bill of Materials

```
Product Template
  → Variant (configuration)
    → Active BOM (versioned)
      → BOM Lines (components with qty, scrap %, routing)
```

**Rules:**
- Versioned (immutable history)
- One active version per product/variant
- No duplicate components

### Workflow 3: Work Order Execution

```
DRAFT → RELEASED → STARTED → COMPLETED → CLOSED
```

**Rules:**
- Created from approved sales orders or manually
- Release reserves materials from inventory
- Completion consumes materials and updates stock
- Scrap tracked separately

### Workflow 4: Inventory Management

```
Stock Levels (by warehouse + location + batch)
  ↑ (on GRN receipt)
  ↓ (on WO completion, manual issue, scrap)

Available = Total - Reserved - Quarantined
```

**Rules:**
- Multi-warehouse support
- Batch/serial tracking (FIFO for consumption)
- Reservations block stock from double-booking
- Low-stock alerts at reorder point

### Workflow 5: Procurement (POs & GRNs)

```
PO (Purchase Order)
  → GRN (Goods Receipt Note)
    → Inspection (QC)
      → Inventory Receipt
```

**GRN Constraint:** `GRN qty ≤ PO qty` (cannot exceed)

**Workflow:**
1. PO created (quantities ordered)
2. GRN created (goods received)
3. QC inspection required
4. Materials added to inventory (if QC passes)

### Workflow 6: Subcontracting

```
Issue Materials → Subcontractor → Receive Output → Return Unused
  (issued_qty)   (produces)       (consumed_qty)   (returned_qty)
```

**Tracking (all separate):**
- `issued_qty` — Material sent to subcontractor
- `consumed_qty` — Material used by subcontractor
- `returned_qty` — Unused material returned
- `yield` = Output / Issued Qty

### Workflow 7: Quality Control (QC)

```
PENDING → IN_PROGRESS → PASSED (release materials)
                     → FAILED (quarantine materials)
```

**Rules:**
- Required for incoming materials
- Required for production output
- Non-conformance reports capture defects
- Root cause analysis tracked

### Workflow 8: Production Completion

```
WO Complete → Consume Materials → Update Inventory → Generate FG Receipt → Invoice Customer
```

**Rules:**
- Materials consumed based on actual output
- Scrap accounted for
- Production metrics updated
- Finished goods received to inventory
- Invoice generated automatically

## Key Inventory Formulas

**Reservation Lifecycle:**
```
STATE: PENDING (created with WO)
  ↓ (WO released)
STATE: RESERVED (blocks other reservations)
  ↓ (WO completed)
STATE: CONSUMED (inventory decreased)
  OR
STATE: RELEASED (back to available if WO cancelled)
```

**Available Stock Calculation:**
```
Available = Current Stock - Reserved Stock - Quarantined Stock
Minimum: 0 (never negative)
```

**Yield Tracking:**
```
Yield = Output / Issued Qty
Example: 100 units issued, 85 units produced → 85% yield
```

## User Roles & Permissions

**13 Total Roles:**
- System: ADMIN, TENANT_ADMIN
- Operations: MANAGER, OPERATOR, STOREKEEPER, PLANNER
- Quality: QC
- Sales: SALES, WORKER
- External: CLIENT, SUPPLIER
- Reporting: VIEWER

Each role has fine-grained permissions scoped to specific modules and actions.

