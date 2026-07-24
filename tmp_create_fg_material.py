"""Create a finished goods material for the correct tenant."""
import asyncio, uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from pathlib import Path
from datetime import datetime, timezone

TENANT_ID = "52323f77-709b-4cb8-818e-c1ad16262541"

def read_db_url():
    for line in Path(".env").read_text().splitlines():
        for key in ("ASYNC_DATABASE_URL", "DATABASE_URL"):
            if line.startswith(key + "="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                if "asyncpg" not in url:
                    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
                    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
                return url

async def main():
    engine = create_async_engine(read_db_url())
    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        # Get the unit of measure (use first available for this tenant, or NOS)
        uom = await conn.execute(text(
            "SELECT id FROM units_of_measure WHERE tenant_id = :tid AND is_active = true LIMIT 1"
        ), {"tid": TENANT_ID})
        uom_row = uom.fetchone()
        # Fallback: get any global unit
        if not uom_row:
            uom = await conn.execute(text(
                "SELECT id FROM units_of_measure WHERE is_active = true LIMIT 1"
            ))
            uom_row = uom.fetchone()

        uom_id = uom_row[0] if uom_row else None
        print(f"Using UOM id: {uom_id}")

        # Insert finished goods material
        mat_id = uuid.uuid4()
        await conn.execute(text("""
            INSERT INTO materials (
                id, tenant_id, code, name, description,
                material_type, base_unit_id, current_stock, reserved_stock,
                current_cost, reorder_level,
                is_batch_tracked, is_serialized, inspection_required,
                is_active, is_deleted, created_at, updated_at
            ) VALUES (
                :id, :tid, :code, :name, :desc,
                'finished', :uom_id, 0, 0,
                0, 0,
                false, false, false,
                true, false, :now, :now
            )
            ON CONFLICT (tenant_id, code) DO UPDATE SET
                material_type = 'finished',
                is_active = true,
                is_deleted = false,
                updated_at = :now
        """), {
            "id": mat_id,
            "tid": TENANT_ID,
            "code": "FG-MET-0001",
            "name": "Rotameter FG",
            "desc": "Finished goods material for Rotameter product variant",
            "uom_id": uom_id,
            "now": now,
        })
        print(f"Created FG material: FG-MET-0001 (id={mat_id})")

        # Verify
        r = await conn.execute(text(
            "SELECT id, code, name, material_type, is_active FROM materials "
            "WHERE tenant_id = :tid ORDER BY material_type, code"
        ), {"tid": TENANT_ID})
        rows = r.fetchall()
        print(f"\nAll materials for your tenant:")
        for row in rows:
            print(f"  [{row[3]}] {row[1]} — {row[2]} (active={row[4]})")

    await engine.dispose()
    print("\nDone. Refresh the variant edit form — FG-MET-0001 will now appear in the dropdown.")

asyncio.run(main())
