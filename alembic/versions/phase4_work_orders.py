"""Phase 4: Work Order & Shop Floor tables.

Revision ID: phase4_work_orders
Revises: 7a8b9c0d_add_sales_module
Create Date: 2026-03-27 00:00:00.000000

Tables created:
  - wo_number_sequences
  - work_orders
  - work_order_materials
  - job_cards
  - production_records
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'phase4_work_orders'
down_revision = '7a8b9c0d_add_sales_module'
branch_labels = None
depends_on = 'bf11eecd68b9'


def upgrade() -> None:
    # ── 1. WO number sequences (one row per tenant) ────────────────────────────
    op.create_table(
        'wo_number_sequences',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_value', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('tenant_id'),
    )

    # ── 2. Work orders ─────────────────────────────────────────────────────────
    op.create_table(
        'work_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wo_number', sa.String(30), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bom_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sales_order_id', postgresql.UUID(as_uuid=True), nullable=True),
        # Quantities
        sa.Column('planned_quantity', sa.Numeric(15, 3), nullable=False),
        sa.Column('produced_quantity', sa.Numeric(15, 3), nullable=False, server_default='0'),
        sa.Column('scrap_quantity', sa.Numeric(15, 3), nullable=False, server_default='0'),
        # Lifecycle
        sa.Column('status', sa.String(20), nullable=False, server_default='PLANNED'),
        sa.Column('priority', sa.String(10), nullable=False, server_default='NORMAL'),
        # Dates
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        # Metadata
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        # Soft delete
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Constraints
        sa.ForeignKeyConstraint(['bom_id'], ['boms.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['product_id'], ['item_variants.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'wo_number', name='uq_work_order_tenant_number'),
        sa.CheckConstraint("status IN ('PLANNED','RELEASED','IN_PROGRESS','COMPLETED','CLOSED')", name='ck_work_order_status'),
        sa.CheckConstraint("priority IN ('LOW','NORMAL','HIGH','URGENT')", name='ck_work_order_priority'),
    )
    op.create_index('ix_work_orders_tenant_id', 'work_orders', ['tenant_id'])
    op.create_index('ix_work_orders_tenant_status', 'work_orders', ['tenant_id', 'status'])
    op.create_index('ix_work_orders_tenant_due', 'work_orders', ['tenant_id', 'due_date'])

    # ── 3. Work order materials (BOM snapshot) ─────────────────────────────────
    op.create_table(
        'work_order_materials',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('work_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('material_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('required_quantity', sa.Numeric(15, 3), nullable=False),
        sa.Column('issued_quantity', sa.Numeric(15, 3), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['unit_id'], ['units_of_measure.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_wo_materials_work_order_id', 'work_order_materials', ['work_order_id'])

    # ── 4. Job cards (operation snapshot) ─────────────────────────────────────
    op.create_table(
        'job_cards',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('work_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['operation_id'], ['operations.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('PENDING','IN_PROGRESS','DONE')", name='ck_job_card_status'),
    )
    op.create_index('ix_job_cards_work_order_id', 'job_cards', ['work_order_id'])

    # ── 5. Production records ─────────────────────────────────────────────────
    op.create_table(
        'production_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('work_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('produced_quantity', sa.Numeric(15, 3), nullable=False),
        sa.Column('scrap_quantity', sa.Numeric(15, 3), nullable=False, server_default='0'),
        sa.Column('recorded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_production_records_work_order_id', 'production_records', ['work_order_id'])


def downgrade() -> None:
    op.drop_index('ix_production_records_work_order_id', table_name='production_records')
    op.drop_table('production_records')

    op.drop_index('ix_job_cards_work_order_id', table_name='job_cards')
    op.drop_table('job_cards')

    op.drop_index('ix_wo_materials_work_order_id', table_name='work_order_materials')
    op.drop_table('work_order_materials')

    op.drop_index('ix_work_orders_tenant_due', table_name='work_orders')
    op.drop_index('ix_work_orders_tenant_status', table_name='work_orders')
    op.drop_index('ix_work_orders_tenant_id', table_name='work_orders')
    op.drop_table('work_orders')

    op.drop_table('wo_number_sequences')
