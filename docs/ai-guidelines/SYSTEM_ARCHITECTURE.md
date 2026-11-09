# MedTrack System Architecture

**Version:** 1.0.0  
**Last Updated:** November 9, 2026  
**Status:** Production Ready

---

## Overview

MedTrack is a multi-tenant Manufacturing ERP System built with a **layered, domain-driven architecture**. The system separates concerns across four distinct layers (Domain, Application, Infrastructure, Interfaces) with an event-driven communication model for real-time updates.

### Architecture Principles

- **Domain-Driven Design (DDD):** Business logic in domain layer, completely isolated from infrastructure
- **CQRS (Command Query Responsibility Segregation):** Write operations separate from read operations
- **Multi-Tenancy:** Tenant isolation at middleware, database, and query levels
- **Async-First:** All I/O operations are asynchronous (database, HTTP, file I/O)
- **Event-Driven:** Domain events trigger asynchronous handlers for loose coupling
- **Soft Deletes:** No hard deletions; all deletions preserve historical audit trail

---

## Layered Architecture

### Layer 1: Domain (`backend/app/domain/`)

**Purpose:** Pure business logic, independent of infrastructure or HTTP.

**Contents:**
- **Entities:** Objects with identity and lifecycle (BOM, WorkOrder, Material)
- **Value Objects:** Immutable objects without identity (Money, Component, BOMLine)
- **Domain Events:** Objects representing state changes (OrderStatusChanged, WorkOrderCompleted)
- **Domain Exceptions:** Business rule violations (InsufficientStockError, DuplicateComponentError)
- **Repository Interfaces:** Abstract contracts for data access (IBOMRepository, IMaterialRepository)
- **Bounded Contexts:** 9 independent business domains:
  - `bom/` — Bill of Materials, versioning, costing
  - `manufacturing/` — Work orders, routing, operations
  - `inventory/` — Stock, reservations, batch/serial tracking
  - `sales/` — Orders, quotes, client management
  - `procurement/` — Purchase orders, GRNs, subcontracting
  - `quality/` — Inspections, non-conformance reports
  - `finance/` — Invoicing, payments, ledger
  - `tenant/` — Multi-tenancy, authentication, RBAC
  - `analytics/` — Reports, dashboards, saved queries
  - `shared/` — Cross-context exceptions, events, value objects

**Key File Patterns:**
```
domain/{context}/
├── entities/          # Domain entities (aggregates)
│   ├── entity.py
│   └── value_object.py
├── events/            # Domain events
│   └── event_name_event.py
├── exceptions/        # Domain-specific exceptions
│   └── error_type.py
├── interfaces/        # Abstract repository interfaces
│   └── irepository.py
└── __init__.py
```

**Example:** Bill of Materials Domain
```
domain/bom/
├── entities/
│   ├── bom.py             # BOM aggregate root
│   ├── bom_line.py        # BOMLine value object
│   └── bom_operation.py   # BOMOperation value object
├── events/
│   ├── bom_created_event.py
│   ├── bom_activated_event.py
│   └── bom_line_added_event.py
├── exceptions/
│   ├── duplicate_component_error.py
│   └── bom_is_active_error.py
├── interfaces/
│   └── ibom_repository.py
└── __init__.py
```

**Characteristics:**
- No dependencies on SQLAlchemy, FastAPI, or HTTP libraries
- No database connections or ORM references
- All methods return domain objects, never database models
- Business rules enforced via domain exceptions
- Domain events raised when state changes occur

---

### Layer 2: Application (`backend/app/application/`)

**Purpose:** Orchestration of domain logic, use case implementation via CQRS pattern.

**Contents:**
- **Commands:** Write operation DTOs (CreateBOMCommand, ReleaseWorkOrderCommand)
- **Command Handlers:** Orchestrate domain entities, call repositories, publish events
- **Queries:** Read operation DTOs (GetBOMQuery, ListMaterialsQuery)
- **Query Handlers:** Return read-optimized DTOs (no side effects)
- **Services:** Complex business logic that spans domains (InventoryService, NotificationService)
- **DTOs:** Data Transfer Objects for API responses (BOMResponse, MaterialResponse)
- **Unit of Work:** Transaction coordination across multiple repositories

