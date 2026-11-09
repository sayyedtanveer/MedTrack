# MedTrack Backend Standards

**Version:** 1.0.0  
**Last Updated:** November 9, 2026  
**Technology Stack:** FastAPI 0.111.0, SQLAlchemy 2.0.30 async, asyncpg 0.29.0, Pydantic v2

---

## Python Standards

### Type Hints (Mandatory)

All functions and variables must have explicit type hints.

**✅ Correct:**
```python
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

async def get_materials(
    tenant_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[Material]:
    """Fetch materials for tenant with pagination."""
    stmt = select(Material).where(
        Material.tenant_id == tenant_id,
        Material.is_deleted == False
    ).offset(skip).limit(limit)
    
    result = await session.execute(stmt)
    return [Material.from_model(m) for m in result.scalars().all()]
```

**❌ Wrong:**
```python
async def get_materials(tenant_id, skip=0, limit=100):  # No type hints
    """Fetch materials."""
    materials = session.query(Material).filter_by(tenant_id=tenant_id).all()
    return materials
```

### Naming Conventions

- **Functions & Variables:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `CONSTANT_CASE` (rarely used; prefer immutable objects)
- **Private functions:** `_private_function()` (single underscore prefix)
- **Protected functions:** Not used in Python; use public with documentation

**Example:**
```python
class BOMHandlers:  # PascalCase
    def __init__(self, bom_repo: IBOMRepository):
        self._bom_repo = bom_repo  # Private
    
    async def handle_create_bom(  # snake_case
        self, cmd: CreateBOMCommand
    ) -> UUID:
        """Public method (no prefix)."""
        pass
```

### Async-First Pattern (Mandatory)

All I/O operations are async. Never use blocking calls.

**✅ Correct:**
```python
# Database
async def get_material(self, material_id: UUID) -> Material | None:
    stmt = select(MaterialModel).where(MaterialModel.id == material_id)
    result = await session.execute(stmt)  # ← await
    model = result.scalars().first()
    return Material.from_model(model) if model else None

# HTTP Client
async def fetch_supplier_data(supplier_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.supplier.com/{supplier_id}")
        return response.json()

# File I/O
async def upload_document(filename: str, content: bytes) -> str:
    path = Path(settings.upload_dir) / filename
    await aiofiles.open(path, 'wb').write(content)  # ← await
    return str(path)
```

**❌ Wrong:**
```python
# Blocking database query
def get_material(self, material_id: UUID) -> Material | None:
    return session.query(MaterialModel).filter_by(id=material_id).first()  # sync

# Blocking HTTP request
def fetch_supplier_data(supplier_id: str) -> dict:
    response = requests.get(f"https://api.supplier.com/{supplier_id}")  # blocking
    return response.json()

# Blocking file I/O
def upload_document(filename: str, content: bytes) -> str:
    with open(Path(settings.upload_dir) / filename, 'wb') as f:  # blocking
        f.write(content)
```

### Imports Organization

Group imports in this order:
1. Standard library
2. Third-party libraries
3. Local application imports

**Example:**
```python
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from backend.app.domain.bom.entities.bom import BOM
from backend.app.application.bom.commands.bom_commands import CreateBOMCommand
from backend.app.infrastructure.container import Container
```

---

## Dependency Injection

### Container Pattern

Instantiate services via the DI container, never use global singletons.

**✅ Correct:**
```python
@router.post("/materials")
async def create_material(
    req: CreateMaterialRequest,
    container: Container = Depends(lambda r: r.app.state.container),
    current_user: User = Depends(get_current_user),
) -> MaterialResponse:
    session = container.session_factory()
    material_repo = MaterialRepository(session)
    handlers = MaterialHandlers(material_repo, container.unit_of_work)
    
    cmd = CreateMaterialCommand(code=req.code, name=req.name)
    material_id = await handlers.handle_create_material(cmd)
    
    return MaterialResponse.from_dto(...)
```

