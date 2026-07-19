"""Phase 2: Add Inventory Reservation System tables.

Revision ID: phase2_inventory_reservation_system
Revises: phase1_operational_workflow_states
Create Date: 2026-05-11 00:00:00.000000

Changes:
  - Add material_shortages table
  - Add inventory_reservations table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'p2_inv_reservation'
down_revision = 'p1_op_wf_states'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Material Shortages table ───────────────────────────────────────────────
    op.create_table(
        'material_shortages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('work_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('material_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('required_quantity', sa.Numeric(15, 3), nullable=False),
        sa.Column('available_quantity', sa.Numeric(15, 3), nullable=False),
        sa.Column('shortage_quantity', sa.Numeric(15, 3), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.Index('ix_ms_tenant_wo', 'tenant_id', 'work_order_id'),
        sa.Index('ix_ms_tenant_material', 'tenant_id', 'material_id'),
        sa.Index('ix_ms_status', 'status'),
    )

    # ── Inventory Reservations table ────────────────────────────────────────────
    op.create_table(
        'inventory_reservations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reference_type', sa.String(40), nullable=False),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('material_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Numeric(15, 3), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='RESERVED'),
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('issued_quantity', sa.Numeric(15, 3), nullable=False, server_default='0'),
        sa.Column('consumed_quantity', sa.Numeric(15, 3), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['unit_id'], ['units_of_measure.id'], ondelete='SET NULL'),
        sa.Index('ix_ir_tenant_ref', 'tenant_id', 'reference_type', 'reference_id'),
        sa.Index('ix_ir_tenant_material', 'tenant_id', 'material_id'),
        sa.Index('ix_ir_status', 'status'),
    )


def downgrade() -> None:
    op.drop_table('inventory_reservations')
    op.drop_table('material_shortages')
