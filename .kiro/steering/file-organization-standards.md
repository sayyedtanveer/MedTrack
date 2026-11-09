---
name: "File Organization Standards"
description: "Mandatory folder structure and naming conventions for all MedTrack files (backend, frontend, tests, scripts)"
inclusion: fileMatch
fileMatchPattern:
  - "backend/app/**/*.py"
  - "frontend/src/**/*.tsx"
  - "frontend/src/**/*.ts"
  - "tests/**/*.py"
  - "scripts/**/*.py"
  - "alembic/**/*.py"
---

# File Organization Standards

**Updated:** November 9, 2026  
**Version:** 1.0.0  
**Critical:** All new files MUST follow these rules. Files created in wrong locations will be rejected in code review.

---

## 1. Backend Structure (Python)

### 1.1 Backend File Organization

```
backend/app/
├── main.py                          # FastAPI entry point
├── config.py                        # Environment config
├── domain/                          # Business logic layer
│   ├── __init__.py
│   ├── {module}/                    # e.g., bom, manufacturing, inventory
│   │   ├── __init__.py
│   │   ├── entities.py              # Domain models
│   │   ├── value_objects.py         # Value types
│   │   ├── events.py                # Domain events
│   │   ├── exceptions.py            # Domain-specific exceptions
│   │   ├── repositories.py          # Repository interfaces (abstract)
│   │   └── services.py              # Domain services
│   └── shared/                      # Cross-domain
│       ├── __init__.py
│       ├── exceptions.py            # Common exceptions
│       ├── events.py                # Common events
│       └── value_objects.py         # Shared value objects
├── application/                     # Use cases layer
│   ├── __init__.py
│   ├── {module}/
│   │   ├── __init__.py
│   │   ├── commands/                # Write operations
│   │   │   ├── __init__.py
│   │   │   ├── create_{entity}.py
│   │   │   ├── update_{entity}.py
│   │   │   └── {action}_{entity}.py
│   │   ├── queries/                 # Read operations
│   │   │   ├── __init__.py
│   │   │   ├── get_{entity}.py
│   │   │   ├── list_{entities}.py
│   │   │   └── find_{entities}_by_{criteria}.py
│   │   └── handlers/                # CQRS handlers
│   │       ├── __init__.py
│   │       ├── command_handlers.py
│   │       └── query_handlers.py
│   └── shared/
│       ├── __init__.py
│       └── dtos.py                  # Common response DTOs
├── infrastructure/                  # Persistence layer
│   ├── __init__.py
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── {module}_models.py   # e.g., bom_models.py
│   │   │   └── base_model.py        # Base model class
│   │   ├── repositories/            # Repository implementations
│   │   │   ├── __init__.py
│   │   │   ├── {module}_repository.py
│   │   │   └── base_repository.py
│   │   └── unit_of_work.py          # Transaction management
│   ├── di/
│   │   ├── __init__.py
│   │   └── container.py             # Dependency injection
│   ├── security/
│   │   ├── __init__.py
│   │   ├── jwt.py
│   │   ├── password.py
│   │   └── permissions.py
│   ├── logging/
│   │   ├── __init__.py
│   │   └── structured_logger.py
│   ├── events/
│   │   ├── __init__.py
│   │   └── dispatcher.py
│   └── services/
│       ├── __init__.py
│       ├── {service_name}_service.py # e.g., export_service.py
│       └── base_service.py
├── interfaces/                      # HTTP layer
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── routes/              # Route handlers
│   │   │   │   ├── __init__.py
│   │   │   │   ├── {module}_routes.py
│   │   │   │   └── health_routes.py
│   │   │   ├── schemas/             # Pydantic models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── {module}_schemas.py
│   │   │   │   └── base_schemas.py
│   │   │   └── middleware/          # Request/response processing
│   │   │       ├── __init__.py
│   │   │       ├── tenant_middleware.py
│   │   │       ├── auth_middleware.py
│   │   │       ├── error_handler.py
│   │   │       └── logging_middleware.py
│   │   └── v2/                      # Future API versions
│   │       └── __init__.py
│   └── websocket/
│       ├── __init__.py
│       └── handlers.py
├── core/                            # Application core
│   ├── __init__.py
│   ├── logging.py
│   └── module_registry.py
├── middleware/                      # Cross-cutting middleware
│   ├── __init__.py
│   ├── security_headers.py
│   ├── rate_limiting.py
│   ├── correlation_id.py
│   └── request_logging.py
├── tests/                           # DEPRECATED: See tests/ folder
└── __init__.py
```