**❌ Wrong:**
```python
# Global singleton
_material_repo = MaterialRepository()

@router.post("/materials")
async def create_material(req: CreateMaterialRequest) -> MaterialResponse:
    handlers = MaterialHandlers(_material_repo)  # Hard-coded dependency
    # Hard to test, multi-tenant unsafe
```

### Dependency Helpers

Create reusable helpers for common patterns:

```python
# dependencies/auth.py
async def get_current_user(
    token: str = Depends(HTTPBearer()),
    container: Container = Depends(get_container),
) -> User:
    """Extract and validate JWT token, return current user."""
    payload = container.jwt_handler.decode(token.credentials)
    user_id = UUID(payload.get("sub"))
    tenant_id = UUID(payload.get("tid"))
    
    user = await container.user_repository().get_by_id(tenant_id, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

# Route handler
@router.post("/materials")
async def create_material(
    req: CreateMaterialRequest,
    current_user: User = Depends(get_current_user),
) -> MaterialResponse:
    # User already authenticated
    pass
```

---

## Command & Query Handlers

### Command Handler Pattern

Commands handle **write operations** (create, update, delete). Always return IDs or void.

**Structure:**
```python
from dataclasses import dataclass
from uuid import UUID

@dataclass
class CreateBOMCommand:
    """Write command: create a BOM."""
    template_id: UUID
    lines: List[BOMLineInput]

# Handler
class BOMHandlers:
    def __init__(self, bom_repo: IBOMRepository, uow: IUnitOfWork):
        self.bom_repo = bom_repo
        self.uow = uow
    
    async def handle_create_bom(self, cmd: CreateBOMCommand) -> UUID:
        """
        Create a BOM. Returns ID for created BOM.
        
        May raise:
        - TemplateNotFoundError: Template doesn't exist
        - DuplicateComponentError: Same material in multiple lines
        """
        # 1. Validate input
        template = await self.bom_repo.get_template(cmd.template_id)
        if not template:
            raise TemplateNotFoundError(cmd.template_id)
        
        # 2. Check uniqueness
        self._ensure_unique_components(cmd.lines)
        
        # 3. Create domain entity
        bom = BOM(
            template_id=cmd.template_id,
            version=1,
            is_active=False,  # New BOMs start inactive
            lines=[
                BOMLine(
                    material_id=line.material_id,
                    quantity=line.quantity,
                )
                for line in cmd.lines
            ]
        )
        
        # 4. Persist via unit of work
        bom_id = await self.uow.save_bom(bom)
        
        # 5. Publish domain events
        await self.event_dispatcher.publish(bom.events)
        
        # 6. Return ID
        return bom_id
    
    def _ensure_unique_components(self, lines: List[BOMLineInput]) -> None:
        """Validate no duplicate materials."""
        material_ids = [line.material_id for line in lines]
        if len(material_ids) != len(set(material_ids)):
            raise DuplicateComponentError("Same material in multiple lines")
```

**Usage in Route Handler:**
```python
@router.post("/boms", status_code=201)
async def create_bom(
    req: CreateBOMRequest,
    current_user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
) -> BOMResponse:
    """Create a new BOM."""
    
    # Build command
    cmd = CreateBOMCommand(
        template_id=UUID(req.template_id),
        lines=[BOMLineInput(...) for line in req.lines]
    )
    
    # Get handlers from container
    handlers = BOMHandlers(
        bom_repo=container.bom_repository(),
        uow=container.unit_of_work()
    )
    
    # Execute (may raise DomainException)
    try:
        bom_id = await handlers.handle_create_bom(cmd)
    except (TemplateNotFoundError, DuplicateComponentError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    # Fetch and return created BOM
    bom = await handlers.handle_get_bom(GetBOMQuery(bom_id))
    return BOMResponse.from_dto(bom)
```

### Query Handler Pattern

