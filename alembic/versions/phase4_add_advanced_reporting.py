"""add_advanced_reporting_analytics_tables

Revision ID: phase4_advanced_reporting
Revises: 2fa_add_auth_enhancements
Create Date: 2026-04-14 14:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'phase4_advanced_reporting'
down_revision = '2fa_add_auth_enhancements'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create saved_reports table
    op.create_table(
        'saved_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column(
            'query_config',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{"metrics": [], "filters": {}, "grouping": null, "sort_by": null, "sort_direction": "asc", "limit": 1000}'
        ),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_saved_reports_tenant_id'), 'saved_reports', ['tenant_id'], unique=False)

    # Create report_schedules table
    op.create_table(
        'report_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('schedule_type', sa.String(50), nullable=False),
        sa.Column('schedule_time', sa.String(5), nullable=False),
        sa.Column('day_of_week', sa.String(20), nullable=True),
        sa.Column('day_of_month', sa.Integer(), nullable=True),
        sa.Column('recipients', postgresql.ARRAY(sa.String()), nullable=True, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_executed_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['report_id'], ['saved_reports.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_report_schedules_tenant_id'), 'report_schedules', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_report_schedules_report_id'), 'report_schedules', ['report_id'], unique=False)

    # Create report_executions table
    op.create_table(
        'report_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('executed_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('export_format', sa.String(20), nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('file_url', sa.String(500), nullable=True),
        sa.Column('file_size_kb', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['executed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['report_id'], ['saved_reports.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_report_executions_tenant_id'), 'report_executions', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_report_executions_report_id'), 'report_executions', ['report_id'], unique=False)
    op.create_index(op.f('ix_report_executions_created_at'), 'report_executions', ['created_at'], unique=False)

    # Create dashboard_metrics table
    op.create_table(
        'dashboard_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_key', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('period_start', sa.String(10), nullable=False),
        sa.Column('period_end', sa.String(10), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cached_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'metric_key', 'period_start', 'period_end', name='uq_dashboard_metrics_key_period')
    )
    op.create_index(op.f('ix_dashboard_metrics_tenant_id'), 'dashboard_metrics', ['tenant_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_dashboard_metrics_tenant_id'), table_name='dashboard_metrics')
    op.drop_table('dashboard_metrics')
    
    op.drop_index(op.f('ix_report_executions_created_at'), table_name='report_executions')
    op.drop_index(op.f('ix_report_executions_report_id'), table_name='report_executions')
    op.drop_index(op.f('ix_report_executions_tenant_id'), table_name='report_executions')
    op.drop_table('report_executions')
    
    op.drop_index(op.f('ix_report_schedules_report_id'), table_name='report_schedules')
    op.drop_index(op.f('ix_report_schedules_tenant_id'), table_name='report_schedules')
    op.drop_table('report_schedules')
    
    op.drop_index(op.f('ix_saved_reports_tenant_id'), table_name='saved_reports')
    op.drop_table('saved_reports')
