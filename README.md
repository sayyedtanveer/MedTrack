# MedTrack ERP

A multi-tenant manufacturing ERP system built with **FastAPI**, **SQLAlchemy (async)**, and **Domain-Driven Design (DDD)** with CQRS.

---

## Architecture

```
backend/app/
├── domain/          # DDD domain layer – entities, value objects, domain events
├── application/     # CQRS use cases – commands, queries, handlers
├── infrastructure/  # Persistence, security, storage, events, logging
└── interfaces/      # FastAPI routes, middleware, schemas
```

---

## Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development without Docker)
- PostgreSQL 15+ (if running locally)

---

## Quick Start (Docker)

```bash
# 1. Clone and configure environment
git clone <repo-url>
cd MedTrack
cp .env.example .env
# Edit .env – at minimum set JWT_SECRET_KEY to a secure random string

# 2. Start all services
docker-compose up --build -d

# 3. Run database migrations
docker-compose exec backend alembic upgrade head

# 4. Verify
curl http://localhost:8000/health
# → {"status":"healthy","environment":"development"}
```

---

## Local Development (without Docker)

```bash
# 1. Create virtualenv
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Fill in DATABASE_URL pointing to your local Postgres instance

# 4. Run migrations
alembic upgrade head

# 5. Start dev server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Documentation

Once running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## PDF Generation

The ERP uses **WeasyPrint** for enterprise document generation (Work Orders, POs, Invoices, QC Reports, Delivery Challans).

### Quick Setup

```bash
# Docker (recommended - WeasyPrint dependencies pre-installed)
docker-compose up --build

# Test PDF generation
curl http://localhost:8000/api/v1/documents/test/pdf
```

### Local Development

**Windows**: PDF generation requires GTK libraries. Backend will start with PDF features disabled gracefully. Use Docker for full functionality.

**Linux/Mac**: Install WeasyPrint dependencies:
```bash
# Ubuntu/Debian
sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info fonts-dejavu

# macOS
brew install cairo pango gdk-pixbuf libffi
```

### Render.com Compatibility

The Dockerfile includes all WeasyPrint dependencies. Deployment works out-of-the-box on Render.com without manual configuration.

**For detailed architecture, troubleshooting, and storage structure, see [docs/pdf-generation.md](docs/pdf-generation.md).**

---

## Key Endpoints (Phase 0)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/auth/register-tenant` | Register new tenant + admin user |
| `POST` | `/api/v1/auth/login` | Login → JWT access token |
| `GET` | `/api/v1/auth/me` | Current user profile |
| `GET` | `/api/v1/tenants/{id}` | Get tenant details (admin only) |
| `POST` | `/api/v1/files/upload` | Upload a file |

---

## Running Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Rollback one step
alembic downgrade -1
```

---

## Environment Variables

See [`.env.example`](.env.example) for all required variables with descriptions.

---

## Project Principles

- **DDD**: Each bounded context is self-contained (domain, application, infrastructure layers)
- **CQRS**: Commands (writes) and Queries (reads) are separate pipelines
- **Multi-tenancy**: All data is scoped to `tenant_id`; extracted per-request via middleware
- **Soft Delete**: No hard deletes — `is_deleted` / `deleted_at` on all entities
- **Interface-first**: Every service hides behind an abstract interface for easy replacement
