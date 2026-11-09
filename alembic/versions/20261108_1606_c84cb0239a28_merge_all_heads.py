"""merge_all_heads

Revision ID: c84cb0239a28
Revises: e1e6de95f2a9, 20260926_add_consumed_quantity, 20260927_1500
Create Date: 2026-11-08 16:06:56.569628

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c84cb0239a28'
down_revision = ('e1e6de95f2a9', '20260926_add_consumed_quantity', '20260927_1500')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