Queries handle **read operations** only. No side effects, return DTOs.

**Structure:**
```python
from dataclasses import dataclass
from uuid import UUID

@dataclass
class GetBOMQuery:
    """Read query: get one BOM by ID."""
    bom_id: UUID

@dataclass
class ListBOMsQuery:
    """Read query: list BOMs for tenant."""
    skip: int = 0
    limit: int = 100

# Handler
class BOMHandlers:
    async def handle_get_bom(self, query: GetBOMQuery) -> BOMResponse:
        """
        Get a BOM by ID. Returns DTO.
        
        May raise:
        - BOMNotFoundError: BOM doesn't exist
        """
        bom = await self.bom_repo.get_by_id(query.bom_id)
        if not bom:
            raise BOMNotFoundError(query.bom_id)
        
        return BOMResponse.from_entity(bom)
    
    async def handle_list_boms(self, query: ListBOMsQuery) -> List[BOMResponse]:
        """List BOMs with pagination."""
        boms = await self.bom_repo.list_by_tenant(
            skip=query.skip,
            limit=query.limit
        )
        return [BOMResponse.from_entity(bom) for bom in boms]
```

**Usage in Route Handler:**
```python
@router.get("/boms/{bom_id}")
async def get_bom(
    bom_id: str,
    container: Container = Depends(get_container),
) -> BOMResponse:
    """Get a BOM by ID."""
    
    handlers = BOMHandlers(
        bom_repo=container.bom_repository(),
        uow=container.unit_of_work()
    )
    
    try:
        return await handlers.handle_get_bom(GetBOMQuery(UUID(bom_id)))
    except BOMNotFoundError:
        raise HTTPException(status_code=404, detail="BOM not found")
```

---

## Repository Pattern

Repositories abstract data access. Always implement domain-defined interfaces.

**Domain Interface:**
```python
# domain/bom/interfaces/ibom_repository.py
from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional

from backend.app.domain.bom.entities.bom import BOM

class IBOMRepository(ABC):
    """Abstract repository for BOM aggregate root."""
    
    @abstractmethod
    async def get_by_id(self, bom_id: UUID) -> Optional[BOM]:
        """Get BOM by ID. Returns None if not found."""
        pass
    
    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[BOM]:
        """List BOMs for tenant with pagination."""
        pass
    
    @abstractmethod
    async def save(self, bom: BOM) -> UUID:
        """Save BOM (insert or update). Returns ID."""
        pass
    
    @abstractmethod
    async def delete(self, bom_id: UUID) -> None:
        """Soft-delete BOM."""
        pass
```

**Implementation:**
```python
# infrastructure/persistence/repositories/bom_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.bom.entities.bom import BOM
from backend.app.domain.bom.interfaces.ibom_repository import IBOMRepository
from backend.app.infrastructure.persistence.models.bom_model import BOMModel

class BOMRepository(IBOMRepository):
    """SQLAlchemy implementation of IBOMRepository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, bom_id: UUID) -> BOM | None:
        """Get BOM by ID, filtering by tenant and soft-delete status."""
        tenant_id = get_tenant_id()
        
        stmt = select(BOMModel).where(
            BOMModel.tenant_id == tenant_id,
            BOMModel.id == bom_id,
            BOMModel.is_deleted == False
        )
        
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        
        return BOM.from_model(model) if model else None
    
    async def list_by_tenant(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[BOM]:
        """List BOMs for tenant with pagination."""
        stmt = select(BOMModel).where(
            BOMModel.tenant_id == tenant_id,
            BOMModel.is_deleted == False
        ).order_by(BOMModel.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [BOM.from_model(m) for m in models]
    
    async def save(self, bom: BOM) -> UUID:
        """Save BOM (insert or update)."""
        model = BOMModel.from_entity(bom)
        self.session.add(model)
        await self.session.flush()
        return model.id
    
    async def delete(self, bom_id: UUID) -> None:
        """Soft-delete BOM."""
        tenant_id = get_tenant_id()
        
        stmt = select(BOMModel).where(
            BOMModel.tenant_id == tenant_id,
            BOMModel.id == bom_id
        )
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        
        if model:
            model.is_deleted = True
            model.deleted_at = datetime.utcnow()
            await self.session.flush()
```

