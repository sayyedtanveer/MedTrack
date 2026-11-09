# MedTrack ERP - Comprehensive Codebase Analysis

**Date:** April 14, 2026 | **Project Version:** 0.1.0  
**Architecture:** FastAPI backend (DDD/CQRS) + React frontend  
**Status:** Multi-phase development (Phase 0-4 in progress)

---

## 1. PROJECT OVERVIEW

### What is MedTrack?
**MedTrack** is a **multi-tenant Manufacturing ERP System** designed for manufacturing companies to manage the complete product lifecycle from design through production and sales. It handles:
- Product templates and variants with configurable attributes
- Bill of Materials (BOM) management with versioning
- Work order creation and shop floor execution
- Inventory and material management
- Sales order processing and client portal
- Supply chain operations (Procurement, GRN, subcontracting)
- Quality control and inspection templates
- Finance module (invoicing, payments, AR/AP)
- Real-time notifications and reporting

### Industry/Use Case
**Target**: Mid-to-large manufacturing facilities with:
- Complex multi-level BOMs
- Multiple production facilities
- Supplier/subcontractor networks
- Quality assurance requirements
- Client-facing portal needs

### Key Features
- ✅ **Multi-tenancy**: Full data isolation per customer; tenant extracted from JWT
- ✅ **DDD Architecture**: Domain-driven design with clear bounded contexts
- ✅ **CQRS Pattern**: Separate command and query pipelines
- ✅ **Async-First**: FastAPI + SQLAlchemy async + asyncpg
- ✅ **Soft Deletes**: All entities have `is_deleted` + `deleted_at`
- ✅ **Audit Logging**: All changes tracked with user/tenant context
- ✅ **File Uploads**: Asset management with /uploads directory
- ✅ **Notifications**: Event-driven notifications to users

---

## 2. AUTHENTICATION & USER ROLES

### Authentication Flow

**Registration (Tenant Onboarding)**
```
POST /api/v1/auth/register-tenant → RegisterTenantRequest
  └─ Creates: Tenant + Admin User + Initial audit log
  └─ Response: RegisterTenantResponse with tenant_id
```

**Login**
```
POST /api/v1/auth/login
  ├─ Input: email + password
  ├─ Validates credentials against User (hashed with bcrypt)
  └─ Returns: JWT access token with claims:
     ├─ sub (user_id)
     ├─ tid (tenant_id)
     ├─ role (string)
     └─ exp (expiration)
```

**Current User**
```
GET /api/v1/auth/me → UserProfileResponse
  └─ Returns authenticated user details + tenant info
```

### User Roles (13 distinct roles)

| Role | Primary Responsibilities | Key Permissions |
|------|---------------------------|-----------------|
| **ADMIN** | System administrator | `*` (all permissions) |
| **TENANT_ADMIN** | Tenant account owner | `*` (all permissions) |
| **MANAGER** | Operations manager | Inventory R/W, Sales R/W, Manufacturing R/W, Finance R, Procurement R/W, Quality R/W, Reports R |
| **OPERATOR** | Shop floor / warehouse | Inventory R/W, Manufacturing R/W, Quality R/W, Procurement R/W |
| **STOREKEEPER** | Inventory manager | Inventory R/W, Manufacturing R/W, Quality R/W, Procurement R/W |
| **PLANNER** | Production planner | Inventory R, Manufacturing R/W, Procurement R/W, Quality R, Reports R |
| **QC** | Quality control | Inventory R, Quality R/W, Procurement R |
| **SALES** | Sales representative | Inventory R, Sales R/W, Manufacturing R, Reports R |
| **WORKER** | Shop floor worker | Manufacturing R/W, Inventory R |
| **CLIENT** | External customer | Sales R, Inventory R (via portal) |
| **SUPPLIER** | External supplier | Procurement R/W (via portal) |
| **VIEWER** | Read-only user | All modules READ only |

### Permission Model

**Fine-grained permissions** using `{module}:{action}` convention:

```python
# Available Permissions
- tenant:read, tenant:write
- user:read, user:write, user:invite
- inventory:read, inventory:write, inventory:delete
- sales:read, sales:write, sales:delete
- manufacturing:read, manufacturing:write
- procurement:read, procurement:write
- finance:read, finance:write
- quality:read, quality:write
- reports:read
```

### Authentication Dependencies
- **JWT Handler**: Encodes/decodes tokens with secret from `.env`
- **Password Hasher**: bcrypt (via passlib)
- **Security Middleware**: `TenantMiddleware` extracts `tenant_id` from JWT
- **Audit Middleware**: Logs all requests with correlation IDs

---

## 3. FRONTEND PAGES & SCREENS

### Application Architecture
- **Framework**: React 18 + React Router v6 + TypeScript
- **State Management**: Zustand + React Query (TanStack Query)
- **UI**: Radix UI components + Tailwind CSS
- **Table Management**: TanStack React Table
- **Visualization**: React Flow (for diagrams/DAGs)
- **Forms**: React Hook Form + Zod validation

### Module Pages (13 Modules, 60+ screens)

#### 📊 **Dashboard Module** (`/modules/dashboard`)
- **DashboardPage**: Main landing page after login
  - KPIs overview (orders, inventory, production status)
  - Recent activity feed
  - Quick action buttons
  - Role-specific dashboard variants: `/planner`, `/storekeeper`, `/sales`, `/qc`, `/client`
- **SystemMapPage**: Module dependency visualization
  - Shows all accessible modules based on user role
  - Interactive diagram of module connections

#### 👤 **Auth Module** (`/modules/auth`)
- **LoginPage**: Tenant-scoped login with email + password
- **RegisterTenantPage**: New tenant registration (creates tenant + admin user)

