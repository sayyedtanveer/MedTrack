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
    # Add missing columns to materials table
    op.add_column('materials', sa.Column('length_uom', sa.String(length=20), nullable=True))
    op.add_column('materials', sa.Column('length_per_unit', sa.Numeric(18, 4), nullable=True))
    op.add_column('materials', sa.Column('weight_per_unit', sa.Numeric(18, 4), nullable=True))
    op.add_column('materials', sa.Column('dimension_spec', sa.Text(), nullable=True))
    op.add_column('materials', sa.Column('preferred_supplier_id', sa.UUID(), nullable=True))
    op.add_column('materials', sa.Column('hazardous_flag', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('materials', sa.Column('qc_required_flag', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('materials', sa.Column('barcode', sa.String(length=100), nullable=True))
    op.add_column('materials', sa.Column('traceability_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('materials', sa.Column('batch_rule', sa.String(length=50), nullable=True))
    op.add_column('materials', sa.Column('expiry_tracking', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('materials', sa.Column('shelf_life_days', sa.Integer(), nullable=True))
    op.add_column('materials', sa.Column('quarantine_required', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('materials', sa.Column('cuttable_inventory', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('materials', sa.Column('remaining_quantity_tracking', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('materials', sa.Column('reusable_remainder', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('materials', sa.Column('decimal_precision', sa.Integer(), nullable=True))
    op.add_column('materials', sa.Column('supplier_item_code', sa.String(length=100), nullable=True))
    op.add_column('materials', sa.Column('purchase_uom', sa.String(length=20), nullable=True))
    op.add_column('materials', sa.Column('min_stock', sa.Numeric(18, 4), nullable=True))
    op.add_column('materials', sa.Column('max_stock', sa.Numeric(18, 4), nullable=True))
    op.add_column('materials', sa.Column('reorder_quantity', sa.Numeric(18, 4), nullable=True))
    op.add_column('materials', sa.Column('moq', sa.Numeric(18, 4), nullable=True))
    
    # Add missing columns to material_categories
    op.alter_column('material_categories', 'is_active',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    
    # Add missing columns to units_of_measure
    op.alter_column('units_of_measure', 'is_active',
               existing_type=sa.BOOLEAN(),
               nullable=False)


def downgrade() -> None:
    # Remove added columns
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
