from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import settings

DEFAULT_DEFINITION_FILE = Path(__file__).with_name("reset_master_data_gear_rotameter.json")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def execute(conn, sql: str, **params):
    return await conn.execute(text(sql), params)


async def scalar(conn, sql: str, **params):
    result = await execute(conn, sql, **params)
    return result.scalar_one_or_none()


async def resolve_tenant_id(conn, tenant_id_arg: str | None) -> uuid.UUID:
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
    user_id = await scalar(
        conn,
        """
        SELECT id
        FROM users
        WHERE tenant_id = :tenant_id
          AND is_active = true
          AND COALESCE(is_deleted, false) = false
        ORDER BY created_at ASC
        LIMIT 1
        """,
        tenant_id=tenant_id,
    )
    if user_id is None:
        raise RuntimeError(
            f"No active user found for tenant {tenant_id}. Create one user before running this reset."
        )
    return user_id


async def purge_transactional_data(conn, tenant_id: uuid.UUID, now: datetime) -> None:
    statements = [
        "DELETE FROM notifications WHERE tenant_id = :tenant_id",
        "DELETE FROM client_notification_settings WHERE tenant_id = :tenant_id",
        "DELETE FROM password_reset_tokens WHERE user_id IN (SELECT id FROM users WHERE tenant_id = :tenant_id)",
        "DELETE FROM supplier_payments WHERE tenant_id = :tenant_id",
        "DELETE FROM payments WHERE tenant_id = :tenant_id",
        "DELETE FROM financial_transactions WHERE tenant_id = :tenant_id",
        "DELETE FROM invoice_lines WHERE tenant_id = :tenant_id",
        "DELETE FROM invoices WHERE tenant_id = :tenant_id",
        "DELETE FROM supplier_invoices WHERE tenant_id = :tenant_id",
        "DELETE FROM delivery_lines WHERE tenant_id = :tenant_id",
        "DELETE FROM delivery_orders WHERE tenant_id = :tenant_id",
        "DELETE FROM grn_lines WHERE tenant_id = :tenant_id",
        "DELETE FROM goods_receipt_notes WHERE tenant_id = :tenant_id",
        "DELETE FROM rfq_suppliers WHERE rfq_id IN (SELECT id FROM rfqs WHERE tenant_id = :tenant_id)",
        "DELETE FROM rfq_lines WHERE tenant_id = :tenant_id",
        "DELETE FROM rfqs WHERE tenant_id = :tenant_id",
        "DELETE FROM material_requests WHERE tenant_id = :tenant_id",
        "DELETE FROM inspection_details WHERE inspection_id IN (SELECT id FROM quality_inspections WHERE tenant_id = :tenant_id)",
        "DELETE FROM quality_inspections WHERE tenant_id = :tenant_id",
        "DELETE FROM non_conformance_reports WHERE tenant_id = :tenant_id",
        "DELETE FROM subcontract_material_issues WHERE subcontract_order_id IN (SELECT id FROM subcontract_orders WHERE tenant_id = :tenant_id)",
        "DELETE FROM subcontract_orders WHERE tenant_id = :tenant_id",
        "DELETE FROM purchase_order_lines WHERE tenant_id = :tenant_id",
        "DELETE FROM purchase_orders WHERE tenant_id = :tenant_id",
        "DELETE FROM stock_reservations WHERE tenant_id = :tenant_id",
        "DELETE FROM stock_ledger_entries WHERE tenant_id = :tenant_id",
        "DELETE FROM inventory_transactions WHERE tenant_id = :tenant_id",
        "DELETE FROM stock_levels WHERE tenant_id = :tenant_id",
        "DELETE FROM batches WHERE tenant_id = :tenant_id",
        "DELETE FROM serial_numbers WHERE tenant_id = :tenant_id",
        "DELETE FROM production_records WHERE work_order_id IN (SELECT id FROM work_orders WHERE tenant_id = :tenant_id)",
        "DELETE FROM job_cards WHERE work_order_id IN (SELECT id FROM work_orders WHERE tenant_id = :tenant_id)",
        "DELETE FROM work_order_materials WHERE work_order_id IN (SELECT id FROM work_orders WHERE tenant_id = :tenant_id)",
        "DELETE FROM work_orders WHERE tenant_id = :tenant_id",
        "DELETE FROM sales_order_lines WHERE sales_order_id IN (SELECT id FROM sales_orders WHERE tenant_id = :tenant_id)",
        "DELETE FROM sales_orders WHERE tenant_id = :tenant_id",
        """
        UPDATE materials
        SET current_stock = 0,
            reserved_stock = 0,
            updated_at = :now
        WHERE tenant_id = :tenant_id
        """,
    ]
    for sql in statements:
        await execute(conn, sql, tenant_id=tenant_id, now=now)