#### 📦 **Inventory Module** (`/modules/inventory`)
- **MaterialListPage**: Browse all materials (raw/semi-finished/finished)
  - Filters: category, material type, availability
  - Actions: view stock, adjust inventory, create material
- **MaterialFormPage**: Create/edit material master
  - Fields: code, name, category, base UOM, type, location
- **BatchListPage**: Manage batch/lot tracking
  - Shows batch number, expiry date, quantity, status
  - Link to material transactions
- **ProductListPage**: List raw/semi-finished products
  - Shows: code, name, UOM, current stock, category
- **ProductFormPage**: Create/manage inventory products
- **StockMovementPage**: Real-time stock transactions
  - Shows: from_location → to_location, quantity, date
  - Filter by material, location, date range
- **TransactionHistoryPage**: Complete audit trail of inventory movements
  - Shows: transaction type, quantity, reference (WO/PO), remarks, user

#### 🏭 **Products Module** (`/modules/products`)
- **ProductTemplateListPage**: Browse item templates
  - Shows: code, name, attributes, variants count, status
  - Actions: view, edit, deactivate, create variants
- **ProductTemplateFormPage**: Create/configure product template
  - Fields: code, name, description, category, base unit
  - Dynamic attributes: text, number, dropdown, checkbox

#### 🔧 **BOM Module** (`/modules/bom`)
- **BOMListPage**: List all BOMs for templates/variants
  - Shows: product, version, status (active/draft), created date
  - Filters: template, variant, status, date range
- **BOMDetailPage**: Full BOM editor
  - Sections:
    - Header: version, valid dates, approval info
    - Line items: add/remove materials, set quantities + scrap %
    - Operations: attach manufacturing operations
    - Costing: roll-up cost calculation
    - Actions: validate, copy, activate, view tree structure

#### 🏃 **Operations Module** (`/modules/operations`)
- **OperationsListPage**: Browse manufacturing operations
  - Shows: name, workstation, setup time, run time, status
- **OperationFormPage**: Create/edit operations
  - Link to workstation
  - Configure setup time, run time
  - Optional description/notes

#### ⚙️ **Workstations Module** (implicitly in Operations)
- Workstation creation/management
- Capacity hours per day, hourly rate configuration

#### 📋 **Work Orders Module** (`/modules/work-orders`)
- **WorkOrdersListPage**: All active/completed work orders
  - Shows: WO number, product, planned qty, produced qty, status, due date
  - Filters: status, date range, product, priority
- **WorkOrderCreatePage**: Create new work order
  - Select product variant + BOM
  - Set planned quantity, dates, priority
  - Assign to workstation/operator
- **WorkOrderDetailPage**: Work order execution
  - Material issuance tracking
  - Production recording (qty, scrap)
  - Job card management
  - Status transitions: PLANNED → RELEASED → IN_PROGRESS → COMPLETED → CLOSED

#### 🏪 **Sales Module** (`/modules/sales`)
- **SalesOrdersListPage**: Browse all sales orders
  - Shows: order number, client, order date, delivery date, status, total
  - Filters: client, status, date range, payment status
- **SalesOrderFormPage**: Create/edit sales orders
  - Select client, add line items (product + qty + price)
  - Apply discounts/taxes
  - Set payment terms
- **SalesOrderDetailPage**: View order details
  - Line items with allocation status
  - Shipment tracking
  - Invoice link
- **ClientsListPage**: Manage sales clients/customers
  - Shows: code, name, credit limit, credit used, payment terms
- **ClientFormPage**: Add/edit client
  - Fields: code, name, email, phone, address, GST number, credit limit
- **PriceListsPage**: Configure price lists
  - Create price lists with effective dates
  - Define product prices
  - Set as default or for specific clients
- **SalesDashboardPage**: Sales KPI dashboard
  - Revenue, orders count, average order value
  - Top clients, recent orders, pending shipments

#### 🛒 **Client Portal Module** (`/modules/client`)
**Separate portal for external customers**
- **ClientDashboard.tsx**: Welcome screen
  - KPIs: total orders, active orders, spent, open balance
  - Credit usage and low credit warnings
  - Recent order list
- **OrdersList.tsx**: Client's orders
  - Filter by status, view details, track shipping
- **OrderDetail.tsx**: Single order view
  - Line items, invoice link, delivery tracking
- **InvoicesList.tsx**: Client invoices
  - Show outstanding balance, payment due dates
- **Reorder.tsx**: Quick reorder from past orders
- **CreditStatus.tsx**: Credit limit and usage info
- **Profile.tsx**: Manage delivery addresses, payment methods
- **Support.tsx**: Contact support, view tickets

#### 👥 **Users Module** (`/modules/users`)
- **UserListPage**: Manage tenant users
  - Shows: name, email, role, status, last login
  - Actions: edit, deactivate, change password
- **UserFormPage**: Create/edit user
  - Set role (with role-specific access levels)
  - Configure permissions manually if needed

#### 📊 **Finance Module** (`/modules/finance`)
- **FinanceDashboardPage**: Finance overview
  - AR/AP summary, invoicing metrics
  - Payment status by client/supplier
- **NewInvoicePage**: Create customer invoice
  - Manual or from sales order
  - Add line items, apply tax, set payment terms
- **NewSupplierInvoicePage**: Create supplier invoice
  - Link to PO, enter invoice details
  - Track against received goods
- **ReportsPage**: Financial reports
  - AR/AP aging, collections, cash flow forecasts

