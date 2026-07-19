# Workflow Ownership Matrix

## Purpose
This document defines the operational ownership matrix for MedTrack ERP workflow orchestration. It serves as the blueprint for:
- Role-based dashboards and queues
- State transition rules
- Notification triggers
- Permission models
- Operational execution flows

---

## 1. Workflow Overview

MedTrack implements a manufacturing operational flow from Work Order creation to delivery. The workflow is divided into operational phases, each owned by specific roles with clear responsibilities.

### Core Operational Entities
- **Work Order**: Production order with BOM, quantity, and timeline
- **Job Card**: Individual operations within a Work Order
- **InventoryService**: Canonical stock mutation gateway (AVAILABLE, RESERVED, ISSUED, CONSUMED, REJECTED)
- **QualityInspection**: QC records linked to Work Orders
- **Delivery**: Dispatch and delivery tracking

### Existing State Machine (from domain/manufacturing/entities/work_order.py)
States: PLANNED, RELEASED, MATERIAL_PENDING, MATERIAL_RESERVED, MATERIAL_ISSUED, IN_PRODUCTION, QC_PENDING, QC_APPROVED, QC_REJECTED, FG_RECEIVED, COMPLETED, CLOSED, REWORK, REJECTED

---

## 2. Operational Roles

| Role | Responsibilities | Dashboard Focus |
|------|----------------|-----------------|
| **Planner** | Create/Release Work Orders, MRP, Material Planning | Shortages, Delayed WOs, MRP Actions |
| **Storekeeper** | Reserve/Issue Material, Stock Management, GRN Processing | Issue Queue, Low Stock, Pending GRN |
| **Worker** | Execute Production Operations, Report Wastage | Assigned Jobs, Active Production |
| **QC Inspector** | Approve/Reject Quality Inspections, Rework Decisions | Inspection Queue, Rejection Analytics |
| **Accountant** | Invoice Processing, Payment Tracking | Unpaid Invoices, Supplier Dues |
| **Admin** | Master Data, User Management, System Configuration | System Overview |

---

## 3. Work Order Lifecycle

### PLANNED
- **Responsible Role**: Planner
- **Trigger Action**: Create Work Order from Sales Order
- **Next States**: RELEASED
- **Inventory Impact**: None
- **Notification Trigger**: None
- **Audit Requirement**: Log creation with sales_order_id reference
- **Allowed Actions**: Edit fields, Delete, Release

### RELEASED
- **Responsible Role**: Planner
- **Trigger Action**: Release Work Order (locks immutable fields)
- **Next States**: MATERIAL_PENDING
- **Inventory Impact**: None
- **Notification Trigger**: Notify Storekeeper of material requirements
- **Audit Requirement**: Log release with created_by
- **Allowed Actions**: View, Cancel (back to PLANNED)

### MATERIAL_PENDING
- **Responsible Role**: Storekeeper
- **Trigger Action**: Work Order released, material requirements calculated
- **Next States**: MATERIAL_RESERVED
- **Inventory Impact**: None (reservation pending)
- **Notification Trigger**: Material shortage alert if stock insufficient
- **Audit Requirement**: None
- **Allowed Actions**: Reserve Material, Report Shortage

### MATERIAL_RESERVED
- **Responsible Role**: Storekeeper
- **Trigger Action**: Reserve stock via InventoryService
- **Next States**: MATERIAL_ISSUED
- **Inventory Impact**: AVAILABLE → RESERVED (via InventoryService.reserve_stock)
- **Notification Trigger**: None
- **Audit Requirement**: Log reservation with work_order_id, material_id, quantity
- **Allowed Actions**: Issue Material, Cancel Reservation

### MATERIAL_ISSUED
- **Responsible Role**: Storekeeper
- **Trigger Action**: Issue material to production floor
- **Next States**: IN_PRODUCTION
- **Inventory Impact**: RESERVED → ISSUED (via InventoryService.issue_stock)
- **Notification Trigger**: Notify Worker that material is ready
- **Audit Requirement**: Log issue with work_order_id, issued_by, timestamp
- **Allowed Actions**: Partial Issue, Return Material

### IN_PRODUCTION
- **Responsible Role**: Worker
- **Trigger Action**: Material issued, worker starts production
- **Next States**: QC_PENDING
- **Inventory Impact**: ISSUED → CONSUMED (via InventoryService.consume_stock)
- **Notification Trigger**: Production progress updates
- **Audit Requirement**: Log operation start/complete, runtime, wastage
- **Allowed Actions**: Start Operation, Pause Operation, Complete Operation, Report Wastage