**Key File Patterns:**
```
application/{context}/
├── commands/          # Command DTOs
│   └── {action}_command.py
├── handlers/          # Command + Query handlers
│   └── {context}_handlers.py
├── queries/           # Query DTOs
│   └── {query}_query.py
├── dtos/              # Response DTOs
│   └── {entity}_response.py
├── services/          # Application services
│   └── {service}_service.py
└── __init__.py
```

**Command Handler Pattern:**
```python
class BOMHandlers:
    def __init__(self, bom_repo: IBOMRepository, uow: IUnitOfWork):
        self.bom_repo = bom_repo
        self.uow = uow
    
    async def handle_create_bom(self, cmd: CreateBOMCommand) -> uuid.UUID:
        # 1. Validate input
        template = await self.bom_repo.get_template(cmd.template_id)
        if not template:
            raise TemplateNotFoundError(cmd.template_id)
        
        # 2. Create entity (domain logic)
        bom = BOM(template_id=cmd.template_id, lines=[...])
        for line in cmd.lines:
            bom.add_line(line)  # May raise DomainException
        
        # 3. Persist via unit of work
        bom_id = await self.uow.save_bom(bom)
        
        # 4. Publish domain events
        await self.event_dispatcher.publish(bom.events)
        
        # 5. Return ID
        return bom_id
```

**Query Handler Pattern:**
```python
async def handle_get_bom(self, query: GetBOMQuery) -> BOMResponse:
    # 1. Fetch from repository
    bom = await self.bom_repo.get_by_id(query.bom_id)
    
    # 2. Convert to DTO
    if not bom:
        raise BOMNotFoundError(query.bom_id)
    
    # 3. Return response (no side effects)
    return BOMResponse.from_entity(bom)
```

**Characteristics:**
- Depends on domain layer (imports entities, exceptions)
- Depends on infrastructure layer (imports repositories via DI)
- No HTTP or FastAPI references
- Commands return IDs or void, queries return DTOs
- Handlers are thin orchestration layers, not business logic

---

### Layer 3: Infrastructure (`backend/app/infrastructure/`)

**Purpose:** Technical implementation of domain contracts, external service integration.

**Contents:**
- **Persistence:**
  - ORM Models (SQLAlchemy): `persistence/models/`
  - Repository Implementations: `persistence/repositories/`
  - Database Connection & Session: `persistence/database.py`
  - Unit of Work: `persistence/unit_of_work.py`
- **Security:**
  - JWT Token Handling: `security/jwt_handler.py`
  - Password Hashing: `security/password_hasher.py`
  - RBAC Enforcement: `security/rbac.py`
- **Storage:**
  - Local File Storage: `storage/local_storage_service.py`
  - Cloudinary Integration: `storage/cloudinary_storage.py`
- **Events:**
  - Event Bus: `events/event_bus.py`
  - Event Dispatcher: `events/event_dispatcher.py`
  - Event Handlers: `events/event_handlers.py`
- **Logging:**
  - Structured Logging: `logging/logger.py`
  - Request Context: `logging/context.py`
  - Error Logging: `logging/error_logger.py`
- **WebSocket:**
  - Connection Management: `websocket/connection_manager.py`
  - Real-Time Event Handlers: `websocket/event_handlers.py`
- **External Services:**
  - Email Service: `external/email_service.py` (interface)
  - Resend Email: `external/resend_email_service.py`
- **Dependency Injection:**
  - DI Container: `di/container.py` (built once at startup)

**Key File Patterns:**
```
infrastructure/
├── persistence/
│   ├── models/
│   │   ├── material_model.py      # SQLAlchemy ORM model
│   │   └── work_order_model.py
│   ├── repositories/
│   │   ├── material_repository.py # Implements IMaterialRepository
│   │   └── work_order_repository.py
│   ├── database.py                # create_engine, session factory
│   └── unit_of_work.py            # Transaction coordination
├── security/
│   ├── jwt_handler.py
│   ├── password_hasher.py
│   └── rbac.py
├── storage/
│   ├── storage_interface.py       # IStorageService
│   ├── local_storage_service.py
│   └── cloudinary_storage.py
├── events/
│   ├── event_bus.py
│   ├── event_dispatcher.py
│   └── event_handler_interface.py
├── logging/
│   ├── logger.py
│   ├── context.py
│   └── error_logger.py
├── websocket/
│   ├── connection_manager.py
│   └── event_handlers.py
├── external/
│   ├── email_service.py           # Interface (IEmailService)
│   └── resend_email_service.py
├── di/
│   └── container.py               # DI Container
└── __init__.py
```