### 1.2 Backend File Naming Rules

**Python Files:**
```
✅ Correct naming:
- entity_name.py              # Single entity
- entity_names.py             # Multiple entities
- command_handlers.py         # Handlers
- {module}_models.py          # ORM models
- {module}_repository.py      # Repository impl
- get_entity.py               # Query operation
- create_entity.py            # Command operation
- {entity}_service.py         # Service

❌ Wrong naming:
- EntityName.py               # PascalCase (use snake_case)
- entity Model.py             # Spaces (use underscore)
- models_entity.py            # Wrong order
- entity_models.py            # Ambiguous (use {module}_models.py)
```

**Module Structure:**
```python
# ✅ Correct: One module per bounded context
backend/app/domain/inventory/
backend/app/domain/manufacturing/
backend/app/domain/sales/

# ❌ Wrong: Nested module folders
backend/app/domain/inventory/materials/entities.py  # Too deep
backend/app/domain/inventory/materials/models.py
backend/app/domain/inventory/warehouse/models.py
```

### 1.3 When to Create a New Module

**Create a new module when:**
- ✅ Feature covers a distinct business bounded context (DDD)
- ✅ It has its own entities, repository, and workflows
- ✅ It may be used by multiple other modules
- ✅ Examples: `bom`, `manufacturing`, `inventory`, `sales`, `procurement`

**Do NOT create a new module when:**
- ❌ Adding a field to existing entity (update model in existing module)
- ❌ Creating a helper utility (add to `shared/` or `infrastructure/`)
- ❌ Creating a one-off calculation (add to existing service)

### 1.4 Backend Layer Responsibilities

| Layer | Purpose | Should Contain | Should NOT Contain |
|-------|---------|----------------|--------------------|
| **domain** | Business logic | Entities, events, exceptions, interfaces | HTTP, database, I/O |
| **application** | Use cases | Commands, queries, handlers, DTOs | Database models, HTTP responses |
| **infrastructure** | Persistence | ORM models, repositories, services | Business logic, HTTP |
| **interfaces** | HTTP | Routes, schemas, middleware | Business logic, database queries |

---

## 2. Frontend Structure (React/TypeScript)

### 2.1 Frontend File Organization

```
frontend/src/
├── main.tsx                         # React entry point
├── App.tsx                          # Root component
├── modules/                         # Business domain modules
│   ├── {module}/                    # e.g., auth, inventory, sales
│   │   ├── __init__.ts
│   │   ├── index.ts                 # Module exports
│   │   ├── pages/                   # Page-level (routed) components
│   │   │   ├── {Entity}Page.tsx
│   │   │   ├── {Entity}ListPage.tsx
│   │   │   └── {Entity}DetailPage.tsx
│   │   ├── components/              # Module-specific components
│   │   │   ├── {Entity}Form.tsx
│   │   │   ├── {Entity}Card.tsx
│   │   │   ├── {Entity}List.tsx
│   │   │   └── __tests__/
│   │   │       └── {Component}.test.tsx
│   │   ├── hooks/                   # Custom React hooks
│   │   │   ├── use{Entity}.ts
│   │   │   ├── use{Entities}List.ts
│   │   │   └── use{Entity}Form.ts
│   │   ├── services/                # API client functions
│   │   │   ├── {entity}Api.ts
│   │   │   └── {entity}Service.ts
│   │   ├── types/                   # TypeScript interfaces
│   │   │   ├── {Entity}.ts
│   │   │   └── {module}Types.ts
│   │   ├── store/                   # Zustand/Redux (if needed)
│   │   │   └── {module}Store.ts
│   │   └── constants/               # Module constants
│   │       └── {module}Constants.ts
│   ├── shared/                      # Shared across modules
│   │   ├── components/              # Generic UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Table.tsx
│   │   │   └── __tests__/
│   │   ├── hooks/                   # Global hooks
│   │   │   ├── useAuth.ts
│   │   │   └── useTenant.ts
│   │   └── types/                   # Shared types
│   │       └── common.ts
│   └── layout/                      # Layout components
│       ├── MainLayout.tsx
│       ├── AuthLayout.tsx
│       └── ErrorBoundary.tsx
├── components/                      # DEPRECATED: Use modules/ instead
│   └── (moved to modules/*/components)
├── hooks/                           # DEPRECATED: Use modules/*/hooks
│   └── (moved to modules/*/hooks)
├── services/                        # Deprecated: Use modules/*/services
│   └── (moved to modules/*/services)
├── types/                           # Deprecated: Use modules/*/types
│   └── (moved to modules/*/types)
├── utils/                           # Global utilities
│   ├── api.ts                       # Axios instance
│   ├── formatters.ts                # Date, number formatting
│   ├── validators.ts                # Input validation
│   └── helpers.ts                   # General helpers
├── config/                          # Configuration
│   ├── api.config.ts
│   ├── auth.config.ts
│   └── feature.config.ts
├── __tests__/                       # Global tests
│   ├── setup.ts
│   └── mocks.ts
└── styles/                          # Global styles
    ├── globals.css
    └── theme.css
```

