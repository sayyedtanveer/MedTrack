"""Add created_at index to notifications for retention queries.
Revision ID: add_notification_retention
Revises: add_failed_tasks
"""
from alembic import op

revision = 'add_notification_retention'
down_revision = 'add_failed_tasks'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notifications_created_at ON notifications (created_at)")

def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_notifications_created_at")
