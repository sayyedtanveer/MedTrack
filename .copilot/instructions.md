# GitHub Copilot - MedTrack File Organization Rules

**Status:** 🔴 ACTIVE - Copilot MUST follow these rules

**Last Updated:** November 9, 2026

---

## Critical: Before Generating ANY Code

Copilot MUST verify file paths match MedTrack structure.

### The 5 Rules

1. **Backend Python** → `backend/app/{layer}/{module}/`
2. **Frontend React** → `frontend/src/modules/{module}/{type}/`
3. **Tests** → `tests/{unit|integration|e2e}/test_*.py`
4. **Migrations** → `alembic/versions/{timestamp}_{desc}.py`
5. **Scripts** → `scripts/{category}/`

---

## File Path Examples

### Backend
```python
# ✅ Correct
# File: backend/app/domain/inventory/entities.py
class Material:
    pass

# ✅ Correct
# File: backend/app/application/inventory/commands/create_material.py
class CreateMaterialCommand:
    pass

# ✅ Correct
# File: backend/app/interfaces/api/v1/routes/material_routes.py
@router.post("/materials")
async def create_material():
    pass
```

### Frontend
```typescript
// ✅ Correct
// File: frontend/src/modules/inventory/types/Material.ts
export interface Material {
  id: string
  code: string
}

// ✅ Correct
// File: frontend/src/modules/inventory/hooks/useMaterials.ts
export const useMaterials = () => {
  // hook
}

// ✅ Correct
// File: frontend/src/modules/inventory/components/MaterialForm.tsx
export const MaterialForm = () => {
  // component
}
```

### Tests
```python
# ✅ Correct
# File: tests/unit/test_material_validation.py
@pytest.mark.unit
def test_material_code():
    pass

# ✅ Correct
# File: tests/integration/test_material_integration.py
@pytest.mark.integration
async def test_create_material():
    pass
```

---

## RED FLAGS: Reject This Code

| Pattern | Problem | Solution |
|---------|---------|----------|
| `File: entities.py` | No full path | Add full path: `backend/app/domain/inventory/entities.py` |
| `File: test_*.py` (in root) | Tests in root | Move to: `tests/unit/test_*.py` |
| `import from '@/components'` | Deprecated path | Use: `import from '@/modules/inventory/components'` |
| `File: backend/material.py` | Wrong layer | Use correct layer: `backend/app/domain/inventory/entities.py` |

**If Copilot violates ANY rule → REJECT and ask to regenerate with correct path**

---

## Copilot Prompt Template

When asking Copilot for code:

```
❌ DON'T:
"Create a handler for creating materials"

✅ DO:
"Create a command handler in backend/app/application/inventory/commands/
named create_material.py with CreateMaterialCommand dataclass that:
- Takes tenant_id, code, name as parameters
- Validates code is unique
- Returns material_id on success"
```

---

## Verification Checklist

Before accepting Copilot's code:

- [ ] Full file path specified in comment
- [ ] Path matches one of 5 correct locations
- [ ] Naming follows conventions (snake_case Python, PascalCase React)
- [ ] Imports use correct module paths
- [ ] Tests in tests/ folder (not root)
- [ ] Backend respects DDD layers
- [ ] Frontend uses modules/ structure

**Reject if ANY fail.**

---

## Reference

- Full guide: `docs/ai-guidelines/AI-COPILOT-CURSOR-GUIDELINES.md`
- Standards: `.kiro/steering/file-organization-standards.md`
- Backend: `.kiro/steering/backend-ddd-patterns.md`
- Frontend: `.kiro/steering/frontend-react-patterns.md`
- Critical: `AGENTS.md` § "File Organization Standards"
