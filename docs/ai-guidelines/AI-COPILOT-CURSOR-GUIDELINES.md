# File Organization Guidelines for External AI Assistants

**For:** GitHub Copilot, Cursor IDE, Claude, ChatGPT, and all external AI tools

**Status:** 🔴 CRITICAL - Must follow for all code generation

**Last Updated:** November 9, 2026

---

## Quick Start: The 5 Golden Rules

Before any AI generates code, it MUST check:

### 1️⃣ Backend Python Code
```
✅ CORRECT: backend/app/{layer}/{module}/file.py
❌ WRONG:   backend/file.py or root/file.py

Layers: domain, application, infrastructure, interfaces
Example: backend/app/domain/inventory/entities.py
```

### 2️⃣ Frontend React/TypeScript
```
✅ CORRECT: frontend/src/modules/{module}/{type}/File.tsx
❌ WRONG:   frontend/src/components/File.tsx (deprecated)

Types: pages, components, hooks, services, types
Example: frontend/src/modules/inventory/components/MaterialForm.tsx
```

### 3️⃣ Test Files
```
✅ CORRECT: tests/{unit|integration|e2e}/test_*.py
❌ WRONG:   test_*.py in root or mixed with source code

Example: tests/unit/test_material_validation.py
```

### 4️⃣ Database Migrations
```
✅ CORRECT: alembic/versions/{timestamp}_{description}.py
❌ WRONG:   any other location

Command: alembic revision --autogenerate -m "description"
```

### 5️⃣ Scripts/Utilities
```
✅ CORRECT: scripts/{category}/{script_name}.py
❌ WRONG:   root/script.py

Categories: database, debug, archived-migrations
Example: scripts/database/seed_data.py
```

---

## For GitHub Copilot Users

### ⚙️ Setup Instructions

**1. Add to your VS Code workspace settings (.vscode/settings.json):**

```json
{
  "github.copilot.enable": {
    "yaml": true,
    "json": true,
    "markdown": true,
    "plaintext": true
  },
  "github.copilot.advanced": {
    "internalUnstableForcedOverrides": {
      "skipCloudTelemetry": true
    }
  }
}
```

**2. Create a .copilotignore file (like .gitignore) to guide Copilot:**

```
# Copilot should NOT suggest edits to these
*.lock
package-lock.json
node_modules/
venv/
.env
.coverage
```

**3. Add context comments in your code:**

```python
# File organization rule: Backend domain layer files go in backend/app/domain/{module}/
# Current file location should follow this pattern

class Material:  # This entity belongs in backend/app/domain/inventory/entities.py
    """Material entity for inventory management."""
    pass
```

### 📋 Copilot Usage Tips

When asking Copilot to create code:

```
❌ DON'T say:
"Create a handler for materials"

✅ DO say:
"Create a command handler in backend/app/application/inventory/commands/
named create_material.py with CreateMaterialCommand class"

❌ DON'T say:
"Create a form component"

✅ DO say:
"Create MaterialForm.tsx component in 
frontend/src/modules/inventory/components/ with these props: {..."
```

---

## For Cursor IDE Users

### ⚙️ Setup Instructions

**1. Create `.cursor/rules` file in project root:**

```markdown
# MedTrack File Organization Rules

## CRITICAL: All file paths MUST follow this structure

### Backend Python
- Domain layer: backend/app/domain/{module}/
- Application layer: backend/app/application/{module}/
- Infrastructure: backend/app/infrastructure/
- HTTP routes: backend/app/interfaces/api/v1/routes/

### Frontend React
- Page components: frontend/src/modules/{module}/pages/
- Reusable components: frontend/src/modules/{module}/components/
- Shared components: frontend/src/modules/shared/components/
- Hooks: frontend/src/modules/{module}/hooks/ or modules/shared/hooks/
- Services: frontend/src/modules/{module}/services/
- Types: frontend/src/modules/{module}/types/

### Tests
- Unit tests: tests/unit/test_*.py
- Integration: tests/integration/test_*.py
- E2E: tests/e2e/test_*.py

### Never
- Create files in repository root (except config)
- Mix tests with source code
- Use deprecated: frontend/src/components/, hooks/, services/, types/

Reference: docs/ai-guidelines/AI-COPILOT-CURSOR-GUIDELINES.md
```

