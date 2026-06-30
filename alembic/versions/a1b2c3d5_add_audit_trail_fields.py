"""Add audit trail fields (created_by, updated_by) to supplier and material models

Revision ID: a1b2c3d5
Revises: a1b2c3d4
Create Date: 2026-04-17 10:30:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d5'
down_revision = 'a1b2c3d4'
branch_labels = None
depends_on = 'sc_foundation'


def upgrade() -> None:
    # NOTE: suppliers.created_by / updated_by already exist from sc_foundation migration.
    # Only add audit trail to materials table here.
    op.add_column('materials', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('materials', sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_materials_created_by', 'materials', 'users', ['created_by'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_materials_updated_by', 'materials', 'users', ['updated_by'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_materials_updated_by', 'materials', type_='foreignkey')
    op.drop_constraint('fk_materials_created_by', 'materials', type_='foreignkey')
    op.drop_column('materials', 'updated_by')
    op.drop_column('materials', 'created_by')
