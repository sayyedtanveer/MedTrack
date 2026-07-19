"""Widen work_orders.status for full operational state machine.

Revision ID: operational_hardening_wo_status
Revises: phase9_notifications
"""
from alembic import op
import sqlalchemy as sa


revision = "operational_hardening_wo_status"
down_revision = "phase9_notifications"
branch_labels = None
depends_on = None

_ALL_STATUSES = (
    "PLANNED", "RELEASED", "MATERIAL_PENDING", "MATERIAL_RESERVED", "MATERIAL_ISSUED",
    "IN_PRODUCTION", "QC_PENDING", "QC_APPROVED", "QC_REJECTED", "FG_RECEIVED",
    "COMPLETED", "CLOSED", "REWORK", "REJECTED",
    # Legacy values mapped on upgrade
    "IN_PROGRESS",
)


def upgrade() -> None:
  # Map legacy statuses before constraint change
    op.execute(
        "UPDATE work_orders SET status = 'IN_PRODUCTION' WHERE status = 'IN_PROGRESS'"
    )
    op.execute(
        "UPDATE work_orders SET status = 'QC_PENDING' WHERE status = 'COMPLETED' "
        "AND produced_quantity > 0"
    )
    op.execute(
        "UPDATE work_orders SET status = 'FG_RECEIVED' WHERE status = 'COMPLETED' "
        "AND produced_quantity = 0"
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE work_orders DROP CONSTRAINT IF EXISTS ck_work_order_status")
        op.execute(
            "ALTER TABLE work_orders ALTER COLUMN status TYPE VARCHAR(32) "
            "USING status::text"
        )
        op.execute("DROP TYPE IF EXISTS work_order_status")
    else:
        # SQLite: recreate check via batch if needed; status is often plain text already
        try:
            op.drop_constraint("ck_work_order_status", "work_orders", type_="check")
        except Exception:
            pass

    statuses_sql = ", ".join(f"'{s}'" for s in _ALL_STATUSES if s != "IN_PROGRESS")
    op.create_check_constraint(
        "ck_work_order_status",
        "work_orders",
        f"status IN ({statuses_sql})",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE work_orders SET status = 'IN_PROGRESS' WHERE status = 'IN_PRODUCTION'"
    )
    op.drop_constraint("ck_work_order_status", "work_orders", type_="check")
    op.create_check_constraint(
        "ck_work_order_status",
        "work_orders",
        "status IN ('PLANNED','RELEASED','IN_PROGRESS','COMPLETED','CLOSED')",
    )
