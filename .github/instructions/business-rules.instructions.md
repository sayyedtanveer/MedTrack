---
applyTo: |
  backend/app/domain/**/*.py
  backend/app/application/**/*.py
---

# Manufacturing Business Rules Instructions

**File:** `.github/instructions/business-rules.instructions.md`  
**Scope:** Domain layer (`backend/app/domain/`) and application handlers  
**Reference:** [AGENTS.md](../../AGENTS.md) § 15 (Inventory and Manufacturing Rules)  
**Updated:** November 9, 2026

---

## Quick Rules

1. **BOM versioning** — BOMs are immutable when active; create new version to change
2. **Work Order state machine** — Linear progression: DRAFT → RELEASED → STARTED → COMPLETED → CLOSED
3. **Material reservations** — Reserved on WO RELEASE, consumed on WO COMPLETION
4. **Low-stock alerts** — Trigger when available < reorder_point
5. **GRN validation** — GRN qty ≤ PO qty
6. **No duplicates** — Same material cannot appear twice in BOM
7. **Audit everything** — All state changes logged with user context

---

## BOM (Bill of Materials) Rules

**Non-Negotiable:**

### Rule 1: Versioning
- BOMs are **versioned**
- Only **one active version** per product template/variant
- **Cannot modify** active BOM — must create new version
- **Immutable once active** unless explicitly created a new version

```python
# ✅ CORRECT: BOM versioning pattern
class BOM(AggregateRoot):
    id: UUID
    template_id: UUID
    version: int
    is_active: bool
    lines: List[BOMLine]
    
    def __init__(self, template_id: UUID, lines: List[BOMLine]):
        self.template_id = template_id
        self.version = 1  # First version
        self.is_active = True
        self.lines = lines
    
    def add_line(self, line: BOMLine) -> None:
        """Cannot add lines to active BOM — must create new version."""
        if self.is_active:
            raise CannotModifyActiveBOMError(self.id)
        if any(l.material_id == line.material_id for l in self.lines):
            raise DuplicateComponentError(line.material_id)
        self.lines.append(line)

# Handler: Create new BOM version
async def handle_update_bom(self, cmd: UpdateBOMCommand) -> UUID:
    # Get current active BOM
    current_bom = await self.repo.get_active_by_template(cmd.template_id)
    if not current_bom:
        raise BOMMustExistError()
    
    # Deactivate current
    current_bom.is_active = False
    
    # Create new version
    new_bom = BOM(template_id=cmd.template_id, lines=cmd.lines)
    new_bom.version = current_bom.version + 1
    new_bom.is_active = True
    
    # Save both
    await self.repo.save_bom(current_bom)
    await self.repo.save_bom(new_bom)
    
    return new_bom.id
```

### Rule 2: No Duplicates
- Same material cannot appear twice in single BOM

```python
# ✅ CORRECT: Duplicate detection
class BOM(AggregateRoot):
    def add_line(self, line: BOMLine) -> None:
        if any(l.material_id == line.material_id for l in self.lines):
            raise DuplicateComponentError(line.material_id)
        self.lines.append(line)
```

### Rule 3: References Must Exist
- All materials and templates must exist and be active

```python
# ✅ CORRECT: Reference validation
async def handle_create_bom(self, cmd: CreateBOMCommand) -> UUID:
    template = await self.template_repo.get_by_id(cmd.template_id)
    if not template or template.is_deleted:
        raise TemplateNotFoundError(cmd.template_id)
    
    for line in cmd.lines:
        material = await self.material_repo.get_by_id(line.material_id)
        if not material or material.is_deleted:
            raise MaterialNotFoundError(line.material_id)
    
    # Create BOM
    bom = BOM(template_id=cmd.template_id, lines=cmd.lines)
    bom_id = await self.repo.save(bom)
    return bom_id
```

---

## Work Order State Machine

**Non-Negotiable Linear Progression:**

```
DRAFT → RELEASED → STARTED → COMPLETED → CLOSED
  ↓       ↓        ↓
  └──────────→ CANCELLED (from DRAFT, RELEASED, STARTED only)
```

### Rule 1: No Skipping Steps
- Cannot go directly from DRAFT to STARTED
- Cannot go from COMPLETED to RELEASED
- Only valid transitions allowed

