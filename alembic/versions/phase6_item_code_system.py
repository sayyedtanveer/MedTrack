"""Add enterprise item code metadata.

Revision ID: phase6_item_code_system
Revises: phase5_mrp_suggestions
Create Date: 2026-05-07 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "phase6_item_code_system"
down_revision = "phase5_mrp_suggestions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "material_categories",
        sa.Column("code_prefix", sa.String(length=20), nullable=False, server_default="GEN"),
    )
    op.add_column(
        "materials",
        sa.Column("code_locked", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "item_templates",
        sa.Column("code_locked", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "item_variants",
        sa.Column("code_locked", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "item_code_sequences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_type", sa.String(length=10), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("next_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["category_id"], ["material_categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "item_type", "category_id", name="uq_item_code_sequence_scope"),
    )
    op.create_index("ix_item_code_sequences_tenant", "item_code_sequences", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_item_code_sequences_tenant", table_name="item_code_sequences")
    op.drop_table("item_code_sequences")
    op.drop_column("item_variants", "code_locked")
    op.drop_column("item_templates", "code_locked")
    op.drop_column("materials", "code_locked")
    op.drop_column("material_categories", "code_prefix")