**2. Create `.cursorignore` file:**

```
# Cursor should not examine these files for context
__pycache__/
node_modules/
.venv/
venv/
.env
.coverage
*.pyc
alembic_err.log
```

**3. Use Cursor's "Rules" feature:**

Settings → Features → Rules → Add above rules

---

## For Claude / ChatGPT Users

### 📝 System Prompt Template

Add this to your conversation:

```
You are assisting with MedTrack, a manufacturing ERP system with strict file organization rules.

BEFORE generating ANY code, verify the file path:

1. Backend Python → backend/app/{domain|application|infrastructure|interfaces}/{module}/
2. Frontend React → frontend/src/modules/{module}/{type}/
3. Tests → tests/{unit|integration|e2e}/test_*.py
4. Migrations → alembic/versions/{timestamp}_{description}.py
5. Scripts → scripts/{category}/

ALWAYS include the full file path in your response like:
// File: frontend/src/modules/inventory/components/MaterialForm.tsx

NEVER suggest:
- Files in repository root
- Tests mixed with source code
- Use of deprecated paths (frontend/src/components/, hooks/, services/, types/)

Reference: docs/AI-ASSISTANT-GUIDELINES.md, .kiro/steering/file-organization-standards.md
```

---

## Common Scenarios & Correct Responses

### Scenario 1: Create Backend Entity

**You ask:**
> "Create a Material entity for the inventory module"

**AI Should Do:**
```python
# File: backend/app/domain/inventory/entities.py
from dataclasses import dataclass
from uuid import UUID

@dataclass
class Material:
    """Material entity for inventory management."""
    id: UUID
    code: str
    name: str
```

✅ **Correct:** Full path specified, domain layer

### Scenario 2: Create React Component

**You ask:**
> "Create a form component for adding materials"

**AI Should Do:**
```typescript
// File: frontend/src/modules/inventory/components/MaterialForm.tsx
import React from 'react'

export const MaterialForm: React.FC = () => {
  return <form>{/* form fields */}</form>
}
```

✅ **Correct:** Full module path, PascalCase component

### Scenario 3: Create Tests

**You ask:**
> "Write tests for material creation"

**AI Should Do:**
```python
# File: tests/unit/test_material_entity.py
import pytest
from backend.app.domain.inventory.entities import Material

@pytest.mark.unit
def test_material_creation():
    material = Material(id=uuid.uuid4(), code="MAT-001", name="Steel")
    assert material.code == "MAT-001"
```

✅ **Correct:** In tests/ folder, not root

---

## Red Flags: When to STOP the AI

If the AI suggests ANY of these, **REJECT** and ask for correction:

| Red Flag | Example | Fix |
|----------|---------|-----|
| Missing path | `// File: entities.py` | Specify full path: `backend/app/domain/inventory/entities.py` |
| Test in root | `test_material.py` (in root) | Move to `tests/unit/test_material.py` |
| Deprecated import | `import Button from '@/components'` | Use `import Button from '@/modules/shared/components'` |
| Wrong layer | `backend/material.py` | Use correct layer: `backend/app/domain/inventory/entities.py` |
| Random folder | `frontend/src/new_folder/Component.tsx` | Use `frontend/src/modules/{module}/` |

---

## Verification Checklist

After AI generates code, verify:

```
[ ] File path matches one of 5 correct locations
[ ] Path is fully specified (not just "entities.py")
[ ] Naming follows conventions (snake_case Python, PascalCase React)
[ ] Import statements use correct module paths
[ ] Tests are in tests/ folder
[ ] Backend respects DDD layers
[ ] Frontend uses modules/{module}/ structure
[ ] No files in repository root
```

**If ANY fail:** Ask AI to regenerate with correct path

---

## Quick Reference: File Paths

