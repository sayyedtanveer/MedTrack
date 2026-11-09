# MedTrack Developer Setup

This document is the reproducible setup guide for a new developer or a new laptop.
The recommended workflow uses Docker only for PostgreSQL and Redis, while the backend
and frontend run locally with hot reload.

## 1. Install prerequisites

Install these tools before cloning the repository:

- Git
- Docker Desktop (Windows or macOS) or Docker Engine plus Docker Compose (Linux)
- Python 3.11 or newer
- Node.js 20 or newer, including npm

On Windows, enable the WSL 2 backend in Docker Desktop. Restart Docker Desktop after
installation and confirm it is running before continuing.

Verify the tools:

```powershell
git --version
docker --version
docker compose version
python --version
node --version
npm --version
```

## 2. Clone the project

Replace `<repository-url>` with the repository URL:

```powershell
git clone <repository-url>
cd MedTrack
```

Linux/macOS use the same commands:

```bash
git clone <repository-url>
cd MedTrack
```

## 3. Create environment files

Create the backend environment file:

```powershell
Copy-Item .env.example .env
```

On Linux/macOS:

```bash
cp .env.example .env
```

Open `.env` and replace `JWT_SECRET_KEY` with a long random value. The other
development defaults are ready for the Docker PostgreSQL and Redis services.

Create the frontend environment file:

```powershell
Copy-Item frontend\.env.example frontend\.env
```

On Linux/macOS:

```bash
cp frontend/.env.example frontend/.env
```

Do not commit either `.env` file. They may contain passwords or API keys.

## 4. Start PostgreSQL and Redis

From the repository root:

```powershell
docker compose up -d postgres redis
docker compose ps
```

Wait until both services show `healthy` or `running`. The local connection details
are:

| Service | Address | Credentials |
| --- | --- | --- |
| PostgreSQL | `localhost:5432` | database `erp_db`, user `erp_user`, password `erp_password` |
| Redis | `localhost:6379` | no password |

## 5. Set up and migrate the backend

### Fast Track: 1-Click Database Setup (Recommended)
If you are running local PostgreSQL or need a complete development database with all tables and sample seed data (admin, tenant, UOMs, BOMs, materials):

- **Windows PowerShell:**
  ```powershell
  .\setup_db.ps1
  ```
- **Linux / macOS / WSL:**
  ```bash
  chmod +x ./setup_db.sh
  ./setup_db.sh
  ```
*(If you are using Docker, PostgreSQL automatically initializes the schema and seed data on the first `docker compose up -d postgres`).*

---

### Python Virtual Environment & Dependencies

#### Windows PowerShell

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
alembic upgrade head
python -c "import uvicorn; print('uvicorn is installed')"
```

If PowerShell activation is unavailable, use Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
alembic upgrade head
python -c "import uvicorn; print('uvicorn is installed')"
```

#### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
alembic upgrade head
```

The virtual environment must be activated whenever backend commands are run. A
successful migration ends without an error and verifies that the database is at the latest revision.

## 6. Install frontend dependencies

Open a second terminal in the repository root:

```powershell
cd frontend
npm ci
```

Use `npm install` instead if `frontend/package-lock.json` is not present in the
copy of the repository.

## 7. Start the application

Use three terminals. Keep each process running.

### Terminal 1: backend

From the repository root, with `.venv` activated:

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload
```

Linux/macOS:

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Terminal 2: frontend

```powershell
cd frontend
npm run dev
```

The frontend is served at `http://localhost:5000` and proxies `/api` requests to
the backend at `http://localhost:8001`.

### Terminal 3: checks

```powershell
Invoke-WebRequest http://localhost:8001/health
```

Open these URLs in a browser:

- Application: `http://localhost:5000`
- API documentation: `http://localhost:8001/docs`
- Backend health: `http://localhost:8001/health`

On Windows, `run.ps1` or `run.bat` can start both development servers after the
database and Redis containers are running. The manual commands above are easier
to diagnose when setup fails.

## 8. Accounts and Login

If you set up the database using `setup_db.ps1` / `setup_db.sh` or Docker initialization, the database already contains standard development data, RBAC roles, and administrative accounts.

You can also register a new company and administrator anytime:
- Use the registration screen in the frontend (`http://localhost:5000`), or
- Use the `POST /api/v1/auth/register-tenant` endpoint in Swagger at `http://localhost:8001/docs`.

## 9. Stop and restart

Stop the backend and frontend with `Ctrl+C` in their terminals. Stop the supporting
services with:

```powershell
docker compose down
```

This keeps the database data in Docker volumes. To remove all local development
data and start with an empty database:

```powershell
docker compose down -v
```

## Troubleshooting

### `JWT_SECRET_KEY` validation error

Ensure `.env` exists in the repository root and contains a non-empty value, for
example `JWT_SECRET_KEY=change-this-to-a-long-random-development-secret`.

### `No module named uvicorn`

The dependencies were not installed in the active virtual environment. From the
repository root, run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload
```

Using `.venv\Scripts\python.exe` ensures that the backend uses the project
environment instead of another Python installation on the computer.

### Cannot connect to PostgreSQL

Run `docker compose ps` and `docker compose logs postgres`. Confirm that port
`5432` is not being used by another PostgreSQL installation. Stop that service or
change the published port and the `DATABASE_URL` values together.

### Port already in use

The default ports are PostgreSQL `5432`, Redis `6379`, backend `8001`, and
frontend `5000`. Stop the conflicting process or change the matching command and
frontend environment target.

### PDF generation fails on Windows

Use Docker for PDF-related work. WeasyPrint requires native GTK/Cairo libraries
that are not installed automatically by Windows Python environments.

### Frontend says it cannot reach the server

Confirm that the backend terminal is running on port `8001`, that
`frontend/.env` contains `VITE_API_TARGET=http://127.0.0.1:8001`, and restart
the Vite process after changing environment values.

## Useful development commands

```powershell
# Backend tests
python -m pytest

# Frontend typecheck/build
cd frontend
npm run build

# Create a migration after changing models
cd ..
alembic revision --autogenerate -m "describe the schema change"

# Apply migrations
alembic upgrade head
```