#### 🛍️ **Procurement Module** (`/modules/procurement`)
- **ProcurementHubPage**: Central procurement dashboard
- **PurchaseOrdersPage**: Browse/create POs
  - Shows: PO number, supplier, order date, delivery date, total
  - Actions: view, edit (draft), receive goods
- **PurchaseOrderDetailPage**: PO details
  - Line items, delivery schedule
  - GRN (Goods Receipt Notes) link
  - Quality inspection results
- **SuppliersListPage**: Supplier master
  - Code, name, contact, payment terms, rating
- **GrnPage**: Goods receipt notes
  - Record received goods against PO
  - Trigger quality inspection if needed
  - Update inventory
- **MaterialRequestsPage**: Internal material requests
  - View/create MRs that trigger PO creation
- **QualityModulePage**: Inspection & QC
  - View inspection templates, non-conformance reports
- **SubcontractListPage**: Manage subcontractor orders
  - Material issued to subcontractor
  - Receive back finished goods
- **SupplierPortalPages**: External supplier portal
  - SupplierPortalPage: Dashboard
  - SupplierPortalPoDetailPage: View POs issued to supplier
  - SupplierPortalQuotationsPage: Quotations list
  - SupplierPortalInvoicesPage: Submit supplier invoices
  - SupplierPortalPaymentsPage: Track payments received

#### 🏗️ **Shop Floor Module** (`/modules/shop-floor`)
- **ShopFloorPage**: Real-time shop floor status
  - Active work orders, current operations
  - Queue of next jobs, delays/issues
- **JobCardsPage**: Job card management
  - Assign job cards to operators
  - Track start/completion times
  - Record production and scrap

---

## 4. USER FLOWS & WORKFLOWS

### Post-Login Journey
```
User Login (LoginPage)
  ↓
JWT Generated (sub, tid, role)
  ↓
DashboardPage (role-specific variant)
  ├─ /planner → Production planning view
  ├─ /storekeeper → Inventory focus
  ├─ /sales → Sales orders & clients
  ├─ /qc → Quality inspections
  └─ /client → Client portal
  ↓
SystemMapPage (optional - see accessible modules)
```

### Complete User Workflows

#### **Workflow 1: Create New Product**
```
1. ProductTemplateFormPage
   ├─ Enter template: code (PK), name, category, base UOM
   ├─ Define attributes (text, number, options)
   └─ Save → ItemTemplate created in DB

2. ProductTemplateListPage
   ├─ Find the new template
   └─ Click "Create Variant"

3. (Implicit) Variant Creation
   ├─ System auto-generates variants from attribute combinations
   ├─ User can edit variant: code, cost, selling price
   └─ Each variant gets unique SKU/code

4. InventorySync (optional)
   ├─ Create corresponding finished material in Inventory
   ├─ Set UOM, category, reorder level
   └─ Initialize stock = 0
```

#### **Workflow 2: Create Bill of Materials (BOM)**
```
1. BOMListPage
   └─ Click "Create BOM for Product"

2. BOMDetailPage (Edit Mode)
   ├─ Select template or variant
   ├─ Set version: "1.0"
   ├─ Set valid_from, valid_to dates
   └─ Save header

3. Add Line Items
   ├─ Click "Add Material"
   ├─ Select material (raw/semi-finished)
   ├─ Set quantity, unit, scrap %
   ├─ Add requirements: quantity * (1 + scrap%)
   └─ Repeat for all components

4. Add Operations (Manufacturing)
   ├─ Click "Attach Operation"
   ├─ Select operation (with workstation + time)
   ├─ Set sequence order
   ├─ System auto-calculates labor cost
   └─ Repeat for all process steps

5. Validation & Activation
   ├─ Click "Validate BOM"
   ├─ Check: no circular dependencies, all materials exist
   ├─ If valid: Click "Activate BOM"
   └─ BOM status → ACTIVE (used by sales orders)

6. Result
   └─ BOM Tree shows: Product → Materials, Operations, Total Cost
```

#### **Workflow 3: Create & Execute Work Order**
```
1. WorkOrderCreatePage
   ├─ Select product (item variant)
   ├─ System fetches active BOM
   ├─ Set planned quantity, dates, priority
   ├─ Select workstation/operator (optional)
   └─ Submit → WO created with status = PLANNED

2. WorkOrderDetailPage (Dashboard)
   ├─ System creates:
   │  ├─ work_order_materials (BOM snapshot)
   │  ├─ job_cards (one per operation in BOM)
   │  └─ Status = PLANNED
   └─ Awaiting materials issuance

3. Issue Materials (Storekeeper)
   ├─ Open work order
   ├─ Click "Issue Materials"
   ├─ System shows required qty by material
   ├─ Confirm issued quantity
   ├─ Inventory deducted (transaction created)
   └─ WO Status → RELEASED

4. Shop Floor Execution (Operator)
   ├─ WO Status → IN_PROGRESS
   ├─ Open first job card
   ├─ Click "Start Job"
   ├─ Record time, operator
   ├─ Perform work...
   ├─ Click "Complete Job"
   ├─ Record: produced qty, scrap qty
   └─ Move to next job card in sequence

5. Production Recording
   ├─ After all jobs complete
   ├─ Click "Complete WO"
   ├─ Record final: produced_quantity, scrap_quantity
   ├─ Finished goods moved to inventory
   └─ WO Status → COMPLETED

6. Close Work Order
   ├─ Optional cleanup, notes
   └─ WO Status → CLOSED (historical record)
```

