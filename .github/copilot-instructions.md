# GitHub Copilot Instructions for MedTrack

**For:** GitHub Copilot inline code suggestions and completions  
**Entry Point:** This file (quick reference)  
**Canonical Reference:** [`AGENTS.md`](../AGENTS.md) (root authority)  
**Updated:** November 9, 2026  
**Status:** Production Ready

---

## Path-Specific Instructions (Context-Aware)

GitHub Copilot will automatically apply path-specific instructions based on file location:

| When Working In | Use This File | Key Rules |
|-----------------|---------------|-----------|
| `backend/**/*.py` | [backend.instructions.md](./instructions/backend.instructions.md) | DDD layers, CQRS, async, FastAPI, type hints |
| `frontend/src/**/*.{tsx,ts}` | [frontend.instructions.md](./instructions/frontend.instructions.md) | React, TypeScript strict, hooks, testing |
| `alembic/**/*.py`, `backend/app/infrastructure/persistence/**/*.py` | [database.instructions.md](./instructions/database.instructions.md) | Migrations, soft deletes, multi-tenancy, indexes |
| `backend/app/domain/**/*.py`, `backend/app/application/**/*.py` | [business-rules.instructions.md](./instructions/business-rules.instructions.md) | Manufacturing domain, BOMs, work orders, inventory |
| **Everywhere** (cross-cutting) | [security.instructions.md](./instructions/security.instructions.md) | Multi-tenancy filtering, RBAC, passwords, audit logging |

---

## Quick Start

**MedTrack** is a multi-tenant manufacturing ERP with strict architecture and data isolation requirements:

| Aspect | Detail |
|--------|--------|
| **Backend** | FastAPI 0.111.0 + SQLAlchemy 2.0.30 async + PostgreSQL 15+ |
| **Frontend** | React 18.3.1 + TypeScript strict mode + Vite 5.4.2 |
| **Architecture** | DDD + CQRS (4 layers: domain, application, infrastructure, interfaces) |
| **Multi-Tenancy** | **Non-negotiable:** Every query must filter by `tenant_id` from JWT |
| **Constraints** | Soft deletes, type safety, async-first, RBAC, audit logging |

**Before suggesting code:** 
1. **Inspect existing patterns** in the same bounded context
2. **Select path-specific file** from the table above for detailed guidance
3. **Follow examples** (✅ CORRECT vs. ❌ WRONG)

---

## Critical Cross-Cutting Rules

### ⚠️ Rule 1: Multi-Tenancy Filtering (Non-Negotiable)

**Every database query must include `WHERE tenant_id = ...`**

```python
# ✅ CORRECT: Always filter by tenant_id
stmt = select(Material).where(
    Material.tenant_id == get_tenant_id(),  # ← MANDATORY
    Material.is_deleted == False            # ← MANDATORY
)

# ❌ WRONG: Missing tenant_id — SECURITY VULNERABILITY
stmt = select(Material).where(Material.status == "ACTIVE")
# Exposes other tenants' data
```

**See:** [security.instructions.md](./instructions/security.instructions.md) § Multi-Tenancy Filtering

---

### ⚠️ Rule 2: Soft Delete Checks (Non-Negotiable)

**All SELECT queries must include `is_deleted = False`**

```python
# ✅ CORRECT: Check soft deletes
where(Material.tenant_id == tenant_id, Material.is_deleted == False)

# ❌ WRONG: Missing soft delete check
where(Material.tenant_id == tenant_id)  # Returns deleted records
```

**See:** [security.instructions.md](./instructions/security.instructions.md) § Soft Delete Checks

---

### ⚠️ Rule 3: Type Safety (Python + TypeScript)

**All code must have full type hints. No `any` types.**

```python
# Python: Full type hints required
async def handle_create_material(self, cmd: CreateMaterialCommand) -> UUID:
    ...
```

```typescript
// TypeScript: No 'any' types
interface Props { tenantId: string; }
export const Component: React.FC<Props> = ({ tenantId }) => { ... }
```

**See:** [backend.instructions.md](./instructions/backend.instructions.md), [frontend.instructions.md](./instructions/frontend.instructions.md)

---

### ⚠️ Rule 4: Never Log Secrets

**Never log passwords, tokens, API keys, PII**