### 2.2 Frontend File Naming Rules

**React Components:**
```
✅ Correct naming:
- EntityForm.tsx                # Form component
- EntityList.tsx                # List component
- EntityCard.tsx                # Card component
- EntityPage.tsx                # Page (routed) component
- {Entity}DetailPage.tsx        # Detail page
- {Entity}ListPage.tsx          # List page
- Error Boundary.tsx            # Error boundary

❌ Wrong naming:
- entity-form.tsx               # kebab-case (use PascalCase)
- entityForm.tsx                # camelCase (use PascalCase for components)
- FormEntity.tsx                # Wrong order
- Entity_Form.tsx               # Underscore in component name
```

**TypeScript/Hooks:**
```
✅ Correct naming:
- useEntity.ts                  # Custom hook
- useEntityList.ts              # List hook
- useEntityForm.ts              # Form hook
- entityApi.ts                  # API client
- entityTypes.ts                # Type definitions

❌ Wrong naming:
- useentity.ts                  # Wrong case
- entity-api.ts                 # kebab-case (use camelCase for non-components)
- Entity.types.ts               # dot notation
- types-entity.ts               # Wrong order
```

### 2.3 When to Create a New Module

**Create a new module when:**
- ✅ Feature covers a distinct business domain (inventory, sales, manufacturing)
- ✅ Multiple pages and components for that domain
- ✅ Custom hooks specific to that domain
- ✅ Examples: `auth`, `inventory`, `sales`, `manufacturing`

**Do NOT create a new module when:**
- ❌ Single reusable component (add to `modules/shared/components`)
- ❌ Global hook (add to `modules/shared/hooks`)
- ❌ One-off utility (add to `utils/`)

---

## 3. Test File Structure

### 3.1 Test File Organization

```
tests/
├── conftest.py                      # Shared fixtures
├── __init__.py
├── unit/                            # Unit tests
│   ├── __init__.py
│   ├── test_worksheet_fix.py
│   ├── test_material_onboarding_integration.py
│   ├── test_sample_upload.py
│   └── create_sample_upload_file.py # Helper scripts
├── integration/                     # Integration tests
│   ├── __init__.py
│   ├── test_{module}_integration.py
│   └── fixtures/
│       └── {module}_fixtures.py
├── e2e/                             # End-to-end tests
│   ├── conftest.py
│   ├── phase_*/                     # Test phases
│   │   ├── test_*.py
│   │   └── conftest.py
│   └── test_complete_workflow.py
└── debug/                           # Debug utilities
    ├── check_database.py
    └── inspect_data.py
```

### 3.2 Test File Naming Rules

**Test Files:**
```
✅ Correct naming:
- test_worksheet_fix.py         # What is tested
- test_material_onboarding_integration.py
- test_{module}_integration.py
- test_{feature}_e2e.py

❌ Wrong naming:
- worksheet_test.py             # Wrong order
- material_test_onboarding.py    # Confusing
- test.py                        # Too generic
- tests.py                       # Not in tests/ folder
```

**Test Functions:**
```python
# ✅ Correct
def test_worksheet_selection_prioritizes_raw_materials():
def test_error_when_no_valid_worksheet():
def test_bulk_import_preserves_tenant_isolation():

# ❌ Wrong
def test1():
def test_materials():  # Too generic
def material_test():   # Wrong order
```

### 3.3 Test Placement Rules