#### **Workflow 4: Create Sales Order**
```
1. SalesOrderFormPage
   ├─ Select client from dropdown
   ├─ Set order date, delivery date
   └─ Status = DRAFT

2. Add Line Items
   ├─ Click "Add Product"
   ├─ Select product (finished good variant)
   ├─ Set quantity
   ├─ System fetches price from price list
   ├─ Can override price
   ├─ Set tax rate, discount
   └─ Line status = PENDING

3. Review & Confirm
   ├─ View line subtotal, tax, grand total
   ├─ Check inventory available for each line
   ├─ Apply order-level discount (optional)
   ├─ Set payment terms (e.g., Net 30)
   ├─ Click "Confirm Order"
   └─ SO Status → CONFIRMED

4. Fulfillment
   ├─ Option A: Auto-create Work Order
   │  └─ System creates WO for each line (if configured)
   ├─ Option B: Manual scheduling
   │  └─ Planner creates WO manually linked to SO
   └─ SO Line Status → ALLOCATED

5. Production & Shipment
   ├─ Work order completes → goods to finished goods inventory
   ├─ Pick & pack goods
   ├─ Create shipment
   ├─ Update SO line: shipped_quantity
   └─ SO Line Status → SHIPPED

6. Invoicing
   ├─ Click "Create Invoice"
   ├─ System pre-fills from SO lines
   ├─ Verify quantities, prices
   ├─ Set invoice date, due date
   └─ Invoice created, sent to client
```

#### **Workflow 5: Purchase Order & GRN**
```
1. PurchaseOrdersPage (Procurer)
   ├─ Click "Create PO"
   ├─ Select supplier
   ├─ Add line items: material, qty, unit price
   ├─ Set delivery date, notes
   └─ PO Status = DRAFT

2. Submit PO
   ├─ Click "Confirm"
   └─ PO Status = CONFIRMED (sent to supplier)

3. Goods Receipt (Storekeeper)
   ├─ Receives actual goods
   ├─ Open PO, click "Create GRN"
   ├─ For each line: enter received_quantity
   ├─ Can note discrepancies (less/more received)
   └─ GRN created with timestamp

4. Quality Inspection (Optional)
   ├─ If configured: trigger QC inspection
   ├─ QC team inspects goods
   ├─ Can reject (return) or accept
   └─ Record inspection results

5. Inventory Update
   ├─ After GRN confirmed
   ├─ Material stock increased
   ├─ If received < ordered: create backorder
   └─ Inventory transaction created

6. Invoicing (AP)
   ├─ Supplier submits invoice
   ├─ Match to PO + GRN (3-way match)
   ├─ Verify quantities, prices
   ├─ Create supplier invoice in Finance
   └─ Set payment due date
```

---

## 5. BACKEND FEATURES & APIs

### Architecture Overview
```
FastAPI Application
├── Interfaces Layer (REST API)
│   ├── routes/ (v1 REST endpoints)
│   ├── schemas/ (Pydantic request/response models)
│   ├── dependencies/ (auth, permissions, container injection)
│   └── middleware/ (logging, tenant extraction, audit)
├── Application Layer (CQRS)
│   ├── Commands (write operations)
│   ├── Queries (read operations)
│   ├── Handlers (command/query processors)
│   └── Services (cross-cutting domain logic)
├── Domain Layer (DDD)
│   ├── Entities (aggregate roots with invariants)
│   ├── Value Objects (immutable data)
│   ├── Events (domain events for async processing)
│   └── Repositories (abstract data access)
└── Infrastructure Layer
    ├── Persistence (SQLAlchemy ORM + models)
    ├── Context (request context, tenant extraction)
    ├── Security (JWT, password hashing)
    ├── Events (event dispatcher, handlers)
    └── Containers (Dependency Injection)
```

### API Modules & Endpoints

#### **1. Authentication** (`/api/v1/auth`)
```
POST   /register-tenant          Create new tenant + admin user
POST   /login                    Get JWT access token
GET    /me                       Get current user profile
```

#### **2. Inventory** (`/api/v1/inventory`)
```
POST   /materials                Create material master
GET    /materials                List materials with filters
GET    /materials/{id}           Get material details
PUT    /materials/{id}           Update material
POST   /stock/add                Add stock (purchase/production)
POST   /stock/remove             Remove stock (consumption)
POST   /stock/adjust             Adjust/correct stock
POST   /stock/reserve            Reserve stock for work order
GET    /stock/{material_id}      Get current stock level
GET    /transactions             List inventory movements (audit trail)
POST   /batches                  Create batch/lot
GET    /batches                  List batches with tracking
```

#### **3. Products** (`/api/v1/products`)
```
POST   /templates                Create item template
GET    /templates                List templates
GET    /templates/{id}           Get template + variants
PUT    /templates/{id}           Update template
POST   /templates/{id}/variants  Create product variant
GET    /templates/{id}/variants  List variants for template
GET    /variants/{id}            Get variant details
PUT    /variants/{id}            Update variant
GET    /variants/search          Search variants (for sales orders)
```

#### **4. Bill of Materials** (`/api/v1/boms*`)
```
POST   /products/{id}/boms       Create BOM for product
GET    /products/{id}/boms       List BOMs for product
GET    /boms/{id}                Get BOM details
PUT    /boms/{id}                Update BOM (draft only)
POST   /boms/{id}/lines          Add line item to BOM
DELETE /boms/{id}/lines/{line}   Remove line from BOM
POST   /boms/{id}/validate       Validate BOM (check dependencies)
POST   /boms/{id}/activate       Activate BOM (make it current)
POST   /boms/{id}/copy           Copy BOM to new version
GET    /boms/{id}/tree           Get BOM tree structure (hierarchical)
GET    /boms/{id}/costs          Calculate total cost (material + labor)
POST   /boms/{id}/operations     Attach operations to BOM
```

