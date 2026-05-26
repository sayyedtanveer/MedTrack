"""Operational hardening: consumption records, batch fields, material dimensions, pick lists.

Revision ID: operational_hardening_consumption
Revises: operational_hardening_wo_status
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "op_hard_consumption"
down_revision = "operational_hardening_wo_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "material_consumption_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("production_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("production_records.id", ondelete="SET NULL"), nullable=True),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("planned_quantity", sa.Numeric(15, 3), nullable=False, server_default="0"),
        sa.Column("actual_quantity", sa.Numeric(15, 3), nullable=False, server_default="0"),
        sa.Column("variance_quantity", sa.Numeric(15, 3), nullable=False, server_default="0"),
        sa.Column("scrap_quantity", sa.Numeric(15, 3), nullable=False, server_default="0"),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("remarks", sa.String(500), nullable=True),
    )
    op.create_index("ix_mcr_tenant_wo", "material_consumption_records", ["tenant_id", "work_order_id"])

    op.add_column("inventory_transactions", sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_inventory_transactions_batch_id",
        "inventory_transactions",
        "batches",
        ["batch_id"],
        ["id"],
    )
    op.create_index(
        "uq_inv_tx_fg_receipt_once",
        "inventory_transactions",
        ["tenant_id", "material_id", "reference_type", "reference_id", "transaction_type"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false AND transaction_type = 'FG_RECEIPT'"),
        sqlite_where=sa.text("is_deleted = 0 AND transaction_type = 'FG_RECEIPT'"),
    )

    op.add_column("inventory_reservations", sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "inventory_reservations",
        sa.Column("returned_quantity", sa.Numeric(15, 3), nullable=False, server_default="0"),
    )
    op.create_foreign_key(
        "fk_inventory_reservations_batch_id",
        "inventory_reservations",
        "batches",
        ["batch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_ir_tenant_batch", "inventory_reservations", ["tenant_id", "batch_id"])

    op.add_column("materials", sa.Column("length_uom", sa.String(20), nullable=True))
    op.add_column("materials", sa.Column("length_per_unit", sa.Numeric(15, 3), nullable=True))
    op.add_column("materials", sa.Column("weight_per_unit", sa.Numeric(15, 3), nullable=True))
    op.add_column("materials", sa.Column("dimension_spec", sa.JSON(), nullable=True))
    op.add_column("materials", sa.Column("preferred_supplier_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("materials", sa.Column("hazardous_flag", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("materials", sa.Column("qc_required_flag", sa.Boolean(), nullable=False, server_default="false"))

    op.add_column("batches", sa.Column("original_quantity", sa.Numeric(18, 4), nullable=True))
    op.add_column("batches", sa.Column("reserved_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"))
    op.add_column("batches", sa.Column("consumed_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"))
    op.add_column("batches", sa.Column("returned_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"))
    op.execute("UPDATE batches SET original_quantity = quantity WHERE original_quantity IS NULL")

    op.create_table(
        "pick_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pick_list_number", sa.String(40), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "pick_list_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pick_list_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pick_lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(15, 3), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("pick_list_lines")
    op.drop_table("pick_lists")
    for col in ("returned_quantity", "consumed_quantity", "reserved_quantity", "original_quantity"):
        op.drop_column("batches", col)
    for col in ("qc_required_flag", "hazardous_flag", "preferred_supplier_id", "dimension_spec", "weight_per_unit", "length_per_unit", "length_uom"):
        op.drop_column("materials", col)
    op.drop_index("ix_ir_tenant_batch", table_name="inventory_reservations")
    op.drop_constraint("fk_inventory_reservations_batch_id", "inventory_reservations", type_="foreignkey")
    op.drop_column("inventory_reservations", "returned_quantity")
    op.drop_column("inventory_reservations", "batch_id")
    op.drop_index("uq_inv_tx_fg_receipt_once", table_name="inventory_transactions")
    op.drop_constraint("fk_inventory_transactions_batch_id", "inventory_transactions", type_="foreignkey")
    op.drop_column("inventory_transactions", "batch_id")
    op.drop_table("material_consumption_records")
