"""Add procurement pricing workflow and PO price metadata.

Revision ID: e06307f2f932
Revises: c84cb0239a28
Create Date: 2026-11-10 19:39:30.504112
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e06307f2f932"
down_revision: str | None = "c84cb0239a28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchase_orders",
        sa.Column("currency_code", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "purchase_order_lines",
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_purchase_order_lines_unit_id",
        "purchase_order_lines",
        "units_of_measure",
        ["unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column(
        "supplier_quotations",
        sa.Column("currency_code", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "supplier_quotations",
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_supplier_quotations_unit_id",
        "supplier_quotations",
        "units_of_measure",
        ["unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column(
        "supplier_price_history",
        sa.Column("grn_line_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "supplier_price_history",
        sa.Column("currency_code", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "supplier_price_history",
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_supplier_price_history_grn_line_id",
        "supplier_price_history",
        "grn_lines",
        ["grn_line_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_supplier_price_history_unit_id",
        "supplier_price_history",
        "units_of_measure",
        ["unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_supplier_price_history_grn_line",
        "supplier_price_history",
        ["tenant_id", "grn_line_id"],
    )

    op.create_table(
        "supplier_price_agreements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("base_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("purchase_uom_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("minimum_order_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("quantity_tier", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["purchase_uom_id"], ["units_of_measure.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supplier_price_agreements_tenant_id",
        "supplier_price_agreements",
        ["tenant_id"],
    )
    op.create_index(
        "ix_supplier_price_agreements_is_deleted",
        "supplier_price_agreements",
        ["is_deleted"],
    )
    op.create_index(
        "ix_supplier_price_agreements_status",
        "supplier_price_agreements",
        ["status"],
    )
    op.create_index(
        "ix_supplier_price_agreements_supplier_id",
        "supplier_price_agreements",
        ["supplier_id"],
    )
    op.create_index(
        "ix_supplier_price_agreements_material_id",
        "supplier_price_agreements",
        ["material_id"],
    )
    op.create_index(
        "ix_supplier_price_agreements_effective_from",
        "supplier_price_agreements",
        ["effective_from"],
    )

    op.create_table(
        "material_cost_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_cost", sa.Numeric(18, 6), nullable=True),
        sa.Column("new_cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("change_type", sa.String(length=30), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_material_cost_history_tenant_id", "material_cost_history", ["tenant_id"])
    op.create_index("ix_material_cost_history_material_id", "material_cost_history", ["material_id"])
    op.create_index("ix_material_cost_history_change_type", "material_cost_history", ["change_type"])
    op.create_index("ix_material_cost_history_created_at", "material_cost_history", ["created_at"])

    op.create_table(
        "standard_cost_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("current_cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("variance_percent", sa.Numeric(8, 2), nullable=True),
        sa.Column("reason", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_standard_cost_revisions_tenant_id", "standard_cost_revisions", ["tenant_id"])
    op.create_index("ix_standard_cost_revisions_material_id", "standard_cost_revisions", ["material_id"])
    op.create_index("ix_standard_cost_revisions_status", "standard_cost_revisions", ["status"])
    op.create_index("ix_standard_cost_revisions_requested_by", "standard_cost_revisions", ["requested_by"])
    op.create_index("ix_standard_cost_revisions_approved_by", "standard_cost_revisions", ["approved_by"])
    op.create_index("ix_standard_cost_revisions_created_at", "standard_cost_revisions", ["created_at"])

    op.create_table(
        "price_override_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("purchase_order_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("grn_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("suggested_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("override_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("variance_percent", sa.Numeric(8, 2), nullable=True),
        sa.Column("override_reason", sa.String(length=50), nullable=True),
        sa.Column("pricing_source", sa.String(length=40), nullable=True),
        sa.Column("currency_code", sa.String(length=3), nullable=True),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("override_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["purchase_order_line_id"], ["purchase_order_lines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["grn_id"], ["goods_receipt_notes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units_of_measure.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["override_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_price_override_records_tenant_id", "price_override_records", ["tenant_id"])
    op.create_index("ix_price_override_records_material_id", "price_override_records", ["material_id"])
    op.create_index("ix_price_override_records_grn_id", "price_override_records", ["grn_id"])
    op.create_index("ix_price_override_records_purchase_order_line_id", "price_override_records", ["purchase_order_line_id"])
    op.create_index("ix_price_override_records_override_by", "price_override_records", ["override_by"])
    op.create_index("ix_price_override_records_created_at", "price_override_records", ["created_at"])

    op.execute(
        """
        CREATE FUNCTION prevent_material_cost_history_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'material_cost_history is append-only; add a reversal entry';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_material_cost_history_append_only
        BEFORE UPDATE OR DELETE ON material_cost_history
        FOR EACH ROW EXECUTE FUNCTION prevent_material_cost_history_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_material_cost_history_append_only ON material_cost_history")
    op.execute("DROP FUNCTION IF EXISTS prevent_material_cost_history_mutation()")

    op.drop_index("ix_price_override_records_created_at", table_name="price_override_records")
    op.drop_index("ix_price_override_records_override_by", table_name="price_override_records")
    op.drop_index("ix_price_override_records_purchase_order_line_id", table_name="price_override_records")
    op.drop_index("ix_price_override_records_grn_id", table_name="price_override_records")
    op.drop_index("ix_price_override_records_material_id", table_name="price_override_records")
    op.drop_index("ix_price_override_records_tenant_id", table_name="price_override_records")
    op.drop_table("price_override_records")

    op.drop_index("ix_standard_cost_revisions_created_at", table_name="standard_cost_revisions")
    op.drop_index("ix_standard_cost_revisions_approved_by", table_name="standard_cost_revisions")
    op.drop_index("ix_standard_cost_revisions_requested_by", table_name="standard_cost_revisions")
    op.drop_index("ix_standard_cost_revisions_status", table_name="standard_cost_revisions")
    op.drop_index("ix_standard_cost_revisions_material_id", table_name="standard_cost_revisions")
    op.drop_index("ix_standard_cost_revisions_tenant_id", table_name="standard_cost_revisions")
    op.drop_table("standard_cost_revisions")

    op.drop_index("ix_material_cost_history_created_at", table_name="material_cost_history")
    op.drop_index("ix_material_cost_history_change_type", table_name="material_cost_history")
    op.drop_index("ix_material_cost_history_material_id", table_name="material_cost_history")
    op.drop_index("ix_material_cost_history_tenant_id", table_name="material_cost_history")
    op.drop_table("material_cost_history")

    op.drop_index("ix_supplier_price_agreements_effective_from", table_name="supplier_price_agreements")
    op.drop_index("ix_supplier_price_agreements_material_id", table_name="supplier_price_agreements")
    op.drop_index("ix_supplier_price_agreements_supplier_id", table_name="supplier_price_agreements")
    op.drop_index("ix_supplier_price_agreements_status", table_name="supplier_price_agreements")
    op.drop_index("ix_supplier_price_agreements_is_deleted", table_name="supplier_price_agreements")
    op.drop_index("ix_supplier_price_agreements_tenant_id", table_name="supplier_price_agreements")
    op.drop_table("supplier_price_agreements")

    op.drop_constraint("uq_supplier_price_history_grn_line", "supplier_price_history", type_="unique")
    op.drop_constraint("fk_supplier_price_history_unit_id", "supplier_price_history", type_="foreignkey")
    op.drop_constraint("fk_supplier_price_history_grn_line_id", "supplier_price_history", type_="foreignkey")
    op.drop_column("supplier_price_history", "unit_id")
    op.drop_column("supplier_price_history", "currency_code")
    op.drop_column("supplier_price_history", "grn_line_id")

    op.drop_constraint("fk_supplier_quotations_unit_id", "supplier_quotations", type_="foreignkey")
    op.drop_column("supplier_quotations", "unit_id")
    op.drop_column("supplier_quotations", "currency_code")

    op.drop_constraint("fk_purchase_order_lines_unit_id", "purchase_order_lines", type_="foreignkey")
    op.drop_column("purchase_order_lines", "unit_id")
    op.drop_column("purchase_orders", "currency_code")
