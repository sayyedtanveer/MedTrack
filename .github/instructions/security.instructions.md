---
applyTo: |
  **/*
---

# Security and Multi-Tenancy Instructions

**File:** `.github/instructions/security.instructions.md`  
**Scope:** Applies to all files  
**Reference:** [AGENTS.md](../../AGENTS.md) § 13-14 (Auth, Multi-Tenancy, Security)  
**Updated:** November 9, 2026

---

## Critical Rules (Override Everything Else)

These rules supersede all other instructions and must never be violated:

1. **Every query filters by `tenant_id`** — No exceptions
2. **Tenant extracted from JWT only** — Never from request parameters
3. **Soft deletes checked in all queries** — `is_deleted = false`
4. **Passwords hashed with bcrypt** — Minimum 12 characters, ≥12 salt rounds
5. **No secrets in logs** — Never log passwords, tokens, API keys, PII
6. **Parameterized queries only** — No string interpolation (SQLAlchemy prevents this)
7. **RBAC enforced on all endpoints** — Every route has permission check

---

## Multi-Tenancy Filtering (Non-Negotiable)

**Every database query MUST include tenant_id filter:**

### Backend (Python)

```python
# ✅ CORRECT: Tenant filter in every query
from backend.app.infrastructure.context import get_tenant_id

async def list_materials(self) -> List[Material]:
    tenant_id = get_tenant_id()  # ← From JWT via middleware
    
    stmt = select(MaterialModel).where(
        MaterialModel.tenant_id == tenant_id,      # ← MANDATORY
        MaterialModel.is_deleted == False          # ← MANDATORY
    )
    result = await session.execute(stmt)
    return [Material.from_model(m) for m in result.scalars().all()]

# ❌ WRONG: Missing tenant_id — SECURITY VIOLATION
async def list_materials(self) -> List[Material]:
    stmt = select(MaterialModel).where(MaterialModel.status == "ACTIVE")
    # Exposes other tenants' data
    result = await session.execute(stmt)
    return [Material.from_model(m) for m in result.scalars().all()]
```

### Frontend (TypeScript)

```typescript
// ✅ CORRECT: Include tenant in API request
const useMaterials = (tenantId: string) => {
  const [materials, setMaterials] = React.useState<Material[]>([]);
  
  React.useEffect(() => {
    const fetch = async () => {
      // tenantId included in request (backend validates from JWT)
      const data = await api.materials.list({ tenantId });
      setMaterials(data);
    };
    fetch();
  }, [tenantId]);
  
  return materials;
};
```

---

## JWT Token Structure and Extraction

**Token contains tenant_id; extracted by middleware:**

```python
# ✅ CORRECT: Token structure
# JWT payload (signed with secret key)
{
  "sub": "user_id_uuid",
  "tid": "tenant_id_uuid",        # ← Tenant ID
  "role": "MANAGER",
  "exp": 1234567890,
  "iat": 1234567890
}

# Middleware extracts and sets context
from contextlib import ContextVar

tenant_context: ContextVar[UUID] = ContextVar('tenant_id')

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
            tenant_id = UUID(payload.get("tid"))
            tenant_context.set(tenant_id)  # ← Set for this request
        except:
            raise HTTPException(status_code=401)
        return await call_next(request)

# Handler retrieves tenant_id
def get_tenant_id() -> UUID:
    return tenant_context.get()
```

---

## Password Security

**Mandatory requirements:**

```python
# ✅ CORRECT: Password hashing
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")
    return pwd_context.hash(password)  # Automatically uses ≥12 salt rounds

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)

# User creation
async def handle_create_user(self, cmd: CreateUserCommand) -> UUID:
    if len(cmd.password) < 12:
        raise PasswordTooShortError()
    
    user = User(
        email=cmd.email,
        password_hash=hash_password(cmd.password),  # ← Never store plaintext
        role=cmd.role
    )
    
    user_id = await self.repo.save(user)
    logger.info("User created", extra={"user_id": str(user_id)})  # No password
    return user_id

# ❌ WRONG: Plaintext password
user.password = cmd.password  # NEVER — data breach risk

# ❌ WRONG: Weak password check
if len(cmd.password) < 8:  # Too short
    raise PasswordTooShortError()

# ❌ WRONG: Logging password
logger.info("User login", extra={"password": cmd.password})  # NEVER
```

---

## RBAC (Role-Based Access Control) Enforcement

**Every endpoint must check permissions:**

```python
# ✅ CORRECT: RBAC on endpoint
@router.post("/materials", status_code=201)
async def create_material(
    request: Request,
    cmd: CreateMaterialRequest,
    handler: BOMHandlers = Depends(get_bom_handlers)
) -> MaterialResponse:
    user = await get_current_user(request)
    
    # Check permission
    tenant_id = get_tenant_id()
    has_permission = await permission_service.check(
        user_id=user.id,
        tenant_id=tenant_id,
        resource="materials",
        action="create"
    )
    
    if not has_permission:
        logger.warning(
            "Access denied",
            extra={"user_id": str(user.id), "action": "create_material"}
        )
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Execute command
    material_id = await handler.handle_create_material(cmd)
    return MaterialResponse(id=material_id)

# ❌ WRONG: No permission check
@router.post("/materials")
async def create_material(cmd: CreateMaterialRequest):
    # Anyone can create material
    return await handler.handle_create_material(cmd)
```

---

## Logging Security

**Never log sensitive data:**

```python
# ✅ CORRECT: Safe logging
logger.info(
    "User authenticated",
    extra={
        "user_id": str(user.id),
        "tenant_id": str(tenant_id),
        "timestamp": datetime.utcnow().isoformat()
        # No password, token, or API key
    }
)

# ❌ WRONG: Logging secrets
logger.info(f"Password reset token: {token}")  # NEVER
logger.error(f"API key: {api_key}")            # NEVER
logger.debug(f"JWT: {jwt_token}")              # NEVER

# ✅ CORRECT: Mask sensitive data in errors
try:
    result = process_payment(card_number=cmd.card_number)
except Exception as e:
    logger.error(
        "Payment processing failed",
        extra={
            "error": str(e),
            "card_number": "****" + cmd.card_number[-4:],  # Masked
            "amount": cmd.amount
        }
    )
```

---

## SQL Injection Prevention (SQLAlchemy)

**Use parameterized queries; never string interpolation:**

```python
# ✅ CORRECT: Parameterized query (SQLAlchemy handles escaping)
stmt = select(MaterialModel).where(
    MaterialModel.tenant_id == tenant_id,
    MaterialModel.code == code
)
result = await session.execute(stmt)

# ✅ CORRECT: Using bind parameters
stmt = select(MaterialModel).where(
    MaterialModel.code.like(f"%{search_term}%")  # SQLAlchemy escapes
)

# ❌ WRONG: String interpolation (never do this)
code_value = "'; DROP TABLE materials; --"
query = f"SELECT * FROM materials WHERE code = '{code_value}'"
# Vulnerable to SQL injection

# ❌ WRONG: f-string without ORM
query = f"SELECT * FROM materials WHERE code = '{code}'"
# SQLAlchemy prevents this, but principle is critical
```

---

## HTTP Security Headers

**Required headers on all responses:**

```python
# ✅ CORRECT: Security headers middleware
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # HTTPS enforcement
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'"
        
        # Prevent XSS
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        return response
```

---

## Input Validation

**All inputs validated via Pydantic:**

```python
# ✅ CORRECT: Request validation
from pydantic import BaseModel, Field, EmailStr, validator

class CreateUserRequest(BaseModel):
    email: EmailStr  # ← Validates email format
    password: str = Field(min_length=12, max_length=128)
    role: str = Field(pattern="^(ADMIN|MANAGER|OPERATOR)$")  # Enum-like validation
    
    @validator("password")
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        return v

# Pydantic automatically rejects invalid input
# Invalid request returns 422 Unprocessable Entity
```

---

## CORS Configuration

**Never use wildcard; whitelist specific origins:**

```python
# ✅ CORRECT: CORS with whitelist
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://medtrack.example.com",
        "https://app.medtrack.example.com"
    ],  # ← Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600
)

# ❌ WRONG: Wildcard CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # NEVER — accepts all origins
    allow_credentials=True
)
```

---

## Rate Limiting

**Applied to all endpoints:**

```python
# ✅ CORRECT: Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/materials")
@limiter.limit("100/minute")  # ← 100 requests per minute
async def list_materials():
    return await handler.handle_list_materials()

# ❌ WRONG: No rate limiting
@app.get("/materials")
async def list_materials():
    # Vulnerable to brute force attacks
    return await handler.handle_list_materials()
```

---

## Soft Delete Checks

**Every query must include soft delete filter:**

```python
# ✅ CORRECT: Soft delete check
stmt = select(WorkOrderModel).where(
    WorkOrderModel.tenant_id == tenant_id,
    WorkOrderModel.is_deleted == False  # ← MANDATORY
)

# ❌ WRONG: Returns deleted records
stmt = select(WorkOrderModel).where(
    WorkOrderModel.tenant_id == tenant_id
)
# Exposes soft-deleted data
```

---

## Audit Logging Requirements

**Every mutation must be logged:**

```python
# ✅ CORRECT: Comprehensive audit logging
async def handle_update_material(self, cmd: UpdateMaterialCommand) -> None:
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    material = await self.repo.get_by_id(tenant_id, cmd.material_id)
    
    # Log before change
    logger.info(
        "Material update initiated",
        extra={
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "material_id": str(material.id),
            "previous_name": material.name
        }
    )
    
    # Apply change
    material.name = cmd.name
    material.code = cmd.code
    
    # Save
    await self.repo.save(material)
    
    # Log after change
    logger.info(
        "Material updated",
        extra={
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "material_id": str(material.id),
            "new_name": material.name
        }
    )
```

---

## Tenant Isolation Verification Test

**Every feature must include isolation test:**

```python
# ✅ CORRECT: Isolation test
@pytest.mark.asyncio
async def test_material_isolation_between_tenants(session: AsyncSession):
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create material for tenant1
    mat1 = MaterialModel(
        tenant_id=tenant1_id,
        code="MAT-001",
        name="Steel",
        created_by=user_id,
        updated_by=user_id
    )
    session.add(mat1)
    await session.commit()
    
    # Attempt to access from tenant2
    repo = MaterialRepository(session)
    result = await repo.get_by_id(tenant2_id, mat1.id)
    
    # Must NOT return material
    assert result is None, "Tenant2 can see Tenant1's material — isolation broken!"
```

---

## Common Security Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Missing tenant filter | Data breach | Add `tenant_id` to every WHERE |
| Plaintext password | Account takeover | Use bcrypt with 12+ salt rounds |
| Logging secrets | Information disclosure | Never log passwords/tokens/keys |
| No RBAC check | Unauthorized access | Check permissions on every endpoint |
| String interpolation | SQL injection | Use parameterized queries (ORM does this) |
| Hard delete | Audit trail loss | Use soft deletes only |
| Wildcard CORS | XSS/CSRF | Whitelist specific origins |
| No rate limiting | Brute force / DoS | Apply rate limits to all endpoints |
| No input validation | Injection attacks | Use Pydantic validators |
| Returning entity | Oversharing data | Return DTO with selective fields |

---

## Do's and Don'ts

| Do | Don't |
|----|-------|
| ✅ Filter by tenant_id always | ❌ Query without tenant filter |
| ✅ Extract tenant from JWT | ❌ Get tenant from request params |
| ✅ Hash passwords with bcrypt | ❌ Store plaintext passwords |
| ✅ Log with context, no secrets | ❌ Log sensitive data |
| ✅ Check RBAC on every endpoint | ❌ Skip permission checks |
| ✅ Use parameterized queries | ❌ String interpolation in queries |
| ✅ Soft delete only | ❌ Hard delete data |
| ✅ Whitelist CORS origins | ❌ Allow wildcard CORS |
| ✅ Apply rate limiting | ❌ No rate limiting |
| ✅ Validate all input | ❌ Trust user input |

---

## Reference

- **Security Details:** [SECURITY_AND_MULTITENANCY.md](../../docs/ai-guidelines/SECURITY_AND_MULTITENANCY.md)
- **Auth Implementation:** `backend/app/infrastructure/security/`
- **Middleware Stack:** `backend/app/interfaces/api/v1/middleware/`
- **Role Definitions:** `backend/app/domain/tenant/enums.py`

---

**Status:** Production Ready  
**Last Updated:** November 9, 2026
