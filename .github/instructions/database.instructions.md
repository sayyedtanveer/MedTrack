---
applyTo: |
  alembic/**/*.py
  backend/app/infrastructure/persistence/**/*.py
---

# Database and Migration Instructions

**File:** `.github/instructions/database.instructions.md`  
**Scope:** Alembic migrations and ORM models  
**Reference:** [AGENTS.md](../../AGENTS.md) § 12 (Database and Migration Rules)  
**Updated:** November 9, 2026

---

## Quick Rules

1. **Soft deletes only** — Never hard delete; mark `is_deleted = True`
2. **Multi-tenancy enforcement** — Every table has `tenant_id` FK
3. **Audit columns required** — `created_by`, `updated_by`, `created_at`, `updated_at`
4. **UUID primary keys** — Use `gen_random_uuid()`
5. **Alembic migrations** — Commit all schema changes as migrations
6. **Every query filters** — `tenant_id` AND `is_deleted = False` (no exceptions)
7. **Async repositories** — All I/O uses `await`, connection pooling

---

## Schema Standards

**Every table must include these columns:**

```python
# ✅ CORRECT: SQLAlchemy model with all required columns
from sqlalchemy import Column, UUID, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from datetime import datetime

class MaterialModel(Base):
    __tablename__ = "materials"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Multi-tenancy (REQUIRED)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Business columns
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_id: Mapped[UUID] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    # Soft delete (REQUIRED)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Audit trail (REQUIRED)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    updated_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )

# ❌ WRONG: Missing multi-tenancy, soft deletes, audit
class MaterialModel(Base):
    __tablename__ = "materials"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    # Missing: tenant_id, is_deleted, deleted_at, created_by, updated_by
```

---

## Indexes Required

**Critical indexes for performance and multi-tenancy:**

```python
# ✅ CORRECT: Required indexes
class MaterialModel(Base):
    __tablename__ = "materials"
    
    # ... columns ...
    
    __table_args__ = (
        # Multi-tenancy filter index (MANDATORY)
        Index("ix_materials_tenant_is_deleted", "tenant_id", "is_deleted"),
        
        # Status/state filter index
        Index("ix_materials_status", "status", postgresql_where=Column("is_deleted") == False),
        
        # Timestamp index for sorting
        Index("ix_materials_created_at", Column("created_at").desc()),
        
        # Unique code per tenant (within non-deleted records)
        UniqueConstraint(
            "tenant_id", "code",
            name="uq_materials_code_per_tenant",
            postgresql_where=Column("is_deleted") == False
        ),
    )
```

---

## Migration Workflow

**Always use Alembic for schema changes:**

```bash
# 1. Modify SQLAlchemy model in backend/app/infrastructure/persistence/models/
#    (e.g., add new column, new table, change constraint)

# 2. Generate migration
alembic revision --autogenerate -m "add_priority_to_sales_orders"
#    → Creates: alembic/versions/20261109_HHMM_add_priority_to_sales_orders.py

# 3. Review generated migration (check it's correct)
#    → Edit if needed (add/remove operations)

# 4. Test locally
alembic upgrade head
#    → Runs all pending migrations

# 5. Test downgrade (if applicable)
alembic downgrade -1
alembic upgrade head

# 6. Commit migration with code
git add alembic/versions/20261109_HHMM_add_priority_to_sales_orders.py
git add backend/app/infrastructure/persistence/models/*.py
git commit -m "TASK-123: Add priority to sales orders"
```