**Repository Pattern Example:**
```python
class MaterialRepository(IMaterialRepository):
    """Implements IMaterialRepository from domain layer."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, tenant_id: UUID, material_id: UUID) -> Material | None:
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.id == material_id,
            MaterialModel.is_deleted == False
        )
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return Material.from_model(model) if model else None
    
    async def list_by_tenant(self, tenant_id: UUID) -> List[Material]:
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted == False
        ).order_by(MaterialModel.created_at.desc())
        result = await self.session.execute(stmt)
        return [Material.from_model(m) for m in result.scalars().all()]
```

**Characteristics:**
- Implements domain repository interfaces
- Contains all database, security, and external service logic
- SQLAlchemy ORM models map database to Python objects
- No domain business logic here (just data access)
- Depends on domain layer (imports entities, exceptions)

---

### Layer 4: Interfaces (`backend/app/interfaces/`)

**Purpose:** HTTP API layer, request/response translation, middleware.

**Contents:**
- **API Routes:** FastAPI route handlers
  - `api/v1/routes/` — 40+ endpoint modules (auth, inventory, manufacturing, sales, etc.)
- **Schemas:** Pydantic request/response validation
  - `api/v1/schemas/` — Input/output validation models
- **Middleware:**
  - TenantMiddleware — Extract tenant from JWT
  - AuditMiddleware — Log all mutations
  - ErrorLoggingMiddleware — Centralized error handling
  - RBACPermissionAuditMiddleware — Log permission denials
  - SecurityHeadersMiddleware — Add security headers (HSTS, CSP)
  - CorrelationIdMiddleware — Trace requests
  - TimingMiddleware — Request timing
  - RequestLoggingMiddleware — Log HTTP requests
- **Dependencies:** FastAPI dependency injection helpers
  - `dependencies/auth.py` — get_current_user, get_current_role
  - `dependencies/db.py` — get_session

**Key File Patterns:**
```
interfaces/api/v1/
├── routes/
│   ├── auth.py             # /auth endpoints
│   ├── inventory.py        # /inventory endpoints
│   ├── work_orders.py      # /work-orders endpoints
│   ├── sales.py            # /sales endpoints
│   └── ... (40+ more)
├── schemas/
│   ├── auth_schemas.py     # Login, RegisterTenant requests/responses
│   ├── inventory_schemas.py # Material, Inventory requests/responses
│   └── ... (more schemas)
├── middleware/
│   ├── tenant_middleware.py
│   ├── audit_middleware.py
│   ├── error_logging_middleware.py
│   ├── rbac_audit.py
│   ├── security_headers.py
│   ├── correlation_id.py
│   ├── timing_middleware.py
│   └── logging_middleware.py
├── dependencies/
│   ├── auth.py
│   └── db.py
├── router.py               # Combines all routes into api_v1_router
└── websocket/
    └── router.py           # WebSocket routes
```

**Route Handler Pattern:**
```python
from fastapi import APIRouter, Depends
from backend.app.infrastructure.container import Container

router = APIRouter(prefix="/materials", tags=["inventory"])

@router.post("/", status_code=201)
async def create_material(
    req: CreateMaterialRequest,
    current_user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
) -> MaterialResponse:
    """Create a new material."""
    
    # Command
    cmd = CreateMaterialCommand(
        code=req.code,
        name=req.name,
        unit_id=req.unit_id,
    )
    
    # Handlers
    handlers = container.material_handlers()
    
    # Execute (application layer orchestration)
    material_id = await handlers.handle_create_material(cmd)
    
    # Fetch and return
    material = await handlers.handle_get_material(GetMaterialQuery(material_id))
    return MaterialResponse.from_dto(material)
```

**Characteristics:**
- Thin translation layer from HTTP to domain
- All request/response validation via Pydantic
- Depends on application layer (imports handlers, commands, queries)
- FastAPI middleware stack processes requests before routes
- Exception handlers convert domain exceptions to HTTP responses

---

## Dependency Injection Container

**Location:** `backend/app/infrastructure/di/container.py`

**Purpose:** Single-instance container built at application startup, stores all singletons.

