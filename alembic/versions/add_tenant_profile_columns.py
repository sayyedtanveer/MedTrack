"""Add timezone and default_warehouse_name columns to tenants table.

Both columns are nullable with no default value and no data backfill required.
This unblocks the Company Profile write API (REQ-008) which needs to persist
timezone (IANA string) and default_warehouse_name (single-facility label) on
the tenant record.

Revision ID: add_tenant_profile_columns
Revises: gap4_so_status_enum_and_constraint
Create Date: 2026-06-12

Requirements: REQ-009
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_tenant_profile_columns"
down_revision: str = "gap4_so_status_enum_and_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("timezone", sa.String(100), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("default_warehouse_name", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "default_warehouse_name")
    op.drop_column("tenants", "timezone")