```python
# ✅ CORRECT: State machine validation
class WorkOrder(AggregateRoot):
    status: WorkOrderStatus
    
    def set_status(self, new_status: WorkOrderStatus) -> None:
        """Enforce valid state transitions."""
        valid_transitions = {
            WorkOrderStatus.DRAFT: [WorkOrderStatus.RELEASED, WorkOrderStatus.CANCELLED],
            WorkOrderStatus.RELEASED: [WorkOrderStatus.STARTED, WorkOrderStatus.CANCELLED],
            WorkOrderStatus.STARTED: [WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED],
            WorkOrderStatus.COMPLETED: [WorkOrderStatus.CLOSED],
            WorkOrderStatus.CLOSED: [],
            WorkOrderStatus.CANCELLED: [],
        }
        
        if new_status not in valid_transitions.get(self.status, []):
            raise InvalidStateTransitionError(
                from_state=self.status,
                to_state=new_status
            )
        
        self.status = new_status
        self.events.append(WorkOrderStatusChangedEvent(self.id, new_status))

# ❌ WRONG: Bypassing state machine
wo.status = WorkOrderStatus.COMPLETED  # Direct assignment without validation
```

### Rule 2: Cannot Cancel After Completion
- Only DRAFT, RELEASED, STARTED can be cancelled
- COMPLETED and CLOSED are final

```python
# ✅ CORRECT: Cancel validation
def cancel(self) -> None:
    if self.status in [WorkOrderStatus.COMPLETED, WorkOrderStatus.CLOSED, WorkOrderStatus.CANCELLED]:
        raise CannotCancelWorkOrderError(self.id, self.status)
    self.status = WorkOrderStatus.CANCELLED
    self.events.append(WorkOrderCancelledEvent(self.id))
```

---

## Material Reservation and Consumption

**Non-Negotiable Inventory Transaction Workflow:**

### Rule 1: Reserve on Release
- When WO status changes to RELEASED → reserve materials
- Materials blocked from other reservations
- Insufficient stock → raises error, WO stays DRAFT

```python
# ✅ CORRECT: Reservation on release
async def handle_release_work_order(self, cmd: ReleaseWorkOrderCommand) -> UUID:
    tenant_id = get_tenant_id()
    
    # Get work order
    wo = await self.repo.get_by_id(tenant_id, cmd.work_order_id)
    if not wo:
        raise WorkOrderNotFoundError(cmd.work_order_id)
    
    # Check stock availability before releasing
    for material_id, qty in wo.materials.items():
        available = await self.inventory_service.get_available_quantity(
            tenant_id, material_id
        )
        if available < qty:
            raise InsufficientStockError(material_id, qty, available)
    
    # Reserve materials (atomic operation)
    for material_id, qty in wo.materials.items():
        await self.inventory_service.reserve_materials(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=qty,
            work_order_id=wo.id
        )
    
    # Update status
    wo.set_status(WorkOrderStatus.RELEASED)
    await self.repo.save(wo)
    
    return wo.id
```

### Rule 2: Consume on Completion
- When WO status changes to COMPLETED → consume reserved materials
- Materials removed from inventory
- Cannot unconsume (soft delete WO if needed)

```python
# ✅ CORRECT: Consumption on completion
async def handle_complete_work_order(self, cmd: CompleteWorkOrderCommand) -> UUID:
    tenant_id = get_tenant_id()
    
    # Get work order
    wo = await self.repo.get_by_id(tenant_id, cmd.work_order_id)
    if not wo or wo.status != WorkOrderStatus.STARTED:
        raise InvalidWorkOrderStateError(wo.id, wo.status)
    
    # Consume materials (removes from inventory, releases reservation)
    for material_id, qty in wo.materials.items():
        await self.inventory_service.consume_materials(
            tenant_id=tenant_id,
            material_id=material_id,
            quantity=qty,
            work_order_id=wo.id
        )
    
    # Update status
    wo.set_status(WorkOrderStatus.COMPLETED)
    await self.repo.save(wo)
    
    logger.info("Work order completed", extra={
        "wo_id": str(wo.id),
        "tenant_id": str(tenant_id)
    })
    
    return wo.id
```

