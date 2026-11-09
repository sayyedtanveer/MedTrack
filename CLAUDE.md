# Claude AI Coding Guidelines for MedTrack

**Model:** Claude Haiku 4.5+  
**Purpose:** Implement features, fix bugs, conduct code review  
**Last Updated:** November 9, 2026  
**Status:** Production Ready

---

## Canonical References

This file is a **quick-start guide for Claude**. For complete standards, refer to:

| Task | Reference File |
|------|-----------------|
| **Any code change** | [`AGENTS.md`](AGENTS.md) (sections 5-13: backend, frontend, database, API, auth, multi-tenancy) |
| **Architecture & Design** | [`docs/ai-guidelines/SYSTEM_ARCHITECTURE.md`](docs/ai-guidelines/SYSTEM_ARCHITECTURE.md) |
| **Python Implementation** | [`docs/ai-guidelines/BACKEND_STANDARDS.md`](docs/ai-guidelines/BACKEND_STANDARDS.md) |
| **React Implementation** | [`docs/ai-guidelines/FRONTEND_STANDARDS.md`](docs/ai-guidelines/FRONTEND_STANDARDS.md) |
| **Database & Migrations** | [`docs/ai-guidelines/DATABASE_STANDARDS.md`](docs/ai-guidelines/DATABASE_STANDARDS.md) |
| **Security & Multi-Tenancy** | [`docs/ai-guidelines/SECURITY_AND_MULTITENANCY.md`](docs/ai-guidelines/SECURITY_AND_MULTITENANCY.md) (includes 4 control audits) |
| **Manufacturing Rules** | [`docs/ai-guidelines/MANUFACTURING_BUSINESS_RULES.md`](docs/ai-guidelines/MANUFACTURING_BUSINESS_RULES.md) |
| **Workflow for Any Task** | [`docs/ai-guidelines/IMPLEMENTATION_WORKFLOW.md`](docs/ai-guidelines/IMPLEMENTATION_WORKFLOW.md) (12 steps) |
| **Quality Checklist** | [`docs/ai-guidelines/DEFINITION_OF_DONE.md`](docs/ai-guidelines/DEFINITION_OF_DONE.md) (13 items) |

---

## 5-Minute Startup

### 1. Understand the Stack

**Backend** (Python 3.11+):
```
FastAPI 0.111.0 (async web framework)
  ↓
SQLAlchemy 2.0.30 async ORM
  ↓
asyncpg 0.29.0 (PostgreSQL driver)
  ↓
Pydantic v2.7.1 (validation)
  ↓
structlog 24.4.0 (structured logging)
```

**Frontend** (Node.js 20+ LTS):
```
React 18.3.1 (with TypeScript strict mode)
  ↓
Vite 5.4.2 (build tool)
  ↓
Tailwind CSS 4.0 (styling)
  ↓
Vitest (testing)
```

**Database:**
```
PostgreSQL 15+
  ↓
Alembic (migrations, 50+ versions)
  ↓
asyncpg (async driver)
```

### 2. Know the Architecture (DDD + CQRS)

**4 Layers** (mandatory separation):
```
Interfaces/  ← FastAPI routes, Pydantic schemas, middleware
  ↓
Application/  ← CQRS handlers, commands, queries
  ↓
Domain/  ← Business logic, entities, events, exceptions
  ↓
Infrastructure/  ← Persistence, security, logging
```

**CQRS Pattern:**
- **Commands** = write operations (create, update, delete) → return ID
- **Queries** = read operations (list, get) → return DTO (no side effects)

### 3. Remember Multi-Tenancy

**Critical Rule:** Every query must filter by tenant_id from JWT `tid` claim.

```python
# ✅ Correct: Filters by tenant_id
stmt = select(Material).where(
    Material.tenant_id == get_tenant_id(),  # From JWT
    Material.is_deleted == False            # Soft delete check
)

# ❌ Wrong: No tenant filter
stmt = select(Material).where(Material.status == "ACTIVE")
# Could leak data to other tenants
```

### 4. Before Coding: Inspect Existing Code

**Always do this:**
1. Check if feature already exists (grep, search codebase)
2. Find similar patterns in same bounded context (e.g., if implementing materials, look at `domain/inventory/`, `application/inventory/`)
3. Review existing tests to understand test patterns
4. Verify RBAC requirements for the feature

