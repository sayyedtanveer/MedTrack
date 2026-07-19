"""Gap #4 — Widen sales_orders.status column to accommodate all SO lifecycle states.

The `status` column was VARCHAR(20); the canonical lifecycle now includes states up to
18 characters (`READY_FOR_DISPATCH`).  Widening to VARCHAR(32) gives headroom for all
current and near-future states without breaking any existing data.

No data migration is required: all existing status values are ≤ 20 characters and will
continue to be valid after the column is widened.

New lifecycle values added (domain layer already supported them as Python enum members):
  CONFIRMED → READY_FOR_DISPATCH   (Gap #4 — FG fully reserved)
  DELIVERED → INVOICED             (Gap #7 — auto-invoice trigger)
  INVOICED → PAYMENT_RECEIVED      (Gap #4)
  PAYMENT_RECEIVED → COMPLETED     (Gap #4 / Gap #10)

Also adds a composite index `idx_sales_orders_tenant_status` recommended in the
design document for dispatch-queue and dashboard queries.

Revision ID: gap4_so_status_enum_and_constraint
Revises: erp_audit_extend_models
Create Date: 2026-06-10

Requirements: 15, 32, 37, 40 — Gap #4
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "gap4_so_status_enum_and_constraint"
down_revision: str = "erp_audit_extend_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Widen the status column so VARCHAR(20) → VARCHAR(32).
    # READY_FOR_DISPATCH (18 chars) is the longest new value; 32 gives future headroom.
    op.alter_column(
        "sales_orders",
        "status",
        existing_type=sa.String(20),
        type_=sa.String(32),
        existing_nullable=False,
    )

    # Composite index for dispatch-queue and dashboard queries (design doc spec).
    # Use `if_not_exists`-style try/except to make the migration idempotent on
    # databases that already have the index from manual scripts.
    try:
        op.create_index(
            "idx_sales_orders_tenant_status",
            "sales_orders",
            ["tenant_id", "status"],
        )
    except Exception:
        pass  # Index already exists — no-op


def downgrade() -> None:
    # Drop the index first, then narrow the column back.
    try:
        op.drop_index("idx_sales_orders_tenant_status", table_name="sales_orders")
    except Exception:
        pass

    op.alter_column(
        "sales_orders",
        "status",
        existing_type=sa.String(32),
        type_=sa.String(20),
        existing_nullable=False,
    )