**Structure:**
```python
@dataclass
class Container:
    # Infrastructure
    db_engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    
    # Security
    jwt_handler: JWTHandler
    password_hasher: IPasswordHasher
    
    # Storage
    storage_service: IStorageService
    
    # Events
    event_bus: InMemoryEventBus
    event_dispatcher: EventDispatcher
    
    # WebSocket
    connection_manager: ConnectionManager
    
    # Tasks
    task_service: BackgroundTaskService
    
    # Audit
    audit_service: AuditService
    
    # Error Logging
    error_log_repository: ErrorLogRepository
    error_logger: ErrorLogger
    
    # External
    email_service: IEmailService
    
    @classmethod
    def create(cls, settings: Settings) -> "Container":
        """Factory method wiring all implementations."""
        # Database
        engine = create_engine(settings.async_database_url)
        session_factory = create_session_factory(engine)
        
        # Security
        jwt_handler = JWTHandler(...)
        password_hasher = BcryptPasswordHasher()
        
        # ... (all other services)
        
        return cls(...)
```

**Usage in FastAPI:**

```python
# main.py: Build container once at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    container = Container.create(settings)
    app.state.container = container
    yield
    await container.db_engine.dispose()

# Route handler: Access via dependency
@router.post("/materials")
async def create_material(
    req: CreateMaterialRequest,
    container: Container = Depends(lambda r: r.app.state.container),
) -> MaterialResponse:
    handlers = BOMHandlers(
        bom_repo=container.bom_repository(),
        uow=container.unit_of_work()
    )
    # ...
```

**Upgrade Path:**
- Swap `LocalStorageService` for `CloudinaryStorageService` by changing one line
- Replace `StubEmailService` with `ResendEmailService` by toggling settings
- Add Redis caching by wiring new service into container
- No changes needed to route handlers or domain logic

---

## Request Lifecycle

```
1. HTTP Request arrives
   ↓
2. Middleware Stack (outermost first):
   - ErrorLoggingMiddleware      (catch all exceptions)
   - CorrelationIdMiddleware     (generate X-Request-ID)
   - TimingMiddleware            (request duration)
   - SecurityHeadersMiddleware   (add headers)
   - SlowAPIMiddleware           (rate limiting)
   - CORSMiddleware              (cross-origin)
   - RBACPermissionAuditMiddleware (log 403 denials)
   - AuditMiddleware             (log mutations)
   - TenantMiddleware            (extract tenant from JWT)
   - RequestLoggingMiddleware    (log request)
   ↓
3. FastAPI Route Handler Executed
   - Extract request data (JSON, query params)
   - Validate with Pydantic schemas
   - Get current user & tenant from context
   - Get container and instantiate handlers
   ↓
4. Application Layer (Handlers)
   - Validate command/query
   - Call domain entities or repositories
   - May raise DomainException
   ↓
5. Domain Layer
   - Business logic (validation, state transitions)
   - Raise DomainException if rules violated
   ↓
6. Repository (Infrastructure Layer)
   - Query/insert/update database
   - Return domain entities or void
   ↓
7. Event Dispatcher
   - Publish domain events (async)
   - Event handlers broadcast WebSocket notifications
   ↓
8. Response Returned
   - Convert domain entity to DTO
   - Serialize to JSON
   ↓
9. Middleware unwinding
   - AuditMiddleware records mutation
   - ErrorLoggingMiddleware logs if error
   ↓
10. HTTP Response sent to client
```

---

## Middleware Stack (Order Matters)

**Outermost (first) to innermost (last):**

```python
app.add_middleware(ErrorLoggingMiddleware)              # ✅ Catch all exceptions
app.add_middleware(CorrelationIdMiddleware)            # ✅ X-Request-ID tracing
app.add_middleware(TimingMiddleware)                   # ✅ Request duration
app.add_middleware(SecurityHeadersMiddleware)          # ✅ HSTS, CSP headers
app.add_middleware(SlowAPIMiddleware)                  # ✅ Rate limiting
app.add_middleware(CORSMiddleware)                     # ✅ Cross-origin policy
app.add_middleware(RBACPermissionAuditMiddleware)      # ✅ Log 403 denials
app.add_middleware(AuditMiddleware)                    # ✅ Log mutations
app.add_middleware(TenantMiddleware)                   # ✅ CRITICAL: Extract tenant
app.add_middleware(RequestLoggingMiddleware)           # ✅ Log requests
```

**Key Middleware:**

1. **TenantMiddleware**
   - Extracts JWT token from Authorization header
   - Decodes JWT and retrieves tenant_id claim
   - Sets ContextVar with tenant_id for application access
   - Enforces tenant isolation at HTTP boundary

