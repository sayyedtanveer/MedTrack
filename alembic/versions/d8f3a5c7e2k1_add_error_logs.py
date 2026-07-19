"""add_error_logs_table

Revision ID: d8f3a5c7e2k1_add_error_logs
Revises: phase4_advanced_reporting
Create Date: 2026-04-15 10:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd8f3a5c7e2k1_add_error_logs'
down_revision = 'phase4_advanced_reporting'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create error_logs table
    op.create_table(
        'error_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('correlation_id', sa.String(36), nullable=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('path', sa.String(2048), nullable=False),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('error_code', sa.String(50), nullable=False),
        sa.Column('error_type', sa.String(255), nullable=False),
        sa.Column('error_message', sa.String(500), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('request_body', sa.Text(), nullable=True),
        sa.Column('request_body_truncated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('query_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient querying
    op.create_index('idx_error_logs_timestamp_desc', 'error_logs', ['timestamp'], unique=False)
    op.create_index('idx_error_logs_tenant_timestamp', 'error_logs', ['tenant_id', 'timestamp'], unique=False)
    op.create_index('idx_error_logs_status_timestamp', 'error_logs', ['status_code', 'timestamp'], unique=False)
    op.create_index('idx_error_logs_trace_id', 'error_logs', ['trace_id'], unique=False)
    op.create_index(op.f('ix_error_logs_trace_id'), 'error_logs', ['trace_id'], unique=False)
    op.create_index(op.f('ix_error_logs_correlation_id'), 'error_logs', ['correlation_id'], unique=False)
    op.create_index(op.f('ix_error_logs_tenant_id'), 'error_logs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_error_logs_status_code'), 'error_logs', ['status_code'], unique=False)
    op.create_index(op.f('ix_error_logs_timestamp'), 'error_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    # Drop all indexes in reverse order
    op.drop_index(op.f('ix_error_logs_timestamp'), table_name='error_logs')
    op.drop_index(op.f('ix_error_logs_status_code'), table_name='error_logs')
    op.drop_index(op.f('ix_error_logs_tenant_id'), table_name='error_logs')
    op.drop_index(op.f('ix_error_logs_correlation_id'), table_name='error_logs')
    op.drop_index(op.f('ix_error_logs_trace_id'), table_name='error_logs')
    op.drop_index('idx_error_logs_trace_id', table_name='error_logs')
    op.drop_index('idx_error_logs_status_timestamp', table_name='error_logs')
    op.drop_index('idx_error_logs_tenant_timestamp', table_name='error_logs')
    op.drop_index('idx_error_logs_timestamp_desc', table_name='error_logs')

    # Drop the table
    op.drop_table('error_logs')