**Never:**
- Assume something is missing without checking
- Rewrite existing modules
- Bypass multi-tenant isolation
- Hardcode configuration

---

## Manufacturing Business Rules (Non-Negotiable)

**These are enforced in the domain layer and must be preserved:**

| Rule | Details |
|------|---------|
| **BOMs are versioned** | Changing active BOM creates new version; only 1 active per product |
| **WO status is linear** | DRAFT → RELEASED → STARTED → COMPLETED → CLOSED (no backtracking, no skipping) |
| **Materials reserved on release** | WO release reserves materials; not on completion |
| **Materials consumed on completion** | WO completion updates inventory (decreases stock) |
| **Soft deletes only** | No hard deletes; all queries check `is_deleted = false` |
| **Multi-tenant always** | Every query: `WHERE tenant_id = ...` from JWT, never from input |
| **Audit everything** | All mutations logged: user_id, timestamp, correlation_id, tenant_id |

---

## Implementation Checklist

**Before you write code:**
- [ ] Understand requirement (what problem does this solve?)
- [ ] Inspect existing code (does similar feature exist?)
- [ ] Identify affected modules (which bounded contexts?)
- [ ] Review business rules (manufacturing processes affected?)
- [ ] Check multi-tenant impact (will this work for all tenants?)

**While coding:**
- [ ] Type hints on all functions (Python + TypeScript)
- [ ] Async I/O (use `await`, no blocking calls)
- [ ] CQRS separation (if applicable)
- [ ] Tenant filter on every query
- [ ] Soft delete check on every query
- [ ] Structured logging with context
- [ ] Error handling appropriate to layer
- [ ] No hardcoded secrets or config

**Before submitting:**
- [ ] Tests passing (unit + integration + E2E as appropriate)
- [ ] Coverage ≥75% (for new code)
- [ ] Type checking: `pyright backend/app` (0 errors)
- [ ] Linting: `ruff check backend/app` (0 violations)
- [ ] Multi-tenant isolation tested
- [ ] Soft deletes respected
- [ ] RBAC enforced
- [ ] Implementation report with all changes documented

---

## Backend Patterns (Python)

### Command Handler (Write Operation)

```python
@dataclass
class CreateMaterialCommand:
    code: str
    name: str
    unit_id: UUID

class MaterialHandlers:
    def __init__(self, repo: IMaterialRepository, uow: IUnitOfWork):
        self.repo = repo
        self.uow = uow
    
    async def handle_create_material(self, cmd: CreateMaterialCommand) -> UUID:
        tenant_id = get_tenant_id()  # From JWT context
        
        # Validate
        existing = await self.repo.get_by_code(tenant_id, cmd.code)
        if existing:
            raise DuplicateMaterialCodeError(cmd.code)
        
        # Create entity
        material = Material(id=uuid.uuid4(), code=cmd.code, name=cmd.name, tenant_id=tenant_id)
        
        # Persist
        material_id = await self.uow.save(material)
        
        # Log
        logger.info("Material created", extra={"material_id": str(material_id), "tenant_id": str(tenant_id)})
        
        return material_id
```

### Query Handler (Read Operation)

```python
@dataclass
class ListMaterialsQuery:
    pass

async def handle_list_materials(self, query: ListMaterialsQuery) -> List[MaterialResponse]:
    tenant_id = get_tenant_id()  # From JWT context
    materials = await self.repo.list_by_tenant(tenant_id)
    return [MaterialResponse.from_entity(m) for m in materials]
```

### Repository with Tenant Filter

```python
class MaterialRepository(IMaterialRepository):
    async def list_by_tenant(self, tenant_id: UUID) -> List[Material]:
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,      # ← Tenant filter (mandatory)
            MaterialModel.is_deleted == False          # ← Soft delete check (mandatory)
        )
        results = await self.session.execute(stmt)
        return [Material.from_model(m) for m in results.scalars()]
```

---

## Frontend Patterns (React + TypeScript)

### Fully Typed Component

```typescript
interface MaterialListProps {
  onSelect?: (material: Material) => void;
}

export const MaterialList: React.FC<MaterialListProps> = ({ onSelect }) => {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await api.materials.list();
        setMaterials(data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Unknown error'));
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, []);
  
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  if (!materials.length) return <EmptyState message="No materials found" />;
  
  return (
    <table>
      {/* Table content */}
    </table>
  );
};
```

