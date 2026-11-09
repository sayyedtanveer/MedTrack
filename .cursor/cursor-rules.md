# Cursor IDE - MedTrack File Organization Rules

**Status:** 🔴 ACTIVE - Cursor MUST follow these rules

**Last Updated:** November 9, 2026

---

## CRITICAL: File Organization Rules

### The 5 Golden Rules

ALL code generation MUST follow these paths:

```
1. Backend Python
   backend/app/domain/{module}/             (business logic)
   backend/app/application/{module}/        (use cases)
   backend/app/infrastructure/              (persistence)
   backend/app/interfaces/api/v1/routes/    (HTTP endpoints)

2. Frontend React/TypeScript
   frontend/src/modules/{module}/pages/     (page components)
   frontend/src/modules/{module}/components/ (reusable components)
   frontend/src/modules/{module}/hooks/     (custom hooks)
   frontend/src/modules/{module}/services/  (API clients)
   frontend/src/modules/{module}/types/     (TypeScript interfaces)
   frontend/src/modules/shared/             (truly shared code only)

3. Tests
   tests/unit/test_*.py                     (unit tests)
   tests/integration/test_*.py              (integration tests)
   tests/e2e/test_*.py                      (end-to-end tests)

4. Database Migrations
   alembic/versions/{timestamp}_{description}.py
   Use: alembic revision --autogenerate -m "description"

5. Scripts
   scripts/{category}/{script_name}.py
   Categories: database, debug, archived-migrations
```

---

## PROHIBITED Patterns

❌ DO NOT SUGGEST:
- Files in repository root (except config)
- `frontend/src/components/` (DEPRECATED)
- `frontend/src/hooks/` (DEPRECATED)
- `frontend/src/services/` (DEPRECATED)
- `frontend/src/types/` (DEPRECATED)
- Tests mixed with source code
- Random new folders
- Files without module context

---

## Backend Code Examples

```python
# ✅ Entity (Domain Layer)
# File: backend/app/domain/inventory/entities.py
class Material:
    id: UUID
    code: str
    name: str

# ✅ Command (Application Layer)
# File: backend/app/application/inventory/commands/create_material.py
@dataclass
class CreateMaterialCommand:
    code: str
    name: str

# ✅ Repository (Infrastructure)
# File: backend/app/infrastructure/persistence/repositories/material_repository.py
class MaterialRepository(IMaterialRepository):
    async def save(self, material: Material) -> UUID:
        pass

# ✅ Route (Interfaces/HTTP)
# File: backend/app/interfaces/api/v1/routes/material_routes.py
@router.post("/materials")
async def create_material(request: CreateMaterialRequest):
    pass
```

---

## Frontend Code Examples

```typescript
// ✅ Type
// File: frontend/src/modules/inventory/types/Material.ts
export interface Material {
  id: string
  code: string
  name: string
}

// ✅ Hook
// File: frontend/src/modules/inventory/hooks/useMaterials.ts
export const useMaterials = () => {
  const [materials, setMaterials] = useState<Material[]>([])
  return { materials }
}

// ✅ Service
// File: frontend/src/modules/inventory/services/materialApi.ts
export const materialApi = {
  async list(): Promise<Material[]> {},
  async create(data): Promise<string> {}
}

// ✅ Component
// File: frontend/src/modules/inventory/components/MaterialForm.tsx
export const MaterialForm: React.FC = () => {
  return <form></form>
}

// ✅ Page
// File: frontend/src/modules/inventory/pages/MaterialPage.tsx
export const MaterialPage: React.FC = () => {
  return <div><MaterialForm /></div>
}
```

---

## Test Code Examples

```python
# ✅ Unit Test
# File: tests/unit/test_material_validation.py
@pytest.mark.unit
def test_material_code_validation():
    assert validate_code("MAT-001") == True

# ✅ Integration Test
# File: tests/integration/test_material_integration.py
@pytest.mark.integration
async def test_create_material_in_database():
    material_id = await create_material(...)
    assert material_id is not None
```

---

## Import Rules

### ✅ CORRECT
```python
from backend.app.domain.inventory.entities import Material
from backend.app.application.inventory.commands import CreateMaterialCommand
```

```typescript
import { Material } from '@/modules/inventory/types/Material'
import { useMaterials } from '@/modules/inventory/hooks/useMaterials'
import { Button } from '@/modules/shared/components/Button'
```

### ❌ WRONG (REJECT)
```python
from app.entities import Material  # Missing module path
from backend.material import Material  # Wrong layer
```

```typescript
import { Button } from '@/components/Button'  # Deprecated path
import { useAuth } from '@/hooks/useAuth'  # Deprecated path
```

---

## Naming Conventions

**Python (snake_case):**
- ✅ create_material.py, material_repository.py
- ❌ CreateMaterial.py, MaterialRepository.py

**TypeScript (PascalCase components, camelCase others):**
- ✅ MaterialForm.tsx, useMaterials.ts, materialApi.ts
- ❌ material-form.tsx, MaterialForm.ts, MaterialApi.ts

---

## RED FLAGS: REJECT This Code

| Pattern | Problem | What to Do |
|---------|---------|-----------|
| `// File: entities.py` | No full path | Require full path: `backend/app/domain/inventory/entities.py` |
| `test_material.py` in root | Tests in root | Must be: `tests/unit/test_material.py` |
| `import from '@/components'` | Deprecated path | Use: `import from '@/modules/inventory/components'` |
| `backend/material.py` | Wrong layer | Ask for correct layer: domain, application, infrastructure, interfaces |

---

## Before Suggesting Code

Verify:
- [ ] File path matches one of 5 correct locations
- [ ] Full path specified (not just filename)
- [ ] Layer correct (if backend)
- [ ] Module clear (inventory, sales, etc.)
- [ ] Naming follows conventions
- [ ] Imports use correct paths
- [ ] No deprecated patterns

**Ask user for clarification if unsure.**

---

## References

- Full: `docs/ai-guidelines/AI-COPILOT-CURSOR-GUIDELINES.md`
- Standards: `.kiro/steering/file-organization-standards.md`
- Backend: `.kiro/steering/backend-ddd-patterns.md`
- Frontend: `.kiro/steering/frontend-react-patterns.md`
- Critical: `AGENTS.md`

**Status:** 🔴 ACTIVE - Apply to all code generation
