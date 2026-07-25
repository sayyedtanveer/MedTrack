"""Merge multiple heads

Revision ID: 42f94e3fc80a
Revises: add_default_price_list_to_clients, add_notification_retention, normalize_material_type_001
Create Date: 2026-07-25 20:06:49.225414

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '42f94e3fc80a'
down_revision = ('add_default_price_list_to_clients', 'add_notification_retention', 'normalize_material_type_001')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
