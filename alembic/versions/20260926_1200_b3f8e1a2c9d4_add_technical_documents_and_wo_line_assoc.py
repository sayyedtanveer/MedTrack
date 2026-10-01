"""Add technical document tables and work_order_line_id to document_associations.

Creates file_attachments, technical_documents, document_revisions, and
document_associations tables if they do not already exist (idempotent).

For databases where document_associations already exists (created via
create_all), adds the work_order_line_id column and its FK if missing.

Revision ID: b3f8e1a2c9d4
Revises: a0cbf2de5265
Create Date: 2026-09-26 12:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

# revision identifiers
revision: str = "b3f8e1a2c9d4"
down_revision = (
    "add_default_price_list_to_clients",
    "add_notification_retention",
    "gap4_so_status_enum_and_constraint",
    "normalize_material_type_001",
    "p1_op_wf_states",
    "p2_inv_reservation",
)
branch_labels = None
depends_on = None


def _table_exists(conn, table_name: str) -> bool:
    inspector = Inspector.from_engine(conn)
    return table_name in inspector.get_table_names()


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    inspector = Inspector.from_engine(conn)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def _fk_exists(conn, table_name: str, fk_name: str) -> bool:
    inspector = Inspector.from_engine(conn)
    fks = inspector.get_foreign_keys(table_name)
    return any(fk.get("name") == fk_name for fk in fks)


def _index_exists(conn, table_name: str, index_name: str) -> bool:
    inspector = Inspector.from_engine(conn)
    indexes = inspector.get_indexes(table_name)
    return any(ix["name"] == index_name for ix in indexes)


def upgrade() -> None:
    conn = op.get_bind()

    # ── file_attachments ────────────────────────────────────────────────────
    if not _table_exists(conn, "file_attachments"):
        op.create_table(
            "file_attachments",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), nullable=False),
            sa.Column("content_type", sa.String(length=100), nullable=False),
            sa.Column("cloudinary_public_id", sa.String(length=500), nullable=False, unique=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_file_attachments_tenant_id", "file_attachments", ["tenant_id"])

    # ── technical_documents ─────────────────────────────────────────────────
    if not _table_exists(conn, "technical_documents"):
        op.create_table(
            "technical_documents",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("document_number", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("document_category", sa.String(length=50), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint(
                "tenant_id",
                "document_number",
                name="uq_technical_doc_tenant_number",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_technical_documents_tenant_id", "technical_documents", ["tenant_id"])

    # ── document_revisions ──────────────────────────────────────────────────
    if not _table_exists(conn, "document_revisions"):
        op.create_table(
            "document_revisions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("file_attachment_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("revision_code", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
            sa.Column("notes", sa.String(length=1000), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["document_id"], ["technical_documents.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["file_attachment_id"], ["file_attachments.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
            sa.UniqueConstraint(
                "tenant_id",
                "document_id",
                "revision_code",
                name="uq_doc_revision_code",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_document_revisions_tenant_id", "document_revisions", ["tenant_id"])

    # ── document_associations ───────────────────────────────────────────────
    if not _table_exists(conn, "document_associations"):
        op.create_table(
            "document_associations",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("revision_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("work_order_line_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "is_print_package_included",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "show_on_wo",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["revision_id"], ["document_revisions.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["work_order_id"], ["work_orders.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["work_order_line_id"],
                ["work_order_lines.id"],
                ondelete="CASCADE",
                name="fk_doc_assoc_wo_line",
            ),
            sa.ForeignKeyConstraint(
                ["variant_id"], ["item_variants.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["template_id"], ["item_templates.id"], ondelete="CASCADE"
            ),
            sa.CheckConstraint(
                "(work_order_id IS NOT NULL AND variant_id IS NULL AND template_id IS NULL) OR "
                "(work_order_id IS NULL AND variant_id IS NOT NULL AND template_id IS NULL) OR "
                "(work_order_id IS NULL AND variant_id IS NULL AND template_id IS NOT NULL)",
                name="ck_document_association_target_exactly_one",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_document_associations_tenant_id", "document_associations", ["tenant_id"]
        )
    else:
        # Table already exists (created via create_all). Add work_order_line_id if missing.
        if not _column_exists(conn, "document_associations", "work_order_line_id"):
            op.add_column(
                "document_associations",
                sa.Column(
                    "work_order_line_id",
                    postgresql.UUID(as_uuid=True),
                    nullable=True,
                ),
            )
            # Add FK only if it does not already exist
            if not _fk_exists(conn, "document_associations", "fk_doc_assoc_wo_line"):
                op.create_foreign_key(
                    "fk_doc_assoc_wo_line",
                    "document_associations",
                    "work_order_lines",
                    ["work_order_line_id"],
                    ["id"],
                    ondelete="CASCADE",
                )

        # Add show_on_wo if the table predates it
        if not _column_exists(conn, "document_associations", "show_on_wo"):
            op.add_column(
                "document_associations",
                sa.Column(
                    "show_on_wo",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("true"),
                ),
            )


def downgrade() -> None:
    conn = op.get_bind()

    # Only drop tables/columns this migration created — do not drop tables
    # that were already present before this migration ran (we can't know).
    # Safe strategy: drop columns we may have added, leave table structure
    # untouched for full downgrade safety.

    if _table_exists(conn, "document_associations"):
        if _column_exists(conn, "document_associations", "work_order_line_id"):
            if _fk_exists(conn, "document_associations", "fk_doc_assoc_wo_line"):
                op.drop_constraint(
                    "fk_doc_assoc_wo_line", "document_associations", type_="foreignkey"
                )
            op.drop_column("document_associations", "work_order_line_id")

        if _column_exists(conn, "document_associations", "show_on_wo"):
            op.drop_column("document_associations", "show_on_wo")
