# Claude - MedTrack File Organization Guidelines

**For:** Claude AI (via Web Chat, API, or Desktop)

**Status:** 🔴 CRITICAL - Claude MUST follow these rules when generating code

**Last Updated:** November 9, 2026

---

## System Prompt to Use With Claude

**Copy and paste this into your Claude conversation:**

```
You are assisting with MedTrack, a manufacturing ERP system with strict file organization standards.

CRITICAL: Before generating ANY code, verify the file path against these 5 rules:

1. BACKEND PYTHON CODE
   Must be in: backend/app/{layer}/{module}/
   Layers: domain, application, infrastructure, interfaces
   Example: backend/app/domain/inventory/entities.py

2. FRONTEND REACT/TYPESCRIPT CODE
   Must be in: frontend/src/modules/{module}/{type}/
   Types: pages, components, hooks, services, types
   Example: frontend/src/modules/inventory/components/MaterialForm.tsx

3. TEST CODE
   Must be in: tests/{unit|integration|e2e}/test_*.py
   Example: tests/unit/test_material_validation.py

4. DATABASE MIGRATIONS
   Must be in: alembic/versions/{timestamp}_{description}.py
   Use: alembic revision --autogenerate -m "description"

5. SCRIPTS/UTILITIES
   Must be in: scripts/{category}/{script_name}.py
   Example: scripts/database/seed_data.py

ALWAYS:
- Include the full file path in comments: // File: {full/path/to/file.py}
- Use correct import paths (no deprecated frontend/src/components/, hooks/, services/)
- Place tests in tests/ folder (NEVER in root)
- Verify backend code respects DDD layers
- Verify frontend uses modules/ structure

NEVER:
- Suggest files in repository root (except config files)
- Use deprecated paths: frontend/src/components/, frontend/src/hooks/, frontend/src/services/, frontend/src/types/
- Mix tests with source code
- Create random new folders

Reference: 
- Main: docs/ai-guidelines/AI-COPILOT-CURSOR-GUIDELINES.md
- Complete: .kiro/steering/file-organization-standards.md
- Backend: .kiro/steering/backend-ddd-patterns.md
- Frontend: .kiro/steering/frontend-react-patterns.md
```

---

## How to Use This Guide

### Option 1: Direct Conversation
1. Copy the system prompt above
2. Paste into Claude conversation
3. Ask for code
4. Verify against checklist below

### Option 2: In API Calls
Include in your API system message:

```json
{
  "model": "claude-3-5-sonnet-20241022",
  "system": "[Copy system prompt above here]",
  "messages": [
    {
      "role": "user",
      "content": "Create a material entity..."
    }
  ]
}
```

---

## Common Scenarios & Expected Claude Response

### Scenario 1: Backend Entity

**You:** "Create a Material entity for the inventory module"

**Claude Should Respond:**
```python
# File: backend/app/domain/inventory/entities.py
from dataclasses import dataclass
from uuid import UUID

@dataclass
class Material:
    """Material entity with unique identity."""
    id: UUID
    code: str
    name: str
```

✅ **Correct:** Full path, correct layer

### Scenario 2: React Component

**You:** "Create a form component for adding materials"

**Claude Should Respond:**
```typescript
// File: frontend/src/modules/inventory/components/MaterialForm.tsx
import React, { useState } from 'react'

export const MaterialForm: React.FC = () => {
  const [formData, setFormData] = useState({})
  return <form>{/* form fields */}</form>
}
```

✅ **Correct:** Full module path, PascalCase

### Scenario 3: Tests

**You:** "Write unit tests for material validation"

**Claude Should Respond:**
```python
# File: tests/unit/test_material_validation.py
import pytest

@pytest.mark.unit
def test_material_code_format():
    from backend.app.domain.inventory.entities import Material
    material = Material(id=..., code="MAT-001", name="Steel")
    assert material.code.startswith("MAT-")
```

✅ **Correct:** In tests/ folder, not root

---

## RED FLAGS: When to Ask Claude to Revise

If Claude generates code with ANY of these, **ASK FOR REVISION:**