**Key Rules:**
- Always filter by `tenant_id` and `is_deleted == False`
- Never return ORM models; convert to domain entities
- Query methods return void (side effects handled by caller)
- Use descriptive method names matching domain language

---

## Structured Logging

Use structlog for all logging, never print statements.

**✅ Correct:**
```python
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

async def handle_create_bom(self, cmd: CreateBOMCommand) -> UUID:
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    correlation_id = get_correlation_id()
    
    logger.info(
        "BOM creation started",
        extra={
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "correlation_id": correlation_id,
            "template_id": str(cmd.template_id),
            "line_count": len(cmd.lines),
        }
    )
    
    try:
        template = await self.bom_repo.get_template(cmd.template_id)
        if not template:
            logger.warning(
                "BOM creation failed: template not found",
                extra={"template_id": str(cmd.template_id)}
            )
            raise TemplateNotFoundError(cmd.template_id)
        
        # ... create BOM ...
        
        logger.info(
            "BOM created successfully",
            extra={
                "bom_id": str(bom_id),
                "version": bom.version,
                "line_count": len(bom.lines),
            }
        )
        
        return bom_id
        
    except DomainException as e:
        logger.error(
            "BOM creation failed with domain error",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "error_code": getattr(e, 'code', None),
            }
        )
        raise
```

**❌ Wrong:**
```python
# Don't use print
print("Creating BOM...")
print(f"BOM ID: {bom_id}")

# Don't use basic logging without context
logging.info(f"BOM {bom_id} created")  # Missing tenant, user, correlation

# Don't log sensitive data
logger.info(f"User password: {password}")  # SECURITY RISK
```

**What to Log:**
- ✅ Operation start/end
- ✅ Business rule violations
- ✅ Errors with context (tenant, user, correlation_id)
- ✅ Important state changes
- ✅ External API calls

**What NOT to Log:**
- ❌ Passwords or plaintext credentials
- ❌ API keys or tokens
- ❌ Credit card numbers
- ❌ Personal identification numbers
- ❌ Encryption keys

---

## Exception Handling

### Domain Exceptions

Define specific, meaningful domain exceptions in `domain/{context}/exceptions/`.

```python
# domain/bom/exceptions/duplicate_component_error.py
from backend.app.domain.shared.exceptions.domain_exception import DomainException

class DuplicateComponentError(DomainException):
    """Raised when same material appears multiple times in BOM."""
    
    def __init__(self, material_id: str):
        super().__init__(
            code="DUPLICATE_COMPONENT",
            message=f"Material {material_id} already in BOM"
        )
        self.material_id = material_id
```

**Usage:**
```python
def add_line(self, line: BOMLineInput) -> None:
    if any(l.material_id == line.material_id for l in self.lines):
        raise DuplicateComponentError(str(line.material_id))
    self.lines.append(BOMLine(...))
```

### Converter to HTTP

Route handlers convert domain exceptions to HTTP responses:

```python
@router.post("/boms", status_code=201)
async def create_bom(req: CreateBOMRequest) -> BOMResponse:
    try:
        bom_id = await handlers.handle_create_bom(cmd)
        return BOMResponse(...)
    
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Template not found: {e.material_id}"
        )
    except DuplicateComponentError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Business rule violation: {e.message}"
        )
    except AuthenticationException as e:
        raise HTTPException(status_code=401, detail=e.message)
    except AuthorizationException as e:
        raise HTTPException(status_code=403, detail=e.message)
    except DomainException as e:
        # Catch-all for other domain exceptions
        raise HTTPException(status_code=422, detail=e.message)
```

