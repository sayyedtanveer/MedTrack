"""Merge heads before adding finance

Revision ID: 67cc7ab2ca76
Revises: 62476545ff2f, phase4_work_orders
Create Date: 2026-03-28 23:17:48.545043

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67cc7ab2ca76'
down_revision = ('62476545ff2f', 'phase4_work_orders')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