| Issue | Example | Fix |
|-------|---------|-----|
| Missing full path | `// File: entities.py` | Ask: "Please include full path: `backend/app/domain/inventory/entities.py`" |
| Test in root | `# File: test_material.py` | Ask: "This should be in: `tests/unit/test_material.py`" |
| Deprecated import | `import Button from '@/components'` | Ask: "Use new path: `import Button from '@/modules/shared/components'`" |
| Wrong backend layer | `# File: backend/app/material.py` | Ask: "Specify layer: domain, application, infrastructure, or interfaces?" |
| No module context | `frontend/src/Component.tsx` | Ask: "Place in module: `frontend/src/modules/{module}/components/`" |

---

## Verification Checklist

After Claude generates code, **verify:**

```
[ ] File path is fully specified (e.g., backend/app/domain/inventory/entities.py)
[ ] Path matches one of 5 correct locations
[ ] Naming follows conventions (snake_case Python, PascalCase React components)
[ ] Imports use correct module paths (not deprecated)
[ ] Tests are in tests/ folder (not mixed with source)
[ ] Backend code respects DDD layers
[ ] Frontend uses modules/{module}/ structure
[ ] No files suggested for repository root
```

**If ANY fail:** Ask Claude to regenerate with corrections

---

## Example: Asking Claude for Backend Code

```
You: "I need a command handler to create materials. 
Please create it in backend/app/application/inventory/commands/ 
named create_material.py with:
- CreateMaterialCommand dataclass with code, name, uom_id
- handle_create_material async function
- Validates code is unique
- Returns material_id
- Include proper type hints"

Claude should generate:
// File: backend/app/application/inventory/commands/create_material.py
@dataclass
class CreateMaterialCommand:
    code: str
    name: str
    uom_id: UUID

async def handle_create_material(cmd: CreateMaterialCommand) -> UUID:
    ...
```

✅ **Correct:** Full path, proper layer, type hints

---

## Example: Asking Claude for Frontend Code

```
You: "Create a React hook for fetching materials in the inventory module.
File should go in frontend/src/modules/inventory/hooks/
named useMaterials.ts
Include:
- Fetch materials from API
- Handle loading and error states
- Return materials array"

Claude should generate:
// File: frontend/src/modules/inventory/hooks/useMaterials.ts
export const useMaterials = () => {
  const [materials, setMaterials] = useState<Material[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  ...
}
```

✅ **Correct:** Full path, proper module structure

---

## Quick Reference: All Paths

### Backend
```
domain/{module}/entities.py              - Business objects
domain/{module}/exceptions.py            - Business errors
application/{module}/commands/           - Write operations
application/{module}/queries/            - Read operations
infrastructure/persistence/models/       - ORM models
infrastructure/persistence/repositories/ - Data access
interfaces/api/v1/routes/                - HTTP endpoints
```

### Frontend
```
modules/{module}/types/                  - TypeScript interfaces
modules/{module}/hooks/                  - Custom hooks
modules/{module}/services/               - API clients
modules/{module}/components/             - Reusable components
modules/{module}/pages/                  - Page components
modules/shared/components/               - Shared UI (Button, Modal)
```

### Tests
```
tests/unit/                              - Pure logic
tests/integration/                       - With database
tests/e2e/                               - Full workflows
```

---

## Common Claude Mistakes to Correct

| Mistake | How to Fix |
|---------|-----------|
| "File: services/material.py" | Ask: "Which layer? This should be in `backend/app/infrastructure/services/` or `frontend/src/modules/inventory/services/`" |
| "import from '@/components/Button'" | Ask: "This path is deprecated. Use: `import from '@/modules/shared/components/Button'`" |
| "test_material.py in root" | Ask: "Tests must be in: `tests/unit/test_material.py`" |
| No file path | Ask: "Please include full file path in the code comment" |

---

## Pro Tips for Getting Best Results

1. **Be Specific:** Include exact folder path in your request
2. **Show Examples:** Point to existing similar files
3. **Verify Immediately:** Check path against 5 rules right away
4. **Ask for Revisions:** Don't accept bad paths - ask Claude to fix
5. **Reference Docs:** "Follow .kiro/steering/file-organization-standards.md"

---

## References

- Complete: `docs/ai-guidelines/AI-COPILOT-CURSOR-GUIDELINES.md`
- Standards: `.kiro/steering/file-organization-standards.md`
- Backend: `.kiro/steering/backend-ddd-patterns.md`
- Frontend: `.kiro/steering/frontend-react-patterns.md`
- Critical: `AGENTS.md` § "File Organization Standards"

---

**Status:** 🔴 ACTIVE - Use system prompt for all Claude sessions
**Last Updated:** November 9, 2026