### QC_PENDING
- **Responsible Role**: QC Inspector
- **Trigger Action**: Production completed, batch submitted for inspection
- **Next States**: QC_APPROVED, QC_REJECTED
- **Inventory Impact**: None
- **Notification Trigger**: Notify QC Inspector of pending inspection
- **Audit Requirement**: Log inspection request
- **Allowed Actions**: Approve, Reject, Request Rework

### QC_APPROVED
- **Responsible Role**: QC Inspector
- **Trigger Action**: Quality inspection passed
- **Next States**: FG_RECEIVED
- **Inventory Impact**: None (FG receipt pending)
- **Notification Trigger**: Notify Storekeeper/Inventory for FG receipt
- **Audit Requirement**: Log approval with inspector_id, inspection_results
- **Allowed Actions**: Approve (final), View Details

### QC_REJECTED
- **Responsible Role**: QC Inspector
- **Trigger Action**: Quality inspection failed
- **Next States**: REWORK, REJECTED
- **Inventory Impact**: None
- **Notification Trigger**: Alert Planner and Worker of rejection
- **Audit Requirement**: Log rejection with reason, defect_details
- **Allowed Actions**: Send to Rework, Reject (scrap)

### FG_RECEIVED
- **Responsible Role**: Storekeeper/Inventory
- **Trigger Action**: QC approved, FG received into inventory
- **Next States**: COMPLETED
- **Inventory Impact**: FG stock increase (via InventoryService.receive_fg)
- **Notification Trigger**: Notify Planner that WO is ready for delivery
- **Audit Requirement**: Log FG receipt with work_order_id, quantity, location
- **Allowed Actions**: Complete WO

### COMPLETED
- **Responsible Role**: Planner
- **Trigger Action**: FG received, WO production complete
- **Next States**: CLOSED
- **Inventory Impact**: None
- **Notification Trigger**: Notify Delivery team
- **Audit Requirement**: Log completion with final quantities
- **Allowed Actions**: Close WO

### CLOSED
- **Responsible Role**: Planner
- **Trigger Action**: WO finalized, no further operations
- **Next States**: None (terminal)
- **Inventory Impact**: None
- **Notification Trigger**: None
- **Audit Requirement**: Log closure
- **Allowed Actions**: View Only

### REWORK
- **Responsible Role**: Worker
- **Trigger Action**: QC rejected, sent for rework
- **Next States**: QC_PENDING
- **Inventory Impact**: Additional material consumption (via InventoryService.consume_stock)
- **Notification Trigger**: Notify Worker of rework assignment
- **Audit Requirement**: Log rework with reason, additional_material_used
- **Allowed Actions**: Execute Rework Operations

### REJECTED
- **Responsible Role**: Planner
- **Trigger Action**: QC rejected, batch scrapped
- **Next States**: CLOSED
- **Inventory Impact**: ISSUED → REJECTED (via InventoryService.reject_stock)
- **Notification Trigger**: Alert Planner of scrap
- **Audit Requirement**: Log rejection with scrap_quantity, scrap_reason
- **Allowed Actions**: Close WO

---

## 4. Storekeeper Flow

### Operational Queue: Material Issue Queue
**Shows**: Pending material issues, shortages, partially issued WOs, reserved stock

### Actions
1. **Reserve Stock**
   - Trigger: WO in MATERIAL_PENDING
   - Action: Call InventoryService.reserve_stock(tenant_id, material_id, quantity, work_order_id)
   - State: MATERIAL_PENDING → MATERIAL_RESERVED
   - Validation: Check AVAILABLE stock >= required quantity
   - On Shortage: Create Material Request, alert Planner

2. **Issue Stock**
   - Trigger: WO in MATERIAL_RESERVED
   - Action: Call InventoryService.issue_stock(tenant_id, material_id, quantity, work_order_id)
   - State: MATERIAL_RESERVED → MATERIAL_ISSUED
   - Validation: Check RESERVED stock >= requested quantity
   - Support: Partial issue allowed

3. **Partial Issue**
   - Trigger: Partial stock available
   - Action: Issue available quantity, keep WO in MATERIAL_RESERVED
   - State: MATERIAL_RESERVED (remains)
   - Validation: Track issued vs remaining quantities

4. **Return Material**
   - Trigger: Material returned from production floor
   - Action: Call InventoryService.return_stock(tenant_id, material_id, quantity, work_order_id)
   - State: MATERIAL_ISSUED → MATERIAL_RESERVED (stock returned)
   - Validation: Log return reason