**Never modify existing migrations** (except development). If a migration is wrong:
1. Create new migration to fix (don't edit committed migration)
2. Document why in commit message

---

## Query Requirements (Non-Negotiable)

**Every SELECT query must include multi-tenancy and soft delete filters:**

```python
# ✅ CORRECT: All filters included
from backend.app.infrastructure.context import get_tenant_id

async def list_materials(self) -> List[Material]:
    tenant_id = get_tenant_id()  # From JWT context
    
    stmt = select(MaterialModel).where(
        MaterialModel.tenant_id == tenant_id,      # ← MANDATORY
        MaterialModel.is_deleted == False          # ← MANDATORY
    ).order_by(MaterialModel.created_at.desc())
    
    result = await session.execute(stmt)
    return [Material.from_model(m) for m in result.scalars().all()]

# ❌ WRONG: Missing tenant filter — SECURITY VIOLATION
async def list_materials(self) -> List[Material]:
    stmt = select(MaterialModel).where(MaterialModel.status == "ACTIVE")
    # Could expose other tenants' data
    result = await session.execute(stmt)
    return [Material.from_model(m) for m in result.scalars().all()]

# ❌ WRONG: Missing soft delete check — RETURNS DELETED RECORDS
async def list_materials(self) -> List[Material]:
    tenant_id = get_tenant_id()
    stmt = select(MaterialModel).where(MaterialModel.tenant_id == tenant_id)
    # Returns deleted records
    result = await session.execute(stmt)
    return [Material.from_model(m) for m in result.scalars().all()]
```

---

## Soft Delete Pattern

**Mark as deleted; never hard delete:**

```python
# ✅ CORRECT: Soft delete
async def delete_material(self, tenant_id: UUID, material_id: UUID) -> None:
    stmt = select(MaterialModel).where(
        MaterialModel.tenant_id == tenant_id,
        MaterialModel.id == material_id,
        MaterialModel.is_deleted == False
    )
    result = await session.execute(stmt)
    material = result.scalars().first()
    
    if not material:
        raise MaterialNotFoundError(material_id)
    
    material.is_deleted = True
    material.deleted_at = datetime.utcnow()
    await session.commit()

# ❌ WRONG: Hard delete
async def delete_material(self, material_id: UUID) -> None:
    stmt = delete(MaterialModel).where(MaterialModel.id == material_id)
    await session.execute(stmt)
    await session.commit()
    # Data permanently lost; audit trail destroyed
```

---

## Repository Pattern

**Async repositories with type safety:**

```python
# ✅ CORRECT: Async repository
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

class MaterialRepository(IMaterialRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, tenant_id: UUID, material_id: UUID) -> Optional[Material]:
        """Get material by ID with multi-tenancy and soft delete checks."""
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.id == material_id,
            MaterialModel.is_deleted == False
        )
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return Material.from_model(model) if model else None
    
    async def list_by_tenant(self, tenant_id: UUID, limit: int = 100, offset: int = 0) -> List[Material]:
        """List materials for tenant with pagination."""
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted == False
        ).order_by(MaterialModel.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.session.execute(stmt)
        return [Material.from_model(m) for m in result.scalars().all()]
    
    async def create(self, tenant_id: UUID, material: Material, user_id: UUID) -> UUID:
        """Create material with audit trail."""
        model = MaterialModel(
            tenant_id=tenant_id,
            code=material.code,
            name=material.name,
            created_by=user_id,
            updated_by=user_id
        )
        self.session.add(model)
        await self.session.flush()  # Generate ID
        return model.id
    
    async def save(self, material: Material, user_id: UUID) -> None:
        """Update material with audit trail."""
        model = await self.session.get(MaterialModel, material.id)
        if not model:
            raise MaterialNotFoundError(material.id)
        
        model.name = material.name
        model.updated_by = user_id
        model.updated_at = datetime.utcnow()
        await self.session.commit()
    
    async def delete(self, tenant_id: UUID, material_id: UUID, user_id: UUID) -> None:
        """Soft delete material."""
        model = await self.session.get(MaterialModel, material_id)
        if not model or model.tenant_id != tenant_id:
            raise MaterialNotFoundError(material_id)
        
        model.is_deleted = True
        model.deleted_at = datetime.utcnow()
        model.updated_by = user_id
        await self.session.commit()
```

---

## Constraints and Validation

**Enforce data integrity at database level:**

```python
# ✅ CORRECT: Constraints
class SalesOrderModel(Base):
    __tablename__ = "sales_orders"
    
    # ... columns ...
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="DRAFT"
    )
    
    __table_args__ = (
        # CHECK constraint for enum status
        CheckConstraint(
            "status IN ('DRAFT', 'APPROVED', 'MANUFACTURING', 'DELIVERED', 'CANCELLED')",
            name="ck_sales_orders_status"
        ),
        
        # Unique identifier per tenant
        UniqueConstraint(
            "tenant_id", "order_number",
            name="uq_sales_orders_number_per_tenant",
            postgresql_where=Column("is_deleted") == False
        ),
    )
```

---

## Foreign Key Constraints

**All FKs should specify ON DELETE behavior:**

```python
# ✅ CORRECT: Foreign key with ON DELETE policy
class BOMLinesModel(Base):
    __tablename__ = "bom_lines"
    
    material_id: Mapped[UUID] = mapped_column(
        ForeignKey("materials.id", ondelete="RESTRICT"),  # ← Prevent deletion if used
        nullable=False
    )
    
    bom_id: Mapped[UUID] = mapped_column(
        ForeignKey("boms.id", ondelete="CASCADE"),  # ← Delete lines when BOM deleted
        nullable=False
    )

# ❌ WRONG: No ON DELETE policy
material_id: Mapped[UUID] = mapped_column(
    ForeignKey("materials.id"),  # Default is RESTRICT; be explicit
    nullable=False
)
```

---

## Testing Migrations

**Verify migrations work locally:**

```bash
# Create test database
createdb medtrack_test

# Test upgrade
DATABASE_URL=postgresql://user:pass@localhost/medtrack_test alembic upgrade head

# Test downgrade (if applicable)
DATABASE_URL=postgresql://user:pass@localhost/medtrack_test alembic downgrade -1

# Clean up
dropdb medtrack_test
```

---

## Multi-Tenant Isolation Verification

**Test that queries don't leak data:**

```python
# ✅ CORRECT: Isolation test
@pytest.mark.asyncio
async def test_material_isolation_between_tenants(session: AsyncSession):
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create materials for each tenant
    mat1 = MaterialModel(
        tenant_id=tenant1_id,
        code="MAT-001",
        name="Steel",
        created_by=user_id,
        updated_by=user_id
    )
    mat2 = MaterialModel(
        tenant_id=tenant2_id,
        code="MAT-002",
        name="Aluminum",
        created_by=user_id,
        updated_by=user_id
    )
    session.add_all([mat1, mat2])
    await session.commit()
    
    # Verify tenant1 cannot see tenant2's material
    repo = MaterialRepository(session)
    result = await repo.get_by_id(tenant1_id, mat2.id)
    assert result is None  # ✅ Isolation verified
    
    # Verify tenant1 sees only their material
    materials = await repo.list_by_tenant(tenant1_id)
    assert len(materials) == 1
    assert materials[0].id == mat1.id
```

---

## Handling Migration Conflicts

**When multiple developers create migrations:**

```bash
# Show all current heads (indicates conflict)
alembic heads
# Output:
#   WARNING: Multiple heads encountered: [head1, head2]

# Merge heads into single path
alembic merge heads -m "merge migrations from development branches"
# Creates: alembic/versions/20261109_HHMM_merge_migrations.py

# Upgrade to merged head
alembic upgrade head

# Commit the merge migration
git add alembic/versions/20261109_HHMM_merge_migrations.py
git commit -m "Merge migration heads"
```

---

## Migration Guidelines

| Action | Guideline |
|--------|-----------|
| **Add column** | Use `nullable=True` initially, populate data, then `nullable=False` in separate migration |
| **Drop column** | Create migration, verify nothing breaks, then commit |
| **Rename column** | Use `op.alter_column()` explicitly (autogenerate may miss this) |
| **Add constraint** | Use `op.create_check_constraint()` with clear naming |
| **Add index** | Include in table definition or via `op.create_index()` |
| **Foreign key** | Always specify `ondelete` behavior explicitly |

---

## Do's and Don'ts

| Do | Don't |
|----|-------|
| ✅ Use soft deletes everywhere | ❌ Hard delete data |
| ✅ Filter by `tenant_id` + `is_deleted` | ❌ Query without filters |
| ✅ Commit all migrations | ❌ Apply migrations without committing |
| ✅ Test migrations locally | ❌ Deploy untested migrations |
| ✅ Use async repositories | ❌ Use synchronous database calls |
| ✅ Specify ON DELETE behavior | ❌ Rely on default FK behavior |
| ✅ Add multi-tenant indexes | ❌ Query performance suffers |
| ✅ Include audit columns | ❌ Skip created_by, updated_by |

---

## Reference

- **Full Database Guide:** [DATABASE_STANDARDS.md](../../docs/ai-guidelines/DATABASE_STANDARDS.md)
- **Database Schema:** `db_scripts/medtrack_schema_latest.sql`
- **ORM Models:** `backend/app/infrastructure/persistence/models/`
- **Migrations:** `alembic/versions/`

---

**Status:** Production Ready  
**Last Updated:** November 9, 2026
