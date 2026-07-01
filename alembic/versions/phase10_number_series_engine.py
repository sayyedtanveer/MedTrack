"""Add Number Series Engine tables.

Creates number_series_config, number_series_prefixes, number_series_sequences,
and number_series_audit_log tables for the generic Number Series Engine.
Does NOT modify or drop the existing item_code_sequences table.

Revision ID: phase10_number_series
Revises: a62c0f8c9545, add_missing_columns_materials, final_merge
Create Date: 2026-06-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "phase10_number_series"
down_revision = ("a62c0f8c9545", "add_missing_columns_materials", "final_merge")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- number_series_config ---
    op.create_table(
        "number_series_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("auto_generate", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("manual_override", sa.String(length=20), nullable=False, server_default="never"),
        sa.Column("prefix", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("include_abbreviation", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("abbreviation_length", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("sequence_length", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("separator", sa.String(length=5), nullable=False, server_default="-"),
        sa.Column("lock_after_save", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "entity_type", name="uq_number_series_config_tenant_entity"),
    )

    # --- number_series_prefixes ---
    op.create_table(
        "number_series_prefixes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("sub_type", sa.String(length=30), nullable=False),
        sa.Column("prefix", sa.String(length=10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "entity_type", "sub_type",
            name="uq_ns_prefix_tenant_entity_subtype",
        ),
    )

    # --- number_series_sequences ---
    op.create_table(
        "number_series_sequences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("prefix", sa.String(length=20), nullable=False),
        sa.Column("next_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "entity_type", "prefix", name="uq_ns_sequence_scope"),
    )
    op.create_index("ix_ns_sequences_tenant", "number_series_sequences", ["tenant_id"])

    # --- number_series_audit_log ---
    op.create_table(
        "number_series_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generated_code", sa.String(length=50), nullable=True),
        sa.Column("old_value", sa.String(length=500), nullable=True),
        sa.Column("new_value", sa.String(length=500), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("metadata_json", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ns_audit_log_tenant", "number_series_audit_log", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_ns_audit_log_tenant", table_name="number_series_audit_log")
    op.drop_table("number_series_audit_log")
    op.drop_index("ix_ns_sequences_tenant", table_name="number_series_sequences")
    op.drop_table("number_series_sequences")
    op.drop_table("number_series_prefixes")
    op.drop_table("number_series_config")
