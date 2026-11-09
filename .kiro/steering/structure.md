---
name: "MedTrack Code Structure & Module Organization"
description: "Backend and frontend folder structure, module responsibilities, architecture boundaries, and shared components"
inclusion: auto
---

# MedTrack Code Structure & Module Organization

**Updated:** November 9, 2026  
**Version:** 1.0.0  
**Canonical Reference:** [`AGENTS.md`](../../AGENTS.md) Section 4 | [`STRUCTURE`](../../docs/structure.md)

**Multi-Tenancy & Security Details:** See [security.instructions.md](../../.github/instructions/security.instructions.md), [SECURITY_AND_MULTITENANCY.md](../../docs/ai-guidelines/SECURITY_AND_MULTITENANCY.md), and [AGENTS.md § 14](../../AGENTS.md)

---

## Backend Structure Overview

```
backend/app/
├── main.py                      # FastAPI app entry point
├── config.py                    # Settings from environment
│
├── domain/                      # Layer 1: Business Logic (DDD)
│   ├── bom/                     # Bill of Materials context
│   │   ├── entities/            # BOM, BOMLine entities
│   │   ├── value_objects/       # Component, Material reference
│   │   ├── events/              # BOMCreatedEvent, BOMActivatedEvent
│   │   ├── exceptions/          # DuplicateComponentError, etc.
│   │   ├── interfaces/          # IBOMRepository interface
│   │   └── __init__.py
│   │
│   ├── manufacturing/           # Work Orders & Production context
│   │   ├── entities/            # WorkOrder, Operation, Job
│   │   ├── value_objects/       # Routing, JobCard
│   │   ├── events/              # WorkOrderReleasedEvent, etc.
│   │   ├── exceptions/          # InvalidStateTransitionError
│   │   ├── interfaces/          # IWorkOrderRepository
│   │   └── __init__.py
│   │
│   ├── inventory/               # Stock & Reservations context
│   │   ├── entities/            # Material, Warehouse, Reservation
│   │   ├── value_objects/       # StockLevel, Batch
│   │   ├── events/              # LowStockAlertEvent, etc.
│   │   ├── exceptions/          # InsufficientStockError
│   │   ├── interfaces/          # IMaterialRepository
│   │   └── __init__.py
│   │
│   ├── sales/                   # Orders & Quotes context
│   │   ├── entities/            # SalesOrder, Quote, Customer
│   │   ├── value_objects/       # OrderLine, Pricing
│   │   ├── events/              # SalesOrderApprovedEvent
│   │   ├── exceptions/          # OrderAlreadyApprovedError
│   │   ├── interfaces/          # ISalesOrderRepository
│   │   └── __init__.py
│   │
│   ├── procurement/             # POs & GRNs context
│   │   ├── entities/            # PurchaseOrder, GRN, Supplier
│   │   ├── value_objects/       # POLine, Shipment
│   │   ├── events/              # GRNReceivedEvent
│   │   ├── exceptions/          # ExcessiveGRNError
│   │   ├── interfaces/          # IPORepository, IGRNRepository
│   │   └── __init__.py
│   │
│   ├── quality/                 # QC & Inspections context
│   │   ├── entities/            # Inspection, NonConformance
│   │   ├── value_objects/       # InspectionResult, Defect
│   │   ├── events/              # QCPassedEvent, QCFailedEvent
│   │   ├── exceptions/          # InspectionFailedError
│   │   ├── interfaces/          # IInspectionRepository
│   │   └── __init__.py
│   │
│   ├── finance/                 # Invoicing & Ledger context
│   │   ├── entities/            # Invoice, Payment, JournalEntry
│   │   ├── value_objects/       # Money, CostAllocation
│   │   ├── events/              # InvoiceIssuedEvent
│   │   ├── exceptions/          # InsufficientFundsError
│   │   ├── interfaces/          # IInvoiceRepository
│   │   └── __init__.py
│   │
│   ├── tenant/                  # Multi-Tenancy & Auth context
│   │   ├── entities/            # Tenant, User, Role
│   │   ├── value_objects/       # Permission, RoleSet
│   │   ├── events/              # UserCreatedEvent
│   │   ├── exceptions/          # UnauthorizedError
│   │   ├── interfaces/          # ITenantRepository
│   │   └── __init__.py
│   │
│   ├── shared/                  # Cross-Cutting Domain Abstractions
│   │   ├── exceptions/          # DomainException (base)
│   │   ├── value_objects/       # Money, Quantity, Price
│   │   ├── events/              # DomainEvent (base)
│   │   └── __init__.py
│   │
│   └── __init__.py
│
├── application/                 # Layer 2: Use Cases (CQRS)
│   ├── bom/
│   │   ├── commands/            # CreateBOMCommand, ActivateBOMCommand
│   │   ├── queries/             # GetBOMQuery, ListBOMsQuery
│   │   ├── handlers/            # BOMHandlers (commands + queries)
│   │   ├── dtos/                # BOMResponse, BOMLineResponse
│   │   ├── services/            # BOMService (orchestration)
│   │   └── __init__.py
│   │
│   ├── manufacturing/           # Work order use cases
│   │   ├── commands/            # ReleaseWorkOrderCommand, etc.
│   │   ├── queries/             # GetWorkOrderQuery, etc.
│   │   ├── handlers/            # WorkOrderHandlers
│   │   ├── dtos/                # WorkOrderResponse
│   │   ├── services/            # InventoryService (coordinating)
│   │   └── __init__.py
│   │
│   ├── inventory/               # Inventory use cases
│   │   ├── commands/            # ResrveInventoryCommand, etc.
│   │   ├── queries/             # GetMaterialQuery, etc.
│   │   ├── handlers/            # InventoryHandlers
│   │   ├── dtos/                # MaterialResponse
│   │   ├── services/            # StockLevelService
│   │   └── __init__.py
│   │
│   ├── sales/                   # Sales order use cases
│   ├── procurement/             # PO/GRN use cases
│   ├── quality/                 # QC use cases
│   ├── finance/                 # Invoice use cases
│   │
│   └── __init__.py
│
├── infrastructure/              # Layer 3: Persistence & Services
│   ├── di/
│   │   └── container.py         # Dependency injection setup
│   │
│   ├── persistence/
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── bom_material_model.py
│   │   │   ├── work_order_model.py
│   │   │   ├── material_model.py
│   │   │   ├── sales_order_model.py
│   │   │   ├── purchase_order_model.py
│   │   │   ├── inspection_model.py
│   │   │   ├── invoice_model.py
│   │   │   └── __init__.py
│   │   │
│   │   ├── repositories/        # Repository implementations
│   │   │   ├── bom_repository.py            # Implements IBOMRepository
│   │   │   ├── work_order_repository.py     # Implements IWorkOrderRepository
│   │   │   ├── material_repository.py       # Implements IMaterialRepository
│   │   │   ├── sales_order_repository.py
│   │   │   ├── purchase_order_repository.py
│   │   │   └── __init__.py
│   │   │
│   │   ├── unit_of_work.py      # Transaction coordination
│   │   ├── session.py           # Async session factory
│   │   └── __init__.py
│   │
│   ├── security/
│   │   ├── auth.py              # JWT creation & validation
│   │   ├── bcrypt_service.py    # Password hashing
│   │   ├── rbac.py              # RBAC permission checking
│   │   └── __init__.py
│   │
│   ├── logging/
│   │   ├── logger.py            # structlog configuration
│   │   ├── context.py           # ContextVars for tenant/user
│   │   └── __init__.py
│   │
│   ├── storage/
│   │   ├── cloudinary_storage.py  # File upload provider (optional)
│   │   ├── local_storage.py       # Local file storage
│   │   └── __init__.py
│   │
│   ├── events/
│   │   ├── event_dispatcher.py   # Publish/subscribe for domain events
│   │   ├── event_handlers.py     # Event listener implementations
│   │   └── __init__.py
│   │
│   ├── websocket/
│   │   ├── connection_manager.py  # WebSocket connection tracking
│   │   ├── event_handlers.py      # WebSocket event handlers
│   │   └── __init__.py
│   │
│   └── __init__.py
│
├── interfaces/                  # Layer 4: HTTP API & Middleware
│   ├── api/
│   │   └── v1/
│   │       ├── routes/          # FastAPI route handlers
│   │       │   ├── bom_routes.py
│   │       │   ├── work_order_routes.py
│   │       │   ├── material_routes.py
│   │       │   ├── sales_order_routes.py
│   │       │   ├── purchase_order_routes.py
│   │       │   ├── inspection_routes.py
│   │       │   └── __init__.py
│   │       │
│   │       ├── schemas/         # Pydantic request/response models
│   │       │   ├── bom_schemas.py
│   │       │   ├── work_order_schemas.py
│   │       │   ├── material_schemas.py
│   │       │   └── __init__.py
│   │       │
│   │       ├── middleware/      # Request/response processing
│   │       │   ├── tenant_middleware.py        # Extract tenant from JWT
│   │       │   ├── rbac_audit.py              # Log permission denials
│   │       │   ├── error_logging_middleware.py
│   │       │   ├── audit_middleware.py        # Log mutations
│   │       │   └── __init__.py
│   │       │
│   │       └── router.py        # Main router combining all routes
│   │
│   ├── websocket/
│   │   └── router.py            # WebSocket routes
│   │
│   └── __init__.py
│
├── middleware/                  # Cross-Cutting Middleware
│   ├── security_headers.py      # HSTS, CSP, etc.
│   ├── rate_limiting.py         # slowapi rate limiting
│   ├── correlation_id.py        # Request tracing
│   └── __init__.py
│
├── services/                    # Shared Business Services
│   ├── notification_service.py  # Send alerts, emails
│   ├── document_service.py      # PDF generation
│   └── __init__.py
│
├── core/                        # Application Core
│   ├── logging.py               # Logging configuration
│   ├── module_registry.py       # System map for dependency validation
│   └── __init__.py
│
├── templates/                   # Jinja2 Templates
│   ├── work_order_template.html
│   ├── invoice_template.html
│   └── purchase_order_template.html
│
├── tests/                       # Test Suite
│   ├── unit/                    # Pure logic tests (no I/O)
│   │   ├── domain/
│   │   │   ├── bom/
│   │   │   │   └── test_bom_entity.py
│   │   │   └── inventory/
│   │   │       └── test_material_entity.py
│   │   └── application/
│   │       └── bom/
│   │           └── test_bom_handlers.py
│   │
│   ├── integration/             # With database
│   │   └── application/
│   │       └── bom/
│   │           └── test_bom_handlers.py
│   │
│   ├── e2e/                     # Full API flow
│   │   └── test_work_order_flow.py
│   │
│   ├── conftest.py              # Pytest fixtures
│   └── __init__.py
│
├── utils/                       # Utility Functions
│   ├── validators.py            # Custom validators
│   ├── formatters.py            # Data formatting
│   └── __init__.py
│
└── __init__.py
```