def load_definition(definition_file: Path) -> dict:
    with definition_file.open("r", encoding="utf-8") as file:
        definition = json.load(file)
    required_keys = {"uom", "location", "template", "variant", "bom", "raw_materials", "bom_lines"}
    missing = required_keys.difference(definition.keys())
    if missing:
        raise RuntimeError(f"Definition file is missing keys: {', '.join(sorted(missing))}")
    return definition


async def ensure_uom(conn, tenant_id: uuid.UUID, now: datetime, definition: dict) -> uuid.UUID:
    uom = definition["uom"]
    result = await execute(
        conn,
        """
        INSERT INTO units_of_measure (
            id, tenant_id, code, name, precision, is_active, is_deleted, created_at, updated_at
        )
        VALUES (:id, :tenant_id, :code, :name, :precision, true, false, :now, :now)
        ON CONFLICT (tenant_id, code) DO UPDATE SET
            name = EXCLUDED.name,
            precision = EXCLUDED.precision,
            is_active = true,
            is_deleted = false,
            updated_at = EXCLUDED.updated_at
        RETURNING id
        """,
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=uom["code"],
        name=uom["name"],
        precision=uom.get("precision", 2),
        now=now,
    )
    return result.scalar_one()


async def ensure_location(conn, tenant_id: uuid.UUID, now: datetime, definition: dict) -> uuid.UUID:
    location = definition["location"]
    result = await execute(
        conn,
        """
        INSERT INTO locations (
            id, tenant_id, name, code, type, parent_location_id, is_active, is_deleted, created_at, updated_at
        )
        VALUES (:id, :tenant_id, :name, :code, :type, NULL, true, false, :now, :now)
        ON CONFLICT (tenant_id, name) DO UPDATE SET
            code = EXCLUDED.code,
            type = EXCLUDED.type,
            is_active = true,
            is_deleted = false,
            updated_at = EXCLUDED.updated_at
        RETURNING id
        """,
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=location["name"],
        code=location.get("code"),
        type=location["type"],
        now=now,
    )
    return result.scalar_one()


async def ensure_template(conn, tenant_id: uuid.UUID, uom_id: uuid.UUID, now: datetime, definition: dict) -> uuid.UUID:
    template = definition["template"]
    result = await execute(
        conn,
        """
        INSERT INTO item_templates (
            id, tenant_id, code, name, description, category_id, base_unit_id, attributes,
            status, is_active, is_deleted, created_at, updated_at
        )
        VALUES (
            :id, :tenant_id, :code, :name,
            :description, NULL, :uom_id, '[]'::jsonb,
            'ACTIVE', true, false, :now, :now
        )
        ON CONFLICT (tenant_id, code) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            base_unit_id = EXCLUDED.base_unit_id,
            status = 'ACTIVE',
            is_active = true,
            is_deleted = false,
            updated_at = EXCLUDED.updated_at
        RETURNING id
        """,
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=template["code"],
        name=template["name"],
        description=template.get("description", ""),
        uom_id=uom_id,
        now=now,
    )
    return result.scalar_one()


