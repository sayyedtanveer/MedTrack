"""Add product lifecycle status to item_templates.

Revision ID: phase4_add_product_lifecycle
Revises: phase4_add_advanced_reporting
Create Date: 2026-04-15 00:00:00.000000

This migration adds the `status` column to item_templates table to support
product lifecycle states: DRAFT, ACTIVE, INACTIVE, ARCHIVED.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'phase4_add_product_lifecycle'
down_revision = 'phase4_advanced_reporting'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column with default ACTIVE for existing records
    op.add_column(
        'item_templates',
        sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE')
    )
    # Drop the server default after creating the column
    op.alter_column('item_templates', 'status', server_default=None)


def downgrade() -> None:
    op.drop_column('item_templates', 'status')
