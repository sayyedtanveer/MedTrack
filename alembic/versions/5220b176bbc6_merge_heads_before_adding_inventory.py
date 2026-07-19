"""Merge heads before adding inventory

Revision ID: 5220b176bbc6
Revises: 9f2c1b7d_client_portal, phase4_add_product_images
Create Date: 2026-04-15 00:28:23.019239

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5220b176bbc6'
down_revision = ('9f2c1b7d_client_portal', 'phase4_add_product_images')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