5. **Reject Issue**
   - Trigger: Material quality issue
   - Action: Reject material, alert QC
   - State: MATERIAL_ISSUED → MATERIAL_RESERVED (if not consumed)
   - Validation: Log rejection

### Inventory States (via InventoryService)
- **AVAILABLE**: Stock ready for reservation
- **RESERVED**: Stock reserved for specific WO
- **ISSUED**: Stock issued to production floor
- **CONSUMED**: Stock consumed in production
- **REJECTED**: Stock rejected/scrapped

---

## 5. Worker Flow

### Operational Queue: Worker Dashboard
**Shows**: Assigned WOs, operations, priorities, due dates, active production

### Actions
1. **Start Operation**
   - Trigger: Job Card assigned, material issued
   - Action: Start job card operation
   - State: Operation → IN_PROGRESS
   - Validation: Check WO status = MATERIAL_ISSUED
   - Tracking: Record start_time

2. **Pause Operation**
   - Trigger: Break, equipment issue
   - Action: Pause job card operation
   - State: Operation → PAUSED
   - Validation: Record pause_reason
   - Tracking: Track pause_duration

3. **Complete Operation**
   - Trigger: Operation finished
   - Action: Complete job card operation
   - State: Operation → COMPLETED
   - Validation: Check all required steps completed
   - Tracking: Record end_time, actual_quantity

4. **Report Wastage**
   - Trigger: Scrap/rejection during production
   - Action: Record wastage quantity
   - State: IN_PRODUCTION (remains)
   - Validation: Log wastage_reason
   - Inventory Impact: CONSUMED → REJECTED (via InventoryService.reject_stock)

5. **Record Production**
   - Trigger: Batch completed
   - Action: Record actual produced quantity
   - State: IN_PRODUCTION → QC_PENDING
   - Validation: produced_quantity > 0
   - Inventory Impact: ISSUED → CONSUMED (via InventoryService.consume_stock)

### Tracking
- Runtime per operation
- Wastage/rejection quantity
- Actual production quantity
- Worker productivity metrics

---

## 6. QC Flow

### Operational Queue: QC Dashboard
**Shows**: Pending inspections, rejected batches, rework queue

### Actions
1. **Approve**
   - Trigger: Inspection passed
   - Action: Mark QC as approved
   - State: QC_PENDING → QC_APPROVED
   - Validation: All quality criteria met
   - Downstream: Trigger FG receipt

2. **Reject**
   - Trigger: Inspection failed
   - Action: Mark QC as rejected
   - State: QC_PENDING → QC_REJECTED
   - Validation: Log defect details, severity
   - Downstream: Trigger rework or scrap decision

3. **Send to Rework**
   - Trigger: Reworkable defect
   - Action: Send batch to rework
   - State: QC_REJECTED → REWORK
   - Validation: Rework cost < scrap cost
   - Downstream: Worker executes rework operations

### QC Reports
- Inspection results
- Defect analysis
- Rework statistics
- Quality trends

---

## 7. Delivery Flow

### Operational Queue: Delivery Dashboard
**Shows**: Ready to dispatch, partially dispatched, pending invoices

### Actions
1. **Create Challan**
   - Trigger: WO COMPLETED, FG received
   - Action: Generate delivery challan
   - State: FG_RECEIVED → READY_FOR_DISPATCH
   - Validation: Check FG stock >= ordered quantity
   - Document: Generate PDF via DocumentService

2. **Dispatch**
   - Trigger: Delivery scheduled
   - Action: Mark as dispatched
   - State: READY_FOR_DISPATCH → DISPATCHED
   - Validation: Log dispatch details (vehicle, driver, route)
   - Tracking: Track dispatch status

3. **Mark Delivered**
   - Trigger: Customer confirms receipt
   - Action: Mark as delivered
   - State: DISPATCHED → DELIVERED
   - Validation: Customer signature/confirmation
   - Downstream: Trigger invoice generation

4. **Partial Dispatch**
   - Trigger: Partial FG stock available
   - Action: Dispatch available quantity
   - State: READY_FOR_DISPATCH (remains for balance)
   - Validation: Track dispatched vs remaining quantities

---

## 8. Inventory State Transitions

### Material Flow (Raw Materials)
```
AVAILABLE → RESERVED → ISSUED → CONSUMED
                    ↓
                 REJECTED (if defective)
```

### FG Flow (Finished Goods)
```
QC_APPROVED → FG_RECEIVED → AVAILABLE (for delivery)
```