**MUST be in tests/ folder:**
- ✅ All `test_*.py` files
- ✅ All test fixtures
- ✅ Helper scripts for testing
- ✅ Test configuration (conftest.py)

**MUST NOT be in repository root:**
- ❌ test_*.py in root
- ❌ Helper scripts in root
- ❌ conftest.py in root

**MUST NOT be in source folders:**
- ❌ test_*.py in backend/app/
- ❌ test_*.py in frontend/src/
- ❌ Mixed with source code

**Exception: Component tests can be colocated:**
```
frontend/src/modules/inventory/components/
├── MaterialForm.tsx
├── MaterialForm.test.tsx  ✅ OK for component-specific tests
└── MaterialForm.stories.tsx
```

---

## 4. Database and Migration Structure

### 4.1 Migration File Organization

```
alembic/
├── env.py                           # Alembic config
├── script.py.mako                   # Migration template
├── versions/                        # Migration files
│   ├── 001_initial.py
│   ├── 20260927_add_priority_to_sales_orders.py
│   ├── 20261108_1606_merge_all_heads.py
│   └── {timestamp}_{description}.py
└── README.md
```

### 4.2 Migration File Naming Rules

**Naming Convention:**
```
{timestamp}_{short_description}.py

Examples:
✅ 20260927_add_priority_to_sales_orders.py
✅ 20261108_1606_merge_all_heads.py
✅ 20261109_create_audit_log_table.py

❌ add_priority.py                  # No timestamp
❌ migration_001.py                 # Wrong format
❌ Add_Priority.py                  # PascalCase
```

**Auto-Generate Migrations:**
```bash
alembic revision --autogenerate -m "add_priority_to_sales_orders"
# Creates: 20260927_add_priority_to_sales_orders.py
```

---

## 5. Scripts and Utilities

### 5.1 Script Organization

```
scripts/
├── __init__.py
├── database/                        # Database utilities
│   ├── __init__.py
│   ├── seed_data.py
│   ├── backup_database.py
│   └── migrate_data.py
├── archived-migrations/             # Historical scripts
│   ├── __init__.py
│   └── {old_migration_name}.py
├── debug-archive/                   # Debug utilities
│   ├── __init__.py
│   ├── check_db.py
│   └── inspect_data.py
└── README.md
```

### 5.2 Script File Naming Rules

**Scripts:**
```
✅ Correct:
- seed_data.py                  # Action + object
- backup_database.py
- migrate_data.py
- check_database.py

❌ Wrong:
- db_seed.py                    # Wrong order (use seed_database.py)
- SEED.py                       # All caps
- seed.py                       # Too generic
```

---

## 6. Documentation Structure

### 6.1 Documentation Organization

```
docs/
├── README.md                        # Index
├── ai-guidelines/                   # AI instruction files
│   ├── AGENTS.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── BACKEND_STANDARDS.md
│   ├── FRONTEND_STANDARDS.md
│   ├── DATABASE_STANDARDS.md
│   ├── SECURITY_AND_MULTITENANCY.md
│   ├── MANUFACTURING_BUSINESS_RULES.md
│   ├── IMPLEMENTATION_WORKFLOW.md
│   └── DEFINITION_OF_DONE.md
├── ERP_COMPLETE_GUIDE.md
├── MANUFACTURING_FUNCTIONAL_FLOW.md
└── architecture/
    ├── system-architecture.md
    ├── database-schema.md
    └── api-design.md
```

### 6.2 Steering File Organization

```
.kiro/steering/
├── README.md                        # Index
├── tech.md                          # Technology stack
├── structure.md                     # Project structure
├── product.md                       # Business context
├── backend-ddd-patterns.md          # Backend patterns
├── frontend-react-patterns.md       # Frontend patterns
├── data-import-export-patterns.md   # Import/export guide
└── file-organization-standards.md   # THIS FILE
```

---

## 7. Critical Rules: File Placement Checklist

### 7.1 Before Creating ANY New File

Ask yourself:

1. **Is it a Python backend file?**
   - ✅ Put in `backend/app/{domain|application|infrastructure|interfaces}`
   - ✅ Follow the appropriate layer structure
   - ✅ Never in root or frontend/

2. **Is it a React/TypeScript frontend file?**
   - ✅ Put in `frontend/src/modules/{module}/{type}`
   - ✅ Use PascalCase for components, camelCase for everything else
   - ✅ Never in root or backend/

