"""Apply subcontracting schema changes directly via SQL.
Idempotent — safe to run multiple times.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

URL = "postgresql+asyncpg://postgres:123@localhost:5432/medtrack"


async def col(conn, table: str, column: str) -> bool:
    r = await conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        f"WHERE table_name='{table}' AND column_name='{column}'"
    ))
    return bool(r.fetchone())


async def tbl(conn, table: str) -> bool:
    r = await conn.execute(text(
        "SELECT 1 FROM information_schema.tables "
        f"WHERE table_name='{table}'"
    ))
    return bool(r.fetchone())


async def apply():
    engine = create_async_engine(URL)
    async with engine.begin() as c:

        # ── subcontract_orders: new columns ───────────────────────────────
        for column, ddl in [
            ("bom_id",            "UUID REFERENCES boms(id) ON DELETE SET NULL"),
            ("due_date",          "DATE"),
            ("notes",             "TEXT"),
            ("output_batch_id",   "UUID REFERENCES batches(id) ON DELETE SET NULL"),
            ("received_quantity", "NUMERIC(15,3) NOT NULL DEFAULT 0"),
            ("created_by",        "UUID"),
            ("approved_by",       "UUID"),
            ("approved_at",       "TIMESTAMP WITH TIME ZONE"),
        ]:
            if not await col(c, "subcontract_orders", column):
                await c.execute(text(f"ALTER TABLE subcontract_orders ADD COLUMN {column} {ddl}"))
                print(f"  + subcontract_orders.{column}")
            else:
                print(f"  = subcontract_orders.{column} already exists")

        # Widen status column if it was VARCHAR(20) — need VARCHAR(30) for new values
        await c.execute(text(
            "ALTER TABLE subcontract_orders ALTER COLUMN status TYPE VARCHAR(30)"
        ))
        print("  ~ subcontract_orders.status widened to VARCHAR(30)")

        # ── subcontract_order_lines: new table ────────────────────────────
        if not await tbl(c, "subcontract_order_lines"):
            await c.execute(text("""
                CREATE TABLE subcontract_order_lines (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL,
                    subcontract_order_id UUID NOT NULL
                        REFERENCES subcontract_orders(id) ON DELETE CASCADE,
                    material_id UUID NOT NULL
                        REFERENCES materials(id) ON DELETE RESTRICT,
                    required_quantity NUMERIC(15,3) NOT NULL,
                    issued_quantity   NUMERIC(15,3) NOT NULL DEFAULT 0,
                    returned_quantity NUMERIC(15,3) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
                )
            """))
            await c.execute(text(
                "CREATE INDEX ix_sco_line_order ON subcontract_order_lines(subcontract_order_id)"
            ))
            await c.execute(text(
                "CREATE INDEX ix_sco_line_tenant ON subcontract_order_lines(tenant_id)"
            ))
            print("  + subcontract_order_lines created")
        else:
            print("  = subcontract_order_lines already exists")

        # ── subcontract_material_issues: new columns ──────────────────────
        for column, ddl in [
            ("batch_id",          "UUID REFERENCES batches(id) ON DELETE SET NULL"),
            ("returned_quantity", "NUMERIC(15,3) NOT NULL DEFAULT 0"),
            ("from_location_id",  "UUID REFERENCES locations(id) ON DELETE SET NULL"),
            ("issued_by",         "UUID"),
        ]:
            if not await col(c, "subcontract_material_issues", column):
                await c.execute(text(
                    f"ALTER TABLE subcontract_material_issues ADD COLUMN {column} {ddl}"
                ))
                print(f"  + subcontract_material_issues.{column}")
            else:
                print(f"  = subcontract_material_issues.{column} already exists")

        # Stamp migration in alembic_version
        r = await c.execute(text(
            "SELECT 1 FROM alembic_version WHERE version_num = 'c5d9f2b1e8a3'"
        ))
        if not r.fetchone():
            await c.execute(text(
                "INSERT INTO alembic_version (version_num) VALUES ('c5d9f2b1e8a3')"
            ))
            print("  + stamped c5d9f2b1e8a3 in alembic_version")

    await engine.dispose()
    print("\nDone.")


asyncio.run(apply())
