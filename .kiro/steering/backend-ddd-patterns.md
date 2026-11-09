---
name: "Backend DDD & CQRS Patterns"
description: "Domain-Driven Design, CQRS command/query handlers, repository patterns, and domain events for backend implementation"
inclusion: fileMatch
fileMatchPattern:
  - "backend/app/domain/**/*.py"
  - "backend/app/application/**/*.py"
  - "backend/app/infrastructure/persistence/**/*.py"
---

# Backend DDD & CQRS Patterns

**Canonical Reference:** [`AGENTS.md`](../../AGENTS.md) Sections 5, 9, 14  
**Detailed Guide:** [`BACKEND_STANDARDS.md`](../../docs/ai-guidelines/BACKEND_STANDARDS.md)

---

## DDD Layer Responsibilities

### Layer 1: Domain (`backend/app/domain/`)
**Purpose:** Pure business logic, zero infrastructure dependencies

**Contains:**
- **Entities** — Objects with identity (BOM, WorkOrder, Material)
- **Value Objects** — Immutable values (Money, Quantity, Component)
- **Domain Events** — State change notifications (WorkOrderReleased, MaterialConsumed)
- **Domain Exceptions** — Business rule violations (InsufficientStockError, DuplicateComponentError)
- **Repository Interfaces** — Abstract data contracts (IBOMRepository, IMaterialRepository)

**Rules:**
- ❌ No database imports (no SQLAlchemy)
- ❌ No HTTP imports (no FastAPI)
- ❌ No external service calls
- ✅ Type hints on all functions
- ✅ Docstrings explaining business logic

**Example Structure:**
```
domain/bom/
├── entities/
│   ├── bom.py              # BOM entity with business methods
│   └── bom_line.py         # BOMLine value object
├── value_objects/
│   ├── component.py        # (material_id, quantity, scrap%)
│   └── routing_step.py     # (operation, sequence, time)
├── events/
│   ├── bom_created.py      # BOMCreatedEvent
│   └── bom_activated.py    # BOMActivatedEvent
├── exceptions/
│   ├── duplicate_component_error.py
│   └── invalid_bom_state_error.py
├── interfaces/
│   └── bom_repository.py   # IBOMRepository (abstract)
└── __init__.py
```

### Layer 2: Application (`backend/app/application/`)
**Purpose:** Use cases, command/query orchestration, transaction management

**Contains:**
- **Commands** — Write operations (CreateBOMCommand, ReleaseWorkOrderCommand)
- **Queries** — Read operations (GetBOMQuery, ListMaterialsQuery)
- **Handlers** — CQRS logic (BOMHandlers, WorkOrderHandlers)
- **DTOs** — Data transfer objects for responses

