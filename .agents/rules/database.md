---
trigger: glob
globs: "alembic/**/*.py, backend/app/infrastructure/persistence/**/*.py"
description: "Database and migration standards: PostgreSQL, Alembic migrations, soft deletes, multi-tenancy"
---

# Database & Migration Standards

**Reference:** See `docs/ai-guidelines/DATABASE_STANDARDS.md` for comprehensive details

## Schema Requirements (EVERY TABLE)

```sql
CREATE TABLE materials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  code VARCHAR(255) NOT NULL,
  is_deleted BOOLEAN NOT NULL DEFAULT false,
  deleted_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_by UUID NOT NULL REFERENCES users(id),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_by UUID NOT NULL REFERENCES users(id),
  -- domain fields
  UNIQUE(tenant_id, code) -- unique per tenant
);

-- Required indexes
CREATE INDEX idx_materials_tenant_soft_delete ON materials(tenant_id, is_deleted);
CREATE INDEX idx_materials_created_at ON materials(created_at DESC);
```

**Every table MUST include:**
- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `tenant_id UUID NOT NULL` (FK to tenants.id, ON DELETE RESTRICT)
- `is_deleted BOOLEAN NOT NULL DEFAULT false`
- `deleted_at TIMESTAMP NULL`
- `created_at TIMESTAMP NOT NULL DEFAULT NOW()`
- `created_by UUID NOT NULL` (FK to users.id)
- `updated_at TIMESTAMP NOT NULL DEFAULT NOW()`
- `updated_by UUID NOT NULL` (FK to users.id)

## Soft Deletes Pattern (MANDATORY)

```python
# Never hard delete
entity.is_deleted = True
entity.deleted_at = datetime.utcnow()
await repo.save(entity)
```

```python
# ALWAYS filter on queries
stmt = select(Material).where(
    Material.tenant_id == tenant_id,
    Material.is_deleted == False  # ← MANDATORY
)
```

## Repository Pattern (Async)

```python
class MaterialRepository(IMaterialRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, tenant_id: UUID, material_id: UUID) -> Material | None:
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.id == material_id,
            MaterialModel.is_deleted == False
        )
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return Material.from_model(model) if model else None
    
    async def list_by_tenant(self, tenant_id: UUID) -> List[Material]:
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted == False
        ).order_by(MaterialModel.created_at.desc())
        result = await self.session.execute(stmt)
        return [Material.from_model(m) for m in result.scalars().all()]
```

## Alembic Migrations

**Workflow:**
1. Modify SQLAlchemy model in `backend/app/infrastructure/persistence/models/`
2. `alembic revision --autogenerate -m "description"`
3. Review generated migration file
4. `alembic upgrade head` (test locally)
5. Commit migration with code changes

**Multi-Developer Conflicts:**
```bash
alembic heads              # Show all heads
alembic merge heads -m "merge description"
alembic upgrade head
```

**DO NOT:**
- Hard delete columns (use nullable flag instead)
- Drop or rename columns without expand-and-contract pattern
- Commit migrations without testing locally
- Use non-async SQLAlchemy operations

## Query Standards

```python
# ✅ CORRECT: Complete query with tenant + soft delete + indexes
async def get_active_materials(self, tenant_id: UUID) -> List[Material]:
    stmt = select(MaterialModel).where(
        MaterialModel.tenant_id == tenant_id,        # Multi-tenancy
        MaterialModel.is_deleted == False,           # Soft delete
        MaterialModel.status == "ACTIVE"             # Business filter
    ).order_by(MaterialModel.created_at.desc()).limit(100)
    result = await self.session.execute(stmt)
    return [Material.from_model(m) for m in result.scalars().all()]

# ❌ WRONG: Missing tenant filter (security vulnerability)
stmt = select(Material).where(Material.status == "ACTIVE")

# ❌ WRONG: Missing soft delete check
stmt = select(Material).where(Material.tenant_id == tenant_id)
```

## Connection Pooling

**asyncpg handles pooling automatically:**
```python
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600    # Recycle connections hourly
)
```

## Indexing Strategy

**Required indexes on every table:**
- `(tenant_id, is_deleted)` — Filter by tenant and soft delete status
- `(status) WHERE is_deleted = false` — Status queries
- `(created_at DESC)` — Timestamp sorting
- Foreign key columns automatically indexed

