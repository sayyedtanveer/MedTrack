"""Add client portal foundation tables and user client linkage.

Revision ID: 9f2c1b7d_client_portal
Revises: 67cc7ab2ca76
Create Date: 2026-03-29 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "9f2c1b7d_client_portal"
down_revision = "67cc7ab2ca76"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_users_client_id", "users", ["client_id"])
    op.create_foreign_key(
        "fk_users_client_id_sales_clients",
        "users",
        "sales_clients",
        ["client_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "client_addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("address_line1", sa.Text(), nullable=False),
        sa.Column("address_line2", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=30), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("type IN ('billing', 'shipping')", name="ck_client_addresses_type"),
        sa.ForeignKeyConstraint(["client_id"], ["sales_clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_client_addresses_tenant", "client_addresses", ["tenant_id"])
    op.create_index("ix_client_addresses_client", "client_addresses", ["client_id"])
    op.create_index("ix_client_addresses_default", "client_addresses", ["client_id", "type", "is_default"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_token_hash"),
    )
    op.create_index("ix_password_reset_user", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tenant", "password_reset_tokens", ["tenant_id"])

    op.create_table(
        "client_notification_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("order_shipped", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("order_delivered", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("invoice_overdue", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("low_credit", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("marketing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["sales_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_client_notification_settings_user"),
    )
    op.create_index("ix_client_notification_settings_tenant", "client_notification_settings", ["tenant_id"])
    op.create_index("ix_client_notification_settings_client", "client_notification_settings", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_client_notification_settings_client", table_name="client_notification_settings")
    op.drop_index("ix_client_notification_settings_tenant", table_name="client_notification_settings")
    op.drop_table("client_notification_settings")

    op.drop_index("ix_password_reset_tenant", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_user", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_index("ix_client_addresses_default", table_name="client_addresses")
    op.drop_index("ix_client_addresses_client", table_name="client_addresses")
    op.drop_index("ix_client_addresses_tenant", table_name="client_addresses")
    op.drop_table("client_addresses")

    op.drop_constraint("fk_users_client_id_sales_clients", "users", type_="foreignkey")
    op.drop_index("ix_users_client_id", table_name="users")
    op.drop_column("users", "client_id")
