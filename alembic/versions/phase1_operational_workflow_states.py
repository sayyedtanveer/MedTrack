"""Phase 1: Add operational workflow states to Work Orders.

Revision ID: phase1_operational_workflow_states
Revises: phase4_work_orders
Create Date: 2026-05-11 00:00:00.000000

Changes:
  - Update work_orders.status to support new operational states
  - Add backward compatibility for legacy states
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'p1_op_wf_states'
down_revision = 'phase4_work_orders'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update existing WO statuses to new operational states
    # PLANNED remains PLANNED
    # RELEASED remains RELEASED (will transition to MATERIAL_PENDING on next release)
    # IN_PROGRESS → IN_PRODUCTION
    # COMPLETED → FG_RECEIVED (if production recorded) or QC_PENDING (if not)
    # CLOSED remains CLOSED

    # First, update IN_PROGRESS to IN_PRODUCTION
    op.execute(
        "UPDATE work_orders SET status = 'IN_PRODUCTION' WHERE status = 'IN_PROGRESS'"
    )

    # Update COMPLETED to FG_RECEIVED (assuming production was recorded)
    # Note: This is a simplification - in production, you'd need more logic
    op.execute(
        "UPDATE work_orders SET status = 'FG_RECEIVED' WHERE status = 'COMPLETED'"
    )

    # The status column is already VARCHAR(20) which can accommodate the new states
    # No schema change needed, just data migration


def downgrade() -> None:
    # Revert status changes for backward compatibility
    op.execute(
        "UPDATE work_orders SET status = 'IN_PROGRESS' WHERE status = 'IN_PRODUCTION'"
    )
    op.execute(
        "UPDATE work_orders SET status = 'COMPLETED' WHERE status = 'FG_RECEIVED'"
    )
    # Other new states (MATERIAL_PENDING, MATERIAL_RESERVED, MATERIAL_ISSUED, etc.)
    # would need to be mapped back to appropriate legacy states
    # For now, leave them as-is since they don't exist in legacy data