### Rule 3: Release on Cancellation
- When WO status changes to CANCELLED → release reserved materials
- Materials go back to available inventory
- Only if WO was RELEASED or STARTED

```python
# ✅ CORRECT: Release on cancellation
async def handle_cancel_work_order(self, cmd: CancelWorkOrderCommand) -> None:
    tenant_id = get_tenant_id()
    
    wo = await self.repo.get_by_id(tenant_id, cmd.work_order_id)
    if not wo:
        raise WorkOrderNotFoundError(cmd.work_order_id)
    
    # Only DRAFT, RELEASED, STARTED can be cancelled
    if wo.status not in [WorkOrderStatus.DRAFT, WorkOrderStatus.RELEASED, WorkOrderStatus.STARTED]:
        raise CannotCancelWorkOrderError(wo.id, wo.status)
    
    # Release reserved materials (only if RELEASED or STARTED)
    if wo.status in [WorkOrderStatus.RELEASED, WorkOrderStatus.STARTED]:
        for material_id, qty in wo.materials.items():
            await self.inventory_service.release_materials(
                tenant_id=tenant_id,
                material_id=material_id,
                quantity=qty,
                work_order_id=wo.id
            )
    
    # Cancel
    wo.cancel()
    await self.repo.save(wo)
```

---

## Low-Stock Alerts

**Non-Negotiable Alert Logic:**

### Rule: Trigger on Availability < Reorder Point

```python
# ✅ CORRECT: Low-stock alert
async def handle_consume_materials(
    self,
    tenant_id: UUID,
    material_id: UUID,
    quantity: Decimal
) -> None:
    material = await self.repo.get_by_id(tenant_id, material_id)
    
    # Consume
    material.available_quantity -= quantity
    await self.repo.save(material)
    
    # Check if below reorder point
    if material.available_quantity < material.reorder_point:
        event = LowStockAlertTriggeredEvent(
            material_id=material.id,
            current_qty=material.available_quantity,
            reorder_point=material.reorder_point
        )
        await self.event_dispatcher.publish(event)
```

---

## GRN (Goods Receipt Note) Validation

**Non-Negotiable PO Constraint:**

### Rule: GRN Qty ≤ PO Qty

```python
# ✅ CORRECT: GRN validation against PO
async def handle_create_grn(self, cmd: CreateGRNCommand) -> UUID:
    tenant_id = get_tenant_id()
    
    # Get PO
    po = await self.po_repo.get_by_id(tenant_id, cmd.po_id)
    if not po:
        raise PONotFoundError(cmd.po_id)
    
    # Validate GRN qty against PO qty
    total_grn_qty = await self.grn_repo.get_total_received(po.id)
    if total_grn_qty + cmd.quantity > po.quantity:
        raise ExcessiveGRNError(
            po_id=po.id,
            po_qty=po.quantity,
            attempted_grn=cmd.quantity,
            already_received=total_grn_qty
        )
    
    # Create GRN
    grn = GRN(
        po_id=cmd.po_id,
        quantity=cmd.quantity,
        received_date=datetime.utcnow()
    )
    
    grn_id = await self.grn_repo.save(grn)
    
    # Publish event for inventory update
    await self.event_dispatcher.publish(
        GRNReceivedEvent(po_id=po.id, grn_id=grn_id, quantity=cmd.quantity)
    )
    
    return grn_id
```

---

## Quality Control Workflow

**Non-Negotiable QC Process:**

### Rule: Status Linear Progression
```
PENDING → IN_PROGRESS → PASSED / FAILED
```

```python
# ✅ CORRECT: QC workflow
class QCInspection(AggregateRoot):
    status: QCStatus  # PENDING, IN_PROGRESS, PASSED, FAILED
    
    def start_inspection(self) -> None:
        if self.status != QCStatus.PENDING:
            raise InvalidQCStateError(self.id, self.status)
        self.status = QCStatus.IN_PROGRESS
        self.events.append(QCInspectionStartedEvent(self.id))
    
    def pass_inspection(self, notes: str = "") -> None:
        if self.status != QCStatus.IN_PROGRESS:
            raise InvalidQCStateError(self.id, self.status)
        self.status = QCStatus.PASSED
        self.notes = notes
        self.events.append(QCInspectionPassedEvent(self.id))
    
    def fail_inspection(self, notes: str) -> None:
        if self.status != QCStatus.IN_PROGRESS:
            raise InvalidQCStateError(self.id, self.status)
        self.status = QCStatus.FAILED
        self.notes = notes
        self.events.append(QCInspectionFailedEvent(self.id))
```