#### **5. Manufacturing Operations** (`/api/v1/operations`, `/workstations`)
```
POST   /workstations             Create workstation
GET    /workstations             List all workstations
PUT    /workstations/{id}        Update workstation config
POST   /operations                Create operation
GET    /operations                List operations
PUT    /operations/{id}           Update operation
GET    /operations/{id}/cost     Calculate operation cost
```

#### **6. Work Orders** (`/api/v1/work-orders`)
```
POST   /                         Create work order from BOM
GET    /                         List work orders (with filters)
GET    /{id}                     Get work order details
PUT    /{id}                     Update work order (draft only)
POST   /{id}/release             Release WO (start issuance)
POST   /{id}/materials/issue     Issue materials from inventory
GET    /{id}/job-cards           List job cards for WO
POST   /{id}/job-cards/{jc}/start  Start job card
POST   /{id}/job-cards/{jc}/complete Complete job card
POST   /{id}/production          Record production (qty, scrap)
POST   /{id}/close               Close work order
```

#### **7. Sales** (`/api/v1/sales`)
```
POST   /clients                  Create customer
GET    /clients                  List customers
GET    /clients/{id}             Get customer (credit check, orders)
PUT    /clients/{id}             Update customer
POST   /orders                   Create sales order (draft)
GET    /orders                   List sales orders
GET    /orders/{id}              Get order details
POST   /orders/{id}/confirm      Confirm order
POST   /orders/{id}/lines        Add line to order
DELETE /orders/{id}/lines/{line} Remove line from order
POST   /orders/{id}/ship         Ship order
POST   /orders/{id}/cancel       Cancel order
POST   /price-lists              Create price list
GET    /price-lists              List price lists
POST   /price-lists/{id}/lines   Add product prices
```

#### **8. Supply Chain** (`/api/v1/supply-chain`)
```
# Suppliers
POST   /suppliers                Create supplier
GET    /suppliers                List suppliers

# Purchase Orders
POST   /purchase-orders          Create PO (with line items)
GET    /purchase-orders          List POs
GET    /purchase-orders/{id}     Get PO details
POST   /purchase-orders/{id}/cancel Cancel PO

# Goods Receipt Notes
POST   /grn                      Create GRN for PO
GET    /grn                      List GRNs
POST   /grn/{id}/confirm        Confirm GRN (update inventory)

# Quality
POST   /quality/inspect          Record inspection
GET    /quality/ncr              List non-conformance reports

# Subcontracting
POST   /subcontract/orders       Issue materials to subcontractor
GET    /subcontract/orders       List subcontract orders
POST   /subcontract/receive      Receive back from subcontractor
```

#### **9. Finance** (`/api/v1/finance`)
```
POST   /invoices                 Create customer invoice
GET    /invoices                 List invoices
POST   /invoices/{id}/payments   Record payment
POST   /supplier-invoices        Create supplier invoice (AP)
GET    /supplier-invoices        List supplier invoices
POST   /payments                 Record supplier payment
GET    /reports/ar-aging         AR aging report
GET    /reports/ap-aging         AP aging report
GET    /reports/cash-flow        Cash flow forecast
```

#### **10. Client Portal** (`/api/v1/client`)
```
POST   /auth/login               Client login
GET    /dashboard                Client dashboard (orders, credit, balance)
GET    /orders                   List client's orders
GET    /orders/{id}              Order details + tracking
GET    /invoices                 List client's invoices
POST   /reorder                  Quick reorder from past orders
GET    /credit-status            Credit limit + usage
PUT    /profile                  Update profile/addresses
```

#### **11. Notifications** (`/api/v1/notifications`)
```
GET    /                         List notifications (with read status)
POST   /{id}/read                Mark notification as read
POST   /mark-all-read            Mark all as read
```

#### **12. System** (`/api/v1`)
```
GET    /health                   Health check
GET    /system-map               Get module registry (modules, connections)
GET    /reports                  Generate various reports
```

### Domain Models (Entities)

**Product Domain**
- `ItemTemplate`: Product template with configurable attributes
- `ItemVariant`: Specific variant with unique SKU, cost, price
- `ProductAttribute`: Dynamic attribute definition (text/number/dropdown)

**BOM Domain**
- `BillOfMaterial`: BOM aggregate with version control
- `BOMLine`: Component line item (qty, scrap %)
- `BOMOperation`: Manufacturing operation attached to BOM
- `Operation`: Defines process step (setup time, run time)
- `Workstation`: Equipment/station (capacity, hourly rate)

**Inventory Domain**
- `Material`: Master material record (type: raw/semi/finished)
- `Batch`: Lot/batch tracking with expiry
- `SerialNumber`: Individual unit tracking
- `StockLevel`: Current stock by location
- `InventoryTransaction`: Audit trail of all movements

**Manufacturing Domain**
- `WorkOrder`: Production order (planned_qty, produced_qty, scrap_qty, status)
- `JobCard`: Operation snapshot (assigned_to, status, start/end times)
- `ProductionRecord`: Production data entry (qty, scrap, timestamp)

**Sales Domain**
- `SalesClient`: Customer master (credit limit, payment terms)
- `SalesOrder`: Customer order with line items
- `SalesOrderLine`: Line item with pricing, allocation, shipment tracking
- `PriceList`: Product price definitions (effective dates)

**Procurement Domain**
- `Supplier`: Vendor master
- `PurchaseOrder`: Supplier order
- `PurchaseOrderLine`: Material line with qty, price, received qty
- `GoodsReceiptNote`: Receipt record linking to PO
- `SubcontractOrder`: Material issued to subcontractor

