# File Organization Guidelines for AI Code Assistants

**For:** GitHub Copilot, Cursor, Kiro, Claude, and all AI-assisted development

**Status:** 🔴 CRITICAL - Apply to all code generation

---

## Core Rules: Check These BEFORE Generating ANY Code

### ✅ Correct Locations

| Type | Path | Example |
|------|------|---------|
| Backend Python (Domain) | `backend/app/domain/{module}/` | `backend/app/domain/inventory/entities.py` |
| Backend Python (Application) | `backend/app/application/{module}/commands` | `backend/app/application/inventory/commands/create_material.py` |
| Backend Python (Infrastructure) | `backend/app/infrastructure/persistence/` | `backend/app/infrastructure/persistence/models/material_models.py` |
| Backend Python (Interfaces/Routes) | `backend/app/interfaces/api/v1/routes/` | `backend/app/interfaces/api/v1/routes/material_routes.py` |
| Frontend React Components | `frontend/src/modules/{module}/components/` | `frontend/src/modules/inventory/components/MaterialForm.tsx` |
| Frontend React Pages | `frontend/src/modules/{module}/pages/` | `frontend/src/modules/inventory/pages/MaterialPage.tsx` |
| Frontend React Hooks | `frontend/src/modules/{module}/hooks/` | `frontend/src/modules/inventory/hooks/useMaterials.ts` |
| Frontend React Services | `frontend/src/modules/{module}/services/` | `frontend/src/modules/inventory/services/materialApi.ts` |
| Frontend React Types | `frontend/src/modules/{module}/types/` | `frontend/src/modules/inventory/types/Material.ts` |
| Shared Frontend Components | `frontend/src/modules/shared/components/` | `frontend/src/modules/shared/components/Button.tsx` |
| Shared Frontend Hooks | `frontend/src/modules/shared/hooks/` | `frontend/src/modules/shared/hooks/useAuth.ts` |
| Unit Tests | `tests/unit/` | `tests/unit/test_material_validation.py` |
| Integration Tests | `tests/integration/` | `tests/integration/test_material_integration.py` |
| E2E Tests | `tests/e2e/` | `tests/e2e/test_complete_workflow.py` |
| Database Migrations | `alembic/versions/` | `alembic/versions/20261109_create_materials_table.py` |
| Scripts/Utilities | `scripts/{category}/` | `scripts/database/seed_data.py` |

### ❌ Prohibited Locations

```
❌ Never create files in:
- Repository root (except config files like .env, docker-compose.yml)
- frontend/src/components/        (deprecated, use modules/*/components)
- frontend/src/hooks/              (deprecated, use modules/*/hooks)
- frontend/src/services/           (deprecated, use modules/*/services)
- frontend/src/types/              (deprecated, use modules/*/types)
- Tests mixed with source code
- Random new folders without structure
```

---

## How to Use This Guide

### Step 1: User Requests Code
> "Create a form component for adding new materials"

### Step 2: Check the Location
```
✅ Is it Frontend React code?
   → Goes in frontend/src/modules/inventory/components/
✅ Is it for creating (not retrieving)?
   → Call it MaterialForm.tsx (not MaterialFormPage)
✅ Is it a component?
   → Use PascalCase: MaterialForm.tsx
```

### Step 3: Verify the Full Path
```typescript
// ✅ CORRECT with full path
// File: frontend/src/modules/inventory/components/MaterialForm.tsx
export const MaterialForm: React.FC = () => {
  // implementation
}

// ❌ WRONG - incomplete path
// File: components/MaterialForm.tsx
```

### Step 4: Verify Imports
```typescript
// ✅ CORRECT imports
import { Button } from '@/modules/shared/components/Button'
import { useMaterialApi } from '@/modules/inventory/hooks/useMaterialApi'
import { Material } from '@/modules/inventory/types/Material'

// ❌ WRONG imports (old deprecated paths)
import { Button } from '@/components/Button'
import { useMaterialApi } from '@/hooks/useMaterialApi'
import { Material } from '@/types/Material'
```

---

## Detailed Scenarios

### Scenario 1: Backend - New Entity Handler

**Request:** "Create a command to create a new material"

**Your Response:**

```python
# Step 1: Define command (in application layer)
# File: backend/app/application/inventory/commands/create_material.py
from dataclasses import dataclass
from uuid import UUID

@dataclass
class CreateMaterialCommand:
    tenant_id: UUID
    code: str
    name: str
    uom_id: UUID

# Step 2: Create domain entity (in domain layer)
# File: backend/app/domain/inventory/entities.py
class Material:
    def __init__(self, code: str, name: str, uom_id: UUID):
        self.code = code
        self.name = name
        self.uom_id = uom_id

# Step 3: Create handler (in application handlers)
# File: backend/app/application/inventory/handlers/command_handlers.py
async def handle_create_material(cmd: CreateMaterialCommand) -> UUID:
    material = Material(
        code=cmd.code,
        name=cmd.name,
        uom_id=cmd.uom_id
    )
    material_id = await repo.save(material)
    return material_id

# Step 4: Create route (in interfaces layer)
# File: backend/app/interfaces/api/v1/routes/material_routes.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/materials")
async def create_material(request: CreateMaterialRequest) -> dict:
    cmd = CreateMaterialCommand(
        tenant_id=tenant_id,
        code=request.code,
        name=request.name,
        uom_id=request.uom_id
    )
    material_id = await handler.handle_create_material(cmd)
    return {"id": material_id}
```

