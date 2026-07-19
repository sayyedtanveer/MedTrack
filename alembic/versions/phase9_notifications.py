"""Phase 9: Add Notifications table.

Revision ID: phase9_notifications
Revises: phase2_inventory_reservation_system
Create Date: 2026-05-11 00:00:00.000000

Changes:
  - Add notifications table for operational alerts
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'phase9_notifications'
down_revision = 'p2_inv_reservation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Notifications table ───────────────────────────────────────────────
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.String(1000), nullable=False),
        sa.Column('reference_type', sa.String(50), nullable=True),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.Index('ix_notification_tenant_user', 'tenant_id', 'user_id'),
        sa.Index('ix_notification_user_read', 'user_id', 'is_read'),
        sa.Index('ix_notification_type', 'notification_type'),
    )


def downgrade() -> None:
    op.drop_table('notifications')
