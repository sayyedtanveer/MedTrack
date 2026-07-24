"""Normalize legacy material_type values to canonical strings.

Maps:
  'finished_goods', 'finished_good', 'FG', 'FINISHED', 'Finished' → 'finished'
  'raw_material', 'RAW', 'Raw'                                    → 'raw'
  'semi_finished', 'SF', 'SEMI_FINISHED'                          → 'semi_finished'

Revision ID: normalize_material_type_001
Revises: add_missing_columns_materials
Create Date: 2025-01-01
"""

from alembic import op

revision = "normalize_material_type_001"
down_revision = None          # set to your latest revision id if chaining
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE materials
        SET material_type = 'finished'
        WHERE lower(trim(material_type)) IN (
            'finished',
            'finished_good',
            'finished_goods',
            'fg',
            'finishedgood',
            'finishedgoods'
        )
          AND material_type != 'finished';
    """)

    op.execute("""
        UPDATE materials
        SET material_type = 'raw'
        WHERE lower(trim(material_type)) IN (
            'raw',
            'raw_material',
            'rawmaterial',
            'rm'
        )
          AND material_type != 'raw';
    """)

    op.execute("""
        UPDATE materials
        SET material_type = 'semi_finished'
        WHERE lower(trim(material_type)) IN (
            'semi_finished',
            'semifinished',
            'semi-finished',
            'sf'
        )
          AND material_type != 'semi_finished';
    """)


def downgrade() -> None:
    # No downgrade — normalization is safe to keep
    pass
