"""Make unit_id nullable in bom_lines table

Revision ID: 26_make_unit_id_nullable
Revises: d332efdcc036
Create Date: 2026-03-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26_make_unit_id_nullable'
down_revision: Union[str, None] = 'bf11eecd68b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make unit_id nullable in bom_lines table
    op.alter_column('bom_lines', 'unit_id',
               existing_type=sa.UUID(),
               nullable=True)


def downgrade() -> None:
    # Revert unit_id back to NOT NULL
    op.alter_column('bom_lines', 'unit_id',
               existing_type=sa.UUID(),
               nullable=False)
