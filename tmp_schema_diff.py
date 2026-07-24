"""
Compare what's in the DB vs what SQLAlchemy models expect.
Prints ALTER TABLE statements for missing tables and columns.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncConnection

DB_URL = "postgresql+asyncpg://postgres:123@localhost:5432/medtrack"

# The tables the confirm flow actually touches
TABLES_NEEDED = [
    "inventory_reservations",
    "material_shortages",
]

async def get_db_columns(conn: AsyncConnection, table: str) -> set[str]:
    r = await conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        f"WHERE table_schema='public' AND table_name='{table}'"
    ))
    return {row[0] for row in r}

async def table_exists(conn: AsyncConnection, table: str) -> bool:
    r = await conn.execute(text(
        "SELECT 1 FROM information_schema.tables "
        f"WHERE table_schema='public' AND table_name='{table}'"
    ))
    return r.scalar_one_or_none() is not None

async def main():
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:

        # 1. Check inventory_reservations
        if not await table_exists(conn, "inventory_reservations"):
            print("-- MISSING TABLE: inventory_reservations")
            print("""
CREATE TABLE inventory_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    material_id UUID NOT NULL REFERENCES materials(id),
    quantity NUMERIC(20,4) NOT NULL,
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reference_type VARCHAR(64) NOT NULL,
    reference_id UUID NOT NULL,
    sales_order_id UUID,
    sales_order_line_id UUID,
    unit_id UUID,
    created_by UUID,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    released_at TIMESTAMPTZ,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_inv_res_tenant_material ON inventory_reservations(tenant_id, material_id);
CREATE INDEX ix_inv_res_reference ON inventory_reservations(reference_type, reference_id);
CREATE INDEX ix_inv_res_sales_order ON inventory_reservations(sales_order_id);
""")
        else:
            print("-- inventory_reservations EXISTS")

        # 2. Check material_shortages
        if not await table_exists(conn, "material_shortages"):
            print("-- MISSING TABLE: material_shortages")
            print("""
CREATE TABLE material_shortages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    work_order_id UUID REFERENCES work_orders(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES materials(id),
    required_quantity NUMERIC(20,4) NOT NULL DEFAULT 0,
    available_quantity NUMERIC(20,4) NOT NULL DEFAULT 0,
    shortage_quantity NUMERIC(20,4) NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    resolved_at TIMESTAMPTZ,
    notes TEXT,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_ms_tenant_wo ON material_shortages(tenant_id, work_order_id);
""")
        else:
            print("-- material_shortages EXISTS")

        # 3. Check sales_order_lines for shortfall/production columns
        so_lines_cols = await get_db_columns(conn, "sales_order_lines")
        missing_so_cols = []
        needed_so_cols = {
            "shortfall_quantity": "NUMERIC(20,4) NOT NULL DEFAULT 0",
            "production_required": "BOOLEAN NOT NULL DEFAULT FALSE",
            "work_order_id": "UUID",
            "allocated_quantity": "NUMERIC(20,4) NOT NULL DEFAULT 0",
            "shipped_quantity": "NUMERIC(20,4) NOT NULL DEFAULT 0",
            "backorder_quantity": "NUMERIC(20,4) NOT NULL DEFAULT 0",
            "status": "VARCHAR(32) NOT NULL DEFAULT 'pending'",
        }
        for col, dtype in needed_so_cols.items():
            if col not in so_lines_cols:
                missing_so_cols.append(f"    ADD COLUMN {col} {dtype}")

        if missing_so_cols:
            print(f"\n-- MISSING COLUMNS on sales_order_lines:")
            print("ALTER TABLE sales_order_lines")
            print(",\n".join(missing_so_cols) + ";")
        else:
            print("\n-- sales_order_lines columns OK")

        # 4. Check sales_orders for confirm-related columns
        so_cols = await get_db_columns(conn, "sales_orders")
        needed_so = {
            "confirmed_at": "TIMESTAMPTZ",
            "confirmed_by": "VARCHAR(255)",
            "ready_at": "TIMESTAMPTZ",
        }
        missing = [f"    ADD COLUMN IF NOT EXISTS {col} {dtype}" 
                   for col, dtype in needed_so.items() if col not in so_cols]
        if missing:
            print(f"\n-- MISSING COLUMNS on sales_orders:")
            print("ALTER TABLE sales_orders")
            print(",\n".join(missing) + ";")
        else:
            print("\n-- sales_orders columns OK")

        # 5. Check materials for reserved_stock column
        mat_cols = await get_db_columns(conn, "materials")
        mat_needed = {
            "reserved_stock": "NUMERIC(20,4) NOT NULL DEFAULT 0",
        }
        missing_mat = [f"    ADD COLUMN IF NOT EXISTS {col} {dtype}"
                       for col, dtype in mat_needed.items() if col not in mat_cols]
        if missing_mat:
            print(f"\n-- MISSING COLUMNS on materials:")
            print("ALTER TABLE materials")
            print(",\n".join(missing_mat) + ";")
        else:
            print("\n-- materials.reserved_stock OK:", "reserved_stock" in mat_cols)

asyncio.run(main())
