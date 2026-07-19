"""Add missing schema columns for materials and related tables.

Revision ID: add_missing_columns_materials
Revises: 48cc745d4daa
Create Date: 2026-05-27 19:40:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "add_missing_columns_materials"
down_revision = "48cc745d4daa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use IF NOT EXISTS so this migration is safe to run even if columns
    # were already added by a prior schema sync or another migration.
    conn = op.get_bind()

    material_columns = [
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS length_uom VARCHAR(20)",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS length_per_unit NUMERIC(18,4)",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS weight_per_unit NUMERIC(18,4)",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS dimension_spec TEXT",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS preferred_supplier_id UUID",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS hazardous_flag BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS qc_required_flag BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS barcode VARCHAR(100)",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS traceability_enabled BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS batch_rule VARCHAR(50)",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS expiry_tracking BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS shelf_life_days INTEGER",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS quarantine_required BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS cuttable_inventory BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS remaining_quantity_tracking BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS reusable_remainder BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS decimal_precision INTEGER",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS supplier_item_code VARCHAR(100)",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS purchase_uom VARCHAR(20)",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS min_stock NUMERIC(18,4)",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS max_stock NUMERIC(18,4)",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS reorder_quantity NUMERIC(18,4)",
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS moq NUMERIC(18,4)",
    ]

    for stmt in material_columns:
        conn.execute(sa.text(stmt))

    # Ensure NOT NULL on these flag columns (safe to re-run)
    conn.execute(sa.text(
        "ALTER TABLE material_categories ALTER COLUMN is_active SET NOT NULL"
    ))
    conn.execute(sa.text(
        "ALTER TABLE units_of_measure ALTER COLUMN is_active SET NOT NULL"
    ))


def downgrade() -> None:
    op.drop_column('materials', 'moq')
    op.drop_column('materials', 'reorder_quantity')
    op.drop_column('materials', 'max_stock')
    op.drop_column('materials', 'min_stock')
    op.drop_column('materials', 'purchase_uom')
    op.drop_column('materials', 'supplier_item_code')
    op.drop_column('materials', 'decimal_precision')
    op.drop_column('materials', 'reusable_remainder')
    op.drop_column('materials', 'remaining_quantity_tracking')
    op.drop_column('materials', 'cuttable_inventory')
    op.drop_column('materials', 'quarantine_required')
    op.drop_column('materials', 'shelf_life_days')
    op.drop_column('materials', 'expiry_tracking')
    op.drop_column('materials', 'batch_rule')
    op.drop_column('materials', 'traceability_enabled')
    op.drop_column('materials', 'barcode')
    op.drop_column('materials', 'qc_required_flag')
    op.drop_column('materials', 'hazardous_flag')
    op.drop_column('materials', 'preferred_supplier_id')
    op.drop_column('materials', 'dimension_spec')
    op.drop_column('materials', 'weight_per_unit')
    op.drop_column('materials', 'length_per_unit')
    op.drop_column('materials', 'length_uom')
