"""Add purchase_requisitions table for procurement recovery workflow

Revision ID: add_purchase_requisitions
Revises: phase10_number_series
Create Date: 2026-06-02 10:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_purchase_requisitions'
down_revision = 'phase10_number_series'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'purchase_requisitions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('requisition_number', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PENDING_APPROVAL'),
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('work_order_id', sa.UUID(), nullable=True),
        sa.Column('required_quantity', sa.Numeric(precision=15, scale=3), nullable=False),
        sa.Column('shortage_quantity', sa.Numeric(precision=15, scale=3), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('linked_po_id', sa.UUID(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['linked_po_id'], ['purchase_orders.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('requisition_number'),
    )
    op.create_index('ix_purchase_requisitions_tenant_id', 'purchase_requisitions', ['tenant_id'])
    op.create_index('ix_purchase_requisitions_tenant_status', 'purchase_requisitions', ['tenant_id', 'status'])
    op.create_index('ix_purchase_requisitions_tenant_material', 'purchase_requisitions', ['tenant_id', 'material_id'])


def downgrade() -> None:
    op.drop_index('ix_purchase_requisitions_tenant_material', table_name='purchase_requisitions')
    op.drop_index('ix_purchase_requisitions_tenant_status', table_name='purchase_requisitions')
    op.drop_index('ix_purchase_requisitions_tenant_id', table_name='purchase_requisitions')
    op.drop_table('purchase_requisitions')
