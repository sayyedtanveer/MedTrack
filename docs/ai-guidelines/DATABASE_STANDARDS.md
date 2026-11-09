# MedTrack Database Standards

**Version:** 1.0.0  
**Last Updated:** November 9, 2026  
**Database:** PostgreSQL 15+  
**ORM:** SQLAlchemy 2.0.30 (async)  
**Migrations:** Alembic 1.13.1

---

## Overview

MedTrack uses **PostgreSQL 15+** with **SQLAlchemy 2.0.30 async ORM** for all data persistence. The architecture enforces:

- ✅ **Async-first** database access (asyncpg driver)
- ✅ **Multi-tenancy** at database layer (tenant_id on every table)
- ✅ **Soft deletes** (is_deleted flag on all entities)
- ✅ **Audit trail** (created_by, updated_by, timestamps)
- ✅ **Repository pattern** (abstract interfaces, concrete implementations)
- ✅ **Unit of Work** for transaction management
- ✅ **Alembic migrations** for schema versioning

---

## PostgreSQL Configuration

### Connection Setup

**Location:** `backend/app/infrastructure/persistence/database.py`

```python
def create_engine(database_url: str) -> AsyncEngine:
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,           # Verify connections before use
        pool_size=10,                 # Connection pool size
        max_overflow=20,              # Max overflow beyond pool_size
    )
    instrument_database(engine)       # Add performance monitoring
    return engine
```

**Database URL Format:**
```
postgresql+asyncpg://user:password@host:5432/medtrack
```

**Key Settings:**
- **Driver:** asyncpg (async PostgreSQL driver)
- **Pool Size:** 10 connections (configurable)
- **Pool Pre-Ping:** Verify connections are alive before use
- **Echo:** False in production (SQL logging disabled)

### Performance Instrumentation

**Automatic Query Monitoring:**
- Query count per request
- SQL execution time
- Connection checkout timing
- N+1 detection (basic table extraction)
- Slow query logging (threshold: 100ms)

```python
SLOW_QUERY_THRESHOLD_MS = 100

# Queries exceeding threshold are logged to 'slow_queries' logger
# with prefix "[PHASE 1.5] Action Required: Run EXPLAIN ANALYZE on the above query!"
```

**Context Variables for Request Timing:**
```python
query_count_ctx         # Number of queries in request
sql_time_ctx            # Total SQL execution time (ms)
conn_checkout_time_ctx  # Connection pool checkout time (ms)
query_tables_ctx        # List of tables queried
```

---

## SQLAlchemy ORM Models

### Model Base Class

All models inherit from `Base`:

```python
from backend.app.infrastructure.persistence.database import Base

class MaterialModel(Base):
    __tablename__ = "materials"
    # ... columns
```

### Mandatory Table Columns (Every Table)

**Every model must include these columns:**

```python
# Primary Key (UUID)
id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True), 
    primary_key=True, 
    default=uuid.uuid4
)

# Multi-Tenancy (Foreign Key to tenants table)
tenant_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True), 
    nullable=False,
    index=True
)

# Soft Delete
is_deleted: Mapped[bool] = mapped_column(
    Boolean, 
    nullable=False, 
    default=False
)
deleted_at: Mapped[Optional[datetime]] = mapped_column(
    DateTime(timezone=True), 
    nullable=True
)

# Audit Trail
created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
    UUID(as_uuid=True), 
    ForeignKey("users.id", ondelete="SET NULL"), 
    nullable=True
)
updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
    UUID(as_uuid=True), 
    ForeignKey("users.id", ondelete="SET NULL"), 
    nullable=True
)

# Timestamps
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), 
    default=lambda: datetime.now(timezone.utc), 
    nullable=False
)
updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    default=lambda: datetime.now(timezone.utc),
    onupdate=lambda: datetime.now(timezone.utc),
    nullable=False
)
```

### Indexing Conventions

**Automatically indexed columns:**
- `tenant_id` — for multi-tenant filtering
- `is_deleted` — for soft delete queries
- Foreign keys — for relationship queries
- Status/state fields — for filtering by status

**Example from MaterialModel:**
```python
__table_args__ = (
    UniqueConstraint("tenant_id", "code", name="uq_material_tenant_code"),
    Index("ix_materials_tenant_id", "tenant_id"),
    Index("ix_materials_is_deleted", "is_deleted"),
)
```

**Index Naming Convention:**
- `ix_<table>_<column>` — Single column index
- `uq_<table>_<columns>` — Unique constraint
- Compound indexes: `ix_<table>_<col1>_<col2>`

