"""Add is_default field to locations table.

Allows marking a single location as default per tenant.
Used for material import Excel template to preselect default location.

Revision ID: 20261109_1145_add_is_default
Revises: 20261110_1939_e06307f2f932_add_procurement_pricing_phase2_tables
Create Date: 2026-11-09 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision = '20261109_1145_add_is_default'
down_revision = 'e06307f2f932'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_default column with default value False
    op.add_column('locations', 
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Create index for faster lookups of default location per tenant
    op.create_index(
        'ix_location_tenant_default',
        'locations',
        ['tenant_id', 'is_default'],
        unique=False,
        postgresql_where=sa.text("is_default = true AND is_deleted = false AND is_active = true")
    )


def downgrade() -> None:
    # Drop the index
    op.drop_index('ix_location_tenant_default', table_name='locations')
    
    # Remove the column
    op.drop_column('locations', 'is_default')
