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
- Node.js 20+ & npm (for frontend)

---

## 🗄️ Database Setup & Developer Quick Reference

MedTrack includes an automated database initialization script and Alembic migration pipeline so developers can set up their local database in seconds without migration errors or manual table creation.

### 📌 Which File Should Developers Refer To?

| Task | File to Refer To / Run | Description |
| :--- | :--- | :--- |
| **Windows 1-Click DB Setup** | [`setup_db.ps1`](setup_db.ps1) | Run `.\setup_db.ps1` in PowerShell. Creates the DB, applies schema, seeds users/roles/materials, and verifies table count. |
| **Linux/Mac 1-Click DB Setup** | [`setup_db.sh`](setup_db.sh) | Run `./setup_db.sh` in terminal for Linux, macOS, or WSL. |
| **Docker Compose Setup** | [`docker-compose.yml`](docker-compose.yml) | Runs `docker compose up -d postgres`. Automatically mounts and applies the complete dev database on first boot. |
| **Complete DB Script** | [`db_scripts/medtrack_complete_dev.sql`](db_scripts/medtrack_complete_dev.sql) | Pure plain-text SQL script (all 98 tables, UUID/pgcrypto extensions, ENUM types, constraints, and dev seed data). |
| **Schema Only (No Data)** | [`db_scripts/medtrack_schema_latest.sql`](db_scripts/medtrack_schema_latest.sql) | Pure DDL schema-only script without test rows. |
| **Database Documentation** | [`db_scripts/README.md`](db_scripts/README.md) | In-depth guide on database structure, seed contents, and Alembic conflict resolution. |
| **Full Environment Setup** | [`SETUP.md`](SETUP.md) | Complete step-by-step developer guide (virtual environment, frontend, WeasyPrint, and troubleshooting). |

---

## 🚀 Quick Start (Docker)

```bash
# 1. Clone and configure environment
git clone <repo-url>
cd MedTrack
cp .env.example .env
# Edit .env – at minimum set JWT_SECRET_KEY to a secure random string

# 2. Start all services (PostgreSQL auto-initializes from db_scripts/medtrack_complete_dev.sql)
docker compose up -d postgres redis

# 3. Start backend and frontend
docker compose up -d

# 4. Verify
curl http://localhost:8000/health
# → {"status":"healthy","environment":"development"}
```

---

## 💻 Local Development (without Docker)

```powershell
# 1. Configure environment
Copy-Item .env.example .env   # (or cp .env.example .env on Linux/Mac)

# 2. Setup the database (creates tables + seed admin, tenants, roles, and materials)
.\setup_db.ps1               # Windows PowerShell
# ./setup_db.sh              # Linux / macOS / WSL

# 3. Create virtualenv & install dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1 # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 4. Verify Alembic status
alembic current
# -> c84cb0239a28 (head)

# 5. Start dev server
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8001
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

## Database Migrations & Multi-Developer Git Workflow

When developing features that modify SQLAlchemy models, maintain the database with Alembic:

```bash
# 1. After pulling latest changes from Git
alembic upgrade head

# 2. When you modify an ORM model in backend/app/.../models/
alembic revision --autogenerate -m "describe_your_changes"

# 3. Apply your migration locally
alembic upgrade head

# 4. If concurrent branches create multiple heads
alembic heads
alembic merge heads -m "merge_branch_heads"

# 5. Check current revision
alembic current
```

For complete details on database management, see [`db_scripts/README.md`](db_scripts/README.md).

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
