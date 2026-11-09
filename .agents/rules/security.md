---
trigger: always_on
description: "Critical security, multi-tenancy, and authorization rules for MedTrack"
---

# MedTrack Security & Multi-Tenancy (CRITICAL)

**Canonical Source:** AGENTS.md §14 and docs/ai-guidelines/SECURITY_AND_MULTITENANCY.md

## Multi-Tenancy: MANDATORY RULE

**Every database query MUST filter by `tenant_id` from JWT `tid` claim:**

```python
# ✅ CORRECT: Tenant filter + soft delete check
stmt = select(Material).where(
    Material.tenant_id == get_tenant_id(),  # From JWT context, MANDATORY
    Material.is_deleted == False            # Soft delete check
)

# ❌ WRONG: Missing tenant filter — SECURITY VULNERABILITY
stmt = select(Material).where(Material.status == "ACTIVE")
# Could expose other tenants' data
```

**Rules:**
- Tenant extracted from JWT `tid` claim ONLY, never from request parameters
- Every SELECT query includes `WHERE tenant_id = ...` filter
- Every INSERT/UPDATE sets `tenant_id` from context (not from input)
- All logs include `tenant_id` in structured context
- Tests verify tenant isolation (tenant1 cannot see tenant2's data)
- Repository methods explicitly accept `tenant_id` parameter

## Authentication & Authorization

**JWT Token Structure:**
```json
{
  "sub": "user_id_uuid",
  "tid": "tenant_id_uuid",      // ← Extract this for tenant scope
  "role": "MANAGER",
  "exp": 1234567890
}
```

**Password Security:**
- Minimum 12 characters
- Bcrypt with ≥12 salt rounds
- Never store plaintext, never log passwords

**RBAC Enforcement:**
- 13 roles: ADMIN, TENANT_ADMIN, MANAGER, OPERATOR, STOREKEEPER, PLANNER, QC, SALES, WORKER, CLIENT, SUPPLIER, VIEWER
- Permission audit logging: log all 403 denials
- Middleware: TenantMiddleware → RBACPermissionAuditMiddleware → route handler

## Soft Deletes (NON-NEGOTIABLE)

**Delete Pattern:**
```python
entity.is_deleted = True
entity.deleted_at = datetime.utcnow()
await repo.save(entity)
```

**Query Pattern - ALWAYS CHECK:**
```python
WHERE is_deleted = False  # MANDATORY on every SELECT
```

**Never:**
- Hard delete data
- Query without `is_deleted` filter
- Allow cross-tenant data access

## Audit Logging

**Structured Logging Required:**
```python
logger.info(
    "Material created",
    extra={
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "action": "CREATE",
        "correlation_id": correlation_id
    }
)
```

**Never log:**
- Passwords or plaintext credentials
- API keys or tokens
- Sensitive payment info
- Personal identification

