---
name: "MedTrack Technical Stack & Conventions"
description: "Verified technologies, database, authentication, security, and testing tools"
inclusion: auto
---

# MedTrack Technical Stack & Conventions

**Updated:** November 9, 2026  
**Version:** 1.0.0  
**Canonical Reference:** [`AGENTS.md`](../../AGENTS.md) Sections 1-2, 5-7

---

## Verified Backend Stack

**Framework & Server:**
- **FastAPI** 0.111.0 (async web framework)
- **Uvicorn** 0.29.0 (ASGI server)

**Database & ORM:**
- **PostgreSQL** 15+ (database)
- **asyncpg** 0.29.0 (async PostgreSQL driver)
- **SQLAlchemy** 2.0.30 (async ORM)
- **Alembic** 1.13.1 (schema migrations)

**Validation & Serialization:**
- **Pydantic** v2.7.1 (request/response validation, strict mode)
- **python-jose** (JWT encoding/decoding)
- **bcrypt** (password hashing, 12+ rounds)

**Logging & Monitoring:**
- **structlog** 24.4.0 (structured logging with context)
- **slowapi** 0.1.9 (rate limiting)

**Document & File Handling:**
- **WeasyPrint** 60.2 (PDF generation)
- **Jinja2** 3.1.4 (email templates)

**External Services:**
- **Resend** 2.32.2 (SaaS email provider)

**Testing:**
- **pytest** 8.2.0 (test framework)
- **pytest-asyncio** 0.23.6 (async test support)
- **pytest-cov** 5.0.0 (coverage reporting)

**Language:**
- **Python** 3.11+

---

## Verified Frontend Stack

**Framework & Language:**
- **React** 18.3.1 (UI framework)
- **TypeScript** (strict mode enabled)

**Build Tool:**
- **Vite** 5.4.2 (build tool with hot reload)
- **Node.js** 20+ LTS

**UI & Styling:**
- **Tailwind CSS** 4.0.0-alpha (utility-first CSS)
- **Lucide React** 0.435.0 (icons)
- **Recharts** 2.12.7 (charts)
- **Motion** 11.11.17 (animations, Framer Motion fork)

**HTTP & API:**
- **axios** (HTTP client with interceptors)

**Testing:**
- **Vitest** (fast unit testing)
- **React Testing Library** (component testing)

---

## Database Architecture

### PostgreSQL 15+

**Required Extensions:**
- `pgcrypto` — UUID generation
- `pg_trgm` — Full-text search (optional)

**Connection Pool:**
- asyncpg manages connection pooling
- Pool size: 20, max overflow: 10
- Connections recycled every hour

**Schema Design:**
- 98+ tables (verified)
- UUID primary keys (distributed system support)
- Soft deletes on all entities
- Audit columns (created_at, created_by, updated_at, updated_by)
- Tenant isolation via FK constraints
- Mandatory indexes on tenant_id, status, timestamps

### Alembic Migrations

**Current State:**
- 50+ migrations committed (as of Nov 9, 2026)
- Version control in `alembic/versions/`
- Latest: `20261108_1606_merge_all_heads.py`

**Workflow:**
```bash
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                               # Apply
alembic downgrade -1                               # Revert one
```

**Conflicts:**
```bash
alembic heads                      # Check for multiple heads
alembic merge heads -m "merge"     # Merge conflicting migrations
alembic upgrade head               # Apply merged
```

---

## Authentication & Security

### JWT (JSON Web Tokens)

**Token Structure:**
```json
{
  "sub": "user_id_uuid",
  "tid": "tenant_id_uuid",
  "role": "MANAGER",
  "exp": 1234567890,
  "iat": 1234567890
}
```

**Library:** `python-jose`

**Expiration:** 24 hours (configurable)

### Password Hashing

**Algorithm:** bcrypt  
**Salt Rounds:** 12+ (minimum)  
**Min Length:** 12 characters

**Library:** `bcrypt`

### RBAC (Role-Based Access Control)

**13 Roles:**
- ADMIN, TENANT_ADMIN, MANAGER, OPERATOR, STOREKEEPER
- PLANNER, QC, SALES, WORKER
- CLIENT (external), SUPPLIER (external)
- VIEWER

**Permission Matrix:** Defined in permission service (20+ permissions)

### Multi-Tenancy Isolation

**See:** [AGENTS.md](../../AGENTS.md) § 14, [SECURITY_AND_MULTITENANCY.md](../../docs/ai-guidelines/SECURITY_AND_MULTITENANCY.md)

**Enforcement Pattern:**
1. **Middleware:** Extract tenant_id from JWT `tid` claim
2. **ContextVars:** Store tenant_id in context (thread-local)
3. **Repository:** Every query filters by tenant_id
4. **Database:** FK constraints enforce tenant boundaries

For implementation details and security rules, see the canonical security guide.

### Security Headers

**Implemented:**
- HTTPS/TLS (production)
- HSTS (Strict-Transport-Security)
- CSP (Content-Security-Policy)
- CORS (specific origins, never `*`)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY

### Rate Limiting

**Library:** slowapi

**Applied to:**
- Login endpoint (5/minute)
- 2FA verification (10/minute)
- General API (1000/hour)

---

## Testing Tools & Patterns

### Backend Testing

**Framework:** pytest with pytest-asyncio

**Markers:**
- `@pytest.mark.unit` — Pure logic (no I/O)
- `@pytest.mark.integration` — With database
- `@pytest.mark.e2e` — Full API flow

**Coverage Target:** ≥75% for new code

**Run:**
```bash
pytest tests/ --cov=backend/app --cov-report=term-missing
```