### Scenario 2: Frontend - New Feature Module

**Request:** "Create a page and form for managing materials"

**Your Response:**

```typescript
// File: frontend/src/modules/inventory/types/Material.ts
export interface Material {
  id: string
  code: string
  name: string
  created_at: string
}

// File: frontend/src/modules/inventory/services/materialApi.ts
export const materialApi = {
  async list(): Promise<Material[]> {
    // API call
  },
  async create(data: Omit<Material, 'id' | 'created_at'>): Promise<string> {
    // API call
  }
}

// File: frontend/src/modules/inventory/hooks/useMaterials.ts
export const useMaterials = () => {
  const [materials, setMaterials] = useState<Material[]>([])
  useEffect(() => {
    materialApi.list().then(setMaterials)
  }, [])
  return { materials }
}

// File: frontend/src/modules/inventory/components/MaterialForm.tsx
export const MaterialForm: React.FC = () => {
  // Form component
}

// File: frontend/src/modules/inventory/pages/MaterialPage.tsx
export const MaterialPage: React.FC = () => {
  return (
    <div>
      <MaterialForm />
    </div>
  )
}
```

### Scenario 3: Tests

**Request:** "Write tests for material creation"

**Your Response:**

```python
# File: tests/unit/test_material_entity.py
import pytest
from backend.app.domain.inventory.entities import Material

@pytest.mark.unit
def test_material_creation():
    material = Material(code="MAT-001", name="Steel")
    assert material.code == "MAT-001"

# File: tests/integration/test_material_integration.py
import pytest

@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_material_via_api(client):
    response = await client.post("/api/v1/materials", json={
        "code": "MAT-001",
        "name": "Steel"
    })
    assert response.status_code == 201
```

---

## For Copilot/Cursor Users

### Add to Your Settings

**In `.cursor/rules` or Copilot settings:**

```markdown
# MedTrack File Organization Rules

CRITICAL: Before generating code, verify file path:

1. Backend Python → backend/app/{domain|application|infrastructure|interfaces}/
2. Frontend React → frontend/src/modules/{module}/{type}/
3. Tests → tests/{unit|integration|e2e}/
4. Migrations → alembic/versions/ (use: alembic revision --autogenerate)
5. Scripts → scripts/{category}/

Always:
- Specify COMPLETE file path in comments
- Use correct module paths in imports
- Place tests in tests/ folder (NEVER root)
- Check existing folder structure first
- Follow naming: snake_case (Python), PascalCase (components)

Reference: docs/AI-ASSISTANT-GUIDELINES.md
```

### Prompt Template

```
When I ask you to create code, ALWAYS:

1. Ask: "Should I create this in [FULL_PATH]?"
2. Check: Show me the exact file path you're creating
3. Verify: Confirm imports use correct module paths
4. Validate: Ensure path matches MedTrack file organization standards

Reference documents:
- Full standards: .kiro/steering/file-organization-standards.md
- Backend patterns: .kiro/steering/backend-ddd-patterns.md
- Frontend patterns: .kiro/steering/frontend-react-patterns.md
```

---

## Checklist: Before Accepting Generated Code

When Copilot/Cursor generates code, verify:

- [ ] **File Path:** Does it match one of the 5 correct locations?
- [ ] **Naming:** Does it follow conventions (snake_case Python, PascalCase components)?
- [ ] **Imports:** Do all imports use correct module paths?
- [ ] **Tests:** Are tests in `tests/` folder, not mixed with source?
- [ ] **Layer:** Does backend code respect DDD layers?
- [ ] **Module:** Does frontend code use `modules/{module}/` structure?
- [ ] **No Root:** Are there no random files in repository root?

**If ANY fail:** Ask the assistant to correct the path before accepting.

---

## Common Mistakes AI Makes

| Mistake | Why Wrong | Fix |
|---------|-----------|-----|
| `File: components/Button.tsx` | Missing module path | `File: frontend/src/modules/shared/components/Button.tsx` |
| `import { Button } from '@/components'` | Deprecated path | `import { Button } from '@/modules/shared/components/Button'` |
| `File: test_material.py` in root | Tests must be in tests/ | `File: tests/unit/test_material.py` |
| `File: material_entity.py` (no path) | Incomplete path | `File: backend/app/domain/inventory/entities.py` |
| `File: backend/Material.tsx` | Wrong layer | Should be `frontend/src/modules/inventory/components/Material.tsx` |

---

## Reference Documents

- **Complete Guide:** `.kiro/steering/file-organization-standards.md` (Sections 1-12)
- **Backend Patterns:** `.kiro/steering/backend-ddd-patterns.md`
- **Frontend Patterns:** `.kiro/steering/frontend-react-patterns.md`
- **Data Import/Export:** `.kiro/steering/data-import-export-patterns.md`
- **CRITICAL RULES:** `AGENTS.md` (read § "File Organization Standards")

---

## Questions?

**If Copilot/Cursor is unsure about file placement:**

1. Check `.kiro/steering/file-organization-standards.md` Section 7.1
2. Check existing similar files and mirror their location
3. Ask yourself: "Is this business logic (domain), use case (application), persistence (infrastructure), or HTTP (interfaces)?"
4. When in doubt, use the 5 core locations table above

---

**Last Updated:** November 9, 2026  
**Status:** 🔴 ACTIVE - Apply to ALL AI-assisted code generation  
**Maintainer:** MedTrack Engineering Team