**Rules:**
- ✅ Orchestrates domain and infrastructure
- ✅ Handles transactions (UnitOfWork)
- ✅ Publishes domain events
- ✅ Catches domain exceptions and logs
- ❌ No HTTP response codes (that's interfaces layer)
- ❌ No direct database queries (uses repositories)

**Example Command Handler:**
```python
# Command definition
@dataclass
class CreateBOMCommand:
    template_id: UUID
    lines: List[BOMLineInput]

# Handler
class BOMHandlers:
    def __init__(self, repo: IBOMRepository, uow: IUnitOfWork):
        self.repo = repo
        self.uow = uow
    
    async def handle_create_bom(self, cmd: CreateBOMCommand) -> UUID:
        # Validate
        template = await self.repo.get_template(cmd.template_id)
        if not template:
            raise TemplateNotFoundError(cmd.template_id)
        
        # Create entity
        bom = BOM(template_id=cmd.template_id)
        
        # Apply business rules
        for line in cmd.lines:
            bom.add_line(line)  # May raise DomainException
        
        # Persist
        bom_id = await self.uow.save_bom(bom)
        
        # Publish events
        await self.event_dispatcher.publish(bom.events)
        
        return bom_id
```

### Layer 3: Infrastructure (`backend/app/infrastructure/`)
**Purpose:** Persistence, external services, security, logging

**Contains:**
- **Repositories** — Implement domain repository interfaces
- **ORM Models** — SQLAlchemy models mapping to database tables
- **Unit of Work** — Transaction coordination
- **Security** — JWT, RBAC, bcrypt
- **Event Dispatcher** — Publish/subscribe domain events
- **Logging** — structlog with tenant context

**Rules:**
- ✅ Implements domain interfaces
- ✅ All I/O is async (database, HTTP, cache)
- ✅ Connection pooling, caching, optimization
- ❌ No business logic (that's domain layer)

### Layer 4: Interfaces (`backend/app/interfaces/`)
**Purpose:** HTTP API endpoints, thin translation layer

**Contains:**
- **Routes** — FastAPI route handlers
- **Schemas** — Pydantic request/response models
- **Middleware** — Request/response processing (tenant, RBAC, logging)

**Rules:**
- ✅ Thin routing logic only
- ✅ Request validation via Pydantic
- ✅ Response serialization
- ✅ HTTP error mapping (401, 403, 422)
- ❌ No business logic
- ❌ No database queries

---

## CQRS Command Pattern

**Structure:**
```python
# 1. Define command
@dataclass
class ReleaseWorkOrderCommand:
    work_order_id: UUID
    expected_completion_date: datetime

# 2. Validate in route
@router.post("/work-orders/{id}/release")
async def release_work_order(
    id: UUID,
    request: ReleaseWorkOrderRequest  # Pydantic validates
):
    # 3. Convert to command
    cmd = ReleaseWorkOrderCommand(
        work_order_id=id,
        expected_completion_date=request.expected_completion_date
    )
    
    # 4. Execute handler
    result = await handlers.handle_release(cmd)
    
    # 5. Return response
    return WorkOrderResponse.from_entity(result)
```

**Handler Responsibilities:**
- Fetch aggregate from repository
- Call domain business methods (may raise DomainException)
- Save to unit of work
- Publish domain events
- Return DTO for response

---

## CQRS Query Pattern

**Structure:**
```python
# 1. Define query
@dataclass
class GetBOMQuery:
    bom_id: UUID

# 2. Execute handler
async def handle_get_bom(self, query: GetBOMQuery) -> BOMResponse:
    # Fetch entity
    bom = await self.repo.get_by_id(query.bom_id)
    if not bom:
        raise BOMNotFoundError(query.bom_id)
    
    # Convert to DTO (no side effects)
    return BOMResponse.from_entity(bom)

# 3. In route
@router.get("/boms/{id}")
async def get_bom(id: UUID):
    query = GetBOMQuery(bom_id=id)
    result = await handlers.handle_get_bom(query)
    return result
```

**Query Responsibilities:**
- Read from repository
- No mutations
- No domain events
- Return DTOs only

---

## Repository Interface Pattern

**Define in domain layer:**
```python
# domain/bom/interfaces/bom_repository.py
from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

class IBOMRepository(ABC):
    @abstractmethod
    async def get_by_id(self, tenant_id: UUID, bom_id: UUID) -> BOM | None:
        """Get BOM by ID (soft delete filter applied)"""
        pass
    
    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID) -> List[BOM]:
        """List all active BOMs for tenant"""
        pass
    
    @abstractmethod
    async def save(self, bom: BOM) -> None:
        """Persist BOM (insert or update)"""
        pass
```

**Implement in infrastructure:**
```python
# infrastructure/persistence/repositories/bom_repository.py
from backend.app.domain.bom.interfaces import IBOMRepository

class BOMRepository(IBOMRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, tenant_id: UUID, bom_id: UUID) -> BOM | None:
        stmt = select(BOMModel).where(
            BOMModel.tenant_id == tenant_id,
            BOMModel.id == bom_id,
            BOMModel.is_deleted == False
        )
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return BOM.from_model(model) if model else None
    
    async def list_by_tenant(self, tenant_id: UUID) -> List[BOM]:
        stmt = select(BOMModel).where(
            BOMModel.tenant_id == tenant_id,
            BOMModel.is_deleted == False
        ).order_by(BOMModel.created_at.desc())
        result = await self.session.execute(stmt)
        return [BOM.from_model(m) for m in result.scalars().all()]
```

---

## Domain Event Pattern

**Define in domain:**
```python
# domain/bom/events/bom_activated.py
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime

@dataclass
class BOMActivatedEvent:
    bom_id: UUID
    template_id: UUID
    previous_active_bom_id: UUID | None
    activated_at: datetime
    tenant_id: UUID
```

**Raise in entity:**
```python
class BOM:
    def __init__(self, ...):
        self.events: List[DomainEvent] = []
    
    async def activate(self):
        """Set as active BOM, deactivate others"""
        # Business logic
        self.status = BOMStatus.ACTIVE
        
        # Publish event
        self.events.append(BOMActivatedEvent(
            bom_id=self.id,
            template_id=self.template_id,
            previous_active_bom_id=...,
            activated_at=datetime.utcnow(),
            tenant_id=self.tenant_id
        ))
```

**Handle in subscribers:**
```python
# Event subscriber in infrastructure
class BOMActivationSubscriber:
    async def on_bom_activated(self, event: BOMActivatedEvent):
        # Deactivate previous BOM
        await self.repo.deactivate(event.tenant_id, event.previous_active_bom_id)
        # Notify planning service
        await self.notification_service.notify_planners(...)
        # Publish WebSocket update
        await self.ws_manager.broadcast(event)
```

---

## Multi-Tenancy in Handlers

**See:** [security.instructions.md](../../.github/instructions/security.instructions.md) § Multi-Tenancy Filtering

**Quick Rule: Tenant from context, never from parameters**

```python
from backend.app.infrastructure.context import get_tenant_id

class MaterialHandlers:
    async def handle_list_materials(self, query: ListMaterialsQuery) -> List[MaterialResponse]:
        # ✅ Correct: Extract from context (set by middleware)
        tenant_id = get_tenant_id()
        materials = await self.repo.list_by_tenant(tenant_id)
        return [MaterialResponse.from_entity(m) for m in materials]
```

**Every repository call includes tenant_id:**
```python
# ✅ Correct
await repo.get_by_id(tenant_id, material_id)

# ❌ Wrong
await repo.get_by_id(material_id)
```

For full multi-tenancy security details, see the canonical security guide.

---

## Dependency Injection

**Container setup (infrastructure/di/):**
```python
from dependency_injector import containers, providers

class MedTrackContainer(containers.DeclarativeContainer):
    # Repositories
    bom_repo = providers.Singleton(
        BOMRepository,
        session=...
    )
    
    # Handlers
    bom_handlers = providers.Singleton(
        BOMHandlers,
        repo=bom_repo,
        uow=...
    )
```

**Inject into routes:**
```python
@router.post("/boms")
async def create_bom(
    request: CreateBOMRequest,
    handlers: BOMHandlers = Depends(get_bom_handlers)  # Injected
):
    cmd = CreateBOMCommand(...)
    result = await handlers.handle_create_bom(cmd)
    return result
```

---

## Error Handling

**Raise domain exceptions in domain layer:**
```python
class BOM:
    def add_line(self, line: BOMLineInput):
        if self._component_exists(line.material_id):
            raise DuplicateComponentError(line.material_id)  # Domain exception
```

**Catch and convert in handlers:**
```python
async def handle_create_bom(self, cmd: CreateBOMCommand):
    try:
        bom = BOM(...)
        bom.add_line(...)  # May raise DuplicateComponentError
    except DuplicateComponentError as e:
        logger.warning("Duplicate component", extra={"material_id": str(e.material_id)})
        raise  # Re-raise for route to convert to HTTP 422
```

**Convert to HTTP in routes:**
```python
@app.exception_handler(DuplicateComponentError)
async def duplicate_component_error_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": "Component already in BOM", "code": "DUPLICATE_COMPONENT"}
    )
```

---

## Async I/O Best Practices

**✅ Always async:**
```python
async def handle_list_materials(self):
    # ✅ Async database call
    materials = await self.repo.list_by_tenant(tenant_id)
    return materials
```

**❌ Never block:**
```python
async def handle_list_materials(self):
    # ❌ Wrong: Synchronous call in async function
    materials = sync_repo.list_materials(tenant_id)
    return materials
```

**✅ Async comprehensions:**
```python
# ✅ Correct: Process async results
results = [Material.from_model(m) async for m in async_generator]

# ❌ Wrong: Blocking call in loop
results = [await repo.get_by_id(id) for id in ids]  # Sequential, slow
```

---

## Testing Patterns

**Unit test (pure domain logic):**
```python
@pytest.mark.unit
def test_bom_duplicate_component_raises_error():
    bom = BOM(id=uuid.uuid4(), lines=[])
    line = BOMLine(material_id=uuid.uuid4(), quantity=Decimal("10"))
    bom.add_line(line)
    with pytest.raises(DuplicateComponentError):
        bom.add_line(line)
```

**Integration test (with database):**
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_bom_repository_filters_by_tenant(db_session):
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    
    repo = BOMRepository(db_session)
    bom1 = await repo.create(tenant1_id, BOM(...))
    bom2 = await repo.create(tenant2_id, BOM(...))
    
    results = await repo.list_by_tenant(tenant1_id)
    assert len(results) == 1
    assert results[0].id == bom1.id
```

---

## Key Checklist

When implementing backend features:

- [ ] Domain entity/value objects define business logic
- [ ] Domain exceptions raised for business rule violations
- [ ] Domain events published when state changes
- [ ] Repository interface defined in domain layer
- [ ] Repository implementation in infrastructure layer
- [ ] Command handler orchestrates domain + infrastructure
- [ ] Query handler reads without side effects
- [ ] Tenant ID extracted from context, not parameters
- [ ] All I/O is async
- [ ] Type hints on all functions
- [ ] Tests cover unit + integration scenarios

---

**Reference:** [`IMPLEMENTATION_WORKFLOW.md`](../../docs/ai-guidelines/IMPLEMENTATION_WORKFLOW.md)
