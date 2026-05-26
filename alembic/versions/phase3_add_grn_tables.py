"""Add GRN (Goods Receipt Note) tables for PO -> GRN -> Inventory flow

Revision ID: phase3_add_grn_tables
Revises: phase4_work_orders
Create Date: 2026-04-29 10:30:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase3_add_grn_tables'
down_revision = 'phase4_work_orders'
branch_labels = None
depends_on = 'sc_foundation'


def upgrade() -> None:
    # Create goods_receipt_notes table
    op.create_table(
        'goods_receipt_notes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('grn_number', sa.String(length=40), nullable=False),
        sa.Column('purchase_order_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('scheduled_delivery_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_receipt_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('warehouse_location_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending_receipt'),
        sa.Column('driver_name', sa.String(length=255), nullable=True),
        sa.Column('vehicle_number', sa.String(length=50), nullable=True),
        sa.Column('transport_company', sa.String(length=255), nullable=True),
        sa.Column('tracking_number', sa.String(length=100), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['warehouse_location_id'], ['locations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('grn_number'),
    )
    op.create_index('ix_grn_tenant_po', 'goods_receipt_notes', ['tenant_id', 'purchase_order_id'])
    op.create_index('ix_grn_tenant_supplier', 'goods_receipt_notes', ['tenant_id', 'supplier_id'])
    op.create_index('ix_grn_tenant_status', 'goods_receipt_notes', ['tenant_id', 'status'])

    # Create grn_lines table
    op.create_table(
        'grn_lines',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('grn_id', sa.UUID(), nullable=False),
        sa.Column('po_line_id', sa.UUID(), nullable=False),
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('po_quantity', sa.Numeric(precision=15, scale=3), nullable=False),
        sa.Column('received_quantity', sa.Numeric(precision=15, scale=3), nullable=False),
        sa.Column('accepted_quantity', sa.Numeric(precision=15, scale=3), nullable=False, server_default='0'),
        sa.Column('rejected_quantity', sa.Numeric(precision=15, scale=3), nullable=False, server_default='0'),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('inventory_transaction_id', sa.UUID(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['grn_id'], ['goods_receipt_notes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['po_line_id'], ['purchase_order_lines.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_grn_line_grn', 'grn_lines', ['grn_id'])
    op.create_index('ix_grn_line_po_line', 'grn_lines', ['po_line_id'])


def downgrade() -> None:
    op.drop_index('ix_grn_line_po_line', table_name='grn_lines')
    op.drop_index('ix_grn_line_grn', table_name='grn_lines')
    op.drop_table('grn_lines')
    op.drop_index('ix_grn_tenant_status', table_name='goods_receipt_notes')
    op.drop_index('ix_grn_tenant_supplier', table_name='goods_receipt_notes')
    op.drop_index('ix_grn_tenant_po', table_name='goods_receipt_notes')
    op.drop_table('goods_receipt_notes')