---

## Frontend Structure Overview

```
frontend/src/
├── main.tsx                     # React entry point
├── App.tsx                      # Root component
├── index.css                    # Global styles (Tailwind)
│
├── app/                         # Application Setup
│   ├── store.ts                 # State management
│   ├── router.ts                # Route definitions
│   └── env.ts                   # Environment variables
│
├── assets/                      # Static Files
│   ├── images/
│   ├── icons/
│   └── fonts/
│
├── components/                  # Shared Components
│   ├── shared/                  # Generic UI components
│   │   ├── Button.tsx           # Reusable button
│   │   ├── Modal.tsx            # Modal dialog
│   │   ├── LoadingSpinner.tsx   # Loading indicator
│   │   ├── ErrorMessage.tsx     # Error display
│   │   ├── EmptyState.tsx       # Empty list state
│   │   ├── Pagination.tsx       # Pagination controls
│   │   └── __tests__/
│   │       ├── Button.test.tsx
│   │       └── Modal.test.tsx
│   │
│   ├── forms/                   # Form Components
│   │   ├── FormField.tsx        # Form input wrapper
│   │   ├── FormSubmitButton.tsx # Submit button with loading
│   │   ├── FormError.tsx        # Error display
│   │   └── __tests__/
│   │
│   ├── layout/                  # Layout Components
│   │   ├── Sidebar.tsx          # Navigation sidebar
│   │   ├── Header.tsx           # Page header
│   │   ├── PageLayout.tsx       # Full page layout
│   │   ├── MainLayout.tsx       # Main app layout
│   │   └── __tests__/
│   │
│   └── shared/
│       ├── AuditHistoryTab.tsx  # Audit trail display
│       └── ...
│
├── modules/                     # Feature Modules (Business Domains)
│   ├── auth/
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   └── TwoFactorPage.tsx
│   │   ├── components/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── TwoFactorPrompt.tsx
│   │   │   └── PasswordReset.tsx
│   │   ├── hooks/
│   │   │   ├── useAuth.ts          # Auth state management
│   │   │   ├── useLogin.ts         # Login mutation hook
│   │   │   └── use2FA.ts
│   │   ├── services/
│   │   │   └── authApi.ts          # Auth API client
│   │   ├── types/
│   │   │   └── auth.types.ts       # TypeScript interfaces
│   │   └── __tests__/
│   │       ├── LoginPage.test.tsx
│   │       ├── useAuth.test.ts
│   │       └── authApi.test.ts
│   │
│   ├── sales/                   # Sales Orders Module
│   │   ├── pages/
│   │   │   ├── SalesOrderListPage.tsx      # List page
│   │   │   ├── SalesOrderDetailPage.tsx    # Detail page
│   │   │   └── CreateSalesOrderPage.tsx    # Create page
│   │   ├── components/
│   │   │   ├── SalesOrderTable.tsx         # Table view
│   │   │   ├── OrderApprovalModal.tsx      # Approve dialog
│   │   │   ├── SalesOrderActionPanel.tsx   # Actions
│   │   │   ├── SalesOrderForm.tsx          # Form
│   │   │   └── ProductionTrackerPanel.tsx  # Production tracking
│   │   ├── hooks/
│   │   │   ├── useSalesOrders.ts
│   │   │   ├── useSalesOrderForm.ts
│   │   │   └── useOrderApproval.ts
│   │   ├── services/
│   │   │   └── salesApi.ts
│   │   ├── types/
│   │   │   └── sales.types.ts
│   │   └── __tests__/
│   │
│   ├── inventory/               # Inventory Module
│   │   ├── pages/
│   │   │   ├── MaterialListPage.tsx
│   │   │   ├── MaterialDetailPage.tsx
│   │   │   ├── MaterialOnboardingPage.tsx
│   │   │   ├── WarehouseStockPage.tsx
│   │   │   └── LowStockAlertsPage.tsx
│   │   ├── components/
│   │   │   ├── MaterialTable.tsx
│   │   │   ├── MaterialForm.tsx
│   │   │   ├── StockLevelView.tsx
│   │   │   ├── BatchTrackingView.tsx
│   │   │   ├── ReservationList.tsx
│   │   │   └── LowStockAlertBanner.tsx
│   │   ├── hooks/
│   │   │   ├── useMaterials.ts
│   │   │   ├── useStockLevels.ts
│   │   │   └── useLowStockAlerts.ts
│   │   ├── services/
│   │   │   └── inventoryApi.ts
│   │   ├── types/
│   │   │   └── inventory.types.ts
│   │   └── __tests__/
│   │
│   ├── manufacturing/           # Manufacturing Module
│   │   ├── pages/
│   │   │   ├── WorkOrderListPage.tsx
│   │   │   ├── WorkOrderDetailPage.tsx
│   │   │   ├── CreateWorkOrderPage.tsx
│   │   │   └── ShopFloorPage.tsx
│   │   ├── components/
│   │   │   ├── WorkOrderTable.tsx
│   │   │   ├── WorkOrderForm.tsx
│   │   │   ├── WorkOrderStatusTracker.tsx
│   │   │   └── ShopFloorDashboard.tsx
│   │   ├── hooks/
│   │   │   ├── useWorkOrders.ts
│   │   │   └── useWorkOrderForm.ts
│   │   ├── services/
│   │   │   └── manufacturingApi.ts
│   │   ├── types/
│   │   │   └── manufacturing.types.ts
│   │   └── __tests__/
│   │
│   ├── procurement/             # Procurement Module
│   │   ├── pages/
│   │   │   ├── POListPage.tsx
│   │   │   ├── PODetailPage.tsx
│   │   │   ├── GRNPage.tsx
│   │   │   └── SubcontractingPage.tsx
│   │   ├── components/
│   │   │   ├── POTable.tsx
│   │   │   ├── POForm.tsx
│   │   │   ├── GRNForm.tsx
│   │   │   ├── IssueMaterialDrawer.tsx
│   │   │   └── SupplierPerformanceChart.tsx
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── __tests__/
│   │
│   ├── quality/                 # Quality Module
│   │   ├── pages/
│   │   │   ├── InspectionListPage.tsx
│   │   │   ├── InspectionDetailPage.tsx
│   │   │   └── NonconformancePage.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── __tests__/
│   │
│   ├── finance/                 # Finance Module
│   │   ├── pages/
│   │   │   ├── InvoiceListPage.tsx
│   │   │   ├── InvoiceDetailPage.tsx
│   │   │   └── ARAPDashboardPage.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── __tests__/
│   │
│   └── analytics/               # Analytics & Reporting
│       ├── pages/
│       │   ├── DashboardPage.tsx
│       │   ├── MRPDashboard.tsx
│       │   └── ProductionMetricsPage.tsx
│       ├── components/
│       ├── hooks/
│       ├── services/
│       ├── types/
│       └── __tests__/
│
├── hooks/                       # Global Custom Hooks
│   ├── useQuery.ts              # Data fetching hook
│   ├── useMutation.ts           # Data mutation hook
│   ├── useAuth.ts               # Auth context hook
│   ├── useNotification.ts       # Toast notifications
│   ├── usePagination.ts         # Pagination logic
│   └── __tests__/
│
├── services/                    # Global API Clients
│   ├── api.ts                   # Axios instance with interceptors
│   ├── authApi.ts               # Auth endpoints
│   ├── materialsApi.ts          # Materials endpoints
│   ├── workOrdersApi.ts         # Work orders endpoints
│   ├── salesOrdersApi.ts        # Sales orders endpoints
│   └── __tests__/
│
├── types/                       # Global TypeScript Interfaces
│   ├── api.types.ts             # API response types
│   ├── entities.types.ts        # Business entity types
│   ├── common.types.ts          # Common types (pagination, etc.)
│   └── errors.types.ts          # Error types
│
├── utils/                       # Utility Functions
│   ├── format.ts                # Formatting helpers
│   ├── validate.ts              # Validation functions
│   ├── date.ts                  # Date utilities
│   └── __tests__/
│
├── config/                      # Configuration
│   ├── env.ts                   # Environment variables
│   ├── constants.ts             # App constants
│   ├── api.config.ts            # API configuration
│   └── routes.config.ts         # Route definitions
│
├── tokens/                      # Design Tokens
│   ├── colors.ts                # Color palette
│   ├── spacing.ts               # Spacing scale
│   ├── typography.ts            # Typography tokens
│   └── shadows.ts               # Shadow definitions
│
├── lib/                         # Third-Party Integrations
│   ├── date.ts                  # date-fns setup
│   ├── form.ts                  # React Hook Form setup
│   └── charts.ts                # Recharts setup
│
├── test/                        # Test Utilities
│   ├── setup.ts                 # Vitest setup
│   ├── mocks/
│   │   ├── api.mock.ts          # Mock API responses
│   │   └── handlers.ts          # MSW handlers
│   └── fixtures/
│       └── testData.ts          # Test data factories
│
└── vite-env.d.ts                # Vite environment types
```

