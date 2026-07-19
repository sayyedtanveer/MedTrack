"""raw material onboarding models and fields

Revision ID: raw_material_onboarding
Revises: shop_floor_execution_metrics
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "raw_material_onboarding"
down_revision = "shop_floor_execution_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for col in [
        sa.Column("barcode", sa.String(length=120), nullable=True),
        sa.Column("traceability_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("batch_rule", sa.String(length=20), nullable=True),
        sa.Column("expiry_tracking", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("shelf_life_days", sa.Integer(), nullable=True),
        sa.Column("quarantine_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cuttable_inventory", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("remaining_quantity_tracking", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reusable_remainder", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("decimal_precision", sa.Integer(), nullable=True),
        sa.Column("supplier_item_code", sa.String(length=120), nullable=True),
        sa.Column("purchase_uom", sa.String(length=40), nullable=True),
        sa.Column("min_stock", sa.Numeric(18, 4), nullable=True),
        sa.Column("max_stock", sa.Numeric(18, 4), nullable=True),
        sa.Column("reorder_quantity", sa.Numeric(18, 4), nullable=True),
        sa.Column("moq", sa.Numeric(18, 4), nullable=True),
    ]:
        op.add_column("materials", col)

    op.create_table(
        "material_onboarding_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("protected_changes_confirmed", sa.Boolean(), nullable=False),
        sa.Column("original_headers_json", sa.Text(), nullable=False),
        sa.Column("mapping_json", sa.Text(), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "material_onboarding_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("material_onboarding_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("normalized_json", sa.Text(), nullable=False),
        sa.Column("validation_json", sa.Text(), nullable=False),
        sa.Column("protected_changes_json", sa.Text(), nullable=False),
        sa.Column("classification", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("result_material_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "material_import_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("mapping_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "material_onboarding_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("defaults_json", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("material_onboarding_profiles")
    op.drop_table("material_import_mappings")
    op.drop_table("material_onboarding_rows")
    op.drop_table("material_onboarding_sessions")
    for name in [
        "moq", "reorder_quantity", "max_stock", "min_stock", "purchase_uom", "supplier_item_code",
        "decimal_precision", "reusable_remainder", "remaining_quantity_tracking", "cuttable_inventory",
        "quarantine_required", "shelf_life_days", "expiry_tracking", "batch_rule", "traceability_enabled", "barcode",
    ]:
        op.drop_column("materials", name)
