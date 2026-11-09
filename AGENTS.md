# MedTrack Master AGENTS.md

**Canonical Engineering Instruction Document for AI Coding Agents**

Version: 1.0.0  
Last Updated: November 9, 2026  
Status: Production Ready

---

## ⚠️ CRITICAL: FILE ORGANIZATION STANDARDS

**ALL new files MUST follow proper folder structure.** Files created in wrong locations will be rejected in code review.

**See:** `.kiro/steering/file-organization-standards.md` for comprehensive rules.

**Quick Rules:**
- ✅ Backend Python → `backend/app/{domain|application|infrastructure|interfaces}/`
- ✅ Frontend React/TS → `frontend/src/modules/{module}/{type}/`
- ✅ Tests → `tests/{unit|integration|e2e}/` (NEVER root)
- ✅ Migrations → `alembic/versions/` (use `alembic revision --autogenerate`)
- ✅ Scripts → `scripts/{category}/`
- ✅ Docs → `docs/` or `.kiro/steering/`

**Prohibited:**
- ❌ `test_*.py` in repository root
- ❌ Test files mixed with source code
- ❌ Random helper scripts in root
- ❌ Misorganized frontend components

**Before Creating Any File:** Consult `file-organization-standards.md` Section 7.1

---

---

## 1. Project Overview

**MedTrack** is a production-grade, multi-tenant Manufacturing ERP System designed for mid-to-large manufacturing companies. It manages the complete product lifecycle from design through production to sales and delivery.

**Key Characteristics:**
- Multi-tenant SaaS architecture (complete data isolation per customer)
- Domain-Driven Design (DDD) with CQRS pattern
- Async-first Python backend (FastAPI + SQLAlchemy async)
- Modern React 18 frontend (TypeScript + Vite)
- PostgreSQL database with Alembic migrations
- Event-driven real-time notifications (WebSocket)
- Comprehensive audit logging and compliance tracking

**Current Phase:** Phase 0 Foundation Complete, Phases 1-4 In Progress

---

## 2. Product Purpose and Manufacturing ERP Scope

MedTrack enables manufacturing companies to manage:

### Core Business Processes
1. **Sales Management** — Customer orders, approvals, pricing, client portal
2. **Bill of Materials (BOM)** — Product templates, variants, versioned BOMs
3. **Manufacturing Execution** — Work orders, shop floor execution, real-time tracking
4. **Inventory Management** — Multi-warehouse stock, reservations, batch tracking, low-stock alerts
5. **Procurement** — Purchase orders, GRNs, supplier management, subcontracting
6. **Quality Control** — Incoming inspections, non-conformance reports, approval workflows
7. **Finance** — Invoicing, accounts receivable/payable, standard costing, ledger management
8. **Reporting & Analytics** — Production metrics, sales dashboards, financial reports, MRP suggestions

### User Roles (13 Total)
- **System:** ADMIN, TENANT_ADMIN
- **Operations:** MANAGER, OPERATOR, STOREKEEPER, PLANNER
- **Quality:** QC
- **Sales:** SALES, WORKER
- **External:** CLIENT, SUPPLIER
- **Reporting:** VIEWER

Each role has fine-grained permissions scoped to specific modules and actions.

---

## 3. Verified Technology Stack

### Backend (Verified from requirements.txt and main.py)
- **Framework:** FastAPI 0.111.0 (async web framework)
- **ASGI Server:** Uvicorn 0.29.0
- **ORM:** SQLAlchemy 2.0.30 (async with asyncpg)
- **Database Driver:** asyncpg 0.29.0 (async PostgreSQL)
- **Migrations:** Alembic 1.13.1
- **Authentication:** python-jose + bcrypt + pyotp (JWT + 2FA)
- **Validation:** Pydantic v2.7.1 (strict mode)
- **Logging:** structlog 24.4.0 (structured logging)
- **Rate Limiting:** slowapi 0.1.9
- **Document Generation:** WeasyPrint 60.2 + Jinja2 3.1.4
- **Email:** Resend 2.32.2 (SaaS provider)
- **Testing:** pytest 8.2.0 + pytest-asyncio 0.23.6 + pytest-cov 5.0.0
- **Type Checking:** Python 3.11+ with type hints

### Frontend (Verified from package.json)
- **Framework:** React 18.3.1
- **Language:** TypeScript (strict mode)
- **Build Tool:** Vite 5.4.2
- **Styling:** Tailwind CSS 4.0.0-alpha
- **Charts:** Recharts 2.12.7
- **Animation:** Motion 11.11.17 (Framer Motion)
- **Icons:** Lucide React 0.435.0
- **Testing:** Vitest (recommended, configuration in vitest.config.ts)
- **Node:** 20+ LTS

### Database (Verified from schema)
- **Primary:** PostgreSQL 15+ with async driver
- **Extensions:** pgcrypto (UUID), pg_trgm (full-text search)
- **Schema:** 98+ tables with soft deletes, audit columns, tenant isolation
- **Migrations:** 50+ Alembic versions committed to repository

