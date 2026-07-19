"""Persist MRP purchase suggestions.

Revision ID: phase5_mrp_suggestions
Revises: phase4_work_orders
Create Date: 2026-05-07 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "phase5_mrp_suggestions"
down_revision = "phase4_work_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mrp_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_code", sa.String(length=100), nullable=False),
        sa.Column("material_name", sa.String(length=255), nullable=False),
        sa.Column("gross_requirement", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("current_stock", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("open_po_qty", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("reserved_stock", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("net_requirement", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("suggested_qty", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("lead_time_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("order_by_date", sa.Date(), nullable=False),
        sa.Column("need_by_date", sa.Date(), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supplier_name", sa.String(length=255), nullable=False, server_default="Unknown"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("po_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mrp_suggestions_tenant_status", "mrp_suggestions", ["tenant_id", "status"])
    op.create_index("ix_mrp_suggestions_tenant_material", "mrp_suggestions", ["tenant_id", "material_id"])
    op.create_index("ix_mrp_suggestions_created_at", "mrp_suggestions", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_mrp_suggestions_created_at", table_name="mrp_suggestions")
    op.drop_index("ix_mrp_suggestions_tenant_material", table_name="mrp_suggestions")
    op.drop_index("ix_mrp_suggestions_tenant_status", table_name="mrp_suggestions")
    op.drop_table("mrp_suggestions")