### Type Safety with SQLAlchemy 2.0

**Use `Mapped[Type]` annotations:**

```python
# ✅ Correct: Full type mapping
from sqlalchemy.orm import Mapped

id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
name: Mapped[str] = mapped_column(String(255), nullable=False)
email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
is_active: Mapped[bool] = mapped_column(Boolean, default=True)

# ❌ Wrong: Old-style Column definitions
name = Column(String(255), nullable=False)  # No type annotation
```

### Relationships

Relationships use `relationship()` from SQLAlchemy:

```python
from sqlalchemy.orm import relationship

class MaterialModel(Base):
    __tablename__ = "materials"
    
    # Foreign key
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("material_categories.id")
    )
    
    # Relationship (lazy loading deferred for async)
    category: Mapped[Optional["MaterialCategoryModel"]] = relationship(
        "MaterialCategoryModel",
        back_populates="materials",
        lazy="select"  # Use "select" for explicit control
    )
```

---

## Async Database Sessions

### Session Factory Pattern

**Location:** `backend/app/infrastructure/persistence/database.py`

```python
def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,        # Objects stay accessible after commit
        autoflush=False,               # Explicit flush control
        autocommit=False,              # Explicit transaction control
    )
```

### Using Sessions

**Dependency Injection:**
```python
async def get_db(session_factory: async_sessionmaker[AsyncSession]):
    """FastAPI dependency — yields an AsyncSession per request."""
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
```

**In Handlers:**
```python
@router.post("/materials")
async def create_material(
    req: CreateMaterialRequest,
    session: AsyncSession = Depends(get_db),
) -> MaterialResponse:
    # Session is automatically closed after response
    pass
```

### Query Execution

**Always use `await` with I/O:**

```python
# ✅ Correct: Async query execution
stmt = select(MaterialModel).where(
    MaterialModel.tenant_id == tenant_id,
    MaterialModel.is_deleted == False
)
result = await session.execute(stmt)
materials = result.scalars().all()

# ❌ Wrong: Blocking call
materials = session.query(Material).all()  # Blocks event loop
```

### Transaction Management

**Explicit transaction control:**

```python
async def update_inventory_and_audit(
    session: AsyncSession,
    material_id: uuid.UUID,
    new_quantity: float,
    user_id: uuid.UUID,
):
    """Update material and create audit log in single transaction."""
    try:
        # Update material
        material = await session.get(MaterialModel, material_id)
        material.current_stock = new_quantity
        material.updated_by = user_id
        material.updated_at = datetime.now(timezone.utc)
        
        # Flush (but don't commit yet)
        await session.flush()
        
        # Create audit log
        audit = AuditLogModel(
            tenant_id=material.tenant_id,
            entity_type="material",
            entity_id=material_id,
            action="UPDATE",
            user_id=user_id,
        )
        session.add(audit)
        
        # Commit both changes atomically
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

**Session Lifecycle:**
1. `async with session_factory() as session:` — Begins implicit transaction
2. `session.add()` / `session.execute()` — Queue operations
3. `await session.flush()` — Send to database (rollback-able)
4. `await session.commit()` — Commit changes
5. `await session.rollback()` — Undo changes
6. Session context exit — Automatically close

---

## Repository Pattern

### Repository Interface (Domain Layer)

**Location:** `backend/app/domain/{context}/interfaces/irepository.py`

```python
from abc import ABC, abstractmethod
from typing import List, Optional
import uuid

from backend.app.domain.inventory.entities.material import Material

class IMaterialRepository(ABC):
    """Abstract repository for Material aggregate."""
    
    @abstractmethod
    async def get_by_id(self, material_id: uuid.UUID) -> Optional[Material]:
        """Get material by ID. Returns None if not found or deleted."""
        pass
    
    @abstractmethod
    async def get_by_code(self, code: str, tenant_id: uuid.UUID) -> Optional[Material]:
        """Get material by code within tenant scope."""
        pass
    
    @abstractmethod
    async def list_by_tenant(
        self, 
        tenant_id: uuid.UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Material]:
        """List materials for tenant with pagination."""
        pass
    
    @abstractmethod
    async def save(self, material: Material) -> uuid.UUID:
        """Save material (insert or update). Returns ID."""
        pass
    
    @abstractmethod
    async def delete(self, material_id: uuid.UUID) -> None:
        """Soft-delete material."""
        pass
