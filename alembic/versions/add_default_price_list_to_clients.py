"""Add default_price_list_id to sales_clients.

Revision ID: add_default_price_list_to_clients
Revises: add_tenant_profile_columns
Create Date: 2026-06-04 00:00:00.000000

Addresses: REQ-SP-003, REQ-SP-007 AC1-AC3
Schema change: nullable FK column sales_clients.default_price_list_id → sales_price_lists.id
No data change — existing rows default to NULL.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_default_price_list_to_clients"
down_revision: str = "add_tenant_profile_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sales_clients",
        sa.Column(
            "default_price_list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sales_price_lists.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_sales_clients_default_price_list_id",
        "sales_clients",
        ["default_price_list_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sales_clients_default_price_list_id",
        table_name="sales_clients",
    )
    op.drop_column("sales_clients", "default_price_list_id")
