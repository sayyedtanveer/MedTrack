"""Add work_order_lines table and backfill from existing single-product work orders.

Also adds nullable work_order_line_id FK to work_order_materials and job_cards
so that per-line material/operation tracking can be introduced gradually without
breaking existing single-product Work Orders.

Idempotent — safe to run on a database that already has these structures.

Revision ID: c5d9f2b1e8a3
Revises: b3f8e1a2c9d4
Create Date: 2026-09-26 14:00:00.000000
"""
from __future__ import annotations

import uuid as _uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

revision: str = "c5d9f2b1e8a3"
down_revision = "b3f8e1a2c9d4"
branch_labels = None
depends_on = None


# ── helpers ───────────────────────────────────────────────────────────────────

def _table_exists(conn, name: str) -> bool:
    return name in Inspector.from_engine(conn).get_table_names()


def _column_exists(conn, table: str, col: str) -> bool:
    return col in [c["name"] for c in Inspector.from_engine(conn).get_columns(table)]


def _fk_exists(conn, table: str, fk_name: str) -> bool:
    return any(
        fk.get("name") == fk_name
        for fk in Inspector.from_engine(conn).get_foreign_keys(table)
    )


# ── upgrade ───────────────────────────────────────────────────────────────────

def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Create work_order_lines ────────────────────────────────────────────
    if not _table_exists(conn, "work_order_lines"):
        op.create_table(
            "work_order_lines",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("bom_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("planned_quantity", sa.Numeric(15, 3), nullable=False),
            sa.Column("produced_quantity", sa.Numeric(15, 3), nullable=False,
                      server_default=sa.text("0")),
            sa.Column("scrap_quantity", sa.Numeric(15, 3), nullable=False,
                      server_default=sa.text("0")),
            sa.Column("status", sa.String(50), nullable=False, server_default="PLANNED"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True), nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["work_order_id"], ["work_orders.id"], ondelete="CASCADE",
                name="fk_wo_line_work_order",
            ),
            sa.ForeignKeyConstraint(
                ["product_id"], ["item_variants.id"], ondelete="RESTRICT",
                name="fk_wo_line_product",
            ),
            sa.ForeignKeyConstraint(
                ["bom_id"], ["boms.id"], ondelete="RESTRICT",
                name="fk_wo_line_bom",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_work_order_lines_work_order_id", "work_order_lines", ["work_order_id"])
        op.create_index("ix_work_order_lines_tenant_id", "work_order_lines", ["tenant_id"])

        # ── 2. Backfill: create one line per existing single-product WO ───────
        # Only needed when the table was freshly created (i.e. no prior data).
        # We use raw SQL to avoid model import issues during migration.
        conn.execute(sa.text("""
            INSERT INTO work_order_lines
                (id, work_order_id, tenant_id, product_id, bom_id,
                 planned_quantity, produced_quantity, scrap_quantity,
                 status, is_deleted, created_at, updated_at)
            SELECT
                gen_random_uuid(),
                id,
                tenant_id,
                product_id,
                bom_id,
                planned_quantity,
                produced_quantity,
                scrap_quantity,
                status,
                is_deleted,
                created_at,
                updated_at
            FROM work_orders
            WHERE is_deleted = false
        """))

    # ── 3. Add work_order_line_id to work_order_materials ────────────────────
    if not _column_exists(conn, "work_order_materials", "work_order_line_id"):
        op.add_column(
            "work_order_materials",
            sa.Column("work_order_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        if not _fk_exists(conn, "work_order_materials", "fk_wo_mat_line"):
            op.create_foreign_key(
                "fk_wo_mat_line",
                "work_order_materials",
                "work_order_lines",
                ["work_order_line_id"],
                ["id"],
                ondelete="SET NULL",
            )

    # ── 4. Add work_order_line_id to job_cards ────────────────────────────────
    if not _column_exists(conn, "job_cards", "work_order_line_id"):
        op.add_column(
            "job_cards",
            sa.Column("work_order_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        if not _fk_exists(conn, "job_cards", "fk_job_card_line"):
            op.create_foreign_key(
                "fk_job_card_line",
                "job_cards",
                "work_order_lines",
                ["work_order_line_id"],
                ["id"],
                ondelete="SET NULL",
            )


# ── downgrade ─────────────────────────────────────────────────────────────────

def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, "job_cards", "work_order_line_id"):
        if _fk_exists(conn, "job_cards", "fk_job_card_line"):
            op.drop_constraint("fk_job_card_line", "job_cards", type_="foreignkey")
        op.drop_column("job_cards", "work_order_line_id")

    if _column_exists(conn, "work_order_materials", "work_order_line_id"):
        if _fk_exists(conn, "work_order_materials", "fk_wo_mat_line"):
            op.drop_constraint("fk_wo_mat_line", "work_order_materials", type_="foreignkey")
        op.drop_column("work_order_materials", "work_order_line_id")

    if _table_exists(conn, "work_order_lines"):
        op.drop_table("work_order_lines")