```

### Repository Implementation (Infrastructure Layer)

**Location:** `backend/app/infrastructure/persistence/repositories/material_repository.py`

```python
class MaterialRepository(BaseRepository[Material, MaterialModel]):
    """SQLAlchemy implementation of IMaterialRepository."""
    
    async def get_by_id(self, material_id: uuid.UUID) -> Optional[Material]:
        """Get material by ID, filtering by tenant and soft-delete status."""
        tenant_id = get_tenant_id()  # From ContextVar
        
        stmt = select(MaterialModel).where(
            MaterialModel.id == material_id,
            MaterialModel.tenant_id == tenant_id,        # ← Tenant filter
            MaterialModel.is_deleted == False             # ← Soft delete filter
        )
        
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        
        return self._to_entity(model) if model else None
    
    async def get_by_code(self, code: str, tenant_id: uuid.UUID) -> Optional[Material]:
        """Get material by code."""
        stmt = select(MaterialModel).where(
            MaterialModel.code == code,
            MaterialModel.tenant_id == tenant_id,        # ← Tenant filter
            MaterialModel.is_deleted == False             # ← Soft delete filter
        )
        
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        
        return self._to_entity(model) if model else None
    
    async def list_by_tenant(
        self, 
        tenant_id: uuid.UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Material]:
        """List materials for tenant with pagination."""
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,        # ← Tenant filter
            MaterialModel.is_deleted == False             # ← Soft delete filter
        ).order_by(MaterialModel.created_at.desc()).offset(skip).limit(limit)
        
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]
    
    async def save(self, material: Material) -> uuid.UUID:
        """Save material (insert or update)."""
        model = self._to_model(material)
        self._session.add(model)
        await self._session.flush()
        return model.id
    
    async def delete(self, material_id: uuid.UUID) -> None:
        """Soft-delete material."""
        tenant_id = get_tenant_id()
        
        stmt = select(MaterialModel).where(
            MaterialModel.id == material_id,
            MaterialModel.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        
        if model:
            model.is_deleted = True
            model.deleted_at = datetime.utcnow()
            await self._session.flush()
```

**Repository Key Principles:**
- ✅ Every query includes `tenant_id` filter
- ✅ Every query includes `is_deleted == False` filter
- ✅ Returns domain entities, not ORM models
- ✅ No business logic (that's in domain layer)
- ✅ All I/O operations are async

---

## Unit of Work Pattern

### Purpose

Coordinates multiple repositories and ensures atomic transactions across multiple entities.

### Implementation

```python
class SQLAlchemyUnitOfWork:
    """Transaction coordinator across multiple repositories."""
    
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._session: Optional[AsyncSession] = None
    
    async def __aenter__(self):
        self._session = self._session_factory()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self._session.rollback()
        else:
            await self._session.commit()
        await self._session.close()
    
    @property
    def materials(self) -> IMaterialRepository:
        return MaterialRepository(self._session)
    
    @property
    def work_orders(self) -> IWorkOrderRepository:
        return WorkOrderRepository(self._session)
```

### Usage

```python
async def transfer_inventory(
    uow: SQLAlchemyUnitOfWork,
    from_material_id: uuid.UUID,
    to_material_id: uuid.UUID,
    quantity: float,
):
    """Transfer inventory between materials atomically."""
    async with uow:
        # Use repositories through UoW
        from_mat = await uow.materials.get_by_id(from_material_id)
        to_mat = await uow.materials.get_by_id(to_material_id)
        
        if from_mat.current_stock < quantity:
            raise InsufficientStockError(f"Need {quantity}, have {from_mat.current_stock}")
        
        # Deduct from source
        from_mat.current_stock -= quantity
        
        # Add to destination
        to_mat.current_stock += quantity
        
        # Both saved atomically when exiting async with block
        await uow.materials.save(from_mat)
        await uow.materials.save(to_mat)
```

**Transaction Semantics:**
- ✅ On success: `await session.commit()` (auto-executed)
- ✅ On exception: `await session.rollback()` (auto-executed)
- ✅ All operations atomic (all-or-nothing)

---

## Alembic Migrations

### Migration Conventions

**Location:** `alembic/versions/`

**Naming Convention:**
```
YYYYMMDD_HHmm_description.py
20261109_1430_add_priority_to_sales_orders.py
20261108_0900_add_missing_columns_materials.py
```

### Creating Migrations

**Auto-generate from model changes:**
```bash
cd /path/to/backend
alembic revision --autogenerate -m "add priority to sales orders"
```

**Manual migration:**
```bash
alembic revision -m "add priority to sales orders"
```

**Review the generated migration before committing:**
```python
# alembic/versions/20261109_1430_add_priority_to_sales_orders.py

def upgrade() -> None:
    # This is the forward migration (upgrade)
    op.add_column('sales_orders', 
        sa.Column('priority', sa.String(20), nullable=False, server_default='MEDIUM')
    )

def downgrade() -> None:
    # This is the reverse migration (rollback)
    op.drop_column('sales_orders', 'priority')
```

### Applying Migrations

**Upgrade to latest:**
```bash
alembic upgrade head
```

**Upgrade specific number of versions:**
```bash
alembic upgrade +2  # Move forward 2 versions
```

**Downgrade:**
```bash
alembic downgrade -1  # Move back 1 version
```

**Check current state:**
```bash
alembic current
```

**View all versions:**
```bash
alembic history
```

### Handling Merge Conflicts

When multiple branches create migrations simultaneously:

```bash
# See conflicting heads
alembic heads

# Merge conflicts
alembic merge heads -m "merge migration heads"

# Apply merged migration
alembic upgrade head
```

### Migration Safety Rules

✅ **MUST DO:**
- Test upgrade and downgrade locally
- Review generated migrations before applying
- Never modify committed migrations (create new ones)
- Test on development database first
- Document breaking changes in migration message

❌ **NEVER DO:**
- Drop tables without explicit approval
- Rename columns without proper migration
- Change column types without careful testing
- Apply destructive migrations to production without backup
- Skip testing downgrade path

### Foreign Key Management

**In migrations, always handle foreign key constraints:**

```python
# Adding a foreign key
def upgrade() -> None:
    op.create_foreign_key(
        'fk_work_orders_material_id',
        'work_orders', 'materials',
        ['material_id'], ['id'],
        ondelete='RESTRICT'
    )

def downgrade() -> None:
    op.drop_constraint(
        'fk_work_orders_material_id',
        'work_orders',
        type_='foreignkey'
    )
```

---

## Soft Delete Implementation

### Pattern

Every table tracks deletion status:

```python
is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
```

### Benefits

1. **Audit Trail** — Know what was deleted and when
2. **Recovery** — Restore accidentally deleted data
3. **Compliance** — Retain records for legal reasons
4. **Referential Integrity** — Foreign keys don't break

### Querying with Soft Deletes

**Always filter:**

```python
# ✅ Correct: Include soft delete filter
stmt = select(Material).where(
    Material.tenant_id == tenant_id,
    Material.is_deleted == False  # ← Always include this
)

# ❌ Wrong: Missing soft delete filter (security risk)
stmt = select(Material).where(
    Material.tenant_id == tenant_id
)
```

### Soft Deletion Operation

```python
async def soft_delete_material(session: AsyncSession, material_id: uuid.UUID):
    """Mark material as deleted."""
    material = await session.get(MaterialModel, material_id)
    
    if material:
        material.is_deleted = True
        material.deleted_at = datetime.utcnow()
        await session.flush()
```

### Hard Deletion (Extremely Rare)

Hard deletion removes data permanently and should only be done by administrators with explicit approval:

```python
async def hard_delete_material(session: AsyncSession, material_id: uuid.UUID):
    """Permanently remove material (DESTRUCTIVE - admin only)."""
    
    # SAFETY: Log the action for compliance
    audit_log(
        action="HARD_DELETE",
        entity_type="material",
        entity_id=material_id,
        reason="[MUST BE DOCUMENTED]",
        approved_by="[ADMIN USER]"
    )
    
    # Remove from database
    stmt = delete(MaterialModel).where(MaterialModel.id == material_id)
    await session.execute(stmt)
    await session.commit()
```

---

## Tenant-Aware Data Access

### Multi-Tenancy Principle

**Every query must filter by tenant_id.**

### Context Variable

```python
# Set by middleware during request processing
tenant_id = get_tenant_id()  # Returns UUID from JWT

# Use in queries
stmt = select(Material).where(
    Material.tenant_id == tenant_id,
    Material.is_deleted == False
)
```

### Enforcing Tenant Isolation

**In Repository:**
```python
async def get_by_id(self, material_id: uuid.UUID) -> Optional[Material]:
    tenant_id = get_tenant_id()  # From context
    
    # CRITICAL: Always filter by tenant
    stmt = select(MaterialModel).where(
        MaterialModel.id == material_id,
        MaterialModel.tenant_id == tenant_id,  # ← Non-negotiable
        MaterialModel.is_deleted == False
    )
    
    result = await self._session.execute(stmt)
    return self._to_entity(result.scalars().first()) if result else None
```

### Database Constraints

PostgreSQL enforces at database level:

```sql
-- Every table has this constraint
ALTER TABLE materials 
ADD CONSTRAINT fk_materials_tenant_id 
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;

-- Prevents orphaned rows if tenant deleted
```

---

## Database Testing Approach

### Unit Tests (Pure Logic)

```python
@pytest.mark.asyncio
@pytest.mark.unit
async def test_material_entity_validation():
    """Test domain entity logic without database."""
    material = Material(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        code="MAT-001",
        name="Steel",
    )
    
    assert material.code == "MAT-001"
    assert material.is_deleted == False
```

### Integration Tests (With Database)

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_material_repository_filters_by_tenant(db_session):
    """Test repository multi-tenant isolation."""
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    
    repo = MaterialRepository(db_session)
    
    # Create materials for different tenants
    mat1 = await repo.save(Material(
        id=uuid.uuid4(),
        tenant_id=tenant1_id,
        code="MAT-001",
        name="Steel"
    ))
    
    mat2 = await repo.save(Material(
        id=uuid.uuid4(),
        tenant_id=tenant2_id,
        code="MAT-002",
        name="Aluminum"
    ))
    
    # Verify tenant1 can only see their materials
    # (This requires context setup — see conftest.py)
    results = await repo.list_by_tenant(tenant1_id)
    assert len(results) == 1
    assert results[0].code == "MAT-001"
```

### Database Fixtures

```python
# conftest.py
@pytest.fixture
async def db_session(db_engine):
    """Provide clean database session for each test."""
    async with db_engine.begin() as conn:
        # Start transaction (auto-rollback after test)
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()
```

---

## Database Mandatory Rules

### 1. Never Modify Production Data

- ❌ Never update/delete records directly in production
- ✅ Only via application API with full audit trail
- ✅ Require explicit approval for schema changes

### 2. Never Drop Tables

- ❌ Never drop or recreate tables
- ✅ Use Alembic migrations for schema changes
- ✅ Use soft deletes instead of dropping rows

### 3. Never Generate Destructive Migrations

- ❌ Never drop columns/tables without explicit approval
- ✅ Review migration upgrade and downgrade paths
- ✅ Test both directions before applying

### 4. Preserve Relationships

- ✅ Use `ON DELETE RESTRICT` to prevent orphaned data
- ✅ Handle foreign key constraints in migrations
- ✅ Never delete parent records with children

### 5. Use Repositories

- ✅ All data access through repositories
- ✅ Never raw SQL without approval
- ✅ Repositories enforce tenant isolation

### 6. Transaction Management

- ✅ Use Unit of Work for multi-entity changes
- ✅ Atomic (all-or-nothing) operations
- ✅ Explicit error handling with rollback

### 7. No Credentials in Code

- ❌ Never hardcode database passwords
- ✅ Use environment variables
- ✅ Use `.env` file (not committed to git)

### 8. Environment Configuration

- ✅ Support different databases per environment
- ✅ Verify connection parameters before migration
- ✅ Never assume same connection everywhere

---

## Key Files Reference

- **Database Setup:** `backend/app/infrastructure/persistence/database.py`
- **Base Model:** `backend/app/infrastructure/persistence/database.py` (Base class)
- **Models:** `backend/app/infrastructure/persistence/models/` (50+ model files)
- **Repositories:** `backend/app/infrastructure/persistence/repositories/`
- **Migrations:** `alembic/versions/` (50+ migration files)
- **Tests:** `tests/integration/` (database-dependent tests)
- **Configuration:** `backend/app/config.py` (database_url setting)

---

## Summary

| Aspect | Implementation |
|--------|-----------------|
| **Database** | PostgreSQL 15+ |
| **Driver** | asyncpg (async) |
| **ORM** | SQLAlchemy 2.0.30 |
| **Migrations** | Alembic 1.13.1 |
| **Session Management** | Async context managers |
| **Multi-Tenancy** | tenant_id on every table + query filters |
| **Soft Deletes** | is_deleted + deleted_at on every table |
| **Audit Trail** | created_by, updated_by, timestamps |
| **Transactions** | Unit of Work pattern |
| **Repository Pattern** | Abstract interfaces + concrete implementations |
| **Indexing** | Automatic on tenant_id, is_deleted, foreign keys |
| **Type Safety** | SQLAlchemy 2.0 Mapped[] annotations |
| **Testing** | Unit + integration tests with fixtures |
