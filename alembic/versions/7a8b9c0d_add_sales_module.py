"""Add sales module tables (clients, orders, price lists).

Revision ID: 7a8b9c0d_add_sales_module
Revises: 68c163da4d5a (or latest migration)
Create Date: 2026-03-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '7a8b9c0d_add_sales_module'
down_revision = '68c163da4d5a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create sales module tables."""
    
    # Create sales_clients table
    op.create_table(
        'sales_clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('gst_number', sa.String(50), nullable=True),
        sa.Column('credit_limit', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('credit_used', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0'),
        sa.Column('payment_terms_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_client_tenant_code'),
    )
    op.create_index('ix_client_tenant_id', 'sales_clients', ['tenant_id'])
    op.create_index('ix_client_is_active', 'sales_clients', ['is_active'])
    op.create_index('ix_client_is_deleted', 'sales_clients', ['is_deleted'])
    
    # Create sales_orders table
    op.create_table(
        'sales_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_number', sa.String(50), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_date', sa.String(), nullable=False),
        sa.Column('delivery_date', sa.String(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='DRAFT'),
        sa.Column('payment_status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('subtotal', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0'),
        sa.Column('discount_amount', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0'),
        sa.Column('tax_amount', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0'),
        sa.Column('grand_total', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0'),
        sa.Column('notes', sa.String(1000), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['sales_clients.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'order_number', name='uq_sales_order_tenant_number'),
    )
    op.create_index('ix_sales_order_tenant_id', 'sales_orders', ['tenant_id'])
    op.create_index('ix_sales_order_client_id', 'sales_orders', ['client_id'])
    op.create_index('ix_sales_order_status', 'sales_orders', ['status'])
    op.create_index('ix_sales_order_order_date', 'sales_orders', ['order_date'])
    op.create_index('ix_sales_order_delivery_date', 'sales_orders', ['delivery_date'])
    op.create_index('ix_sales_order_is_deleted', 'sales_orders', ['is_deleted'])
    
    # Create sales_order_lines table
    op.create_table(
        'sales_order_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sales_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_type', sa.String(50), nullable=False),
        sa.Column('uom_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('tax_amount', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0'),
        sa.Column('line_total', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0'),
        sa.Column('allocated_quantity', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0'),
        sa.Column('shipped_quantity', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0'),
        sa.Column('backorder_quantity', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0'),
        sa.Column('work_order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['sales_order_id'], ['sales_orders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sales_order_line_order_id', 'sales_order_lines', ['sales_order_id'])
    op.create_index('ix_sales_order_line_product_id', 'sales_order_lines', ['product_id'])
    op.create_index('ix_sales_order_line_status', 'sales_order_lines', ['status'])
    
    # Create sales_price_lists table
    op.create_table(
        'sales_price_lists',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('valid_from', sa.String(), nullable=False),
        sa.Column('valid_to', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_price_list_tenant_id', 'sales_price_lists', ['tenant_id'])
    op.create_index('ix_price_list_is_default', 'sales_price_lists', ['is_default'])
    op.create_index('ix_price_list_valid_from', 'sales_price_lists', ['valid_from'])
    op.create_index('ix_price_list_is_active', 'sales_price_lists', ['is_active'])
    op.create_index('ix_price_list_is_deleted', 'sales_price_lists', ['is_deleted'])
    
    # Create sales_price_list_lines table
    op.create_table(
        'sales_price_list_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('price_list_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_type', sa.String(50), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['price_list_id'], ['sales_price_lists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_price_list_line_price_list_id', 'sales_price_list_lines', ['price_list_id'])
    op.create_index('ix_price_list_line_product', 'sales_price_list_lines', ['price_list_id', 'product_id', 'product_type'])


def downgrade() -> None:
    """Drop sales module tables."""
    
    op.drop_index('ix_price_list_line_product', table_name='sales_price_list_lines')
    op.drop_index('ix_price_list_line_price_list_id', table_name='sales_price_list_lines')
    op.drop_table('sales_price_list_lines')
    
    op.drop_index('ix_price_list_is_deleted', table_name='sales_price_lists')
    op.drop_index('ix_price_list_is_active', table_name='sales_price_lists')
    op.drop_index('ix_price_list_valid_from', table_name='sales_price_lists')
    op.drop_index('ix_price_list_is_default', table_name='sales_price_lists')
    op.drop_index('ix_price_list_tenant_id', table_name='sales_price_lists')
    op.drop_table('sales_price_lists')
    
    op.drop_index('ix_sales_order_line_status', table_name='sales_order_lines')
    op.drop_index('ix_sales_order_line_product_id', table_name='sales_order_lines')
    op.drop_index('ix_sales_order_line_order_id', table_name='sales_order_lines')
    op.drop_table('sales_order_lines')
    
    op.drop_index('ix_sales_order_is_deleted', table_name='sales_orders')
    op.drop_index('ix_sales_order_delivery_date', table_name='sales_orders')
    op.drop_index('ix_sales_order_order_date', table_name='sales_orders')
    op.drop_index('ix_sales_order_status', table_name='sales_orders')
    op.drop_index('ix_sales_order_client_id', table_name='sales_orders')
    op.drop_index('ix_sales_order_tenant_id', table_name='sales_orders')
    op.drop_table('sales_orders')
    
    op.drop_index('ix_client_is_deleted', table_name='sales_clients')
    op.drop_index('ix_client_is_active', table_name='sales_clients')
    op.drop_index('ix_client_tenant_id', table_name='sales_clients')
    op.drop_table('sales_clients')