2. **AuditMiddleware**
   - Logs all state-changing requests (POST, PUT, PATCH, DELETE)
   - Captures entity, action, user, timestamp, tenant
   - Stores in audit_logs table for compliance

3. **ErrorLoggingMiddleware**
   - Catches all unhandled exceptions
   - Logs with full context (tenant, user, correlation_id)
   - Converts DomainException to HTTP responses (401/422)

4. **RBACPermissionAuditMiddleware**
   - Logs all 403 Forbidden responses
   - Tracks permission denial attempts for security monitoring

5. **CorrelationIdMiddleware**
   - Generates/preserves X-Request-ID header
   - Logs correlation_id with all structured logging
   - Enables end-to-end request tracing

---

## Event-Driven Architecture

**Flow:**

```
Domain Entity State Change
  ↓
Domain Event Created (e.g., WorkOrderCompletedEvent)
  ↓
Event Dispatcher.publish(events)
  ↓
Event Bus finds subscribers for event type
  ↓
Multiple subscribers execute in parallel:
  - InventoryService: Consume reserved materials
  - ProductionMetricsService: Update KPIs
  - WebSocketHandler: Broadcast real-time update to clients
  - NotificationService: Send alerts
  ↓
All side effects completed (async)
```

**Event Types (Domain Events in `domain/shared/events/`):**

- `order.status_changed` → OrderStatusChangeHandler
- `inventory.low_stock_alert` → InventoryLowStockAlert
- `work_order.released` → WorkOrderReleased
- `work_order.started` → WorkOrderStarted
- `work_order.completed` → WorkOrderCompleted
- `invoice.overdue` → InvoiceOverdue
- `quality.inspection_failed` → QualityInspectionFailed

**WebSocket Event Handlers (real-time updates):**

```python
class OrderStatusChangeHandler(WebSocketNotificationHandler):
    @property
    def event_type(self) -> str:
        return "order.status_changed"
    
    async def handle(self, event: DomainEvent) -> None:
        # Create notification
        notification = {
            "type": "ORDER_STATUS_CHANGED",
            "order_id": str(event.order_id),
            "status": event.status,
        }
        
        # Broadcast to all clients in tenant
        await self.connection_manager.broadcast_to_tenant(
            tenant_id=event.tenant_id,
            message_type="notification",
            payload=notification
        )
```

**Registration (main.py):**

```python
event_dispatcher.subscribe(
    "order.status_changed", OrderStatusChangeHandler(connection_manager)
)
event_dispatcher.subscribe(
    "work_order.completed", WorkOrderCompleted(connection_manager)
)
# ... (all 7+ event types)
```

---

## WebSocket Real-Time Updates

**Location:** `backend/app/infrastructure/websocket/`

**Architecture:**

```
Client connects: POST /api/v1/ws?token=JWT
  ↓
ConnectionManager tracks connection (tenant_id, connection_id)
  ↓
Domain event published: work_order.completed
  ↓
Event Dispatcher publishes to subscribers
  ↓
WebSocketEventHandler.handle() processes event
  ↓
ConnectionManager.broadcast_to_tenant() sends message
  ↓
All connected clients receive: 
  {
    "type": "notification",
    "data": {
      "type": "WORK_ORDER_COMPLETED",
      "work_order_id": "...",
      "status": "COMPLETED"
    }
  }
```

**Connection Manager:**

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, tenant_id: str, websocket: WebSocket):
        await websocket.accept()
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = []
        self.active_connections[tenant_id].append(websocket)
    
    async def broadcast_to_tenant(self, tenant_id: str, message_type: str, payload: dict):
        connections = self.active_connections.get(tenant_id, [])
        for connection in connections:
            await connection.send_json({
                "type": message_type,
                "data": payload
            })
```

**Usage in Frontend:**

```typescript
const websocket = new WebSocket('ws://localhost:8001/api/v1/ws?token=JWT');

