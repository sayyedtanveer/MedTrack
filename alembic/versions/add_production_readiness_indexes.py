"""Add production readiness indexes for manufacturing ERP performance.

Revision ID: add_prod_indexes
Revises: s1_op_hard_merge
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op

revision = 'add_prod_indexes'
down_revision = 's1_op_hard_merge'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block (Alembic
    # wraps migrations in transactions by default).  Use plain CREATE INDEX with
    # IF NOT EXISTS instead — safe to re-run and equivalent for a dev database.
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_orders_tenant_status ON sales_orders (tenant_id, status, is_deleted)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_work_orders_tenant_status ON work_orders (tenant_id, status, is_deleted)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_delivery_orders_tenant_status ON delivery_orders (tenant_id, status, is_deleted)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inventory_transactions_tenant_material ON inventory_transactions (tenant_id, material_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant_entity ON audit_logs (tenant_id, entity_type, entity_id, occurred_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_tenant_unread ON notifications (tenant_id, user_id, is_read, sent_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_sales_orders_tenant_status")
    op.execute("DROP INDEX IF EXISTS ix_work_orders_tenant_status")
    op.execute("DROP INDEX IF EXISTS ix_delivery_orders_tenant_status")
    op.execute("DROP INDEX IF EXISTS ix_inventory_transactions_tenant_material")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_tenant_entity")
    op.execute("DROP INDEX IF EXISTS ix_notifications_tenant_unread")