**Finance Domain**
- `Invoice`: Customer invoice (AR)
- `InvoiceLine`: Line item with tax
- `Payment`: Received/recorded payment
- `SupplierInvoice`: Vendor bill (AP)
- `SupplierPayment`: Supplier payment record

**Quality Domain**
- `InspectionTemplate`: Configurable inspection parameters
- `QualityInspection`: Inspection record result
- `NonConformanceReport`: NCR for defects

**Tenant Domain**
- `Tenant`: Customer/organization
- `User`: User account scoped to tenant
- `Role`: User role (ADMIN, OPERATOR, etc.)

---

## 6. PROJECT STATUS

### ✅ COMPLETED & WORKING FEATURES

#### Phase 0 - Foundation
- ✅ **Multi-tenancy**: Full tenant isolation, JWT-based tenant extraction
- ✅ **Authentication**: JWT tokens, bcrypt password hashing
- ✅ **User Management**: User creation, role assignment, permissions
- ✅ **Audit Logging**: All changes tracked with user/tenant context
- ✅ **DDD/CQRS Architecture**: Clear separation of concerns

#### Phase 1 - Core Inventory
- ✅ **Material Master**: Create/manage materials (raw, semi, finished)
- ✅ **Stock Management**: Add/remove/adjust inventory
- ✅ **Locations**: Warehouse/bin location tracking
- ✅ **Stock Levels**: Current stock by location
- ✅ **Inventory Transactions**: Full audit trail of movements
- ✅ **UOM Management**: Units of measure with conversions
- ✅ **Material Categories**: Organization and classification

#### Phase 2.1 - Product Configuration
- ✅ **Item Templates**: Create product templates with attributes
- ✅ **Dynamic Attributes**: Text, number, dropdown, checkbox support
- ✅ **Item Variants**: Auto-generate variants from attribute combinations
- ✅ **Variant Pricing**: Cost and selling price per variant
- ✅ **Batch & Serial Tracking**: For traceability

#### Phase 2.2 - Bill of Materials
- ✅ **BOM Creation**: Create BOMs for products
- ✅ **BOM Versioning**: Multiple versions with effective dates
- ✅ **Line Items**: Add materials with quantity + scrap %
- ✅ **BOM Validation**: Circular dependency detection
- ✅ **BOM Activation**: Version control, activate/deactivate
- ✅ **BOM Copy**: Clone BOMs to new versions
- ✅ **Tree Structure**: Hierarchical BOM view
- ✅ **Cost Calculation**: Roll-up cost (materials + labor)

#### Phase 2.3 - Manufacturing Operations
- ✅ **Workstations**: Create equipment with capacity + rate
- ✅ **Operations**: Create process steps (setup time, run time)
- ✅ **Attach to BOM**: Link operations to BOM
- ✅ **Operation Sequencing**: Order of operations
- ✅ **Cost per Operation**: Labor cost calculation

#### Phase 3 - Sales Module
- ✅ **Sales Clients**: Customer master with credit limits
- ✅ **Sales Orders**: Create orders with line items
- ✅ **Pricing**: Product prices, price lists, discounts
- ✅ **Order Statuses**: Draft → Confirmed → Shipped → Delivered
- ✅ **Tax & Discount**: Per-line and order-level calculations

#### Phase 4 - Work Orders & Shop Floor
- ✅ **Work Order Creation**: Auto from BOM or manual
- ✅ **Material Issuance**: Deduct from inventory
- ✅ **Job Cards**: Operation execution tracking
- ✅ **Production Recording**: Qty, scrap, timestamps
- ✅ **Work Order Lifecycle**: PLANNED → RELEASED → IN_PROGRESS → COMPLETED → CLOSED
- ✅ **Finished Goods**: Auto stock into FG inventory

#### Additional Completed Features
- ✅ **Supply Chain (Procurement)**:
  - Purchase orders, GRN (Goods Receipt), Quality inspection
  - Supplier management, quotations
  - Subcontracting (material issuance/receipt)
- ✅ **Finance Module**:
  - Customer invoicing, payment tracking
  - Supplier invoices (AP), supplier payments
  - AR/AP aging reports, cash flow forecasting
- ✅ **Quality Control**:
  - Inspection templates with configurable parameters
  - Non-conformance reports (NCR)
  - Quality gate at GRN
- ✅ **Client Portal**:
  - Separate login for external customers
  - Order history, current shipments, credit tracking
  - Reorder functionality
  - Notification preferences
- ✅ **Supplier Portal**:
  - Separate login for suppliers
  - View assigned POs, submit quotations/invoices
  - Track payments from customer
- ✅ **File Uploads**:
  - /uploads directory for assets
  - API endpoint: `POST /api/v1/files/upload`
- ✅ **Notifications**:
  - Event-driven, stored notifications
  - Read/unread tracking
  - Notification preferences per user
- ✅ **Reports**:
  - AR/AP aging, collections forecast
  - Production status, capacity utilization
  - Inventory turnover, stockout alerts

---

### 🟡 PARTIALLY COMPLETED FEATURES

#### Advanced BOM Features
- 🟡 **BOM Simulation**: Cost impact analysis (not fully tested)
- 🟡 **Waste Tracking**: Scrap % calculation exists but forecasting incomplete

#### Advanced Inventory
- 🟡 **Cycle Counting**: Partial implementation
- 🟡 **Slow-Moving Items**: Detection logic exists but monitoring dashboard incomplete
- 🟡 **Negative Stock Prevention**: Rule enforced but override mechanisms incomplete