### Stock Mutation via InventoryService
All stock mutations MUST go through InventoryService canonical layer:
- `reserve_stock(tenant_id, material_id, quantity, work_order_id)`
- `issue_stock(tenant_id, material_id, quantity, work_order_id)`
- `consume_stock(tenant_id, material_id, quantity, work_order_id)`
- `return_stock(tenant_id, material_id, quantity, work_order_id)`
- `reject_stock(tenant_id, material_id, quantity, work_order_id)`
- `receive_fg(tenant_id, product_id, quantity, work_order_id)`

### Audit Trail
Track for each mutation:
- who moved stock (user_id)
- when (timestamp)
- why (reason, work_order_id/purchase_order_id)
- quantity
- from_state → to_state

---

## 9. Notification Triggers

### WebSocket-Based Alerts
Use existing WebSocket infrastructure for real-time notifications:

| Event | Recipients | Channel | Payload |
|-------|-----------|---------|---------|
| Material Shortage | Planner, Storekeeper | `material-shortage` | work_order_id, material_id, required_qty, available_qty |
| QC Rejection | Planner, Worker | `qc-rejection` | work_order_id, reason, defect_details |
| Delayed WO | Planner | `wo-delayed` | work_order_id, due_date, current_status |
| Invoice Overdue | Accountant | `invoice-overdue` | invoice_id, amount, overdue_days |
| Low Stock | Storekeeper, Planner | `low-stock` | material_id, current_qty, reorder_level |
| Material Ready | Worker | `material-ready` | work_order_id, issued_materials |
| FG Received | Planner, Delivery | `fg-received` | work_order_id, quantity, location |
| Rework Assigned | Worker | `rework-assigned` | work_order_id, reason, operations |

---

## 10. Role Ownership Matrix

| State | Responsible Role | Allowed Actions | Next States | Inventory Impact | Notification Trigger | Audit Requirement |
|-------|------------------|-----------------|-------------|-----------------|---------------------|------------------|
| PLANNED | Planner | Edit, Delete, Release | RELEASED | None | None | Log creation |
| RELEASED | Planner | View, Cancel | MATERIAL_PENDING | None | Notify Storekeeper | Log release |
| MATERIAL_PENDING | Storekeeper | Reserve, Report Shortage | MATERIAL_RESERVED | None | Shortage alert | None |
| MATERIAL_RESERVED | Storekeeper | Issue, Cancel Reservation | MATERIAL_ISSUED | AVAILABLE → RESERVED | None | Log reservation |
| MATERIAL_ISSUED | Storekeeper | Partial Issue, Return | IN_PRODUCTION | RESERVED → ISSUED | Notify Worker | Log issue |
| IN_PRODUCTION | Worker | Start, Pause, Complete, Report Wastage | QC_PENDING | ISSUED → CONSUMED | Progress updates | Log operations |
| QC_PENDING | QC Inspector | Approve, Reject, Rework | QC_APPROVED, QC_REJECTED | None | Notify QC | Log inspection |
| QC_APPROVED | QC Inspector | Approve (final) | FG_RECEIVED | None | Notify Storekeeper | Log approval |
| QC_REJECTED | QC Inspector | Rework, Reject | REWORK, REJECTED | None | Alert Planner/Worker | Log rejection |
| FG_RECEIVED | Storekeeper | Complete WO | COMPLETED | FG stock increase | Notify Planner | Log receipt |
| COMPLETED | Planner | Close WO | CLOSED | None | Notify Delivery | Log completion |
| CLOSED | Planner | View Only | None | None | None | Log closure |
| REWORK | Worker | Execute Rework | QC_PENDING | Additional consumption | Notify Worker | Log rework |
| REJECTED | Planner | Close WO | CLOSED | ISSUED → REJECTED | Alert Planner | Log scrap |

---

## 11. State Transition Rules