3. **Is it a test file?**
   - ✅ Put in `tests/{unit|integration|e2e}`
   - ✅ NEVER in repository root
   - ✅ NEVER mixed with source code
   - ✅ Name it `test_*.py`

4. **Is it a migration file?**
   - ✅ Put in `alembic/versions/`
   - ✅ Name it `{timestamp}_{description}.py`
   - ✅ Never manually create, use `alembic revision --autogenerate`

5. **Is it a utility/helper script?**
   - ✅ Put in `scripts/{category}/` or `utils/`
   - ✅ Name it descriptively (`backup_database.py`)
   - ✅ Never in root unless temporary

6. **Is it documentation?**
   - ✅ Put in `docs/` for guides
   - ✅ Put in `.kiro/steering/` for team standards
   - ✅ Name it descriptively

### 7.2 Prohibited File Locations

```
❌ NEVER create files here:
- Repository root (except config files)
- Backend mixed with tests
- Frontend mixed with tests
- Tests in source folders
- Helper scripts in root (temporary only)
- Random .md files without organization
```

### 7.3 File Organization Enforcement

**Code Review Checklist:**
- [ ] File is in correct folder
- [ ] File is named according to convention
- [ ] File follows layer responsibilities
- [ ] Tests are in tests/ folder
- [ ] No debug/temporary files left
- [ ] Documentation in proper location

---

## 8. Common Mistakes and Corrections

| Mistake | Problem | Solution |
|---------|---------|----------|
| `test_*.py` in root | Not discoverable by pytest | Move to `tests/unit/` |
| `test_*.py` in `backend/app/` | Mixed with source code | Move to `tests/unit/` |
| Random helper scripts in root | Pollutes repository | Move to `scripts/` or cleanup |
| Component in `frontend/src/components/` | Not modular | Move to `frontend/src/modules/{module}/components/` |
| Hook in `frontend/src/hooks/` | Shared but not organized | Move to `frontend/src/modules/shared/hooks/` |
| New `.md` file not in docs/ or .kiro/steering/ | Not discoverable | Move to appropriate location |
| `database_seed.py` naming | Wrong order | Rename to `seed_database.py` |
| Backend file not following DDD layers | Architectural violation | Reorganize to correct layer |

---

## 9. Git Workflow: Moving Misplaced Files

**If a file was created in the wrong location:**

```bash
# Move the file
git mv wrong/path/file.py correct/path/file.py

# If it's a new file not yet committed
git add correct/path/file.py
git rm wrong/path/file.py

# Commit with explanation
git commit -m "chore: Move file to correct location

- Moved {file} from {wrong} to {correct}
- Follows file organization standards"
```

---

## Summary Checklist

✅ **When creating any new file, verify:**
- File is in the correct folder
- File follows naming convention
- File respects layer responsibilities (backend)
- File uses correct case (PascalCase for components, snake_case for others)
- Tests are in `tests/` folder
- No temporary files left in repository root
- Documentation is in `docs/` or `.kiro/steering/`

✅ **For code review:**
- Request immediate fix if file is misplaced
- Ask developer to move and update imports
- Verify test files are in `tests/` folder
- Block merge if structure is violated



---

## 11. Migration Plan: Deprecated Frontend Folders

### 11.1 Current State (Legacy Structure)

**Deprecated folders still in repository:**
```
frontend/src/
├── components/          ⚠️ DEPRECATED (71 files)
├── hooks/               ⚠️ DEPRECATED (12 files)
├── services/            ⚠️ DEPRECATED (29 files)
└── types/               ⚠️ DEPRECATED (8 files)
```

**These folders contain shared/generic components that should be migrated to:**
```
frontend/src/modules/shared/
├── components/          ✅ NEW (generic UI components)
├── hooks/               ✅ NEW (global hooks)
└── types/               ✅ NEW (shared types)

frontend/src/modules/{module}/
├── services/            ✅ NEW (module-specific API clients)
└── types/               ✅ NEW (module-specific types)
```

### 11.2 Migration Strategy

**Phase 1: Identify Shared vs. Module-Specific**
- Generic UI components (Button, Modal, Table) → `modules/shared/components/`
- Global hooks (useAuth, useTenant) → `modules/shared/hooks/`
- Global types (common interfaces) → `modules/shared/types/`
- Module-specific services → `modules/{module}/services/`
- Module-specific types → `modules/{module}/types/`