### Custom Hook for Logic Extraction

```typescript
export const useMaterials = () => {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const fetch = async () => {
      const data = await api.materials.list();
      setMaterials(data);
      setLoading(false);
    };
    fetch();
  }, []);
  
  return { materials, loading };
};
```

---

## Database Patterns (PostgreSQL + Alembic)

### Schema Requirements

**Every table must have:**
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT
is_deleted BOOLEAN NOT NULL DEFAULT false
deleted_at TIMESTAMP NULL
created_at TIMESTAMP NOT NULL DEFAULT NOW()
created_by UUID NOT NULL REFERENCES users(id)
updated_at TIMESTAMP NOT NULL DEFAULT NOW()
updated_by UUID NOT NULL REFERENCES users(id)

-- Mandatory indexes:
INDEX idx_<table>_tenant_status ON (<table>) WHERE is_deleted = false
```

### Creating a Migration

```bash
# 1. Modify SQLAlchemy model
# 2. Generate migration
alembic revision --autogenerate -m "add_priority_to_sales_orders"

# 3. Review generated migration (alembic/versions/*.py)
# 4. Test locally
alembic upgrade head

# 5. Commit migration with code changes
```

---

## Workflow for Any Task

**12-step process** (see `IMPLEMENTATION_WORKFLOW.md` for details):

1. **Understand** the requirement (business problem, acceptance criteria)
2. **Inspect** existing code (is feature already there? similar patterns?)
3. **Identify** related components (routes, handlers, repos, models, tests)
4. **Understand** business rules and dependencies
5. **Identify** risks (cross-module? destructive? security?)
6. **Present** plan (what, why, tests, risks)
7. **Wait for approval** (if high-risk: schema changes, cross-module, architecture)
8. **Implement** smallest complete solution
9. **Run tests** and validation
10. **Report** changes, test results, deployment notes
11. **Code review** checklist (DDD, CQRS, types, logging, tests, isolation, audit)
12. **Deploy** with runbook and rollback plan

---

## Quality Gate: Definition of Done

**Every change must satisfy ALL 13 criteria** (see `DEFINITION_OF_DONE.md`):

1. ✅ **Requirement met** — All acceptance criteria satisfied
2. ✅ **Architecture validated** — DDD layers correct, CQRS separation
3. ✅ **Business rules enforced** — Manufacturing workflows correct
4. ✅ **Multi-tenant isolation** — Tenant from JWT, every query filtered, audit logged
5. ✅ **Authorization** — RBAC enforced, 403 on denial
6. ✅ **Database migrations** — Alembic migration created, tested, reversible
7. ✅ **Tests passing** — ≥75% coverage, unit + integration + E2E
8. ✅ **Frontend components** — Fully typed, error-handled, accessible, tested
9. ✅ **Backend code quality** — Type hints, async-first, logging, no debug code
10. ✅ **No unrelated changes** — Only feature files modified
11. ✅ **Clean commits** — Branch strategy, atomic commits, clear messages
12. ✅ **Limitations documented** — Known issues, tech debt tracked
13. ✅ **Security verified** — No secrets in logs, input validated, audit logged

**Before submitting for review, complete this checklist manually.** Do not claim task done unless all 13 items are checked.

---

## Common Gotchas

### ❌ Forgetting Tenant Filter

```python
# ❌ Wrong: Gets ALL materials, not just tenant's
stmt = select(Material).where(Material.status == "ACTIVE")

# ✅ Correct: Scoped to tenant
stmt = select(Material).where(
    Material.tenant_id == get_tenant_id(),
    Material.is_deleted == False
)
```

### ❌ Hardcoding Secrets

```python
# ❌ Wrong: Secret in code
API_KEY = "sk-abc123xyz"

# ✅ Correct: From environment
API_KEY = os.getenv("API_KEY")
```

### ❌ Silent Exception Swallowing

```python
# ❌ Wrong: Error is silently ignored
try:
    await self.repo.save(entity)
except:
    pass  # What error? Nobody will know

# ✅ Correct: Log and handle explicitly
try:
    await self.repo.save(entity)
except DomainException as e:
    logger.warning("Save failed", extra={"error": str(e)})
    raise
