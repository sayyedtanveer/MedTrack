# Backend Python Patterns for Copilot

When working with backend Python files, always follow these guidelines.

**applyTo:** `backend/**/*.py`

## DDD & CQRS

**See:** [`docs/ai-guidelines/BACKEND_STANDARDS.md`](../../docs/ai-guidelines/BACKEND_STANDARDS.md) (comprehensive patterns)

**Quick Rules:**
- Domain layer: Pure business logic, NO infrastructure imports
- Application layer: Commands (write), Queries (read), Handlers (orchestration)
- Infrastructure layer: Repositories, ORM, Security, Logging
- Interfaces layer: Routes (thin HTTP translation layer)

**Command Pattern:**
```python
@dataclass
class CreateMaterialCommand:
    code: str
    name: str

async def handle_create_material(self, cmd: CreateMaterialCommand) -> UUID:
    material = Material(code=cmd.code, name=cmd.name)
    await self.validate_business_rules(material)  # May raise DomainException
    material_id = await self.uow.save(material)
    await self.event_dispatcher.publish(material.events)
    return material_id
```

## Type Safety

**Required:** Full type hints on all functions and parameters

```python
from typing import List, Optional, Dict
from uuid import UUID
from decimal import Decimal

async def create_work_order(
    self,
    tenant_id: UUID,
    sales_order_id: UUID,
    quantities: Dict[UUID, Decimal]
) -> UUID:
    # implementation
    return work_order_id
```

## Async-First

**Required:** `await` all I/O operations (database, HTTP, files)

```python
# ✅ CORRECT: Async database call
result = await session.execute(stmt)

# ❌ WRONG: Synchronous call in async function
result = sync_session.execute(stmt)  # Blocks event loop
```

## Multi-Tenancy

**Required:** Tenant filter on every SELECT query

```python
# ✅ CORRECT
stmt = select(Material).where(
    Material.tenant_id == tenant_id,        # Mandatory
    Material.is_deleted == False            # Mandatory
)

# ❌ WRONG: No tenant filter
stmt = select(Material).where(Material.status == "ACTIVE")
```

## Soft Deletes

**Required:** Check `is_deleted = False` on all SELECT queries

```python
# ✅ CORRECT: Soft delete check
stmt = select(Entity).where(
    Entity.tenant_id == tenant_id,
    Entity.is_deleted == False  # Mandatory
)

# ❌ WRONG: No soft delete check
stmt = select(Entity).where(Entity.tenant_id == tenant_id)
```

## Repository Pattern

```python
class MaterialRepository(IMaterialRepository):
    async def get_by_id(self, tenant_id: UUID, material_id: UUID) -> Material | None:
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.id == material_id,
            MaterialModel.is_deleted == False
        )
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return Material.from_model(model) if model else None
```

## Error Handling

**Never silent failures. Always log before re-raising.**

```python
async def handle_release_work_order(self, cmd: ReleaseWorkOrderCommand) -> ReleaseWorkOrderResponse:
    try:
        wo = await self.repo.get_by_id(cmd.work_order_id)
        if not wo:
            raise WorkOrderNotFoundError(cmd.work_order_id)
        
        await self.inventory_service.reserve_materials(wo.materials)
        wo.set_status(WorkOrderStatus.RELEASED)
        await self.repo.save(wo)
        
        logger.info("WO released", extra={"wo_id": str(wo.id)})
        return ReleaseWorkOrderResponse(id=wo.id)
    except DomainException as e:
        logger.warning("Release failed", extra={"error": str(e)})
        raise
```

## Structured Logging

```python
logger.info(
    "Material created",
    extra={
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "material_id": str(material_id),
        "correlation_id": correlation_id
    }
)
```

## Dependency Injection

**No global singletons. Always inject dependencies.**

```python
class BOMHandlers:
    def __init__(self, repo: IBOMRepository, uow: IUnitOfWork, event_dispatcher: IEventDispatcher):
        self.repo = repo
        self.uow = uow
        self.event_dispatcher = event_dispatcher
```

## Testing Patterns

**Unit test: Pure domain logic**
```python
@pytest.mark.unit
def test_bom_duplicate_component_raises_error():
    bom = BOM(id=uuid.uuid4(), lines=[])
    line = BOMLine(material_id=uuid.uuid4(), quantity=Decimal("10"))
    bom.add_line(line)
    with pytest.raises(DuplicateComponentError):
        bom.add_line(line)
```

**Integration test: With database**
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_material_repository_filters_by_tenant(db_session):
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    
    repo = MaterialRepository(db_session)
    mat1 = await repo.create(tenant1_id, Material(...))
    mat2 = await repo.create(tenant2_id, Material(...))
    
    results = await repo.list_by_tenant(tenant1_id)
    assert len(results) == 1
    assert results[0].id == mat1.id
```

---

**Reference:** [`docs/ai-guidelines/BACKEND_STANDARDS.md`](../../docs/ai-guidelines/BACKEND_STANDARDS.md)