```python
# ✅ CORRECT: No sensitive data
logger.info("User created", extra={"user_id": str(user_id)})

# ❌ WRONG: Logging secrets
logger.info(f"JWT token: {jwt_token}")  # NEVER
logger.error(f"Password: {password}")   # NEVER
```

**See:** [security.instructions.md](./instructions/security.instructions.md) § Logging Security

---

## Manufacturing Business Rules

**See:** [business-rules.instructions.md](./instructions/business-rules.instructions.md)

Key rules when suggesting code for manufacturing operations:

| Rule | Enforce In |
|------|-----------|
| **BOMs versioned** | Only create new version when changing active BOM |
| **WO status linear** | DRAFT → RELEASED → STARTED → COMPLETED → CLOSED (no backtracking) |
| **Materials reserved on release** | Inventory reserved when WO status = RELEASED |
| **Materials consumed on completion** | Inventory decreased when WO status = COMPLETED |
| **No duplicate BOM lines** | Same material_id cannot appear twice in BOM |
| **GRN qty ≤ PO qty** | GRN cannot exceed related PO quantity |
| **Soft deletes only** | Never suggest hard deletes; use is_deleted flag |

---

## When to Accept Copilot Suggestions

✅ **Accept if the suggestion:**
- Includes multi-tenant filtering (`tenant_id` in WHERE clause)
- Includes soft delete check (`is_deleted == False` in WHERE clause)
- Uses async/await for all I/O
- Has full type hints (Python + TypeScript)
- Respects DDD layer boundaries
- Follows CQRS pattern (if applicable)
- Includes error handling (try-catch, logging)
- Matches existing code style in the module
- Doesn't refactor unrelated code

❌ **Reject if the suggestion:**
- Missing tenant_id filtering on queries
- Missing soft delete check on queries
- Uses synchronous I/O in async context
- Has missing or loose type hints
- Breaks DDD layer separation
- Mixes command and query logic
- Has silent error handling (bare except)
- Introduces new patterns not used elsewhere
- Refactors unrelated code or modules
- Hardcodes secrets or configuration

---

## Complete Reference Documentation

**For deeper guidance by topic:**

| Topic | File | Location |
|-------|------|----------|
| **Backend Architecture & Patterns** | backend.instructions.md | ./instructions/backend.instructions.md |
| **Frontend Architecture & Patterns** | frontend.instructions.md | ./instructions/frontend.instructions.md |
| **Database & Migrations** | database.instructions.md | ./instructions/database.instructions.md |
| **Manufacturing Business Rules** | business-rules.instructions.md | ./instructions/business-rules.instructions.md |
| **Security & Multi-Tenancy** | security.instructions.md | ./instructions/security.instructions.md |
| **Full Authority** | AGENTS.md | ../AGENTS.md |
| **Architecture Deep Dive** | SYSTEM_ARCHITECTURE.md | ../docs/ai-guidelines/SYSTEM_ARCHITECTURE.md |
| **Python Patterns** | BACKEND_STANDARDS.md | ../docs/ai-guidelines/BACKEND_STANDARDS.md |
| **React Patterns** | FRONTEND_STANDARDS.md | ../docs/ai-guidelines/FRONTEND_STANDARDS.md |
| **Database & Migrations** | DATABASE_STANDARDS.md | ../docs/ai-guidelines/DATABASE_STANDARDS.md |
| **Security Implementation** | SECURITY_AND_MULTITENANCY.md | ../docs/ai-guidelines/SECURITY_AND_MULTITENANCY.md |
| **Business Rules** | MANUFACTURING_BUSINESS_RULES.md | ../docs/ai-guidelines/MANUFACTURING_BUSINESS_RULES.md |

---

## Summary Checklist

**For every Copilot code suggestion, verify:**
- [ ] Multi-tenant filtering present (`tenant_id` in WHERE)
- [ ] Soft delete check present (`is_deleted = False` in WHERE)
- [ ] Async/await used for all I/O
- [ ] Full type hints (Python + TypeScript)
- [ ] DDD layers respected
- [ ] CQRS pattern followed (if applicable)
- [ ] Error handling explicit (no silent failures)
- [ ] No unrelated refactoring
- [ ] Matches existing code style
- [ ] Manufacturing business rules enforced

**If all checks pass:** ✅ Accept the suggestion  
**If any check fails:** ❌ Reject and ask for correction

---

**Last Updated:** November 9, 2026  
**Status:** Production Ready  
**Questions?** See [AGENTS.md](../AGENTS.md)