async def ensure_variant(
    conn,
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    uom_id: uuid.UUID,
    now: datetime,
    definition: dict,
) -> uuid.UUID:
    variant = definition["variant"]
    result = await execute(
        conn,
        """
        INSERT INTO item_variants (
            id, tenant_id, template_id, code, name, variant_key, attribute_values,
            base_unit_id, standard_cost, selling_price, is_active, is_deleted, created_at, updated_at
        )
        VALUES (
            :id, :tenant_id, :template_id, :code, :name,
            :variant_key, '{}'::jsonb, :uom_id, :standard_cost, :selling_price, true, false, :now, :now
        )
        ON CONFLICT (tenant_id, code) DO UPDATE SET
            template_id = EXCLUDED.template_id,
            name = EXCLUDED.name,
            variant_key = EXCLUDED.variant_key,
            attribute_values = EXCLUDED.attribute_values,
            base_unit_id = EXCLUDED.base_unit_id,
            is_active = true,
            is_deleted = false,
            updated_at = EXCLUDED.updated_at
        RETURNING id
        """,
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        template_id=template_id,
        code=variant["code"],
        name=variant["name"],
        variant_key=variant["variant_key"],
        uom_id=uom_id,
        standard_cost=variant.get("standard_cost", 0),
        selling_price=variant.get("selling_price", 0),
        now=now,
    )
    return result.scalar_one()


async def ensure_material(
    conn,
    tenant_id: uuid.UUID,
    uom_id: uuid.UUID,
    location_id: uuid.UUID,
    now: datetime,
    definition: dict,
    product_name: str,
) -> uuid.UUID:
    code = definition["code"]
    name = definition["name"]
    stock = definition.get("stock", 0)
    reorder = definition.get("reorder", 0)
    cost = definition.get("cost", 0)
    result = await execute(
        conn,
        """
        INSERT INTO materials (
            id, tenant_id, code, name, description, category_id, base_unit_id, material_type,
            current_cost, current_stock, reserved_stock, reorder_level, location_id,
            is_batch_tracked, is_serialized, inspection_required, is_active, is_deleted,
            created_at, updated_at
        )
        VALUES (
            :id, :tenant_id, :code, :name, :description,
            NULL, :uom_id, 'raw', :cost, :stock, 0, :reorder, :location_id,
            false, false, false, true, false, :now, :now
        )
        ON CONFLICT (tenant_id, code) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            base_unit_id = EXCLUDED.base_unit_id,
            material_type = 'raw',
            current_cost = EXCLUDED.current_cost,
            current_stock = EXCLUDED.current_stock,
            reserved_stock = 0,
            reorder_level = EXCLUDED.reorder_level,
            location_id = EXCLUDED.location_id,
            is_active = true,
            is_deleted = false,
            updated_at = EXCLUDED.updated_at
        RETURNING id
        """,
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=code,
        name=name,
        description=f"Master data reset example for {product_name}",
        uom_id=uom_id,
        cost=cost,
        stock=stock,
        reorder=reorder,
        location_id=location_id,
        now=now,
    )
    return result.scalar_one()


async def ensure_bom(
    conn,
    tenant_id: uuid.UUID,
    variant_id: uuid.UUID,
    created_by: uuid.UUID,
    now: datetime,
    definition: dict,
) -> uuid.UUID:
    bom = definition["bom"]
    await execute(
        conn,
        """
        UPDATE boms
        SET is_active = false,
            updated_at = :now
        WHERE tenant_id = :tenant_id
          AND variant_id = :variant_id
        """,
        tenant_id=tenant_id,
        variant_id=variant_id,
        now=now,
    )
    result = await execute(
        conn,
        """
        INSERT INTO boms (
            id, tenant_id, template_id, variant_id, version, is_active,
            valid_from, valid_to, created_by, approved_by,
            is_deleted, deleted_at, created_at, updated_at
        )
        VALUES (
            :id, :tenant_id, NULL, :variant_id, :version, true,
            :now, NULL, :created_by, :created_by,
            false, NULL, :now, :now
        )
        ON CONFLICT (tenant_id, variant_id, version) DO UPDATE SET
            is_active = true,
            valid_from = EXCLUDED.valid_from,
            valid_to = NULL,
            approved_by = EXCLUDED.approved_by,
            is_deleted = false,
            deleted_at = NULL,
            updated_at = EXCLUDED.updated_at
        RETURNING id
        """,
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        variant_id=variant_id,
        version=bom.get("version", "v1.0"),
        created_by=created_by,
        now=now,
    )
    return result.scalar_one()