### Controlled Transitions (from domain/manufacturing/entities/work_order.py)
```python
_TRANSITIONS = {
    WorkOrderStatus.PLANNED: {WorkOrderStatus.RELEASED},
    WorkOrderStatus.RELEASED: {WorkOrderStatus.MATERIAL_PENDING},
    WorkOrderStatus.MATERIAL_PENDING: {WorkOrderStatus.MATERIAL_RESERVED},
    WorkOrderStatus.MATERIAL_RESERVED: {WorkOrderStatus.MATERIAL_ISSUED},
    WorkOrderStatus.MATERIAL_ISSUED: {WorkOrderStatus.IN_PRODUCTION},
    WorkOrderStatus.IN_PRODUCTION: {WorkOrderStatus.QC_PENDING},
    WorkOrderStatus.QC_PENDING: {WorkOrderStatus.QC_APPROVED, WorkOrderStatus.QC_REJECTED},
    WorkOrderStatus.QC_APPROVED: {WorkOrderStatus.FG_RECEIVED},
    WorkOrderStatus.FG_RECEIVED: {WorkOrderStatus.COMPLETED},
    WorkOrderStatus.COMPLETED: {WorkOrderStatus.CLOSED},
    WorkOrderStatus.QC_REJECTED: {WorkOrderStatus.REWORK, WorkOrderStatus.REJECTED},
    WorkOrderStatus.REWORK: {WorkOrderStatus.QC_PENDING},
    WorkOrderStatus.REJECTED: {WorkOrderStatus.CLOSED},
    WorkOrderStatus.CLOSED: set(),
}
```

### Business Rules
1. Cannot start production before material issued (MATERIAL_ISSUED → IN_PRODUCTION)
2. Cannot FG receipt before QC approval (QC_APPROVED → FG_RECEIVED)
3. Cannot complete WO with produced_quantity = 0
4. Partial material issue allowed (WO stays in MATERIAL_RESERVED)
5. Partial dispatch allowed (WO stays in READY_FOR_DISPATCH)
6. Rework only allowed if rework_cost < scrap_cost

---

## 12. Exception/Rework Flows

### Rework Flow
1. **Trigger**: QC rejects batch with reworkable defect
2. **Decision**: Compare rework_cost vs scrap_cost
3. **If Rework**: QC_REJECTED → REWORK
4. **Execution**: Worker executes rework operations
5. **Completion**: REWORK → QC_PENDING (re-submit for inspection)
6. **If Scrap**: QC_REJECTED → REJECTED → CLOSED

### Material Shortage Handling
1. **Trigger**: Insufficient AVAILABLE stock for reservation
2. **Action**: Create Material Request via MRP
3. **Notification**: Alert Planner of shortage
4. **Resolution**: Procurement creates PO → GRN → stock available
5. **Retry**: Storekeeper resumes reservation

### Production Delay Handling
1. **Trigger**: WO due_date < current_date
2. **Action**: Mark as delayed
3. **Notification**: Alert Planner
4. **Resolution**: Planner reschedules or escalates

### Quality Failure Handling
1. **Trigger**: QC rejection rate > threshold
2. **Action**: Root cause analysis
3. **Notification**: Alert Planner, Production Manager
4. **Resolution**: Process improvement, supplier quality review

---

## Implementation Notes

### Existing Services to Reuse
- **InventoryService**: backend/app/application/inventory/inventory_service.py (canonical stock mutation)
- **WorkOrderHandler**: backend/app/application/manufacturing/handlers/work_order_handler.py
- **StorekeeperHandler**: backend/app/application/inventory/handlers/storekeeper_handler.py
- **WorkerHandler**: backend/app/application/manufacturing/handlers/worker_handler.py
- **DeliveryDashboardHandler**: backend/app/application/delivery/handlers/delivery_dashboard_handler.py
- **NotificationService**: backend/app/application/notification/services/notification_service.py
- **WebSocket Infrastructure**: backend/app/interfaces/api/v1/routes/websocket/__init__.py

### Existing Models
- **WorkOrderModel**: backend/app/infrastructure/persistence/models/manufacturing_model.py
- **WorkOrderMaterialModel**: backend/app/infrastructure/persistence/models/manufacturing_model.py
- **QualityInspectionModel**: backend/app/infrastructure/persistence/models/quality_model.py
- **InventoryTransactionModel**: backend/app/infrastructure/persistence/models/inventory_model.py
- **DeliveryOrderModel**: backend/app/infrastructure/persistence/models/delivery_model.py

### Next Steps
1. Implement QC Operational Execution (Phase 1)
2. Implement Storekeeper Execution Flow (Phase 2)
3. Implement Worker/Production Execution (Phase 3)
4. Implement Workflow State Hardening (Phase 4)
5. Implement Inventory Orchestration (Phase 5)
6. Implement Delivery Operational Flow (Phase 6)
7. Implement Enterprise Document Generation (Phase 7)
8. Implement Role-Based Dashboards (Phase 8)
9. UUID Cleanup (Phase 9)
10. Implement Notifications & Alerts (Phase 10)
11. Implement Finance & Procurement Orchestration (Phase 11)
12. Full E2E Validation (Phase 12)