---

## Database & ORM Patterns

### SQLAlchemy Async

All database operations must be async with asyncpg driver.

```python
# infrastructure/persistence/database.py
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

def create_engine(database_url: str):
    """Create async PostgreSQL engine."""
    return create_async_engine(
        database_url,  # postgresql+asyncpg://...
        echo=False,    # Set to True for SQL logging
        pool_pre_ping=True,  # Verify connections before use
        pool_size=10,
        max_overflow=20,
    )

def create_session_factory(engine):
    """Create async session factory."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
```

### ORM Models

Map database schema to Python classes with SQLAlchemy.

```python
# infrastructure/persistence/models/bom_model.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UUID
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class BOMModel(Base):
    """SQLAlchemy ORM model for BOM table."""
    
    __tablename__ = "boms"
    
    # ── Primary & Foreign Keys ────────────────────
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False, index=True)
    
    # ── Data ──────────────────────────────────────
    template_id = Column(UUID, ForeignKey("product_templates.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=False)
    
    # ── Soft Delete ───────────────────────────────
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # ── Audit Trail ───────────────────────────────
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    
    # ── Relationships ─────────────────────────────
    # relationship("BOMLine") defined in BOMLineModel
    
    @classmethod
    def from_entity(cls, entity: BOM) -> "BOMModel":
        """Convert domain entity to ORM model."""
        return cls(
            id=entity.id,
            tenant_id=entity.tenant_id,
            template_id=entity.template_id,
            version=entity.version,
            is_active=entity.is_active,
            created_at=entity.created_at,
            created_by=entity.created_by,
            updated_at=entity.updated_at,
            updated_by=entity.updated_by,
        )
```

### Queries with Filtering

Always filter by tenant and soft-delete status.

```python
# Get one
stmt = select(MaterialModel).where(
    MaterialModel.tenant_id == tenant_id,
    MaterialModel.id == material_id,
    MaterialModel.is_deleted == False
)
result = await session.execute(stmt)
model = result.scalars().first()

# List with pagination
stmt = select(MaterialModel).where(
    MaterialModel.tenant_id == tenant_id,
    MaterialModel.is_deleted == False,
    MaterialModel.status == "ACTIVE"  # Optional business filter
).order_by(MaterialModel.created_at.desc()).offset(skip).limit(limit)

result = await session.execute(stmt)
models = result.scalars().all()
```

---

## Pydantic v2 Schemas

Validate all HTTP requests and responses with Pydantic.

**Request Schema:**
```python
# interfaces/api/v1/schemas/bom_schemas.py
from pydantic import BaseModel, Field
from typing import List
from decimal import Decimal

class BOMLineInput(BaseModel):
    """Input for BOM line."""
    material_id: str = Field(..., pattern="^[0-9a-f-]+$")  # UUID format
    quantity: Decimal = Field(..., ge=Decimal("0.01"))
    
    class Config:
        json_schema_extra = {
            "example": {
                "material_id": "123e4567-e89b-12d3-a456-426614174000",
                "quantity": "10.50"
            }
        }

class CreateBOMRequest(BaseModel):
    """Create BOM request."""
    template_id: str = Field(..., pattern="^[0-9a-f-]+$")
    lines: List[BOMLineInput] = Field(..., min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "...",
                "lines": [{"material_id": "...", "quantity": "10.50"}]
            }
        }
```

**Response Schema:**
```python
class BOMLineResponse(BaseModel):
    """BOM line response."""
    material_id: str
    quantity: Decimal
    material_name: str
    unit: str

class BOMResponse(BaseModel):
    """Complete BOM response."""
    id: str
    template_id: str
    version: int
    is_active: bool
    lines: List[BOMLineResponse]
    created_at: datetime
    created_by: str
    
    @classmethod
    def from_dto(cls, dto: BOMResponseDTO) -> "BOMResponse":
        """Convert DTO to response schema."""
        return cls(
            id=str(dto.id),
            template_id=str(dto.template_id),
            version=dto.version,
            is_active=dto.is_active,
            lines=[BOMLineResponse(...) for line in dto.lines],
            created_at=dto.created_at,
            created_by=str(dto.created_by),
        )
```