#### Advanced Manufacturing
- 🟡 **Alternative BOMs**: No secondary/fallback BOM logic
- 🟡 **Resource Planning**: Workstation capacity check incomplete
- 🟡 **Rework/Scrap Management**: Basic tracking, but rework workflows incomplete

#### Advanced Sales
- 🟡 **Credit Limit Enforcement**: Check exists but hard blocks incomplete
- 🟡 **Backorder Management**: Flag exists, fulfillment workflow incomplete
- 🟡 **Multi-currency**: Architecture ready but conversion rates incomplete

#### Analytics
- 🟡 **Dashboard Charts**: Basic KPIs exist, advanced visualizations incomplete
- 🟡 **Forecasting**: Modules exist but accuracy tuning needed
- 🟡 **Variance Analysis**: Planned vs actual, implementation partial

---

### ❌ PENDING/TODO FEATURES

#### Real-Time Features
- ❌ **WebSockets**: No real-time notifications or live updates (infrastructure ready)
- ❌ **Live Dashboards**: No push updates to connected clients
- ❌ **Presence Tracking**: Who is viewing what screen

#### Advanced Manufacturing
- ❌ **Rush Order Capability**: Priority scheduling not fully implemented
- ❌ **Resource Scheduling**: Advanced capacity planning tool
- ❌ **Predictive Maintenance**: Equipment health tracking
- ❌ **OEE Calculations**: Overall Equipment Effectiveness metrics

#### Supply Chain
- ❌ **Demand Forecasting**: AI-based demand prediction
- ❌ **Supplier Selection**: Multi-criteria supplier scoring
- ❌ **shipper Integration**: Direct carrier API connectivity
- ❌ **Track & Trace**: Real-time shipment tracking

#### Financial
- ❌ **Multi-currency**: Full GL and currency conversion
- ❌ **Advanced Costing**: ABC costing, variance analysis refinement
- ❌ **Intercompany Transactions**: For multi-entity manufacturers
- ❌ **Customs/Duty**: For international orders

#### Quality
- ❌ **Statistical Process Control**: SPC charts, capability analysis
- ❌ **Root Cause Analysis**: RCA tracking workflows
- ❌ **Traceability Tree**: Forward/backward traceability browser
- ❌ **CAPA (Corrective/Preventive Action)**: Full CAPA workflow

#### Compliance & Security
- ❌ **2FA/MFA**: Multi-factor authentication
- ❌ **Role-based Data Masking**: Field-level encryption for sensitive data
- ❌ **Compliance Workflows**: GxP validation, audit trail compliance
- ❌ **API Versioning**: Multiple API version support strategy

#### Mobile
- ❌ **Mobile App**: iOS/Android native or PWA
- ❌ **Offline Support**: Work offline, sync when connected
- ❌ **QR Code Scanning**: For batch/serial intake, job card receipt

#### Integrations
- ❌ **ERP APIs**: Sync with other ERP systems
- ❌ **MES Integration**: Manufacturing Execution System
- ❌ **E-commerce Integration**: Shopify, WooCommerce, Magento
- ❌ **Accounting Integration**: QuickBooks, Xero, SAP
- ❌ **EDI**: Electronic Data Interchange for orders/invoices

---

### 🐛 KNOWN ISSUES

From code analysis and terminal history:

1. **Frontend Build Warnings** (tsc errors, eslint rules)
   - TypeScript compilation issues in newer versions
   - ESLint configuration may need updates
   - Status: Code compiles but with warnings

2. **Test Structure**
   - Loose test files in root directory (not following pytest best practices)
   - conftest.py fixtures may have issues
   - Status: Tests run but organization needs improvement

3. **Missing Configurations**
   - No `.env.example` clearly documented in some modules
   - Docker networking between backend/frontend may need tuning
   - Status: Local dev works, Docker may have connectivity issues

4. **Database Migrations**
   - 15 migrations exist; dependency chain is clean
   - No known schema conflicts
   - Status: `alembic upgrade head` works

---

## 7. KEY COMPONENTS & INFRASTRUCTURE

### Database Schema Overview

**Core Tables** (46+ tables total)

**Multi-tenancy & Auth:**
- `tenants`: Organization/customer records
- `users`: User accounts (belongs to tenant)
- `audit_logs`: All changes, searchable by correlation_id
- `password_reset_tokens`: For forgotten password flows

**Inventory:**
- `materials`: Master material records
- `material_categories`: Classification
- `materials`: Categorization
- `stock_levels`: Current stock by location
- `inventory_transactions`: Audit trail
- `batches`: Lot/batch tracking
- `serial_numbers`: Individual unit tracking
- `locations`: Warehouse/bin hierarchy
- `units_of_measure`: UOM definitions
- `uom_conversions`: Conversion factors

**Product:**
- `item_templates`: Product master
- `item_variants`: Specific SKUs
- `product_attributes`: Dynamic attribute definitions

**Manufacturing:**
- `boms`: Bill of Materials (aggregate)
- `bom_lines`: Component line items
- `workstations`: Equipment/station
- `operations`: Process steps
- `bom_operations`: BOM sequence
- `work_orders`: Production orders
- `work_order_materials`: BOM snapshot at WO creation
- `job_cards`: Operation execution
- `production_records`: Production data

**Sales:**
- `sales_clients`: Customer master
- `sales_orders`: Customer orders
- `sales_order_lines`: Line items
- `sales_price_lists`: Price configurations
- `sales_price_list_lines`: Product prices

**Supply Chain:**
- `suppliers`: Vendor master
- `purchase_orders`: Supplier orders
- `material_requests`: Internal MRs
- `quality_inspections`: Inspection results
- `quality_inspection_templates`: Reusable templates
- `non_conformance_reports`: NCR records
- `subcontract_orders`: Subcontractor work
- `stock_allocation`: Reserved stock