```

### ❌ Forgetting Soft Delete Check

```python
# ❌ Wrong: Returns deleted records too
stmt = select(Material).where(Material.code == code)

# ✅ Correct: Excludes deleted
stmt = select(Material).where(
    Material.code == code,
    Material.is_deleted == False
)
```

### ❌ Skipping Tests

```python
# ❌ Wrong: No tests for new code
def new_feature():
    return calculate_something()
# Coverage drops; code untested

# ✅ Correct: Tests written first or alongside
def test_new_feature():
    result = calculate_something()
    assert result == expected_value
```

---

## When to Stop and Ask

- **Multi-tenant isolation verification:** Unsure if tenant context is properly scoped?
- **RBAC permission requirements:** Which roles should have access?
- **Manufacturing business rule interpretation:** How should BOMs/WOs/inventory behave?
- **Cross-module dependencies:** Will this change affect other bounded contexts?
- **Performance impact:** Will this query scale to large datasets?

**Escalate to user if stuck.** Don't guess.

---

## Implementation Report Template

After every task, provide:

```markdown
## Implementation Report: [TASK-ID] - [Feature Name]

### Changes Made
- File 1: What changed
- File 2: What changed

### Business Logic Verified
- ✓ [Rule 1] — verified via [test/screenshot]
- ✓ [Rule 2] — verified via [test/screenshot]

### Tests
- ✓ Unit: X passing
- ✓ Integration: X passing
- ✓ Coverage: X% (target 75%)

### Multi-Tenant Isolation
- ✓ Tested: Tenant A cannot see Tenant B data

### Definition of Done
- ✓ All 13 items checked

### Sign-Off
✅ Ready for: Code Review → Testing → Production
```

---

## File Structure Reference

```
backend/app/
├── domain/              ← Business logic (entities, exceptions, events)
├── application/         ← Use cases (handlers, commands, queries)
├── infrastructure/      ← Persistence (repositories, models, logging)
└── interfaces/          ← API (routes, schemas, middleware)

frontend/src/
├── modules/             ← Business domains (auth, sales, inventory, etc.)
├── components/          ← Shared components
├── hooks/               ← Custom React hooks
├── services/            ← API clients
└── types/               ← TypeScript interfaces

docs/ai-guidelines/     ← Reference documentation
├── SYSTEM_ARCHITECTURE.md
├── BACKEND_STANDARDS.md
├── FRONTEND_STANDARDS.md
├── DATABASE_STANDARDS.md
├── SECURITY_AND_MULTITENANCY.md
├── MANUFACTURING_BUSINESS_RULES.md
├── IMPLEMENTATION_WORKFLOW.md
└── DEFINITION_OF_DONE.md
```

---

## Quick Command Reference

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ --cov=backend/app

# Type check
pyright backend/app

# Lint
ruff check backend/app

# Database
alembic upgrade head          # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
alembic downgrade -1          # Rollback one migration
```

### Frontend
```bash
# Install dependencies
npm install

# Run dev server (or run in terminal, don't block)
npm run dev

# Run tests
npm run test

# Type check
npm run type-check

# Lint
npm run lint
```

---

## Summary

**Before writing any code:**
1. Read `AGENTS.md` (mandatory reference for all standards)
2. Reference relevant guideline file from `docs/ai-guidelines/`
3. Inspect existing code for patterns
4. Follow 12-step workflow from `IMPLEMENTATION_WORKFLOW.md`
5. Verify against 13-point checklist in `DEFINITION_OF_DONE.md`

**Key constraints:**
- ✅ Multi-tenant filtering on every query
- ✅ Soft delete check on every query
- ✅ Type hints on all code
- ✅ Tests for new code
- ✅ No hardcoded secrets or config
- ✅ No breaking changes without migration plan
- ✅ No async/await violations
- ✅ No CQRS mixing

**Never:**
- ❌ Query without tenant_id filter
- ❌ Hardcode configuration
- ❌ Skip error handling
- ❌ Assume feature is missing without checking
- ❌ Rewrite existing modules
- ❌ Bypass multi-tenant isolation or RBAC
- ❌ Use blocking I/O in async context

---

**Questions?** See the relevant guide in `docs/ai-guidelines/` or `AGENTS.md`.

**Status:** Production Ready | Last Updated: November 9, 2026