---

## Sales Order Approval Workflow

**Non-Negotiable Approval Process:**

### Rule: Status Linear Progression
```
DRAFT → APPROVED → MANUFACTURING → DELIVERED
```

```python
# ✅ CORRECT: Sales order workflow
class SalesOrder(AggregateRoot):
    status: SalesOrderStatus  # DRAFT, APPROVED, MANUFACTURING, DELIVERED, CANCELLED
    priority: OrderPriority   # LOW, MEDIUM, HIGH, URGENT
    
    def approve(self) -> None:
        if self.status != SalesOrderStatus.DRAFT:
            raise InvalidOrderStateError(self.id, self.status)
        self.status = SalesOrderStatus.APPROVED
        self.events.append(SalesOrderApprovedEvent(self.id))
    
    def set_priority(self, priority: OrderPriority) -> None:
        if self.status != SalesOrderStatus.DRAFT:
            raise CannotChangePriorityError(self.id)
        self.priority = priority
```

---

## Domain Exception Naming

**Clear, specific exceptions for all business rules:**

```python
# ✅ CORRECT: Specific exceptions
class DuplicateComponentError(DomainException):
    def __init__(self, material_id: UUID):
        self.code = "DUPLICATE_COMPONENT"
        self.message = f"Material {material_id} already exists in this BOM"

class InsufficientStockError(DomainException):
    def __init__(self, material_id: UUID, required: Decimal, available: Decimal):
        self.code = "INSUFFICIENT_STOCK"
        self.message = f"Insufficient stock for {material_id}: required {required}, available {available}"

class InvalidStateTransitionError(DomainException):
    def __init__(self, from_state: str, to_state: str):
        self.code = "INVALID_STATE_TRANSITION"
        self.message = f"Cannot transition from {from_state} to {to_state}"

class ExcessiveGRNError(DomainException):
    def __init__(self, po_id: UUID, po_qty: Decimal, attempted_grn: Decimal, already_received: Decimal):
        self.code = "EXCESSIVE_GRN"
        self.message = f"GRN exceeds PO: PO={po_qty}, already received={already_received}, attempted={attempted_grn}"
```

---

## Audit Trail Requirements

**All business state changes must be logged:**

```python
# ✅ CORRECT: Audit logging
async def handle_release_work_order(self, cmd: ReleaseWorkOrderCommand) -> UUID:
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    wo = await self.repo.get_by_id(tenant_id, cmd.work_order_id)
    
    # Business operation
    wo.set_status(WorkOrderStatus.RELEASED)
    
    # Audit log
    logger.info(
        "Work order released",
        extra={
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "work_order_id": str(wo.id),
            "previous_status": str(WorkOrderStatus.DRAFT),
            "new_status": str(WorkOrderStatus.RELEASED),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    await self.repo.save(wo)
    return wo.id
```

---

## Do's and Don'ts

| Do | Don't |
|----|-------|
| ✅ Enforce state machines | ❌ Allow invalid transitions |
| ✅ Check inventory before reserving | ❌ Reserve without stock check |
| ✅ Create new BOM versions | ❌ Modify active BOMs |
| ✅ Validate GRN against PO | ❌ Accept excessive GRNs |
| ✅ Log all state changes | ❌ Silent state modifications |
| ✅ Raise specific exceptions | ❌ Generic errors |
| ✅ Include audit context | ❌ Skip user/tenant context |

---

## Reference

- **Full Business Rules:** [MANUFACTURING_BUSINESS_RULES.md](../../docs/ai-guidelines/MANUFACTURING_BUSINESS_RULES.md)
- **Domain Entities:** `backend/app/domain/*/entities/`
- **Domain Exceptions:** `backend/app/domain/shared/exceptions.py`
- **Application Handlers:** `backend/app/application/*/handlers/`

---

**Status:** Production Ready  
**Last Updated:** November 9, 2026
