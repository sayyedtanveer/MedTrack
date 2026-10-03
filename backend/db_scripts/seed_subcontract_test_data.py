"""Seed test data for Subcontracting / Outside Processing flow.

Creates:
- 1 Test Supplier (SUP-SC-TEST-001)
- 10 Raw Materials (SC-RM-001 through SC-RM-010)
- 1 Semi-Finished Material (SC-SF-001)
- 1 Item Variant linked to SC-SF-001
- 1 BOM with 10 components
- Test inventory stock for all 10 raw materials

Safe to run multiple times - checks for existing data before inserting.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def execute(conn, sql: str, **params):
    return await conn.execute(text(sql), params)


async def scalar(conn, sql: str, **params):
    result = await execute(conn, sql, **params)
    return result.scalar_one_or_none()


async def resolve_tenant_id(conn, tenant_id_arg: str | None) -> uuid.UUID:
    """Get tenant ID from arg or first active tenant."""
    if tenant_id_arg:
        return uuid.UUID(tenant_id_arg)
    tenant_id = await scalar(
        conn,
        "SELECT id FROM tenants WHERE is_active = true ORDER BY created_at ASC LIMIT 1",
    )
    if tenant_id is None:
        raise RuntimeError("No active tenant found. Pass --tenant-id explicitly.")
    return tenant_id


async def resolve_user_id(conn, tenant_id: uuid.UUID) -> uuid.UUID:
    """Get first active user for tenant."""
    user_id = await scalar(
        conn,
        """
        SELECT id FROM users
        WHERE tenant_id = :tenant_id AND is_active = true AND COALESCE(is_deleted, false) = false
        ORDER BY created_at ASC LIMIT 1
        """,
        tenant_id=tenant_id,
    )
    if user_id is None:
        raise RuntimeError(f"No active user found for tenant {tenant_id}.")
    return user_id


async def ensure_category(conn, tenant_id: uuid.UUID, now: datetime) -> uuid.UUID:
    """Get or create 'Test Subcontract' category."""
    cat_id = await scalar(
        conn,
        "SELECT id FROM material_categories WHERE tenant_id = :tid AND name = 'Test Subcontract'",
        tid=tenant_id,
    )
    if cat_id:
        print("  Category: Test Subcontract (exists)")
        return cat_id

    cat_id = uuid.uuid4()
    await execute(
        conn,
        """
        INSERT INTO material_categories (id, tenant_id, name, code_prefix, is_active, is_deleted, created_at, updated_at)
        VALUES (:id, :tid, 'Test Subcontract', 'SC', true, false, :now, :now)
        """,
        id=cat_id,
        tid=tenant_id,
        now=now,
    )
    print("  Category: Test Subcontract (created)")
    return cat_id


async def ensure_uom(conn, tenant_id: uuid.UUID, now: datetime) -> uuid.UUID:
    """Get or create 'PCS' unit."""
    uom_id = await scalar(
        conn,
        "SELECT id FROM units_of_measure WHERE tenant_id = :tid AND code = 'PCS'",
        tid=tenant_id,
    )
    if uom_id:
        print("  UOM: PCS (exists)")
        return uom_id

    uom_id = uuid.uuid4()
    await execute(
        conn,
        """
        INSERT INTO units_of_measure (id, tenant_id, code, name, created_at, updated_at)
        VALUES (:id, :tid, 'PCS', 'Pieces', :now, :now)
        """,
        id=uom_id,
        tid=tenant_id,
        now=now,
    )
    print("  UOM: PCS (created)")
    return uom_id


async def ensure_location(conn, tenant_id: uuid.UUID, now: datetime) -> uuid.UUID:
    """Get or create 'Test Warehouse' location."""
    loc_id = await scalar(
        conn,
        "SELECT id FROM locations WHERE tenant_id = :tid AND name = 'Test Warehouse' AND location_type = 'warehouse'",
        tid=tenant_id,
    )
    if loc_id:
        print("  Location: Test Warehouse (exists)")
        return loc_id

    loc_id = uuid.uuid4()
    await execute(
        conn,
        """
        INSERT INTO locations (id, tenant_id, name, location_type, is_active, created_at, updated_at)
        VALUES (:id, :tid, 'Test Warehouse', 'warehouse', true, :now, :now)
        """,
        id=loc_id,
        tid=tenant_id,
        now=now,
    )
    print("  Location: Test Warehouse (created)")
    return loc_id


async def ensure_supplier(conn, tenant_id: uuid.UUID, user_id: uuid.UUID, now: datetime) -> uuid.UUID:
    """Get or create test supplier."""
    supplier_id = await scalar(
        conn,
        "SELECT id FROM suppliers WHERE tenant_id = :tid AND code = 'SUP-SC-TEST-001'",
        tid=tenant_id,
    )
    if supplier_id:
        print("  Supplier: SUP-SC-TEST-001 (exists)")
        return supplier_id

    supplier_id = uuid.uuid4()
    await execute(
        conn,
        """
        INSERT INTO suppliers (
            id, tenant_id, code, name, contact_name, email, phone,
            address, city, country, status, is_active, created_by, created_at, updated_at
        ) VALUES (
            :id, :tid, 'SUP-SC-TEST-001', 'Test Subcontract Vendor',
            'John Vendor', 'vendor@test.local', '+1234567890',
            '123 Test St', 'Test City', 'Test Country', 'active', true,
            :uid, :now, :now
        )
        """,
        id=supplier_id,
        tid=tenant_id,
        uid=user_id,
        now=now,
    )
    print("  Supplier: SUP-SC-TEST-001 (created)")
    return supplier_id


async def ensure_raw_materials(
    conn,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    cat_id: uuid.UUID,
    uom_id: uuid.UUID,
    location_id: uuid.UUID,
    now: datetime,
) -> list[uuid.UUID]:
    """Create 10 raw materials with stock."""
    material_ids = []
    for i in range(1, 11):
        code = f"SC-RM-{i:03d}"
        name = f"SC Test Raw Material {i:02d}"

        mat_id = await scalar(
            conn,
            "SELECT id FROM materials WHERE tenant_id = :tid AND code = :code",
            tid=tenant_id,
            code=code,
        )

        if not mat_id:
            mat_id = uuid.uuid4()
            await execute(
                conn,
                """
                INSERT INTO materials (
                    id, tenant_id, code, name, material_type, category_id, base_unit_id,
                    location_id, reorder_level, is_batch_tracked, is_serialized,
                    is_active, is_deleted, created_by, created_at, updated_at
                ) VALUES (
                    :id, :tid, :code, :name, 'raw', :cid, :uid,
                    :lid, 10, false, false,
                    true, false, :user, :now, :now
                )
                """,
                id=mat_id,
                tid=tenant_id,
                code=code,
                name=name,
                cid=cat_id,
                uid=uom_id,
                lid=location_id,
                user=user_id,
                now=now,
            )
            print(f"  Material: {code} (created)")
        else:
            print(f"  Material: {code} (exists)")

        # Ensure stock level exists
        sl_exists = await scalar(
            conn,
            "SELECT 1 FROM stock_levels WHERE tenant_id = :tid AND material_id = :mid AND location_id = :lid",
            tid=tenant_id,
            mid=mat_id,
            lid=location_id,
        )
        if not sl_exists:
            await execute(
                conn,
                """
                INSERT INTO stock_levels (
                    id, tenant_id, material_id, location_id,
                    quantity_on_hand, reserved_quantity, updated_at
                ) VALUES (
                    :id, :tid, :mid, :lid, 10, 0, :now
                )
                """,
                id=uuid.uuid4(),
                tid=tenant_id,
                mid=mat_id,
                lid=location_id,
                now=now,
            )
            print(f"    Stock: {code} = 10 (created)")
        else:
            print(f"    Stock: {code} (exists)")

        material_ids.append(mat_id)

    return material_ids


async def ensure_semi_finished_material(
    conn,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    cat_id: uuid.UUID,
    uom_id: uuid.UUID,
    location_id: uuid.UUID,
    now: datetime,
) -> uuid.UUID:
    """Create semi-finished material."""
    code = "SC-SF-001"
    name = "Test Subcontracted Assembly"

    mat_id = await scalar(
        conn,
        "SELECT id FROM materials WHERE tenant_id = :tid AND code = :code",
        tid=tenant_id,
        code=code,
    )

    if mat_id:
        print(f"  Material: {code} (exists)")
        return mat_id

    mat_id = uuid.uuid4()
    await execute(
        conn,
        """
        INSERT INTO materials (
            id, tenant_id, code, name, material_type, category_id, base_unit_id,
            location_id, reorder_level, is_batch_tracked, is_serialized,
            is_active, is_deleted, created_by, created_at, updated_at
        ) VALUES (
            :id, :tid, :code, :name, 'semi_finished', :cid, :uid,
            :lid, 5, false, false,
            true, false, :user, :now, :now
        )
        """,
        id=mat_id,
        tid=tenant_id,
        code=code,
        name=name,
        cid=cat_id,
        uid=uom_id,
        lid=location_id,
        user=user_id,
        now=now,
    )
    print(f"  Material: {code} (created)")
    return mat_id


async def ensure_item_template(conn, tenant_id: uuid.UUID, user_id: uuid.UUID, now: datetime) -> uuid.UUID:
    """Get or create test template."""
    tmpl_id = await scalar(
        conn,
        "SELECT id FROM item_templates WHERE tenant_id = :tid AND code = 'SC-TEST-TMPL'",
        tid=tenant_id,
    )
    if tmpl_id:
        print("  Template: SC-TEST-TMPL (exists)")
        return tmpl_id

    tmpl_id = uuid.uuid4()
    await execute(
        conn,
        """
        INSERT INTO item_templates (
            id, tenant_id, code, name, description, attribute_definitions,
            is_active, is_deleted, created_by, created_at, updated_at
        ) VALUES (
            :id, :tid, 'SC-TEST-TMPL', 'Subcontract Test Template',
            'Template for subcontract test data', '[]'::jsonb,
            true, false, :uid, :now, :now
        )
        """,
        id=tmpl_id,
        tid=tenant_id,
        uid=user_id,
        now=now,
    )
    print("  Template: SC-TEST-TMPL (created)")
    return tmpl_id


async def ensure_item_variant(
    conn,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    template_id: uuid.UUID,
    material_id: uuid.UUID,
    uom_id: uuid.UUID,
    now: datetime,
) -> uuid.UUID:
    """Create item variant linked to semi-finished material."""
    code = "SC-SF-001"

    var_id = await scalar(
        conn,
        "SELECT id FROM item_variants WHERE tenant_id = :tid AND code = :code",
        tid=tenant_id,
        code=code,
    )

    if var_id:
        print(f"  Variant: {code} (exists)")
        return var_id

    var_id = uuid.uuid4()
    await execute(
        conn,
        """
        INSERT INTO item_variants (
            id, tenant_id, template_id, code, name, variant_key, attribute_values,
            base_unit_id, material_id, standard_cost, is_active, is_deleted,
            code_locked, created_at, updated_at
        ) VALUES (
            :id, :tid, :tmpl, :code, 'Test Subcontracted Assembly', 'BASE',
            '{}'::jsonb, :uid, :mid, 0, true, false, true, :now, :now
        )
        """,
        id=var_id,
        tid=tenant_id,
        tmpl=template_id,
        code=code,
        uid=uom_id,
        mid=material_id,
        now=now,
    )
    print(f"  Variant: {code} (created, linked to material)")
    return var_id


async def ensure_bom(
    conn,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    variant_id: uuid.UUID,
    raw_material_ids: list[uuid.UUID],
    uom_id: uuid.UUID,
    now: datetime,
) -> uuid.UUID:
    """Create BOM with 10 components."""
    bom_code = "BOM-SC-TEST-001"

    bom_id = await scalar(
        conn,
        "SELECT id FROM boms WHERE tenant_id = :tid AND variant_id = :vid AND is_active = true",
        tid=tenant_id,
        vid=variant_id,
    )

    if bom_id:
        print(f"  BOM: {bom_code} (exists)")
        return bom_id

    bom_id = uuid.uuid4()
    await execute(
        conn,
        """
        INSERT INTO boms (
            id, tenant_id, variant_id, version, is_active, valid_from,
            is_deleted, created_by, created_at, updated_at
        ) VALUES (
            :id, :tid, :vid, 'A', true, :now, false, :uid, :now, :now
        )
        """,
        id=bom_id,
        tid=tenant_id,
        vid=variant_id,
        uid=user_id,
        now=now,
    )
    print(f"  BOM: {bom_code} (created)")

    # Add 10 component lines
    for idx, mat_id in enumerate(raw_material_ids, start=1):
        line_id = uuid.uuid4()
        await execute(
            conn,
            """
            INSERT INTO bom_lines (
                id, tenant_id, bom_id, line_number, material_id,
                quantity, scrap_percentage, unit_id, is_deleted,
                created_at, updated_at
            ) VALUES (
                :id, :tid, :bid, :ln, :mid, 1.0, 0.0, :uid, false, :now, :now
            )
            """,
            id=line_id,
            tid=tenant_id,
            bid=bom_id,
            ln=idx * 10,
            mid=mat_id,
            uid=uom_id,
            now=now,
        )

    print(f"    BOM lines: 10 components added")
    return bom_id


async def seed_subcontract_test_data(conn, tenant_id: uuid.UUID, now: datetime) -> dict:
    """Main seeding function."""
    print(f"\n{'='*70}")
    print(f"TENANT: {tenant_id}")
    print(f"{'='*70}\n")

    user_id = await resolve_user_id(conn, tenant_id)
    print(f"User: {user_id}\n")

    # Master data
    print("Master Data:")
    cat_id = await ensure_category(conn, tenant_id, now)
    uom_id = await ensure_uom(conn, tenant_id, now)
    location_id = await ensure_location(conn, tenant_id, now)
    supplier_id = await ensure_supplier(conn, tenant_id, user_id, now)

    print("\nMaterials:")
    raw_material_ids = await ensure_raw_materials(
        conn, tenant_id, user_id, cat_id, uom_id, location_id, now
    )
    sf_material_id = await ensure_semi_finished_material(
        conn, tenant_id, user_id, cat_id, uom_id, location_id, now
    )

    print("\nProduct/Variant:")
    template_id = await ensure_item_template(conn, tenant_id, user_id, now)
    variant_id = await ensure_item_variant(
        conn, tenant_id, user_id, template_id, sf_material_id, uom_id, now
    )

    print("\nBOM:")
    bom_id = await ensure_bom(
        conn, tenant_id, user_id, variant_id, raw_material_ids, uom_id, now
    )

    return {
        "tenant_id": str(tenant_id),
        "supplier_id": str(supplier_id),
        "semi_finished_material_id": str(sf_material_id),
        "variant_id": str(variant_id),
        "bom_id": str(bom_id),
        "raw_material_count": len(raw_material_ids),
    }


async def main(tenant_id_arg: str | None = None):
    """Entry point."""
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        tenant_id = await resolve_tenant_id(conn, tenant_id_arg)
        now = utcnow()
        result = await seed_subcontract_test_data(conn, tenant_id, now)

    await engine.dispose()

    print(f"\n{'='*70}")
    print("✅ SEEDING COMPLETE")
    print(f"{'='*70}\n")
    print("Summary:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print("1. Open: http://localhost:3000/procurement/subcontract")
    print("2. Click: + New order")
    print("3. Select: Test Subcontract Vendor")
    print("4. Select: SC-SF-001 — Test Subcontracted Assembly")
    print("5. BOM should auto-discover with 10 components")
    print("6. Create → Approve → Issue materials → Receive output")
    print("="*70 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed subcontracting test data")
    parser.add_argument("--tenant-id", help="Tenant UUID (optional, uses first active tenant)")
    args = parser.parse_args()

    asyncio.run(main(args.tenant_id))