---

## Module Responsibilities

### Backend Modules (Bounded Contexts)

| Module | Responsibility | Primary Entities |
|--------|----------------|------------------|
| **BOM** | Product configuration, versioning | BOM, BOMLine, Template |
| **Manufacturing** | Production execution, work orders | WorkOrder, Operation, Routing |
| **Inventory** | Stock management, reservations | Material, Warehouse, Reservation |
| **Sales** | Customer orders, pricing | SalesOrder, Quote, Customer |
| **Procurement** | POs, suppliers, GRNs | PurchaseOrder, GRN, Supplier |
| **Quality** | QC inspections, compliance | Inspection, NonConformance |
| **Finance** | Invoicing, ledger | Invoice, Payment, JournalEntry |
| **Tenant** | Multi-tenancy, auth | User, Role, Permission |

### Frontend Modules (Feature Domains)

| Module | Pages | Responsibility |
|--------|-------|-----------------|
| **auth** | Login, Register, 2FA | User authentication, login/logout |
| **sales** | Orders, Details, Create | Sales order management |
| **inventory** | Materials, Stock, Alerts | Stock management, inventory |
| **manufacturing** | Work Orders, Shop Floor | Production execution |
| **procurement** | POs, GRNs, Suppliers | Procurement workflows |
| **quality** | Inspections, Issues | Quality control workflows |
| **finance** | Invoices, AR/AP | Financial tracking |
| **analytics** | Dashboards, Reports | Real-time analytics |