---

## Testing

### Unit Tests (Pure Logic)

Test domain entities and business rules.

```python
# tests/unit/domain/bom/test_bom_entity.py
import pytest
from uuid import uuid4
from decimal import Decimal

from backend.app.domain.bom.entities.bom import BOM, BOMLine
from backend.app.domain.bom.exceptions.duplicate_component_error import DuplicateComponentError

@pytest.mark.unit
def test_bom_add_line_duplicate_raises_error():
    """Adding same material twice should raise DuplicateComponentError."""
    bom = BOM(id=uuid4(), template_id=uuid4(), version=1)
    material_id = uuid4()
    
    # Add first line
    bom.add_line(BOMLine(material_id=material_id, quantity=Decimal("10")))
    
    # Add same material again → should raise
    with pytest.raises(DuplicateComponentError):
        bom.add_line(BOMLine(material_id=material_id, quantity=Decimal("20")))
```

### Integration Tests (With Database)

Test repositories and handlers with real database.

```python
# tests/integration/application/bom/test_bom_handlers.py
import pytest
from uuid import uuid4

from backend.app.application.bom.commands.bom_commands import CreateBOMCommand, BOMLineInput
from backend.app.application.bom.handlers.bom_handlers import BOMHandlers
from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository

@pytest.mark.asyncio
@pytest.mark.integration
async def test_handle_create_bom_creates_bom_in_db(db_session):
    """Creating BOM should insert into database."""
    tenant_id = uuid4()
    template_id = uuid4()
    material_id = uuid4()
    
    # Setup
    repo = BOMRepository(db_session)
    handlers = BOMHandlers(repo, unit_of_work)
    
    cmd = CreateBOMCommand(
        template_id=template_id,
        lines=[BOMLineInput(material_id=material_id, quantity=Decimal("10"))]
    )
    
    # Execute
    bom_id = await handlers.handle_create_bom(cmd)
    
    # Verify in database
    bom = await repo.get_by_id(bom_id)
    assert bom is not None
    assert bom.template_id == template_id
    assert len(bom.lines) == 1
```

---

## Summary of Patterns

| Pattern | Purpose | Example |
|---------|---------|---------|
| **Async-First** | All I/O operations | `await session.execute(stmt)` |
| **Type Hints** | Full type safety | `async def fn() -> Result:` |
| **DI Container** | Service construction | `container.bom_repository()` |
| **Commands** | Write operations | `CreateBOMCommand(...)` |
| **Queries** | Read operations | `GetBOMQuery(bom_id)` |
| **Repositories** | Data access | `IBOMRepository` + `BOMRepository` |
| **Domain Exceptions** | Business rules | `DuplicateComponentError(...)` |
| **Structured Logging** | Context tracking | `logger.info("...", extra={...})` |
| **Pydantic Schemas** | HTTP validation | `CreateBOMRequest(...)` |
| **Soft Deletes** | Audit trail | `is_deleted = True; deleted_at = now()` |

---

## Key Files Reference

- **Configuration:** `backend/app/config.py`
- **DI Container:** `backend/app/infrastructure/di/container.py`
- **Logging Setup:** `backend/app/core/logging.py` and `backend/app/infrastructure/logging/logger.py`
- **Database Setup:** `backend/app/infrastructure/persistence/database.py`
- **Repository Examples:** `backend/app/infrastructure/persistence/repositories/`
- **Handler Examples:** `backend/app/application/{context}/handlers/`
- **Exception Hierarchy:** `backend/app/domain/shared/exceptions/`