### Infrastructure (Verified from docker-compose.yml)
- **Containerization:** Docker + Docker Compose
- **Caching:** Redis (optional, for session/pub-sub)
- **File Storage:** Local uploads/ directory or Cloudinary integration
- **CI/CD:** GitHub Actions (workflows in .github/workflows/)

---

## 4. Repository Structure

### Root Level
```
MedTrack/
├── AGENTS.md                    # This file
├── CLAUDE.md                    # Claude-specific guidance
├── README.md                    # Project overview
├── SETUP.md                     # Developer setup
├── package.json                 # Frontend dependencies
├── requirements.txt             # Backend dependencies
├── docker-compose.yml           # Local dev environment
├── tsconfig.json                # TypeScript config
├── vite.config.ts               # Frontend build
└── pytest.ini                   # Backend testing config
```

### Backend Structure
```
backend/app/
├── main.py                      # FastAPI app entry point
├── config.py                    # Settings from environment
├── domain/                      # Business logic (DDD Layer 1)
│   ├── bom/                     # Bill of Materials context
│   ├── manufacturing/           # Work orders, routing
│   ├── inventory/               # Stock, reservations
│   ├── sales/                   # Orders, quotes
│   ├── procurement/             # POs, GRNs
│   ├── quality/                 # Inspections
│   ├── finance/                 # Invoicing
│   ├── tenant/                  # Auth, RBAC
│   └── shared/                  # Domain exceptions, events
├── application/                 # Use cases (DDD Layer 2)
│   ├── */commands/              # Command DTOs
│   ├── */queries/               # Query DTOs
│   └── */handlers/              # CQRS handlers
├── infrastructure/              # Persistence (DDD Layer 3)
│   ├── persistence/             # ORM models, repositories
│   ├── di/container.py          # Dependency injection
│   ├── security/                # JWT, RBAC, bcrypt
│   ├── logging/                 # structlog setup
│   └── events/                  # Event dispatcher
├── interfaces/                  # HTTP layer (DDD Layer 4)
│   ├── api/v1/routes/           # FastAPI route handlers
│   ├── api/v1/schemas/          # Pydantic request/response models
│   └── api/v1/middleware/       # Middleware (tenant, RBAC, logging)
├── core/                        # Application core
│   ├── logging.py               # Logging configuration
│   └── module_registry.py       # Dependency validation
├── middleware/                  # Cross-cutting middleware
│   ├── security_headers.py      # HSTS, CSP, etc.
│   ├── rate_limiting.py         # slowapi setup
│   └── correlation_id.py        # Request tracing
└── tests/                       # Unit, integration, E2E tests
```

### Frontend Structure
```
frontend/src/
├── main.tsx                     # React entry point
├── App.tsx                      # Root component
├── modules/                     # Business domain modules
│   ├── auth/                    # Authentication
│   ├── sales/                   # Sales orders
│   ├── inventory/               # Materials, stock
│   ├── manufacturing/           # Work orders
│   ├── procurement/             # Purchase orders
│   ├── quality/                 # QC inspections
│   ├── finance/                 # Invoicing
│   └── analytics/               # Dashboards
├── components/                  # Shared components
│   ├── shared/                  # Generic UI (Button, Modal, etc.)
│   ├── forms/                   # Form components
│   └── layout/                  # Layout wrappers
├── hooks/                       # Global React hooks
├── services/                    # API clients
├── types/                       # TypeScript interfaces
├── utils/                       # Helper functions
├── config/                      # Configuration
└── test/                        # Test setup, mocks, fixtures
```

### Database Structure
```
alembic/
├── env.py                       # Alembic configuration
├── script.py.mako               # Migration template
└── versions/                    # 50+ committed migrations
    ├── 001_initial.py           # Initial schema
    ├── 20260927_add_priority_to_sales_orders.py
    ├── 20261108_1606_merge_all_heads.py
    └── ... (latest at bottom)

db_scripts/
├── medtrack_complete_dev.sql    # Full schema + seed data
├── medtrack_schema_latest.sql   # DDL only
└── README.md                    # Database documentation
```

### Documentation
```
docs/
├── ERP_COMPLETE_GUIDE.md        # Full business/technical guide
├── MANUFACTURING_FUNCTIONAL_FLOW.md
├── ai-guidelines/               # AI instruction files
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── BACKEND_STANDARDS.md
│   ├── FRONTEND_STANDARDS.md
│   ├── DATABASE_STANDARDS.md
│   ├── SECURITY_AND_MULTITENANCY.md
│   ├── MANUFACTURING_BUSINESS_RULES.md
│   ├── IMPLEMENTATION_WORKFLOW.md
│   └── DEFINITION_OF_DONE.md
└── ... (40+ other guides)
```

### Scripts Directory
```
scripts/
├── database/                    # Active utilities (14 files)
├── archived-migrations/         # Historical fixes (25 files)
├── debug-archive/               # Debug utilities (65+ files)
└── README.md                    # Scripts documentation
```

---

## 5. Backend Architecture

### DDD + CQRS Pattern

