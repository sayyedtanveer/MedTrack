"""Add failed_tasks table for background task failure tracking.

Revision ID: add_failed_tasks
Revises: add_prod_indexes
Create Date: 2026-07-03

Requirements: 46.1, 46.2, 46.4, 46.5
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_failed_tasks"
down_revision = "add_prod_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "failed_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("task_name", sa.String(length=255), nullable=False, index=True),
        sa.Column("arguments_json", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=False),
        sa.Column("retry_count", sa.Integer, nullable=False, default=0),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_failed_tasks_tenant_failed_at",
        "failed_tasks",
        ["tenant_id", "failed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_failed_tasks_tenant_failed_at", table_name="failed_tasks")
    op.drop_table("failed_tasks")
