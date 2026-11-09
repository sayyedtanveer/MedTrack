---
name: "MedTrack Product & Business Context"
description: "Manufacturing ERP product purpose, workflows, and business rules"
inclusion: auto
---

# MedTrack Product & Business Context

**Updated:** November 9, 2026  
**Version:** 1.0.0  
**Canonical Reference:** [`AGENTS.md`](../../AGENTS.md) Section 2

---

## Product Purpose

**MedTrack** is a multi-tenant Manufacturing ERP system for mid-to-large manufacturing companies. It manages the complete product lifecycle:

- **Design** → Product templates, BOMs, variants
- **Production** → Work orders, shop floor execution, routing
- **Sales** → Customer orders, pricing, order management
- **Procurement** → Purchase orders, supplier management, subcontracting
- **Quality** → Inspections, non-conformance tracking
- **Finance** → Invoicing, AR/AP, cost tracking
- **Reporting** → Real-time dashboards, analytics, MRP

---

## 8 Core Manufacturing Workflows

### 1. Sales Order Lifecycle

```
DRAFT → APPROVED → MANUFACTURING → DELIVERED
```

**Rules:**
- Orders must be approved before manufacturing starts
- Priority level: LOW, MEDIUM, HIGH, URGENT
- Driven by customer demand or planning

### 2. Bill of Materials (BOM)

```
Product Template
  → Variant (configuration)
    → Active BOM (versioned)
      → BOM Lines (components)
```

**Rules:**
- BOMs are versioned (immutable history)
- One active version per product/variant
- No duplicate components in BOM
- Each line specifies: material, quantity, scrap %, routing

### 3. Work Order Execution

```
DRAFT → RELEASED → STARTED → COMPLETED → CLOSED
```

**Rules:**
- Created from approved sales orders or manually
- Release reserves materials from inventory
- Completion consumes materials
- Scrap tracked separately
- Shop floor can see real-time status

### 4. Inventory Management

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
- Soft deletes only (no hard deletions)

### 5. Procurement (POs & GRNs)

```
PO (Purchase Order)
  → GRN (Goods Receipt Note)
    → Inspection (QC)
      → Inventory Receipt
```

**Rules:**
- GRN qty ≤ PO qty (cannot exceed)
- Materials quarantined until QC passes
- Batch tracking from supplier
- Supplier performance metrics

### 6. Subcontracting

```
Issue Materials → Subcontractor → Receive Output → Return Unused
  (issued_qty)   (produces)       (consumed_qty)   (returned_qty)
```

**Rules:**
- Track issued, consumed, and returned separately
- Material consumption proportional to output
- Yield tracking
- Cost allocation

### 7. Quality Control (QC)

```
Inspection Pending → In Progress → Passed / Failed
                                    ↓
                              Release / Quarantine
```

**Rules:**
- Incoming inspections for materials
- QC approval before use
- Non-conformance reporting
- Defect tracking & root cause analysis

### 8. Production Completion

```
WO Complete → Consume Materials → Update Inventory → Generate FG Receipt → Invoice Customer
```

**Rules:**
- Materials consumed based on actual output
- Scrap accounted for
- Production metrics updated
- Finished goods received to inventory
- Invoice generated automatically

---

## Key Business Concepts

### Multi-Tenancy (Non-Negotiable)

**See:** [AGENTS.md](../../AGENTS.md) § 14, [security.instructions.md](../../.github/instructions/security.instructions.md)

- **Complete data isolation** per customer
- **Tenant ID** from JWT `tid` claim
- **Every query** scoped by `tenant_id`
- **No cross-tenant visibility** possible

### Soft Deletes (Non-Negotiable)

- **No hard deletions** (preserves audit trail)
- **All records marked** `is_deleted = true` + `deleted_at` timestamp
- **Historical data preserved** for compliance
- **All queries filter** `WHERE is_deleted = false`

### Audit Logging (Non-Negotiable)

- **Every mutation logged:**
  - user_id (who changed it)
  - timestamp (when)
  - tenant_id (which tenant)
  - correlation_id (request trace)
  - action (what changed)
  - before/after (data change)

### Multi-Warehouse Inventory

**Hierarchy:**
```
Company
  → Warehouse A
    → Location 1 (Rack A, Shelf B)
      → Batch 001 (25 units, received 2026-11-01)
      → Batch 002 (30 units, received 2026-11-02)
    → Location 2 (Rack C, Shelf D)
      → Batch 003 (15 units, received 2026-11-01)
```

**Rules:**
- FIFO consumption (oldest batch first)
- Quality level tracking (good, scrap, quarantine)
- Available = Total - Reserved - Quarantined

### Inventory Reservation Lifecycle

```
STATE: PENDING
  ↓ (WO released)
STATE: RESERVED (blocks other reservations)
  ↓ (WO completed)
STATE: CONSUMED (inventory decreased)
  OR
STATE: RELEASED (back to available if WO cancelled)
```

---

## 13 User Roles & Permissions

| Role | Modules | UI | Notes |
|------|---------|----|----|
| **ADMIN** | All | Admin console | System-wide access |
| **TENANT_ADMIN** | All | Admin console | Tenant configuration only |
| **MANAGER** | Most R/W | Ops dashboard | Operations oversight |
| **OPERATOR** | Mfg, Inv | Shop floor | Shop floor execution |
| **STOREKEEPER** | Inv, Proc | Warehouse | Inventory management |
| **PLANNER** | Mfg, Proc | Planning | Production planning |
| **QC** | Quality, Inv R | QC console | Quality inspections |
| **SALES** | Sales, Inv R | Sales dashboard | Sales representative |
| **WORKER** | Mfg, Inv | Shop floor | Production worker |
| **CLIENT** | Sales R | Client portal | External customer |
| **SUPPLIER** | Proc R/W | Supplier portal | External supplier |
| **VIEWER** | All R | Analytics | Read-only reporting |