**Layer 1: Domain** (`domain/` directory)
- **Entities:** Business objects with identity (BOM, WorkOrder, Material)
- **Value Objects:** Immutable value types (Money, Component)
- **Domain Events:** State changes (WorkOrderCompleted, InventoryConsumed)
- **Domain Exceptions:** Business rule violations (InsufficientStockError)
- **Repository Interfaces:** Abstract data access contracts

**Layer 2: Application** (`application/` directory)
- **Commands:** Write operations (CreateBOMCommand, ReleaseWorkOrderCommand)
- **Queries:** Read operations (GetBOMQuery, ListMaterialsQuery)
- **Handlers:** CQRS orchestration (BOMHandlers, WorkOrderHandlers)
- **DTOs:** Data transfer objects for API responses

**Layer 3: Infrastructure** (`infrastructure/` directory)
- **Repositories:** Implement domain repository interfaces
- **ORM Models:** SQLAlchemy models mapping to database
- **Unit of Work:** Transaction coordination
- **Security:** JWT validation, RBAC enforcement
- **Event Dispatcher:** Publish/subscribe for domain events
- **Logging:** Structured logging with tenant context

**Layer 4: Interfaces** (`interfaces/` directory)
- **Routes:** FastAPI route handlers (thin translation layer)
- **Schemas:** Pydantic request/response models (validation)
- **Middleware:** Request/response processing (tenant extraction, RBAC)

### Middleware Stack (Order Matters)
```
ErrorLoggingMiddleware              # Catch all exceptions
CorrelationIdMiddleware             # Generate request trace ID
TimingMiddleware                    # Request timing
SecurityHeadersMiddleware           # Security headers (HSTS, CSP)
SlowAPIMiddleware                   # Rate limiting
CORSMiddleware                      # Cross-origin handling
RBACPermissionAuditMiddleware       # Log permission denials (403)
AuditMiddleware                     # Log all mutations
TenantMiddleware ← CRITICAL         # Extract tenant from JWT
RequestLoggingMiddleware            # Log request/response
```

### Event-Driven Communication
```
Domain Entity raises event
  ↓
Event Dispatcher publishes
  ↓
Multiple subscribers listen:
  - Inventory Service (consume materials)
  - Production Metrics (update KPIs)
  - Notification Service (send alerts)
  - WebSocket Handler (real-time UI updates)
```

### Async-First Execution
- **All I/O is async:** Database, HTTP, file operations use `await`
- **No blocking calls:** Never use `requests.get()`, use `httpx.AsyncClient()`
- **Connection pooling:** asyncpg manages PostgreSQL connection pool
- **Background tasks:** Long-running operations via Celery or background tasks

---

## 6. Frontend Architecture

### React + TypeScript Pattern

**Module Structure**
Each business domain (auth, sales, inventory) is a self-contained module:
```
modules/{domain}/
├── pages/              # Page-level components (routed)
├── components/         # Domain-specific components
├── hooks/              # Custom React hooks (state management)
├── services/           # API client functions
├── types/              # TypeScript interfaces for domain
└── __tests__/          # Component and hook tests
```

**Component Best Practices**
- **Functional components only** (no class components)
- **Full TypeScript types** on all props, state, and returns
- **Custom hooks for logic** extraction and reuse
- **Error boundaries** for graceful error handling
- **React.memo for expensive renders** (sparingly)

**State Management**
- **useState** for simple, isolated state
- **useReducer** for complex component state
- **Context API** for cross-component state (theme, auth)
- **Custom hooks** for shared logic patterns

**API Communication**
- **Axios instances** in `services/` with interceptors for auth
- **Type-safe API responses** with TypeScript interfaces
- **Error handling** via try-catch with logging
- **Loading and error states** managed locally in hooks

### Build & Development
- **Vite dev server** for hot module reload (HMR)
- **Tailwind CSS** for utility-first styling
- **TypeScript strict mode** enforced via tsconfig
- **ESLint** for code quality (config in eslint.config.js)

---

## 7. Database Architecture

### PostgreSQL Schema Design