**Finance:**
- `invoices`: Customer invoices
- `invoice_lines`: Line items
- `payments`: Payment records
- `supplier_invoices`: AP bills
- `supplier_payments`: Payment to suppliers

**Notifications:**
- `notifications`: User notifications (read/unread)
- `client_notification_settings`: Preferences

### Technology Stack

**Backend:**
```
FastAPI==0.111.0          # Web framework, auto-docs
SQLAlchemy[asyncio]==2.0  # ORM + async support
asyncpg==0.29.0           # PostgreSQL async driver
Alembic==1.13.1           # Database migrations
pydantic==2.7.1           # Data validation
python-jose==3.3.0        # JWT tokens
bcrypt==4.1.3             # Password hashing
aiofiles==23.2.1          # Async file operations
```

**Frontend:**
```
React==18.3.1             # UI library
React Router v6==6.30.3   # Routing
TypeScript==5.6.2         # Type safety
TailwindCSS==3.4.19       # Styling
React Hook Form==7.72.0   # Form management
Zod==3.25.76              # Schema validation
TanStack Query==5.95.2    # Server state management
TanStack Table==8.21.3    # Table component
Zustand==4.5.7            # Client state (if needed)
Radix UI                  # Accessible components
React Flow==12.10.1       # Diagram/flow visualization
```

**Database:**
```
PostgreSQL 15+            # Relational DB
JSONB columns             # Semi-structured data
UUID PKs                  # Unique identifiers
Async connection pool     # Performance
```

**DevOps:**
```
Docker & Docker Compose   # Containerization
Alembic                   # Schema migrations
pytest                    # Testing framework
pytest-asyncio            # Async test support
```

### File Upload Management

**Upload Endpoint**
```
POST /api/v1/files/upload
├─ Input: multipart/form-data (file)
├─ Validation: file size, type
└─ Output: { file_id, url, created_at }

File Storage
├─ Directory: settings.upload_dir (from .env)
├─ Served at: /uploads/{file_id}
├─ Retention: Manual cleanup or configurable TTL
└─ Soft delete: is_deleted flag (not physical deletion)
```

### Real-Time Features (Infrastructure Ready)

**Event Dispatcher** (exists but not actively used)
```python
container.event_dispatcher
├─ Publish domain events
├─ Subscribe to events asynchronously
└─ Ready for WebSocket integration
```

**Notification System** (exists)
```
Domain Event → Event Dispatcher → Notification Service
└─ Creates notification record
   ├─ user_id
   ├─ type (order_confirmed, shipment, invoice_due, etc.)
   ├─ title, message
   └─ is_read (boolean)
```

**WebSocket Support** (not yet implemented)
- FastAPI supports WebSockets natively
- Event dispatcher ready for async event handling
- Client: Socket.IO or native WebSocket ready

### Security Model

**Authentication**
```
Email + Password (via bcrypt)
     ↓
JWT Token (HS256, expires in 24 hours)
     ↓
Bearer Token in Authorization header
     ↓
Middleware extracts user_id, tenant_id, role
```

**Authorization**
```
Role → Permissions (fine-grained)
     ↓
Middleware checks permission before endpoint
     ↓
Custom dependency: @Depends(require_permission("module:action"))
```

**Multi-tenancy**
```
JWT includes tenant_id (tid claim)
     ↓
TenantMiddleware sets context variable
     ↓
All queries filtered by tenant_id
     ↓
Soft delete ensures permanent isolation
```

**Audit**
```
Every API call logged with:
├─ user_id
├─ tenant_id
├─ action (POST, GET, PUT, DELETE)
├─ entity_type, entity_id
├─ before_value, after_value (JSONB)
├─ ip_address
└─ correlation_id (for request tracing)
```

---

## 8. DEPLOYMENT & CONFIGURATION

### Environment Variables (.env)

Required:
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/medtrack_db
JWT_SECRET_KEY=your_secret_key_here
ENVIRONMENT=development|production
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
UPLOAD_DIR=./uploads
APP_NAME=MedTrack ERP
APP_VERSION=0.1.0
```

### Docker Setup

**Services**
```
docker-compose.yml:
  - backend: FastAPI (port 8000)
  - frontend: React dev server (port 5173)
  - postgres: PostgreSQL 15 (port 5432)
```

**Run:**
```bash
docker-compose up --build
docker-compose exec backend alembic upgrade head
```

### Local Development

```bash
# Python
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\activate (Windows)
pip install -r requirements.txt

# Database
alembic upgrade head

# Start backend
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev

# API Docs
http://localhost:8000/docs        # Swagger UI
http://localhost:8000/redoc       # ReDoc
http://localhost:8000/health      # Health check
```

---

## SUMMARY

**MedTrack** is a sophisticated, multi-phase ERP system with strong architectural foundations (DDD/CQRS), comprehensive feature coverage across manufacturing, sales, inventory, and finance, and clear roadmaps for advanced capabilities.

**Strengths:**
- Clean, maintainable code structure
- Comprehensive audit trails and security
- Multi-tenancy fully embedded
- Extensive domain models and business logic
- Ready for enterprise deployments

**Next Priorities:**
1. Complete real-time features (WebSockets)
2. Advanced analytics and forecasting
3. Mobile application
4. Third-party integrations (Shopify, accounting software)
5. Compliance modules (GxP, traceability)

**Test Suite:** 156+ tests across unit, API, and E2E scenarios—run with `pytest tests/ -v --cov`.