---

## Architecture Boundaries

### DDD Layer Boundaries

**Domain Layer:**
- ✅ Business entities, value objects
- ✅ Domain events, exceptions
- ❌ No database access
- ❌ No HTTP concerns
- ❌ No external service calls

**Application Layer:**
- ✅ CQRS handlers, commands, queries
- ✅ Orchestration between domain and infrastructure
- ✅ DTOs for API responses
- ❌ No business logic (delegate to domain)
- ❌ No direct database queries (use repositories)

**Infrastructure Layer:**
- ✅ Repository implementations
- ✅ Database access via ORM
- ✅ External service integrations
- ❌ No business logic
- ❌ No HTTP routing

**Interfaces Layer:**
- ✅ FastAPI routes (thin translation)
- ✅ Pydantic schemas (validation)
- ✅ Middleware (cross-cutting)
- ❌ No business logic (delegate to handlers)
- ❌ No database queries (use handlers)

---

## Shared Components & Services

### Shared Backend Services

| Service | Location | Purpose |
|---------|----------|---------|
| **NotificationService** | `services/notification_service.py` | Send alerts, emails |
| **DocumentService** | `services/document_service.py` | PDF generation |
| **EventDispatcher** | `infrastructure/events/` | Domain event publishing |
| **PermissionService** | `infrastructure/security/rbac.py` | RBAC checking |
| **AuditLogger** | `infrastructure/logging/` | Mutation logging |

### Shared Frontend Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **LoadingSpinner** | `components/shared/` | Loading indicator |
| **Modal** | `components/shared/` | Dialog modal |
| **ErrorMessage** | `components/shared/` | Error display |
| **Button** | `components/shared/` | Reusable button |
| **AuditHistoryTab** | `components/shared/` | Audit trail display |

### Shared Frontend Hooks

| Hook | Location | Purpose |
|------|----------|---------|
| **useAuth** | `hooks/` | Auth state management |
| **useQuery** | `hooks/` | Data fetching |
| **useMutation** | `hooks/` | Data mutation |
| **useNotification** | `hooks/` | Toast notifications |

---

## Reference

- **Detailed backend structure:** `docs/guides/BACKEND_STRUCTURE.md`
- **Detailed frontend structure:** `docs/guides/FRONTEND_STRUCTURE.md`
- **Architecture patterns:** [`AGENTS.md`](../../AGENTS.md) Section 4
- **Module organization:** [`STRUCTURE`](../../docs/structure.md)

---

**Status:** Production Ready | Last Updated: November 9, 2026
