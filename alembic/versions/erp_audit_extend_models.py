"""Extend models for manufacturing ERP audit: SO dates, SO line dispatch tracking,
WO hold fields, delivery cancellation fields.

Revision ID: erp_audit_extend_models
Revises: add_purchase_requisitions
Create Date: 2026-06-01

Requirements: 19.3, 20.1, 20.3, 26.2, 28.1, 33.3
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "erp_audit_extend_models"
down_revision = "add_purchase_requisitions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- SalesOrderModel: estimated dates for order tracking (Req 28.1) ---
    op.add_column(
        "sales_orders",
        sa.Column("estimated_completion_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("expected_dispatch_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
    )

    # --- SalesOrderLineModel: dispatch tracking (Req 19.3, 20.1, 20.3) ---
    op.add_column(
        "sales_order_lines",
        sa.Column(
            "dispatched_quantity",
            sa.Numeric(precision=18, scale=4),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "sales_order_lines",
        sa.Column(
            "line_status",
            sa.String(length=30),
            nullable=False,
            server_default="PENDING",
        ),
    )

    # --- WorkOrderModel: production hold tracking (Req 26.2) ---
    op.add_column(
        "work_orders",
        sa.Column("hold_reason", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "work_orders",
        sa.Column(
            "hold_started_at", sa.DateTime(timezone=True), nullable=True
        ),
    )

    # --- DeliveryOrderModel: cancellation fields (Req 33.3) ---
    op.add_column(
        "delivery_orders",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "delivery_orders",
        sa.Column(
            "cancelled_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "delivery_orders",
        sa.Column(
            "cancellation_reason", sa.String(length=500), nullable=True
        ),
    )


def downgrade() -> None:
    # --- DeliveryOrderModel ---
    op.drop_column("delivery_orders", "cancellation_reason")
    op.drop_column("delivery_orders", "cancelled_by")
    op.drop_column("delivery_orders", "cancelled_at")

    # --- WorkOrderModel ---
    op.drop_column("work_orders", "hold_started_at")
    op.drop_column("work_orders", "hold_reason")

    # --- SalesOrderLineModel ---
    op.drop_column("sales_order_lines", "line_status")
    op.drop_column("sales_order_lines", "dispatched_quantity")

    # --- SalesOrderModel ---
    op.drop_column("sales_orders", "expected_delivery_date")
    op.drop_column("sales_orders", "expected_dispatch_date")
    op.drop_column("sales_orders", "estimated_completion_date")
