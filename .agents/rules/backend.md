---
trigger: glob
globs: "backend/app/**/*.py, backend/**/*.py"
description: "Backend Python patterns: DDD, CQRS, async patterns, type hints, dependency injection"
---

# Backend Python Implementation Patterns

**Reference:** See `docs/ai-guidelines/BACKEND_STANDARDS.md` for comprehensive patterns

## DDD Layer Structure

**Layer 1: Domain** (`backend/app/domain/`)
- Pure business logic, NO infrastructure imports
- Entities, Value Objects, Domain Events, Domain Exceptions
- Repository interfaces (abstract contracts)

**Layer 2: Application** (`backend/app/application/`)
- Commands (write operations), Queries (read operations), Handlers
- Orchestrates domain + infrastructure
- Handles transactions via Unit of Work
- Publishes domain events

**Layer 3: Infrastructure** (`backend/app/infrastructure/`)
- Repositories (implement domain interfaces)
- ORM models (SQLAlchemy), Event Dispatcher
- Security, Logging, DI Container

**Layer 4: Interfaces** (`backend/app/interfaces/`)
- Routes (thin HTTP layer)
- Schemas (Pydantic request/response validation)
- Middleware (tenant, RBAC, logging)

## CQRS Pattern (Mandatory)

**Commands:** Write operations
```python
@dataclass
class CreateBOMCommand:
    template_id: UUID
    lines: List[BOMLineInput]

async def handle_create_bom(self, cmd: CreateBOMCommand) -> UUID:
    # Validate, create entity, apply rules, persist, publish events
    return bom_id
```

**Queries:** Read operations (NO side effects)
```python
@dataclass
class GetBOMQuery:
    bom_id: UUID

async def handle_get_bom(self, query: GetBOMQuery) -> BOMResponse:
    bom = await self.repo.get_by_id(query.bom_id)
    return BOMResponse.from_entity(bom)
```

## Async-First (MANDATORY)

```python
# ✅ All I/O is async
async def list_materials(self, tenant_id: UUID) -> List[Material]:
    stmt = select(MaterialModel).where(
        MaterialModel.tenant_id == tenant_id,
        MaterialModel.is_deleted == False
    )
    result = await session.execute(stmt)
    return [Material.from_model(m) for m in result.scalars().all()]

# ❌ WRONG: Blocking call in async function
sync_result = sync_repo.list_materials()
```

## Type Hints (Required on All Functions)

```python
async def create_material(
    self,
    tenant_id: UUID,
    code: str,
    name: str
) -> Material:
    """Create new material in tenant scope."""
```

## Dependency Injection (NO Global Singletons)

```python
class BOMHandlers:
    def __init__(self, repo: IBOMRepository, uow: IUnitOfWork):
        self.repo = repo
        self.uow = uow
```

## Error Handling

**Domain layer raises specific exceptions:**
```python
if self._component_exists(line.material_id):
    raise DuplicateComponentError(line.material_id)
```

**Application layer catches and logs:**
```python
except DuplicateComponentError as e:
    logger.warning("Duplicate component", extra={"material_id": str(e.material_id)})
    raise
```

**Interface layer converts to HTTP:**
```python
@app.exception_handler(DuplicateComponentError)
async def duplicate_component_error_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": "Component already in BOM", "code": "DUPLICATE_COMPONENT"}
    )
```

## Multi-Tenancy in Handlers

**MANDATORY: Tenant from context, never from parameters**
```python
from backend.app.infrastructure.context import get_tenant_id

async def handle_list_materials(self) -> List[MaterialResponse]:
    tenant_id = get_tenant_id()  # From JWT via middleware
    materials = await self.repo.list_by_tenant(tenant_id)
    return [MaterialResponse.from_entity(m) for m in materials]
```