**Phase 2: Gradual Migration**
```bash
# Do NOT migrate all at once - causes merge conflicts
# Migrate incrementally as files are edited

# When editing a file in deprecated location:
1. Move file to new location
2. Update all imports across codebase
3. Commit separately
4. Delete deprecated file only when empty
```

**Phase 3: Cleanup**
- Delete deprecated folders ONLY after all files migrated
- Update import statements in entire codebase
- Verify no broken imports remain

### 11.3 Current Usage Rules

**Until migration is complete:**

✅ **New files:**
- MUST be created in `modules/{module}/` structure
- MUST NOT be created in deprecated folders

⚠️ **Existing files:**
- May remain in deprecated folders temporarily
- MUST be migrated when edited
- MUST use new location for all NEW imports

❌ **Prohibited:**
- Creating new files in `components/`, `hooks/`, `services/`, `types/` root folders
- Adding new imports from deprecated locations

### 11.4 Example: Migrate a Component

**Before (❌ Deprecated):**
```typescript
// frontend/src/components/Button.tsx
export const Button: React.FC<ButtonProps> = ({ ... }) => { ... }

// Imported from:
// import { Button } from '@/components/Button'
```

**After (✅ New Location):**
```typescript
// frontend/src/modules/shared/components/Button.tsx
export const Button: React.FC<ButtonProps> = ({ ... }) => { ... }

// Imported from:
// import { Button } from '@/modules/shared/components/Button'
```

**Migration Steps:**
```bash
# 1. Move file
git mv frontend/src/components/Button.tsx frontend/src/modules/shared/components/Button.tsx

# 2. Find all imports (search in IDE for "@/components/Button")
grep -r "@/components/Button" frontend/src/

# 3. Update imports in all files
# In each file:
# FROM: import { Button } from '@/components/Button'
# TO:   import { Button } from '@/modules/shared/components/Button'

# 4. Commit
git commit -m "refactor: Migrate Button component to modules/shared/components

- Moved from frontend/src/components/ to frontend/src/modules/shared/components/
- Updated all import statements across codebase
- Follows new file-organization-standards.md"
```

### 11.5 Import Path Updates

**Update imports systematically:**

```typescript
// ❌ OLD (Deprecated)
import { Button } from '@/components/Button'
import { useAuth } from '@/hooks/useAuth'
import { api } from '@/services/api'
import { Material } from '@/types/Material'

// ✅ NEW (Correct)
import { Button } from '@/modules/shared/components/Button'
import { useAuth } from '@/modules/shared/hooks/useAuth'
import { materialApi } from '@/modules/inventory/services/materialApi'
import { Material } from '@/modules/inventory/types/Material'
```

### 11.6 Timeline and Responsibility

| Phase | Timeline | Owner | Action |
|-------|----------|-------|--------|
| Phase 1 | Ongoing | All developers | Migrate files when editing |
| Phase 2 | Next 2-3 sprints | Frontend lead | Coordinate bulk migrations |
| Phase 3 | After Phase 2 | Frontend lead | Delete empty deprecated folders |

**No hard deadline - migrate gradually to avoid merge conflicts.**

### 11.7 Checking Deprecated Folder Usage

**Script to find remaining deprecated imports:**
```bash
# Find all imports from deprecated locations
grep -r "from '@/components" frontend/src/ | grep -v "modules/shared"
grep -r "from '@/hooks" frontend/src/ | grep -v "modules/shared"
grep -r "from '@/services" frontend/src/ | grep -v "modules"
grep -r "from '@/types" frontend/src/ | grep -v "modules"

# Once these commands return nothing, deprecated folders are ready for deletion
```

---

## 12. File Organization Enforcement Timeline

### Immediate (Starting Now)
- ✅ All NEW files must follow correct structure
- ✅ All NEW imports must use correct paths
- ❌ Deprecated folders marked as deprecated (not deleted)
- ✅ Code review blocks misplaced files

### Short Term (Next 1-2 sprints)
- ✅ Migrate files when editing
- ✅ Update imports gradually
- ✅ Monitor deprecated folder usage

### Medium Term (Next 3-6 sprints)
- ✅ Coordinate bulk migrations if needed
- ✅ Delete deprecated folders once empty
- ✅ Celebrate cleaner codebase!

---