### Frontend Testing

**Framework:** Vitest + React Testing Library

**Patterns:**
- Unit tests for components
- Integration tests for features
- Property-based tests (if needed)

**Run:**
```bash
npm run test --run  # Single run
npm run test        # Watch mode
```

### Type Checking

**Backend:** `pyright` (Python type checker)  
**Frontend:** TypeScript built-in

**Run:**
```bash
pyright backend/app
npm run type-check
```

### Linting

**Backend:** `ruff` (Python linter)  
**Frontend:** `eslint` (configured in project)

**Run:**
```bash
ruff check backend/app
npm run lint
```

---

## Async-First Conventions

### Backend

**All I/O operations are async:**
```python
# ✅ Database query
materials = await session.execute(stmt)

# ✅ External HTTP
response = await http_client.get(url)

# ✅ File operations
content = await file.read()

# ❌ Never synchronous in async context
materials = session.execute(stmt)  # Blocking!
```

**async def pattern:**
```python
async def handle_operation(cmd: Command) -> Result:
    result = await repository.get(cmd.id)
    return result
```

### Frontend

**All state updates via hooks:**
```typescript
const [data, setData] = useState(null);

useEffect(() => {
  const fetch = async () => {
    const result = await api.fetch();
    setData(result);
  };
  fetch();
}, []);
```

---

## Code Organization Conventions

### Backend Directory Structure

```
backend/app/
├── domain/          # Business logic (DDD Layer 1)
├── application/     # Use cases (DDD Layer 2)
├── infrastructure/  # Persistence (DDD Layer 3)
├── interfaces/      # API endpoints (DDD Layer 4)
├── middleware/      # Cross-cutting
├── services/        # Business services
└── tests/           # Test suite
```

### Frontend Module Structure

```
modules/{context}/
├── pages/           # Page components
├── components/      # Domain components
├── hooks/           # Custom React hooks
├── services/        # API clients
├── types/           # TypeScript interfaces
└── __tests__/       # Component tests
```

---

## Naming Conventions

### Python (Backend)

- **Modules:** snake_case (`material_repository.py`)
- **Classes:** PascalCase (`MaterialRepository`)
- **Functions/Methods:** snake_case (`list_materials()`)
- **Constants:** UPPER_SNAKE_CASE (`MAX_QUANTITY = 1000`)
- **Private:** Leading underscore (`_internal_method()`)

### TypeScript (Frontend)

- **Files:** PascalCase (`MaterialList.tsx`)
- **Components:** PascalCase (`const MaterialList = () => {}`)
- **Functions:** camelCase (`const fetchMaterials = () => {}`)
- **Constants:** UPPER_SNAKE_CASE (`const MAX_ITEMS = 100`)
- **Interfaces:** PascalCase, leading I (`interface IMaterial {}`)

---

## Dependency Management

### Backend

**Package Manager:** pip

**File:** `requirements.txt` (pinned versions)

**Example:**
```
FastAPI==0.111.0
SQLAlchemy==2.0.30
asyncpg==0.29.0
```

### Frontend

**Package Manager:** npm

**File:** `package.json` (with package-lock.json)

**Example:**
```json
{
  "react": "18.3.1",
  "typescript": "latest",
  "vite": "5.4.2"
}
```

---

## Environment Configuration

### Backend

**File:** `.env` (gitignore'd) or environment variables

**Key Variables:**
- `SECRET_KEY` — JWT secret
- `DATABASE_URL` — PostgreSQL connection
- `ENVIRONMENT` — dev/staging/production
- `CORS_ORIGINS` — Allowed origins
- `LOG_LEVEL` — structlog level

### Frontend

**File:** `.env` (gitignore'd) or environment variables

**Key Variables:**
- `VITE_API_BASE_URL` — Backend API URL
- `VITE_APP_NAME` — Application name
- `VITE_ENVIRONMENT` — dev/staging/production

---

## Development Environment

### Docker Compose

**Services:**
- PostgreSQL 15 (database)
- Redis (optional, caching)
- Backend (FastAPI)
- Frontend (Vite dev server)

**Startup:**
```bash
docker compose up -d postgres redis
```

### Local Setup

**Backend:**
```bash
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Performance Targets

| Metric | Target |
|--------|--------|
| API Response Time (p95) | <500ms |
| Database Query | <100ms (list), <50ms (get) |
| WebSocket Latency | <1 second |
| Frontend Load Time | <3 seconds |
| JSON Payload Size | <1MB |
| Test Execution | <60 seconds |

---

## Logging Conventions

**Library:** structlog

**Pattern:**
```python
logger.info(
    "event_name",
    extra={
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "correlation_id": correlation_id,
        "key": "value"
    }
)
```

**Never Log:**
- Passwords or plaintext credentials
- API keys or tokens
- Credit card numbers
- Personal identification numbers
- Encryption keys

---

## Reference

- **Full backend standards:** [`BACKEND_STANDARDS.md`](../../docs/ai-guidelines/BACKEND_STANDARDS.md)
- **Full frontend standards:** [`FRONTEND_STANDARDS.md`](../../docs/ai-guidelines/FRONTEND_STANDARDS.md)
- **Database standards:** [`DATABASE_STANDARDS.md`](../../docs/ai-guidelines/DATABASE_STANDARDS.md)
- **Security details:** [`SECURITY_AND_MULTITENANCY.md`](../../docs/ai-guidelines/SECURITY_AND_MULTITENANCY.md)
- **Complete tech stack:** [`AGENTS.md`](../../AGENTS.md) Sections 1-2, 5-7

---

**Status:** Production Ready | Last Updated: November 9, 2026