async def replace_bom_lines(
    conn,
    tenant_id: uuid.UUID,
    bom_id: uuid.UUID,
    uom_id: uuid.UUID,
    material_ids: dict[str, uuid.UUID],
    now: datetime,
    definition: dict,
) -> None:
    await execute(conn, "DELETE FROM bom_operations WHERE bom_id = :bom_id", bom_id=bom_id)
    await execute(conn, "DELETE FROM bom_lines WHERE bom_id = :bom_id", bom_id=bom_id)

    for line in definition["bom_lines"]:
        await execute(
            conn,
            """
            INSERT INTO bom_lines (
                id, tenant_id, bom_id, material_id, template_id, variant_id,
                quantity, scrap_percentage, unit_id, is_deleted, deleted_at, created_at, updated_at
            )
            VALUES (
                :id, :tenant_id, :bom_id, :material_id, NULL, NULL,
                :quantity, 0, :unit_id, false, NULL, :now, :now
            )
            """,
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            bom_id=bom_id,
            material_id=material_ids[line["material_code"]],
            quantity=line["quantity"],
            unit_id=uom_id,
            now=now,
        )


async def seed_master_data(conn, tenant_id: uuid.UUID, now: datetime, definition: dict) -> dict[str, str]:
    uom_id = await ensure_uom(conn, tenant_id, now, definition)
    location_id = await ensure_location(conn, tenant_id, now, definition)
    template_id = await ensure_template(conn, tenant_id, uom_id, now, definition)
    variant_id = await ensure_variant(conn, tenant_id, template_id, uom_id, now, definition)
    created_by = await resolve_user_id(conn, tenant_id)

    material_ids: dict[str, uuid.UUID] = {}
    product_name = definition["variant"]["name"]
    for raw_material in definition["raw_materials"]:
        material_ids[raw_material["code"]] = await ensure_material(
            conn,
            tenant_id,
            uom_id,
            location_id,
            now,
            raw_material,
            product_name,
        )

    bom_id = await ensure_bom(conn, tenant_id, variant_id, created_by, now, definition)
    await replace_bom_lines(conn, tenant_id, bom_id, uom_id, material_ids, now, definition)

    return {
        "tenant_id": str(tenant_id),
        "template_id": str(template_id),
        "variant_id": str(variant_id),
        "bom_id": str(bom_id),
        "uom_id": str(uom_id),
    }


async def run(tenant_id_arg: str | None, definition_file: Path) -> None:
    now = utcnow()
    definition = load_definition(definition_file)
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        tenant_id = await resolve_tenant_id(conn, tenant_id_arg)
        await purge_transactional_data(conn, tenant_id, now)
        summary = await seed_master_data(conn, tenant_id, now, definition)

    await engine.dispose()
    print("MASTER_DATA_RESET_COMPLETE")
    for key, value in summary.items():
        print(f"{key}={value}")
    print(f"seeded_product={definition['variant']['name']}")
    print(
        "seeded_raw_materials="
        + ", ".join(material["name"] for material in definition["raw_materials"])
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clear transactional ERP data for a tenant and keep only understandable master data."
    )
    parser.add_argument(
        "--tenant-id",
        help="Tenant UUID to reset. If omitted, the first active tenant is used.",
    )
    parser.add_argument(
        "--definition-file",
        default=str(DEFAULT_DEFINITION_FILE),
        help="Path to a JSON file that defines the product, raw materials, and BOM lines to seed.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.tenant_id, Path(args.definition_file)))