**Every Table Must Include:**
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT
is_deleted BOOLEAN NOT NULL DEFAULT false
deleted_at TIMESTAMP NULL
created_at TIMESTAMP NOT NULL DEFAULT NOW()
created_by UUID NOT NULL REFERENCES users(id)
updated_at TIMESTAMP NOT NULL DEFAULT NOW()
updated_by UUID NOT NULL REFERENCES users(id)
```

**Indexes (Required):**
- Tenant filter index: `(tenant_id, is_deleted)`
- Status/state index: `(status) WHERE is_deleted = false`
- Timestamp index: `(created_at DESC)`
- Foreign key indexes on all FK columns

**Constraints:**
- NOT NULL on critical columns
- CHECK constraints for enums/status values
- UNIQUE constraints for codes/identifiers (within tenant scope)
- Foreign key constraints with ON DELETE RESTRICT

### Migrations (Alembic)

**Current State:** 50+ committed migrations, latest at `20261108_1606_merge_all_heads.py`

**Workflow:**
1. Modify SQLAlchemy model
2. `alembic revision --autogenerate -m "description"`
3. Review generated migration
4. `alembic upgrade head` (test locally)
5. Commit migration with code changes

**Multi-Developer Conflicts:**
```bash
alembic heads              # Show all heads
alembic merge heads -m "merge description"
alembic upgrade head
```

### Soft Deletes Pattern

**Delete (mark as deleted):**
```python
entity.is_deleted = True
entity.deleted_at = datetime.utcnow()
await repo.save(entity)
```

**Query (always exclude deleted):**
```python
stmt = select(Entity).where(
    Entity.tenant_id == tenant_id,
    Entity.is_deleted == False  # ← MANDATORY
)
```

### Repository Pattern

**Async Repositories:**
```python
class MaterialRepository(IMaterialRepository):
    async def get_by_id(self, tenant_id: UUID, material_id: UUID) -> Material | None:
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.id == material_id,
            MaterialModel.is_deleted == False
        )
        result = await session.execute(stmt)
        model = result.scalars().first()
        return Material.from_model(model) if model else None
    
    async def list_by_tenant(self, tenant_id: UUID) -> List[Material]:
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted == False
        ).order_by(MaterialModel.created_at.desc())
        result = await session.execute(stmt)
        return [Material.from_model(m) for m in result.scalars().all()]
```

---

## 8. Coding Principles

### 1. Domain-Driven Design (Mandatory)
- Business logic lives in `domain/`
- Repositories are abstract in domain, implemented in infrastructure
- Domain exceptions are specific and meaningful
- No domain objects should reference database or HTTP layers

### 2. CQRS Separation (Mandatory)
- **Commands** handle writes (return IDs)
- **Queries** handle reads (return DTOs, no side effects)
- Handlers orchestrate between domain and infrastructure
- Routes are thin translation layers only

### 3. Type Safety (Mandatory)
- Python: Full type hints (Python 3.11+)
- TypeScript: Strict mode enabled, no `any` types
- Pydantic schemas for all API requests/responses
- SQLAlchemy models with type annotations

### 4. Async-First (Mandatory)
- All I/O operations are async (`async def`, `await`)
- No synchronous calls in async functions
- Connection pooling for database access
- WebSocket for real-time client updates

### 5. Multi-Tenancy (Non-Negotiable)
- Every query filters by `tenant_id`
- Tenant extracted from JWT, never from user input
- All logs include tenant context
- Database enforces via FK and constraints

### 6. Soft Deletes (Non-Negotiable)
- No hard deletes
- Every query checks `is_deleted = false`
- Historical data preserved for audit
- Reversible and compliant

### 7. Structured Logging (Required)
- Use structlog, not print statements
- Include tenant_id, user_id, correlation_id
- Log level: INFO for normal, WARNING for issues, ERROR for failures
- Never log passwords, tokens, or sensitive data

### 8. Error Handling (Required)
- Domain layer: Raise specific exceptions
- Application layer: Catch and log
- Interface layer: Convert to HTTP responses (401/403/422)
- Never swallow exceptions silently

---

## 9. Backend Implementation Rules

### Python Style
- **Language:** Python 3.11+
- **Type Hints:** Required on all functions and variables
- **Naming:** snake_case for functions/variables, PascalCase for classes
- **Async:** `async def` for all I/O, `await` for all I/O calls
- **Imports:** Group as standard library, third-party, local

### Dependency Injection
```python
# ✅ Correct: Injected via container
class BOMHandlers:
    def __init__(self, repo: IBOMRepository, uow: IUnitOfWork):
        self.repo = repo
        self.uow = uow

# ❌ Wrong: Global singleton
_repo = BOMRepository()  # Hard to test, multi-tenant unsafe
```

### Command Handler Pattern
```python
@dataclass
class CreateBOMCommand:
    template_id: UUID
    lines: List[BOMLineInput]

async def handle_create_bom(self, cmd: CreateBOMCommand) -> UUID:
    # Validate input
    template = await self.repo.get_template(cmd.template_id)
    if not template:
        raise TemplateNotFoundError(cmd.template_id)
    
    # Create entity
    bom = BOM(template_id=cmd.template_id, lines=[...])
    
    # Apply business rules
    for line in cmd.lines:
        bom.add_line(line)  # May raise DomainException
    
    # Persist and publish
    bom_id = await self.uow.save_bom(bom)
    await self.event_dispatcher.publish(bom.events)
    
    return bom_id
```

### Query Handler Pattern
```python
@dataclass
class GetBOMQuery:
    bom_id: UUID

async def handle_get_bom(self, query: GetBOMQuery) -> BOMResponse:
    bom = await self.repo.get_by_id(query.bom_id)
    if not bom:
        raise BOMNotFoundError(query.bom_id)
    return BOMResponse.from_entity(bom)
```

### Multi-Tenancy Extraction
```python
from backend.app.infrastructure.context import get_tenant_id

async def list_materials(self) -> List[Material]:
    tenant_id = get_tenant_id()  # From JWT via middleware
    return await self.repo.list_by_tenant(tenant_id)