websocket.onmessage = (event) => {
  const { type, data } = JSON.parse(event.data);
  
  if (type === 'notification') {
    if (data.type === 'WORK_ORDER_COMPLETED') {
      // Update UI with new status
      setWorkOrders(prev => 
        prev.map(wo => wo.id === data.work_order_id 
          ? { ...wo, status: 'COMPLETED' }
          : wo
        )
      );
      toast.success(`Order completed: ${data.work_order_id}`);
    }
  }
};
```

---

## Multi-Tenancy Architecture

**Principle:** Complete data isolation per tenant at every layer.

**Implementation:**

1. **JWT Extraction (TenantMiddleware)**
   ```python
   # JWT claims
   {
     "sub": "user-id",
     "tid": "tenant-id",  # ← Tenant ID in token
     "role": "MANAGER",
     "exp": 1234567890
   }
   ```

2. **ContextVar Storage**
   ```python
   # middleware/tenant_middleware.py
   def set_tenant_id(tenant_id: str):
       _tenant_context.set(tenant_id)
   
   def get_tenant_id() -> str:
       return _tenant_context.get()
   ```

3. **Database Queries**
   ```python
   # Every query MUST filter by tenant_id
   stmt = select(Material).where(
       Material.tenant_id == get_tenant_id(),  # ← Mandatory filter
       Material.is_deleted == False
   )
   ```

4. **Audit Logging**
   ```python
   logger.info("Material created", extra={
       "tenant_id": str(tenant_id),  # ← Always log tenant
       "user_id": str(user_id),
       "material_id": str(material_id)
   })
   ```

**Verification:**
- Every route receives tenant from JWT
- Every repository method accepts tenant_id parameter
- Every SELECT query includes tenant_id filter
- Every INSERT/UPDATE/DELETE sets tenant_id from context
- Foreign key constraints enforce tenant_id references
- Logs always include tenant context

---

## Configuration Management

**Location:** `backend/app/config.py`

**Pattern:** Pydantic BaseSettings with environment variables

**Key Settings:**
```python
class Settings(BaseSettings):
    # Application
    app_name: str = "MedTrack ERP"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    
    # Database
    database_url: str  # postgresql+asyncpg://...
    jwt_secret_key: str  # Must set in production
    
    # CORS
    cors_origins: str = "*"  # Set explicitly in production
    
    # File Storage
    upload_dir: str = "./uploads"
    cloudinary_cloud_name: str = ""
    
    # Email
    email_backend: str = "resend"
    resend_api_key: str = ""
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    def validate_cors_for_production(self) -> None:
        if self.is_production and self.cors_origins == "*":
            raise ValueError("CORS must be explicitly configured for production")
```

**Usage:**
```python
settings = get_settings()

# In lifespan
if settings.is_production:
    settings.validate_cors_for_production()
```

---

## Error Handling Strategy

**Layer-by-Layer:**

1. **Domain Layer**
   ```python
   if not template:
       raise TemplateNotFoundError(template_id)
   if self.is_active:
       raise BOMIsActiveError(self.id)
   ```

2. **Application Layer (Handlers)**
   ```python
   try:
       bom = BOM(...)
       bom.add_line(line)  # May raise DomainException
   except DomainException as e:
       logger.error("Business rule violation", extra={"error": str(e)})
       raise
   ```

3. **Interface Layer (Exception Handler)**
   ```python
   @app.exception_handler(DomainException)
   async def domain_exception_handler(request, exc: DomainException):
       if exc.code in _AUTH_CODES:
           return JSONResponse(status_code=401, content={"detail": exc.message})
       return JSONResponse(status_code=422, content={"detail": exc.message})
   ```

**Domain Exception Hierarchy:**
```
DomainException (base, code + message)
├── AuthenticationException (401)
├── AuthorizationException (403)
└── BusinessRuleViolation (422)
    ├── InsufficientStockError
    ├── DuplicateComponentError
    ├── InvalidStateTransitionError
    └── TemplateNotFoundError
```

---

## Summary

| Layer | Purpose | Dependencies | Examples |
|-------|---------|--------------|----------|
| **Domain** | Pure business logic | None (isolated) | Entities, events, exceptions |
| **Application** | CQRS orchestration | Domain, Infrastructure | Handlers, commands, queries, DTOs |
| **Infrastructure** | Technical implementation | Domain | Repositories, ORM, security, storage |
| **Interfaces** | HTTP translation | Application, Domain | Routes, schemas, middleware |

---

## Key Files Reference

- **Application Entry:** `backend/app/main.py`
- **Configuration:** `backend/app/config.py`
- **DI Container:** `backend/app/infrastructure/di/container.py`
- **Middleware Stack:** `backend/app/interfaces/api/v1/middleware/`
- **API Routes:** `backend/app/interfaces/api/v1/routes/`
- **Domain Events:** `backend/app/domain/shared/events/`
- **WebSocket Handlers:** `backend/app/infrastructure/websocket/event_handlers.py`
