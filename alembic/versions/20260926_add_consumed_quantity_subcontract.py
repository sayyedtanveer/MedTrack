"""Add consumed_quantity to subcontract_order_lines for tracking raw material consumption.

Revision ID: 20260926_add_consumed_quantity
Revises: add_notification_retention
Create Date: 2026-09-26

Business Context:
- Subcontract orders need to track CONSUMED vs ISSUED vs RETURNED separately
- consumed_quantity tracks actual raw material consumption based on output produced
- Formula: consumed = output_received × (bom_requirement / order_output_qty)
- This field enables proper inventory accounting and prevents double-counting

See: docs/SUBCONTRACT_INVENTORY_AUDIT_AND_PLAN.md
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260926_add_consumed_quantity'
down_revision = '20260926_2000'  # Previous subcontract status fix
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add consumed_quantity column to track actual raw material consumption
    op.add_column(
        'subcontract_order_lines',
        sa.Column(
            'consumed_quantity',
            sa.Numeric(precision=15, scale=3),
            nullable=False,
            server_default='0'
        )
    )
    
    # Note: Historical records will have consumed_quantity=0
    # This is intentional - we do NOT backfill historical consumption
    # as it cannot be reliably determined from existing data


def downgrade() -> None:
    op.drop_column('subcontract_order_lines', 'consumed_quantity')
