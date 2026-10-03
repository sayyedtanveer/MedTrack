"""add priority to sales orders

Revision ID: 20260927_1500
Revises: 
Create Date: 2026-09-27 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260927_1500'
down_revision = 'c5d9f2b1e8a3'  # Current production revision
branch_labels = None
depends_on = None


def upgrade():
    # Add priority column to sales_orders table
    op.add_column(
        'sales_orders',
        sa.Column('priority', sa.String(20), nullable=False, server_default='NORMAL')
    )
    
    # Add check constraint for valid priority values
    op.create_check_constraint(
        'ck_sales_order_priority',
        'sales_orders',
        "priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')"
    )
    
    # Add index for efficient filtering by priority
    op.create_index(
        'ix_sales_orders_priority',
        'sales_orders',
        ['tenant_id', 'priority']
    )


def downgrade():
    op.drop_index('ix_sales_orders_priority', table_name='sales_orders')
    op.drop_constraint('ck_sales_order_priority', 'sales_orders', type_='check')
    op.drop_column('sales_orders', 'priority')