```

### Structured Logging
```python
from backend.app.infrastructure.logging import get_logger

logger = get_logger(__name__)

logger.info(
    "Material created",
    extra={
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "material_code": code,
        "correlation_id": correlation_id
    }
)
```

---

## 10. Frontend Implementation Rules

### TypeScript Strict Mode (Required)
- Enable `strict: true` in tsconfig
- No `any` types without explicit justification
- All props and returns fully typed
- No implicit `any`

### React Patterns
```typescript
// ✅ Correct: Functional component, fully typed
interface MaterialListProps {
  onSelect?: (material: Material) => void;
}

export const MaterialList: React.FC<MaterialListProps> = ({ onSelect }) => {
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
  
  return <div>{/* JSX */}</div>;
};

// ❌ Wrong: Class component, no types
class MaterialList extends React.Component {
  render() {
    return <div>{/* JSX */}</div>;
  }
}
```

### Custom Hooks Pattern
```typescript
// Extract logic into reusable hooks
interface UseMaterialsReturn {
  materials: Material[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export const useMaterials = (): UseMaterialsReturn => {
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
  
  return { materials, loading, error, refetch: fetch };
};
```

### API Client Pattern
```typescript
// Type-safe API clients in services/
interface Material {
  id: string;
  code: string;
  name: string;
  quantity: number;
}

export const materialApi = {
  async list(): Promise<Material[]> {
    const response = await api.get<Material[]>('/materials');
    return response.data;
  },
  
  async get(id: string): Promise<Material> {
    const response = await api.get<Material>(`/materials/${id}`);
    return response.data;
  }
};
```

---

## 11. API Design Rules

### REST Conventions
```
GET    /api/v1/materials              # List (with filters, pagination)
POST   /api/v1/materials              # Create
GET    /api/v1/materials/{id}         # Get one
PUT    /api/v1/materials/{id}         # Update
DELETE /api/v1/materials/{id}         # Soft delete
PATCH  /api/v1/materials/{id}/action  # Specific action
```

### Request/Response Schemas
```python
# Pydantic validation
class CreateMaterialRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., pattern=r"^[A-Z0-9-]+$")
    unit_id: str = Field(...)

class MaterialResponse(BaseModel):
    id: str
    name: str
    code: str
    created_at: datetime
```

### Error Responses
```json
{
  "detail": "Material code already exists",
  "code": "DUPLICATE_CODE"
}
```

### Domain Exception → HTTP Mapping
```python
@app.exception_handler(DomainException)
async def domain_exception_handler(request, exc: DomainException):
    if exc.code in {"INVALID_TOKEN", "TOKEN_EXPIRED", "UNAUTHORIZED"}:
        return JSONResponse(status_code=401, content={"detail": exc.message})
    return JSONResponse(status_code=422, content={"detail": exc.message, "code": exc.code})
```

---

## 12. Database and Migration Rules

### Schema Standards
- **UUID primary keys:** `gen_random_uuid()`
- **Multi-tenancy:** Every table has `tenant_id` FK
- **Soft deletes:** `is_deleted`, `deleted_at` on all entities
- **Audit trail:** `created_at`, `created_by`, `updated_at`, `updated_by`
- **Indexes:** On filter columns, foreign keys, and timestamps

### Migration Commands
```bash
# Check current state
alembic current

# View all heads (for conflicts)
alembic heads

# Create new migration
alembic revision --autogenerate -m "add_priority_to_sales_orders"

# Upgrade/downgrade
alembic upgrade head
alembic downgrade -1
```

### Query Requirements
```python
# ✅ Always include all filters
stmt = select(Material).where(
    Material.tenant_id == tenant_id,        # Multi-tenancy
    Material.is_deleted == False,           # Soft delete
    Material.status == "ACTIVE"             # Business filter
).limit(100).offset(0)

# ❌ Incomplete
stmt = select(Material).where(Material.status == "ACTIVE")
# Could leak other tenants' data or deleted records
```

---

## 13. Authentication and Authorization

### JWT Token Structure
```json
{
  "sub": "user_id_uuid",
  "tid": "tenant_id_uuid",
  "role": "MANAGER",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Tenant Extraction (Middleware)
```python
class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        payload = jwt.decode(token, settings.jwt_secret_key)
        tenant_id = payload.get("tid")  # ← Extracted here
        ContextVars.tenant_id.set(tenant_id)
        return await call_next(request)
```

### Password Security
- Minimum 12 characters
- Bcrypt with ≥12 salt rounds
- Never store plaintext
- Never log passwords

### RBAC Enforcement
```python
class RBACPermissionAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user = await get_current_user(request)
        has_permission = await permission_service.check(
            user_id=user.id,
            resource=request.url.path,
            action=request.method
        )
        if not has_permission:
            logger.warning("Access denied", extra={"user_id": str(user.id)})
            raise HTTPException(status_code=403, detail="Access denied")
        return await call_next(request)
```

---

## 14. Multi-Tenancy Rules

### Core Principles (Non-Negotiable)
1. **Tenant extraction from JWT only** — Never from request parameters
2. **Every query filters by tenant_id** — No exceptions
3. **Database enforces via FK constraints** — `tenant_id` references `tenants(id)`
4. **Soft deletes preserved per tenant** — Historical data per tenant
5. **Audit logging includes tenant** — All mutations tracked by tenant

### Implementation Checklist
- [ ] Tenant context set in middleware
- [ ] `get_tenant_id()` available in all handlers
- [ ] Every repository method accepts `tenant_id` parameter
- [ ] Every SELECT query includes `tenant_id` filter
- [ ] Every INSERT/UPDATE sets `tenant_id` from context
- [ ] Logs include tenant context
- [ ] Tests verify tenant isolation

### Isolation Verification Test
```python
@pytest.mark.asyncio
async def test_tenant_isolation(db_session):
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    
    # Create object with tenant1
    obj = await create_object(tenant1_id, "Test")
    
    # Verify tenant2 cannot see it
    result = await repo.get_by_id(tenant2_id, obj.id)
    assert result is None  # Should not find
```

---

## 15. Inventory and Manufacturing Business Rules

### Rule 1: Bill of Materials (BOM)
**Non-Negotiable:**
- BOMs are **versioned** — changing active BOM creates new version
- Only **one active version** per product template/variant
- **No duplicate components** — same material appears once per BOM
- **Immutable when active** — must create new version to modify
- **References must exist** — all materials and templates must exist and be active

### Rule 2: Work Order Status (State Machine)
```
DRAFT → RELEASED → STARTED → COMPLETED → CLOSED
          ↓          ↓
        CANCELLED  CANCELLED
```
**Non-Negotiable:**
- Cannot skip steps (DRAFT→STARTED invalid)
- Cannot go backward (COMPLETED→STARTED invalid)
- Only RELEASED or STARTED can be CANCELLED
- CLOSED is final and immutable

### Rule 3: Inventory Reservations
**Non-Negotiable:**
- Materials **reserved on WO release**, not consumed
- Reservation **blocks other reservations**
- On WO completion → materials **consumed** (inventory updated)
- On WO cancellation → materials **released** (back to available)
- **Cannot release WO without sufficient stock**

### Rule 4: Low-Stock Alerts
- Alert triggered when `available_stock < reorder_point`
- Configurable per material
- Event-driven via domain events
- Published to planners and managers

### Rule 5: GRN Against PO
- GRN must reference existing PO
- GRN quantity cannot exceed PO quantity
- Raises `ExcessiveGRNError` if violated

### Rule 6: Quality Control
- All incoming materials require QC inspection
- Status: PENDING → IN_PROGRESS → PASSED/FAILED
- Failed batches are quarantined

### Rule 7: Sales Order Approval
- Orders require approval before manufacturing
- Approval: DRAFT → APPROVED → MANUFACTURING → DELIVERED
- Can set priority: LOW, MEDIUM, HIGH, URGENT

---

## 16. Error Handling and Logging

### Error Hierarchy
```
DomainException (business rule violation)
├── DuplicateComponentError
├── InsufficientStockError
├── InvalidStateTransitionError
└── TemplateNotFoundError

HTTPException (HTTP level)
├── 400 Bad Request (validation)
├── 401 Unauthorized (auth)
├── 403 Forbidden (RBAC)
└── 422 Unprocessable Entity (business rule)
```

### Logging Pattern
```python
logger.info(
    "Work order released",
    extra={
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "work_order_id": str(wo_id),
        "correlation_id": correlation_id
    }
)

logger.error(
    "Material consumption failed",
    extra={
        "error": str(e),
        "error_type": type(e).__name__,
        "material_id": str(material_id)
    }
)
```

### Never Log
- Passwords or plaintext credentials
- API keys or tokens
- Credit card numbers or sensitive payment info
- Personal identification numbers
- Encryption keys

---

## 17. Testing Requirements

### Minimum Coverage: 75%

### Test Categories
1. **Unit Tests** — Pure logic, no I/O (backend/app/domain/)
2. **Integration Tests** — With database (backend/app/application/, repositories)
3. **E2E Tests** — Full API flow (tests/e2e/)
4. **Component Tests** — React components (frontend/src/**/__tests__/)

### Test Patterns
```python
# Unit test: Pure business logic
@pytest.mark.unit
def test_bom_duplicate_component_raises_error():
    bom = BOM(id=uuid.uuid4(), lines=[])
    line = BOMLine(material_id=uuid.uuid4(), quantity=Decimal("10"))
    bom.add_line(line)
    with pytest.raises(DuplicateComponentError):
        bom.add_line(line)

# Integration test: With database
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

# E2E test: Full API
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_create_material_via_api(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/materials",
        json={"code": "MAT-001", "name": "Steel", "unit_id": str(uuid.uuid4())},
        headers=auth_headers
    )
    assert response.status_code == 201
```

---

## 18. Performance and Security Requirements

### Performance Targets
- **API response time:** <500ms p95
- **Database queries:** <100ms for list operations, <50ms for get
- **WebSocket latency:** <1 second for real-time updates
- **Frontend load time:** <3 seconds initial load
- **JSON payload size:** <1MB for list responses

### Security Hardening
- **HTTPS only** (enforced in production)
- **HSTS headers** (Strict-Transport-Security)
- **CSP headers** (Content-Security-Policy)
- **CORS whitelist** (never `allow_origins=["*"]`)
- **Rate limiting:** 100-1000 requests/minute per endpoint
- **Input validation:** Pydantic schemas on all inputs
- **SQL injection prevention:** Parameterized queries (SQLAlchemy)
- **XSS prevention:** React escaping + CSP headers
- **CSRF tokens:** For state-changing operations
- **Audit logging:** All mutations logged

### Database Security
- **Encrypted columns:** Phone, email, sensitive data
- **Connection pooling:** asyncpg with SSL
- **Backups:** Automated with encryption
- **Access control:** Role-based database permissions

---

## 19. Git and Change Management

### Branch Strategy
- **main/master:** Production-ready code (protected)
- **develop:** Integration branch (protected)
- **feature/TASK-ID-description:** Feature branches (unprotected)
- **bugfix/ISSUE-ID-description:** Bug fix branches (unprotected)

### Commit Message Format
```
TASK-ID: Type: Short description

Longer description explaining what and why.

- Changed X to Y
- Added feature Z

Tests:
- ✓ Unit tests passing
- ✓ Integration tests passing
```

### Pull Request Process
1. Create branch from develop
2. Implement changes
3. Push to origin
4. Create PR with description
5. Wait for CI/CD to pass
6. Code review and approval
7. Merge to develop
8. CI/CD deploys to staging

### Destructive Operations Require Approval
- Database migrations
- Production deployments
- Hard deletes
- Secret rotations
- Infrastructure changes

---

## 20. Mandatory AI Implementation Workflow

**Every coding task must follow this exact workflow:**

### STEP 1: Understand the Request
- Read and clarify the business requirement
- Identify which manufacturing process is affected
- Ask clarifying questions if ambiguous
- Document assumptions

### STEP 2: Inspect Existing Implementation
- Check if feature already exists
- Review related bounded contexts
- Examine existing patterns in same domain
- Look for similar implementations to mirror

### STEP 3: Identify Related Components
- **Routes:** FastAPI endpoints
- **Services:** Application handlers
- **Repositories:** Data access layer
- **Models:** ORM and domain entities
- **Tests:** Existing test patterns
- **Dependencies:** Imports and services used

### STEP 4: Understand Business Rules and Dependencies
- Read manufacturing business rules
- Check domain exceptions that could be raised
- Identify multi-tenant implications
- Understand inventory transaction workflows
- Check RBAC requirements

### STEP 5: Identify Risks and Affected Modules
- **Cross-cutting:** Does this affect multiple bounded contexts?
- **Destructive:** Will this delete or modify data?
- **Multi-tenant:** Could tenant isolation be compromised?
- **Performance:** Will this impact query performance?
- **Security:** Does this affect auth/RBAC?

### STEP 6: Present Implementation Plan
Show:
- What will be changed (files, functions)
- Why changes are needed (design rationale)
- Which tests will be added/modified
- How multi-tenancy is preserved
- Estimated implementation time

### STEP 7: Wait for Approval (If High-Risk)
**Request approval for:**
- Destructive operations (schema changes, data deletion)
- Cross-module changes
- Architecture changes
- Business rule modifications

**Proceed directly for low-risk tasks:**
- Bug fixes in single module
- New features in isolated domain
- UI improvements
- Performance optimizations

### STEP 8: Implement Smallest Complete Solution
- Make minimal, focused changes
- Don't refactor unrelated code
- Don't add unnecessary abstractions
- Don't introduce new dependencies without justification
- Follow existing patterns

### STEP 9: Run Relevant Tests and Validation
```bash
# Backend
pytest tests/ --cov=backend/app --cov-report=term-missing

# Frontend
npm run test

# Type checking
pyright backend/app
npm run type-check

# Linting
ruff check backend/app
npm run lint
```

### STEP 10: Report All Changes and Test Results
Document:
- Files modified (with diffs)
- Tests added/modified
- Coverage metrics
- Performance impact (if any)
- Deployment considerations
- Breaking changes (if any)

---

## 21. Definition of Done

Every change must satisfy **ALL** of these criteria:

### Code Quality
- [ ] Code follows DDD layer boundaries
- [ ] CQRS pattern used for write/read
- [ ] All functions have type hints (Python + TypeScript)
- [ ] No hardcoded values or secrets
- [ ] Error handling appropriate to layer
- [ ] Structured logging with context

### Multi-Tenancy
- [ ] Tenant context from JWT only
- [ ] Every query filters by tenant_id
- [ ] All logs include tenant context
- [ ] Multi-tenant isolation verified via test

### Database
- [ ] Soft deletes respected
- [ ] Audit columns present
- [ ] Alembic migration created (if schema changed)
- [ ] Migration tested locally

### Testing
- [ ] Unit tests written for domain logic
- [ ] Integration tests written for repositories
- [ ] E2E tests written for new endpoints
- [ ] All tests passing locally
- [ ] Coverage ≥75%

### Security
- [ ] Input validation via Pydantic
- [ ] Permissions checked on endpoints
- [ ] No sensitive data in logs
- [ ] Passwords hashed (bcrypt)
- [ ] Rate limiting applied

### Manufacturing Rules
- [ ] Business rules enforced
- [ ] Inventory reservations working
- [ ] Work order status validated
- [ ] BOMs versioned correctly
- [ ] Audit trail complete

### Documentation
- [ ] Code comments on complex logic
- [ ] Docstrings on functions
- [ ] API docs updated
- [ ] Business process docs updated
- [ ] CHANGELOG.md updated

---

## 22. Prohibited Actions

### Never Do These (Critical Violations)

1. **Never assume a feature is missing** without inspecting code
2. **Never rewrite an existing module** unnecessarily
3. **Never introduce duplicate services or repositories**
4. **Never bypass inventory transaction workflows**
5. **Never bypass tenant isolation or RBAC**
6. **Never execute destructive database operations** without explicit approval
7. **Never modify production data** without explicit approval
8. **Never silently change API contracts** (breaking changes require migration)
9. **Never introduce new dependencies** without explaining why
10. **Never claim tests passed** unless actually executed
11. **Never invent architecture details** — inspect code first
12. **Never leave debug code** in commits (console.log, print statements, etc.)
13. **Never hardcode configuration** — use environment variables
14. **Never log sensitive data** (passwords, tokens, PII)
15. **Never use global singletons** — use dependency injection
16. **Never add blocking I/O** to async functions
17. **Never query without tenant_id filter** (security vulnerability)
18. **Never skip soft delete checks** in queries
19. **Never commit secrets** to repository
20. **Never force-push to main/develop** branches

---

## 23. Final Implementation Report Format

After completing any task, provide a report with this structure:

```markdown
## Implementation Report: [Task Name]

### Changes Made
- **File 1:** Description of changes
- **File 2:** Description of changes

### Business Logic Verified
- ✓ Multi-tenant isolation maintained
- ✓ Inventory reservations working correctly
- ✓ BOM versioning respected
- ✓ Work order status workflow enforced

### Tests Executed
- ✓ Unit tests: XX passing, X new
- ✓ Integration tests: XX passing, X new
- ✓ E2E tests: XX passing, X new
- ✓ Coverage: XX% (target: ≥75%)

### Migrations
- Migration: `20261109_description.py` (if database changed)
- Status: Tested locally, ready for production

### Deployment Notes
- Breaking changes: None (or list them)
- Database migration: Required (or none needed)
- Feature flags: None (or list them)
- Estimated deployment time: X minutes

### Review Checklist
- ✓ Code follows DDD patterns
- ✓ CQRS separation maintained
- ✓ Type hints complete
- ✓ Logging includes context
- ✓ Tests passing
- ✓ Multi-tenancy verified
- ✓ Audit trail complete

### Sign-Off
Ready for: [Code Review / Testing / Production Deploy]
```

---

## Summary of Key Principles

| Principle | Description |
|-----------|-------------|
| **DDD** | Entities, value objects, domain events in domain/ layer only |
| **CQRS** | Commands for writes, Queries for reads, separate concerns |
| **Async-First** | All I/O is async, no blocking calls |
| **Multi-Tenant** | Every query filters by tenant_id, extracted from JWT |
| **Soft Deletes** | No hard deletes, all queries check is_deleted=false |
| **Type Safety** | Full type hints in Python and TypeScript |
| **Logging** | Structured with tenant context, never log secrets |
| **Testing** | 75% minimum coverage, unit+integration+E2E |
| **Security** | RBAC enforced, input validated, audit logged |
| **Workflow** | Inspect → Plan → Wait for approval (if risky) → Implement → Test → Report |

---

## Documentation References

For detailed information, consult these files in `docs/ai-guidelines/`:
- `SYSTEM_ARCHITECTURE.md` — Deep dive into layered architecture
- `BACKEND_STANDARDS.md` — Python/async patterns and practices
- `FRONTEND_STANDARDS.md` — React/TypeScript patterns and practices
- `DATABASE_STANDARDS.md` — PostgreSQL schema and migration patterns
- `SECURITY_AND_MULTITENANCY.md` — Security implementation and isolation
- `MANUFACTURING_BUSINESS_RULES.md` — Domain-specific business rules
- `IMPLEMENTATION_WORKFLOW.md` — Step-by-step implementation guide
- `DEFINITION_OF_DONE.md` — Quality checklist for all changes

Do not duplicate these documents in this file. Reference them instead.

---

**Last Updated:** November 9, 2026  
**Status:** Production Ready  
**Version:** 1.0.0

For questions or updates, see the relevant steering file in `.kiro/steering/` or the AI guidelines in `docs/ai-guidelines/`.