---

## 7 Non-Negotiable Business Rules

### Rule 1: BOMs Are Versioned

**When:** Changing active BOM  
**Action:** Create new version, deactivate old  
**Why:** Historical accuracy, audit trail

```
Active BOM v1 → Change components → Active BOM v2 (v1 remains in history)
```

### Rule 2: Work Order Status Is Linear

**Valid Path:** DRAFT → RELEASED → STARTED → COMPLETED → CLOSED

**Invalid:**
- Cannot skip steps (DRAFT → COMPLETED)
- Cannot go backward (STARTED → RELEASED)
- Can cancel from DRAFT, RELEASED, STARTED

### Rule 3: Materials Reserved on WO Release

**Timing:** When WO.status = RELEASED

**Rules:**
- Cannot release without sufficient stock
- Reservation blocks stock for other WOs
- Raises `InsufficientStockError` if not enough

### Rule 4: Materials Consumed on WO Completion

**Timing:** When WO.status = COMPLETED

**Rules:**
- Inventory decreased by consumed qty
- Scrap tracked separately
- Reserved qty released
- Inventory updated atomically

### Rule 5: Multi-Tenancy Enforced

**Implementation:**
- Tenant from JWT, never from user input
- Every query: `WHERE tenant_id = ...`
- Database enforces via FK constraints
- Middleware sets tenant context

### Rule 6: Soft Deletes Only

**Pattern:**
```python
entity.is_deleted = True
entity.deleted_at = datetime.utcnow()
```

**Query:**
```python
WHERE is_deleted = False
```

### Rule 7: All Mutations Audited

**Logged:**
- user_id (who)
- timestamp (when)
- tenant_id (which customer)
- correlation_id (request trace)
- operation (create/update/delete)
- before/after values

---

## GRN (Goods Receipt Note) Rules

**Constraint:** GRN qty ≤ PO qty

```python
# Validate on GRN creation
total_received = po_line.grn_qty_received + new_grn_qty
if total_received > po_line.qty:
    raise ExcessiveGRNError()
```

**Workflow:**
1. PO created (quantities ordered)
2. GRN created (goods received)
3. QC inspection required
4. Materials added to inventory (if QC passes)

---

## Low-Stock Alerts

**Trigger:** Stock falls below reorder_point

**Rules:**
- Configurable per material
- Alert users with PLANNER or MANAGER role
- Clear alert when stock > reorder_point
- Event-driven (real-time WebSocket notification)

---

## Quality Control (QC) Workflow

**Status Machine:**
```
PENDING → IN_PROGRESS → PASSED (release materials)
                     → FAILED (quarantine materials)
```

**Rules:**
- Required for incoming materials
- Required for production output
- Non-conformance reports capture defects
- Root cause analysis tracked

---

## Subcontracting Model

**Tracking (All Separate):**
- **issued_qty** — Material sent to subcontractor
- **consumed_qty** — Material used by subcontractor
- **returned_qty** — Unused material returned
- **yield** — Output / issued_qty

**Formula:**
```
Yield = Output / Issued Qty
Example: 100 units issued, 85 units produced → 85% yield
```

---

## Finance & Costing

**Standard Costing:**
- Each material has standard cost
- Work order cost = Σ(material qty × standard cost) + labor
- Actual cost tracked vs. standard (variance analysis)
- Invoice cost from BOM + labor

**Inventory Valuation:**
- FIFO (First-In-First-Out) for batch consumption
- Standard costing for pricing

---

## MRP (Material Requirements Planning) Logic

**Triggered by:**
- Sales orders
- Production plans
- Reorder points

**Calculates:**
- Required materials
- Timing (when to order/produce)
- Quantities (considering scrap %, safety stock)
- Vendor lead times

---

## Key Features (Verified Implementation)

✅ **Multi-tenancy** — Complete isolation, JWT-based  
✅ **RBAC** — 13 roles with fine-grained permissions  
✅ **BOMs** — Versioned, multi-level, component tracking  
✅ **Work Orders** — Status machine, material reservations, scrap tracking  
✅ **Inventory** — Multi-warehouse, batch/serial, reservations, alerts  
✅ **Procurement** — POs, GRNs, subcontracting, supplier tracking  
✅ **Quality** — Inspections, non-conformance, quarantine  
✅ **Finance** — Invoicing, AR/AP, standard costing  
✅ **Audit Logging** — All mutations logged with context  
✅ **Real-Time** — WebSocket notifications, live dashboards  
✅ **PDF Documents** — POs, invoices, QC reports  
✅ **Multi-Language** — i18n support (if needed)  

---

## Success Criteria

- **Uptime:** 99.9%
- **Response Time:** <500ms p95
- **Data Consistency:** 100% (no cross-tenant leaks)
- **Order Fulfillment:** 2x faster than manual

---

## Reference

- **Detailed workflows:** [`MANUFACTURING_BUSINESS_RULES.md`](../../docs/ai-guidelines/MANUFACTURING_BUSINESS_RULES.md)
- **Complete standards:** [`AGENTS.md`](../../AGENTS.md)
- **Business process guide:** `docs/ERP_COMPLETE_GUIDE.md`

---

**Status:** Production Ready | Last Updated: November 9, 2026