### Backend Paths
```python
# Domain (business logic)
backend/app/domain/{module}/entities.py
backend/app/domain/{module}/exceptions.py
backend/app/domain/{module}/repositories.py  # interfaces

# Application (use cases)
backend/app/application/{module}/commands/create_{entity}.py
backend/app/application/{module}/queries/get_{entity}.py
backend/app/application/{module}/handlers/command_handlers.py

# Infrastructure (persistence)
backend/app/infrastructure/persistence/models/{module}_models.py
backend/app/infrastructure/persistence/repositories/{module}_repository.py
backend/app/infrastructure/services/{service}_service.py

# Interfaces (HTTP)
backend/app/interfaces/api/v1/routes/{module}_routes.py
backend/app/interfaces/api/v1/schemas/{module}_schemas.py
```

### Frontend Paths
```typescript
// Module structure
frontend/src/modules/{module}/
├── pages/{Entity}Page.tsx
├── components/{Entity}Form.tsx
├── hooks/use{Entity}.ts
├── services/{entity}Api.ts
└── types/{Entity}.ts

// Shared (use only for truly shared code)
frontend/src/modules/shared/
├── components/Button.tsx
└── hooks/useAuth.ts
```

### Test Paths
```python
tests/unit/test_module_functionality.py
tests/integration/test_module_integration.py
tests/e2e/test_complete_workflow.py
```

---

## For Teams Using Multiple AI Tools

### Consistency Strategy

**If using Copilot + Cursor + Claude:**

1. **Have ONE source of truth:** `.kiro/steering/file-organization-standards.md`
2. **Provide same rules to each AI** (add to each tool's settings)
3. **Human reviews code** before accepting (verify paths)
4. **Code review blocks violations** (don't merge wrong paths)

### Example Review Comment

```
❌ File path issue:
The suggested file path doesn't follow our standards.

Current: backend/material_handler.py
Required: backend/app/application/inventory/commands/create_material.py

See: .kiro/steering/file-organization-standards.md
Please regenerate with correct path.
```

---

## Handling AI Mistakes

**When AI gets path wrong:**

```
You: "Create a Material service"

AI: "// File: services/material.py"

You: "That path isn't correct. MedTrack requires:
- Backend services go in: backend/app/infrastructure/services/material_service.py
- Frontend services go in: frontend/src/modules/{module}/services/

Which would you like me to create?"
```

---

## Key Documents to Share with AI

When using external AI, provide these documents:

1. **Main guide:** `docs/AI-ASSISTANT-GUIDELINES.md`
2. **Complete standards:** `.kiro/steering/file-organization-standards.md`
3. **Backend patterns:** `.kiro/steering/backend-ddd-patterns.md`
4. **Frontend patterns:** `.kiro/steering/frontend-react-patterns.md`
5. **AGENTS.md section:** Critical rules in AGENTS.md

---

## Testing Your AI Setup

**Quick test to verify AI follows rules:**

```
Ask: "Create a new React component called ProductForm for the sales module"

Expected response should include:
✅ "File: frontend/src/modules/sales/components/ProductForm.tsx"
✅ "import { useProduct } from '@/modules/sales/hooks/useProduct'"
✅ "export const ProductForm: React.FC = () => { ... }"

If you see:
❌ "File: components/ProductForm.tsx" (missing module path)
❌ "import { useProduct } from '@/hooks/useProduct'" (deprecated path)
❌ No file path specified

Then reconfigure the AI with the rules above.
```

---

## Summary: 3-Step Process

### Step 1: Prime the AI
Provide file organization rules before asking for code

### Step 2: Request Specific Paths
Ask with full path details, not generic requests

### Step 3: Verify Results
Check generated code matches the 5 golden rules

---

**Reference:** 
- Complete guide: `.kiro/steering/file-organization-standards.md`
- Backend patterns: `.kiro/steering/backend-ddd-patterns.md`
- Frontend patterns: `.kiro/steering/frontend-react-patterns.md`
- Critical rules: `AGENTS.md`

**Last Updated:** November 9, 2026
