# MedTrack Database Scripts & Multi-Developer Guide

This directory contains the database schema, seed data, and migration reference for the **MedTrack ERP** project.

---

## 📁 Files in this Directory

| File | Purpose | When to Use |
| :--- | :--- | :--- |
| **`medtrack_complete_dev.sql`** | **Complete Database (Schema + Seed Data)** | **Recommended for all developers.** Sets up all 98 tables, extensions, enum types, indexes, and ready-to-use development seed data (tenants, admin accounts, RBAC roles/permissions, UOMs, and demo items). |
| **`medtrack_schema_latest.sql`** | **DDL Schema Only** | Sets up only the database schema without test rows. |
| **`setup_db.ps1`** (Root) | **Windows 1-Click Installer** | Automatically creates the PostgreSQL database and applies `medtrack_complete_dev.sql`. |
| **`setup_db.sh`** (Root) | **Linux/macOS 1-Click Installer** | Shell script for Linux, macOS, and WSL. |

---

## 🚀 Quick Setup for New Developers

### Option A: Using Local PostgreSQL (Windows / Mac / Linux)

#### 1. Windows (PowerShell)
```powershell
.\setup_db.ps1
```
*(Prompts for password if needed, or reads from your `.env` file).*

Alternatively, run manually with `psql`:
```powershell
$env:PGPASSWORD="123"
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE medtrack;"
psql -U postgres -h localhost -p 5432 -d medtrack -f db_scripts\medtrack_complete_dev.sql
```

#### 2. Linux / macOS / WSL
```bash
chmod +x ./setup_db.sh
./setup_db.sh
```

---

### Option B: Using Docker Compose
If developers prefer Docker, PostgreSQL automatically executes `medtrack_complete_dev.sql` on the initial container run:

```bash
docker compose up -d postgres redis
```

---

## 👥 Multi-Developer Git Workflow (Best Practices)

When multiple developers are working on features concurrently, follow this standard pattern:

### 1. New Developer Onboarding (Day 1)
Run `setup_db.ps1` or `setup_db.sh` to get a complete working database in ~5 seconds.

### 2. Daily Development & Pulling from Git
When another developer adds a table or column and commits an Alembic migration:
```bash
git pull origin main
alembic upgrade head
```
*(Your local data remains intact, and the schema updates automatically).*

### 3. Adding New Tables or Modifying Columns
1. Update or create your SQLAlchemy model in `backend/app/infrastructure/persistence/models/`.
2. Generate an Alembic migration:
   ```bash
   alembic revision --autogenerate -m "describe_your_change"
   ```
3. Inspect the generated file in `alembic/versions/` to verify accuracy.
4. Apply it locally:
   ```bash
   alembic upgrade head
   ```
5. Commit both your model and the new `alembic/versions/*.py` file to Git.

### 4. Resolving Migration Conflicts (Branch Divergence)
If two developers create migrations from the same base revision on separate Git branches, Alembic will notify you of multiple heads:
```bash
alembic heads
```
Merge them into a single head:
```bash
alembic merge heads -m "merge_feature_heads"
git add alembic/versions/*
git commit -m "Merge migration heads"
```
